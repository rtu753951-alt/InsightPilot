import { apiFetch, setToken, clearToken } from "./apiClient";

export async function register(email: string, password: string) {
  return apiFetch<{ id: number; email: string }>("/api/auth/register", {
    method: "POST",
    body: { email, password },
  });
}

export async function login(email: string, password: string) {
  const res = await apiFetch<{ access_token: string; token_type: string }>("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
  setToken(res.access_token);
  return res;
}

export function logout() {
  clearToken();
}

export async function me() {
  return apiFetch<{ id: number; email: string }>("/api/auth/me");
}
