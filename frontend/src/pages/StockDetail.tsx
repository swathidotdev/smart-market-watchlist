import { useEffect, useState } from "react";
import { api, ApiError, type StockDetailOut } from "../api/client";
import { ComponentBreakdown } from "../components/ComponentBreakdown";
import { FreshnessIndicator } from "../components/FreshnessIndicator";

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: StockDetailOut }
  | { kind: "error"; message: string };

export function StockDetail({
  symbol,
  onBack,
}: {
  symbol: string;
  onBack?: () => void;
}) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const loadStock = async () => {
      try {
        setState({ kind: "loading" });
        const data = await api.stock.get(symbol);
        setState({ kind: "ok", data });
      } catch (err) {
        const message = err instanceof ApiError ? err.message : "Failed to load stock details";
        setState({ kind: "error", message });
      }
    };

    loadStock();
  }, [symbol]);

  if (state.kind === "loading") {
    return (
      <div className="stock-detail">
        <button onClick={onBack} className="btn-back">
          ← Back
        </button>
        <p className="muted">Loading…</p>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="stock-detail">
        <button onClick={onBack} className="btn-back">
          ← Back
        </button>
        <p className="err">Error: {state.message}</p>
      </div>
    );
  }

  const { data } = state;
  const changeSign = data.direction === "up" ? "+" : data.direction === "down" ? "−" : "";
  const directionClass =
    data.direction === "up" ? "gain" : data.direction === "down" ? "loss" : "flat";

  return (
    <div className="stock-detail">
      {/* Back button */}
      {onBack && (
        <button onClick={onBack} className="btn-back">
          ← Back
        </button>
      )}

      {/* Header */}
      <header className="stock-detail__header">
        <div>
          <h1 className="stock-detail__symbol">{data.symbol}</h1>
          <p className="stock-detail__exchange">{data.exchange}</p>
        </div>
        <div className="stock-detail__meta">
          <FreshnessIndicator freshness={data.freshness} />
        </div>
      </header>

      {/* Price info */}
      <section className="stock-detail__price">
        <div className="price-item">
          <dt>Current price</dt>
          <dd>{data.price !== null ? `₹${data.price.toFixed(2)}` : "—"}</dd>
        </div>
        <div className="price-item">
          <dt>Change</dt>
          <dd className={directionClass}>
            {data.day_change_pct !== null
              ? `${changeSign}${Math.abs(data.day_change_pct).toFixed(2)}%`
              : "—"}
          </dd>
        </div>
        <div className="price-item">
          <dt>Volume</dt>
          <dd>{data.volume !== null ? (data.volume / 1000000).toFixed(1) + "M" : "—"}</dd>
        </div>
      </section>

      {/* Score and explanation */}
      <section className="stock-detail__analysis">
        <h2>Score: {data.score.toFixed(2)}</h2>
        <p className="stock-detail__explanation">{data.explanation}</p>
      </section>

      {/* Component breakdown */}
      {data.components && <ComponentBreakdown components={data.components} />}

      {/* History */}
      {data.history && data.history.length > 0 && (
        <section className="stock-detail__history">
          <h3>Recent history</h3>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th className="text-right">Close</th>
                <th className="text-right">Volume</th>
              </tr>
            </thead>
            <tbody>
              {data.history.map((bar) => (
                <tr key={bar.date}>
                  <td>{new Date(bar.date).toLocaleDateString()}</td>
                  <td className="text-right">₹{bar.close.toFixed(2)}</td>
                  <td className="text-right">{(bar.volume / 1000000).toFixed(1)}M</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

