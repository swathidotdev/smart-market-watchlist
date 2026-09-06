import { FreshnessOut } from "../api/client";

export function FreshnessIndicator({ freshness }: { freshness: FreshnessOut }) {
  return (
    <span className="freshness" data-state={freshness.state.toLowerCase()}>
      {freshness.label}
    </span>
  );
}

