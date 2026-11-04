function getResolvedApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (process.env.NODE_ENV === "production" && !envUrl) {
    // In production, fallback to production API domain instead of localhost
    return "https://api.atdesk.thesortedclub.com/api";
  }
  let base = envUrl || "http://localhost:8000/api";
  // Strip trailing slashes
  base = base.replace(/\/+$/, "");
  // Ensure base ends with /api
  if (!base.endsWith("/api")) {
    base = `${base}/api`;
  }
  return base;
}

const API_BASE_URL = getResolvedApiBase();

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("atdesk_token");
}

export function setAuthToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem("atdesk_token", token);
  } else {
    localStorage.removeItem("atdesk_token");
  }
}

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const cleanEndpoint = endpoint.replace(/^\/+/, "");
  const url = `${API_BASE_URL}/${cleanEndpoint}`;
  const token = getAuthToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options?.headers as Record<string, string>) || {}),
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMsg = `API Error: ${res.status}`;
      try {
        const errorJson = await res.json();
        errorMsg = errorJson.detail || errorJson.message || errorMsg;
      } catch (e) {
        // ignore json parse error
      }
      throw new Error(errorMsg);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`Fetch error at ${endpoint}:`, err);
    throw err;
  }
}
