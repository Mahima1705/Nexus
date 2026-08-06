import { useAuthStore } from "@/lib/store/auth-store";
import type { ApiErrorBody } from "@/types/api";
import type { Token } from "@/types/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Deduplicates concurrent refresh attempts so ten simultaneous 401s don't fire
// ten separate refresh requests (which would race to rotate the same token).
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clear();
      return false;
    }
    const data: Token = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clear();
    return false;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  isFormData?: boolean;
  skipAuth?: boolean;
  /** Internal: prevents infinite refresh loops on repeated 401s. */
  retry?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, isFormData, skipAuth, retry = true, headers, ...rest } = options;

  const finalHeaders: Record<string, string> = { ...(headers as Record<string, string>) };
  if (!isFormData && body !== undefined) {
    finalHeaders["Content-Type"] = "application/json";
  }

  if (!skipAuth) {
    const { accessToken } = useAuthStore.getState();
    if (accessToken) {
      finalHeaders["Authorization"] = `Bearer ${accessToken}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
    body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && !skipAuth && retry) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const refreshed = await refreshPromise;
    if (refreshed) {
      return apiFetch<T>(path, { ...options, retry: false });
    }
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await response.json() : undefined;

  if (!response.ok) {
    const errorBody = data as ApiErrorBody | undefined;
    throw new ApiError(
      response.status,
      errorBody?.error?.code ?? "UNKNOWN_ERROR",
      errorBody?.error?.message ?? response.statusText ?? "Request failed",
      errorBody?.error?.details
    );
  }

  return data as T;
}

export interface StreamHandlers<TDone> {
  onChunk: (content: string) => void;
  onDone: (data: TDone) => void;
  onError: (message: string) => void;
}

/** Consumes a `text/event-stream` POST endpoint, parsing `{"type": "chunk"|"done"|"error", ...}`
 * events. Doesn't attempt the 401-refresh-retry apiFetch does — if the token expires mid-stream
 * the caller's onError fires and the user can just retry, which is an acceptable tradeoff for
 * the added complexity a mid-stream token swap would require.
 */
export async function apiStream<TDone>(
  path: string,
  body: unknown,
  { onChunk, onDone, onError }: StreamHandlers<TDone>
): Promise<void> {
  const { accessToken } = useAuthStore.getState();

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify(body),
    });
  } catch {
    onError("Couldn't reach the server. Please try again.");
    return;
  }

  if (!response.ok || !response.body) {
    let message = "Something went wrong.";
    try {
      const errorBody = (await response.json()) as ApiErrorBody;
      message = errorBody.error?.message ?? message;
    } catch {
      // Response wasn't JSON (e.g. a truly dead connection) — fall back to the generic message.
    }
    onError(message);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data:"));
      if (!dataLine) continue;

      const parsed = JSON.parse(dataLine.slice("data:".length).trim()) as
        | { type: "chunk"; content: string }
        | { type: "done"; message: TDone }
        | { type: "error"; message: string };

      if (parsed.type === "chunk") onChunk(parsed.content);
      else if (parsed.type === "done") onDone(parsed.message);
      else onError(parsed.message);
    }
  }
}
