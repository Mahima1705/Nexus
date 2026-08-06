import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "./auth-store";
import type { User } from "@/types/auth";

const sampleUser: User = {
  id: "user-1",
  email: "test@nexus.ai",
  full_name: "Test User",
  is_active: true,
  is_superuser: false,
  created_at: "2026-01-01T00:00:00Z",
};

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, user: null, hasHydrated: true });
  });

  it("starts with no session", () => {
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
  });

  it("setTokens stores both tokens", () => {
    useAuthStore.getState().setTokens("access-123", "refresh-456");

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-123");
    expect(state.refreshToken).toBe("refresh-456");
  });

  it("setUser stores the user", () => {
    useAuthStore.getState().setUser(sampleUser);

    expect(useAuthStore.getState().user).toEqual(sampleUser);
  });

  it("clear resets tokens and user but not hasHydrated", () => {
    useAuthStore.getState().setTokens("access-123", "refresh-456");
    useAuthStore.getState().setUser(sampleUser);

    useAuthStore.getState().clear();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
    expect(state.hasHydrated).toBe(true);
  });
});
