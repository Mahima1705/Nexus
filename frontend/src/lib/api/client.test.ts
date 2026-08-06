import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, apiStream } from "./client";
import { useAuthStore } from "@/lib/store/auth-store";

function fakeResponse(overrides: {
  ok?: boolean;
  status?: number;
  statusText?: string;
  jsonBody?: unknown;
  headers?: Headers;
}): Response {
  return {
    ok: overrides.ok ?? true,
    status: overrides.status ?? 200,
    statusText: overrides.statusText ?? "",
    headers: overrides.headers ?? new Headers({ "content-type": "application/json" }),
    json: async () => overrides.jsonBody,
  } as Response;
}

describe("apiFetch", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, user: null, hasHydrated: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches the Authorization header when a token is present", async () => {
    useAuthStore.getState().setTokens("test-access-token", "test-refresh-token");
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(fakeResponse({ jsonBody: { ok: true } }));

    await apiFetch("/some-path");

    const [, options] = fetchMock.mock.calls[0]!;
    expect((options?.headers as Record<string, string>)["Authorization"]).toBe("Bearer test-access-token");
  });

  it("does not attach Authorization when skipAuth is true", async () => {
    useAuthStore.getState().setTokens("test-access-token", "test-refresh-token");
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(fakeResponse({ jsonBody: {} }));

    await apiFetch("/public", { skipAuth: true });

    const [, options] = fetchMock.mock.calls[0]!;
    expect((options?.headers as Record<string, string>)["Authorization"]).toBeUndefined();
  });

  it("returns parsed JSON on success", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(fakeResponse({ jsonBody: { id: 1 } }));

    const result = await apiFetch<{ id: number }>("/thing");

    expect(result).toEqual({ id: 1 });
  });

  it("throws ApiError with the server's error code/message on failure", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      fakeResponse({
        ok: false,
        status: 404,
        jsonBody: { error: { code: "NOT_FOUND", message: "Repository not found." } },
      })
    );

    await expect(apiFetch("/missing")).rejects.toMatchObject({
      status: 404,
      code: "NOT_FOUND",
      message: "Repository not found.",
    });
  });

  it("returns undefined for 204 No Content", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(fakeResponse({ status: 204, headers: new Headers() }));

    const result = await apiFetch("/deleted");

    expect(result).toBeUndefined();
  });

  it("retries once after a successful token refresh on 401", async () => {
    useAuthStore.getState().setTokens("expired-token", "valid-refresh-token");

    const fetchMock = vi.spyOn(global, "fetch");
    fetchMock
      .mockResolvedValueOnce(fakeResponse({ ok: false, status: 401, jsonBody: {} })) // original request
      .mockResolvedValueOnce(
        fakeResponse({
          jsonBody: { access_token: "new-access", refresh_token: "new-refresh", token_type: "bearer" },
        })
      ) // refresh call
      .mockResolvedValueOnce(fakeResponse({ jsonBody: { success: true } })); // retried request

    const result = await apiFetch("/protected");

    expect(result).toEqual({ success: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(useAuthStore.getState().accessToken).toBe("new-access");
  });

  it("clears the session and does not loop forever when refresh itself fails", async () => {
    useAuthStore.getState().setTokens("expired-token", "invalid-refresh-token");

    const fetchMock = vi.spyOn(global, "fetch");
    fetchMock
      .mockResolvedValueOnce(fakeResponse({ ok: false, status: 401, jsonBody: {} })) // original request
      .mockResolvedValueOnce(fakeResponse({ ok: false, status: 401, jsonBody: {} })); // failed refresh

    await expect(apiFetch("/protected")).rejects.toThrow();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});

describe("apiStream", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses chunk events then the done event", async () => {
    const encoder = new TextEncoder();
    const body = [
      `data: ${JSON.stringify({ type: "chunk", content: "Hel" })}\n\n`,
      `data: ${JSON.stringify({ type: "chunk", content: "lo" })}\n\n`,
      `data: ${JSON.stringify({ type: "done", message: { id: "m1", content: "Hello" } })}\n\n`,
    ].join("");

    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(body));
        controller.close();
      },
    });

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      body: stream,
      headers: new Headers(),
      json: async () => ({}),
    } as unknown as Response);

    const chunks: string[] = [];
    let doneMessage: unknown = null;

    await apiStream("/stream-path", { content: "hi" }, {
      onChunk: (c) => chunks.push(c),
      onDone: (m) => {
        doneMessage = m;
      },
      onError: () => {
        throw new Error("onError should not fire in this test");
      },
    });

    expect(chunks.join("")).toBe("Hello");
    expect(doneMessage).toEqual({ id: "m1", content: "Hello" });
  });

  it("calls onError with the server's message when the response is not ok", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      body: null,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ error: { code: "ERR", message: "boom" } }),
    } as unknown as Response);

    let errorMessage = "";
    await apiStream(
      "/stream-path",
      {},
      {
        onChunk: () => {},
        onDone: () => {},
        onError: (m) => {
          errorMessage = m;
        },
      }
    );

    expect(errorMessage).toBe("boom");
  });

  it("calls onError when the network request itself fails", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("network down"));

    let errorMessage = "";
    await apiStream(
      "/stream-path",
      {},
      {
        onChunk: () => {},
        onDone: () => {},
        onError: (m) => {
          errorMessage = m;
        },
      }
    );

    expect(errorMessage).toContain("Couldn't reach the server");
  });
});
