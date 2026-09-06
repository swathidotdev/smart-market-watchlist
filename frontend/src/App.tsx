import { useEffect, useState } from "react";
import { api, type HealthResponse } from "./api/client";

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "error"; message: string };

export default function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    api
      .health()
      .then((data) => setState({ kind: "ok", data }))
      .catch((e: unknown) =>
        setState({ kind: "error", message: e instanceof Error ? e.message : "Unknown error" }),
      );
  }, []);

  return (
    <main className="shell">
      <h1>Smart Market Watchlist</h1>
      {state.kind === "loading" && <p className="muted">Checking backend…</p>}
      {state.kind === "ok" && (
        <p className="ok">
          Backend reachable — {state.data.app} ({state.data.environment})
        </p>
      )}
      {state.kind === "error" && <p className="err">Backend unreachable — {state.message}</p>}
    </main>
  );
}