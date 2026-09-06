import { FeedItemOut } from "../api/client";
import { FreshnessIndicator } from "./FreshnessIndicator";

export interface ChangeFeedCardProps {
  item: FeedItemOut;
  isHeroCard?: boolean;
  onAcknowledge?: (symbol: string) => void;
}

export function ChangeFeedCard({ item, isHeroCard = false, onAcknowledge }: ChangeFeedCardProps) {
  const changeSign = item.direction === "up" ? "+" : item.direction === "down" ? "−" : "";
  const directionClass = item.direction === "up" ? "gain" : item.direction === "down" ? "loss" : "flat";

  return (
    <article className={`feed-card ${isHeroCard ? "feed-card--hero" : ""}`}>
      <div className="feed-card__header">
        <div className="feed-card__symbol-block">
          <h3 className="feed-card__symbol">{item.symbol}</h3>
          <p className="feed-card__change">
            <span className={`change-value ${directionClass}`}>
              {changeSign}
              {Math.abs(item.day_change_pct ?? 0).toFixed(1)}%
            </span>
          </p>
        </div>
        <div className="feed-card__meta">
          <FreshnessIndicator freshness={item.freshness} />
          {onAcknowledge && (
            <button
              className="feed-card__acknowledge"
              onClick={() => onAcknowledge(item.symbol)}
              aria-label={`Mark ${item.symbol} as reviewed`}
            >
              ✓
            </button>
          )}
        </div>
      </div>
      <div className="feed-card__explanation">
        <p>{item.explanation}</p>
      </div>
    </article>
  );
}

