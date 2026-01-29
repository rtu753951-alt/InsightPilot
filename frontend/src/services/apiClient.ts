// src/services/apiClient.ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown; // 允許傳 object，會自動 JSON.stringify
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;

  const headers = new Headers(options.headers);

  // JSON body 自動處理
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  // 自動帶 token（如果有）
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(url, {
    ...options,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  // 盡量解析回傳（不管成功或失敗）
  const text = await res.text();
  const data = text ? safeJsonParse(text) : null;

  if (!res.ok) {
    const msg =
      (data && (data.detail || data.message)) ||
      `Request failed: ${res.status} ${res.statusText}`;
    throw new ApiError(String(msg), res.status, data);
  }

  return data as T;
}

function safeJsonParse(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
