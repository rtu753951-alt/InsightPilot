import { apiFetch } from "./apiClient";

export function getHealth(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/api/health");
}
