import { useEffect, useRef, useState } from "react";
import { api, ApiError, type DashboardOut } from "../api/client";
import { ChangeFeedCard } from "../components/ChangeFeedCard";
import { EmptyState } from "../components/EmptyState";
import { WatchlistTable } from "../components/WatchlistTable";

type ViewMode = "feed" | "list";
type State =
  | { kind: "loading" }
  | { kind: "ok"; data: DashboardOut }
  | { kind: "error"; message: string };

export function Dashboard({ onStockSelect }: { onStockSelect?: (symbol: string) => void }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [viewMode, setViewMode] = useState<ViewMode>("feed");
  const [newSymbol, setNewSymbol] = useState("");
  const [isLoadingAction, setIsLoadingAction] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const loadDashboard = async () => {
    try {
      setState({ kind: "loading" });
      const data = await api.dashboard.get();
      setState({ kind: "ok", data });
      setActionError(null);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to load dashboard";
      setState({ kind: "error", message });
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleAddSymbol = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSymbol.trim()) return;

    setIsLoadingAction(true);
    setActionError(null);
    try {
      await api.watchlist.add(newSymbol.toUpperCase());
      setNewSymbol("");
      await loadDashboard();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to add symbol";
      setActionError(message);
    } finally {
      setIsLoadingAction(false);
    }
  };

  const handleRemoveSymbol = async (symbol: string) => {
    setIsLoadingAction(true);
    setActionError(null);
    try {
      await api.watchlist.remove(symbol);
      await loadDashboard();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to remove symbol";
      setActionError(message);
    } finally {
      setIsLoadingAction(false);
    }
  };

  const handleAcknowledge = async (symbol: string) => {
    setIsLoadingAction(true);
    setActionError(null);
    try {
      await api.acknowledge(symbol);
      await loadDashboard();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to acknowledge";
      setActionError(message);
    } finally {
      setIsLoadingAction(false);
    }
  };

  const handleStockSelect = (symbol: string) => {
    onStockSelect?.(symbol);
  };

  if (state.kind === "loading") {
    return (
      <div className="dashboard">
        <p className="muted">Loading watchlist…</p>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="dashboard">
        <p className="err">Error: {state.message}</p>
        <button onClick={loadDashboard} className="btn-retry">
          Retry
        </button>
      </div>
    );
  }

  const { data } = state;
  const baselineDate = data.baseline_at
    ? new Date(data.baseline_at).toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <div className="dashboard">
      {/* Top control bar */}
      <div className="dashboard__controls">
        <div className="dashboard__tabs">
          <button
            className={`tab ${viewMode === "feed" ? "tab--active" : ""}`}
            onClick={() => setViewMode("feed")}
          >
            Feed
          </button>
          <button
            className={`tab ${viewMode === "list" ? "tab--active" : ""}`}
            onClick={() => setViewMode("list")}
          >
            Watchlist
          </button>
        </div>
        <form ref={formRef} onSubmit={handleAddSymbol} className="dashboard__add-symbol">
          <input
            type="text"
            placeholder="Add symbol"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            disabled={isLoadingAction}
            maxLength={10}
          />
          <button type="submit" disabled={isLoadingAction || !newSymbol.trim()}>
            Add
          </button>
        </form>
      </div>

      {/* Error message */}
      {actionError && <p className="action-error">{actionError}</p>}

      {/* Feed view */}
      {viewMode === "feed" && (
        <section className="dashboard__feed">
          {data.meaningful_change_count > 0 && baselineDate && (
            <h2 className="dashboard__headline">
              {data.meaningful_change_count} meaningful change{data.meaningful_change_count !== 1 ? "s" : ""}{" "}
              since {baselineDate}
            </h2>
          )}

          {data.feed.length > 0 ? (
            <>
              {data.feed.map((item, idx) => (
                <div key={item.symbol}>
                  <ChangeFeedCard
                    item={item}
                    isHeroCard={idx === 0}
                    onAcknowledge={handleAcknowledge}
                  />
                  {idx < data.feed.length - 1 && <hr className="divider" />}
                </div>
              ))}

              {/* Quiet list */}
              {data.watchlist.filter((r) => !r.flagged).length > 0 && (
                <>
                  <hr className="divider" />
                  <p className="quiet-list-label">
                    Quiet:{" "}
                    {data.watchlist
                      .filter((r) => !r.flagged)
                      .map((r) => r.symbol)
                      .join(" · ")}{" "}
                    — no meaningful change
                  </p>
                </>
              )}
            </>
          ) : (
            <EmptyState reason={data.watchlist.length === 0 ? "empty-watchlist" : "no-change"} />
          )}
        </section>
      )}

      {/* List view */}
      {viewMode === "list" && (
        <section className="dashboard__list">
          {data.watchlist.length > 0 ? (
            <WatchlistTable
              rows={data.watchlist}
              onRemove={handleRemoveSymbol}
              onSelect={handleStockSelect}
            />
          ) : (
            <EmptyState reason="empty-watchlist" />
          )}
        </section>
      )}
    </div>
  );
}

