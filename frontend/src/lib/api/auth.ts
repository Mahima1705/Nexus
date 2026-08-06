import { apiFetch } from "@/lib/api/client";
import type { LoginRequest, RegisterRequest, Token, User } from "@/types/auth";

export const authApi = {
  register: (payload: RegisterRequest) =>
    apiFetch<User>("/auth/register", { method: "POST", body: payload, skipAuth: true }),

  login: (payload: LoginRequest) =>
    apiFetch<Token>("/auth/login", { method: "POST", body: payload, skipAuth: true }),

  refresh: (refresh_token: string) =>
    apiFetch<Token>("/auth/refresh", { method: "POST", body: { refresh_token }, skipAuth: true }),

  logout: (refresh_token: string) =>
    apiFetch<void>("/auth/logout", { method: "POST", body: { refresh_token } }),

  me: () => apiFetch<User>("/users/me"),
};
