import { WatchlistRowOut } from "../api/client";
import { FreshnessIndicator } from "./FreshnessIndicator";

export interface WatchlistTableProps {
  rows: WatchlistRowOut[];
  onRemove?: (symbol: string) => void;
  onSelect?: (symbol: string) => void;
}

export function WatchlistTable({ rows, onRemove, onSelect }: WatchlistTableProps) {
  if (rows.length === 0) {
    return null;
  }

  return (
    <section className="watchlist-table">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th className="text-right">Price</th>
            <th className="text-right">Change</th>
            <th className="text-right">Volume</th>
            <th>Freshness</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const changeSign = row.direction === "up" ? "+" : row.direction === "down" ? "−" : "";
            const directionClass =
              row.direction === "up" ? "gain" : row.direction === "down" ? "loss" : "flat";

            return (
              <tr key={row.symbol} className={row.flagged ? "row--flagged" : ""}>
                <td>
                  <button
                    className="symbol-link"
                    onClick={() => onSelect?.(row.symbol)}
                  >
                    {row.symbol}
                  </button>
                </td>
                <td className="text-right">
                  {row.price !== null ? `₹${row.price.toFixed(2)}` : "—"}
                </td>
                <td className={`text-right ${directionClass}`}>
                  {row.day_change_pct !== null
                    ? `${changeSign}${Math.abs(row.day_change_pct).toFixed(2)}%`
                    : "—"}
                </td>
                <td className="text-right">
                  {row.volume !== null ? (row.volume / 1000000).toFixed(1) + "M" : "—"}
                </td>
                <td>
                  <FreshnessIndicator freshness={row.freshness} />
                </td>
                <td>
                  {onRemove && (
                    <button
                      className="remove-btn"
                      onClick={() => onRemove(row.symbol)}
                      aria-label={`Remove ${row.symbol}`}
                    >
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

