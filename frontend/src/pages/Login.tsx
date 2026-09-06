import { useState } from "react";
import { api, ApiError, setToken } from "../api/client";

export interface LoginProps {
  onLoginSuccess?: () => void;
}

type Mode = "login" | "register";
type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "success" };

export function Login({ onLoginSuccess }: LoginProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  const validateEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!email || !password) {
      setState({ kind: "error", message: "Email and password required" });
      return;
    }

    if (!validateEmail(email)) {
      setState({ kind: "error", message: "Please enter a valid email" });
      return;
    }

    if (mode === "register" && password.length < 8) {
      setState({ kind: "error", message: "Password must be at least 8 characters" });
      return;
    }

    setState({ kind: "loading" });
    try {
      const response =
        mode === "login"
          ? await api.auth.login(email, password)
          : await api.auth.register(email, password);

      setToken(response.access_token);
      setState({ kind: "success" });
      onLoginSuccess?.();
    } catch (err) {
      let message = "Something went wrong";
      if (err instanceof ApiError) {
        message = err.message;
        // Log error details to console for debugging
        console.error(`Auth error (${err.status}):`, err.message);
      } else if (err instanceof Error) {
        message = err.message;
        console.error("Auth error:", err);
      } else {
        console.error("Unknown error:", err);
      }
      setState({ kind: "error", message });
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Smart Market Watchlist</h1>
        <form onSubmit={handleSubmit} className="login-form">
          <h2>{mode === "login" ? "Sign In" : "Create Account"}</h2>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={state.kind === "loading"}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={state.kind === "loading"}
              required
            />
            {mode === "register" && (
              <p className="form-hint">
                {password.length < 8 ? (
                  <span className="hint-error">
                    Minimum 8 characters ({password.length}/8)
                  </span>
                ) : (
                  <span className="hint-ok">✓ Password meets requirements</span>
                )}
              </p>
            )}
          </div>

          {state.kind === "error" && <p className="error-message">{state.message}</p>}

          <button type="submit" disabled={state.kind === "loading"} className="submit-btn">
            {state.kind === "loading"
              ? "Loading…"
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>

        <p className="mode-toggle">
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setState({ kind: "idle" });
            }}
            className="toggle-link"
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>

        <p className="dev-hint">
          <strong>Dev tip:</strong> Use any email/password to sign up or sign in.
        </p>
      </div>
    </div>
  );
}
