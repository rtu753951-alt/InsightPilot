import { apiFetch } from "./apiClient";

export type CustomerOut = {
  id: number;
  customer_code: string;
  last_visit_date: string; // 後端回 ISO date 字串
  total_spent: number;
  visit_count: number;
  membership_type: string;
  days_since_last_visit: number;
  risk_level: "low" | "medium" | "high";
  risk_reason: string;

};

export type ImportResult = {
  inserted: number;
  updated: number;
  total_rows: number;
};

export async function importCustomersCSV(file: File): Promise<ImportResult> {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const url = `${base}/api/customers/import`;

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(url, {
    method: "POST",
    body: form,
    // ⚠️ multipart 不要手動設 Content-Type，瀏覽器會自動加 boundary
  });

  const text = await res.text();
  const data = text ? safeJsonParse(text) : null;

  if (!res.ok) {
    const msg =
      (data && (data.detail || data.message)) ||
      `Import failed: ${res.status} ${res.statusText}`;
    throw new Error(String(msg));
  }

  return data as ImportResult;
}

export function listCustomers(params?: {
  limit?: number;
  offset?: number;
}): Promise<CustomerOut[]> {
  const qs = new URLSearchParams();
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));

  const path = `/api/customers${qs.toString() ? `?${qs.toString()}` : ""}`;
  return apiFetch<CustomerOut[]>(path);
}

function safeJsonParse(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export function getFollowupSuggestion(customerId: number) {
  return apiFetch<any>(`/api/customers/${customerId}/followup_suggestion`, {
    method: "POST",
  });
}
