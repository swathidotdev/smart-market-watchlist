const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "smw_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
    ...(init?.headers ?? {}),
  };

  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...init,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      /* non-JSON error body; keep statusText */
    }
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as T;
}

export interface HealthResponse {
  status: string;
  app: string;
  environment: string;
}

export interface FreshnessOut {
  state: "LIVE" | "RECENT" | "DELAYED" | "STALE" | "UNAVAILABLE";
  label: string;
}

export interface FeedItemOut {
  symbol: string;
  exchange: string;
  price: number | null;
  day_change_pct: number | null;
  direction: "up" | "down" | "flat";
  score: number;
  dominant_factor: string;
  explanation: string;
  event_date: string;
  freshness: FreshnessOut;
}

export interface WatchlistRowOut {
  symbol: string;
  exchange: string;
  price: number | null;
  previous_close: number | null;
  day_change_pct: number | null;
  direction: string;
  volume: number | null;
  freshness: FreshnessOut;
  flagged: boolean;
}

export interface DashboardOut {
  baseline_at: string | null;
  meaningful_change_count: number;
  feed: FeedItemOut[];
  watchlist: WatchlistRowOut[];
}

export interface ComponentBreakdownOut {
  return_pct: number;
  volatility_ratio: number;
  market_excess_pp: number;
  volume_ratio: number;
  volatility_norm: number;
  market_norm: number;
  volume_norm: number;
}

export interface HistoryBarOut {
  date: string;
  close: number;
  volume: number;
}

export interface StockDetailOut {
  symbol: string;
  exchange: string;
  price: number | null;
  previous_close: number | null;
  day_change_pct: number | null;
  volume: number | null;
  direction: string;
  freshness: FreshnessOut;
  status: string;
  score: number;
  dominant_factor: string;
  explanation: string;
  components: ComponentBreakdownOut | null;
  history: HistoryBarOut[];
}

export interface AcknowledgeRequest {
  symbol: string;
}

export interface AddWatchlistRequest {
  symbol: string;
}

export interface TokenResponse {
  access_token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  email: string;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  auth: {
    login: (email: string, password: string) => request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password } as LoginRequest),
    }),
    register: (email: string, password: string) => request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password } as RegisterRequest),
    }),
    me: () => request<UserResponse>("/auth/me"),
  },
  dashboard: {
    get: () => request<DashboardOut>("/dashboard"),
  },
  watchlist: {
    add: (symbol: string) => request<void>("/watchlist", {
      method: "POST",
      body: JSON.stringify({ symbol } as AddWatchlistRequest),
    }),
    remove: (symbol: string) => request<void>(`/watchlist/${symbol}`, {
      method: "DELETE",
    }),
  },
  acknowledge: (symbol: string) => request<void>("/acknowledge", {
    method: "POST",
    body: JSON.stringify({ symbol } as AcknowledgeRequest),
  }),
  stock: {
    get: (symbol: string) => request<StockDetailOut>(`/stock/${symbol}`),
  },
};