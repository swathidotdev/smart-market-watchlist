import { ComponentBreakdownOut } from "../api/client";

export interface ComponentBreakdownProps {
  components: ComponentBreakdownOut;
}

export function ComponentBreakdown({ components }: ComponentBreakdownProps) {
  return (
    <section className="component-breakdown">
      <h3>Component breakdown</h3>
      <div className="component-breakdown__grid">
        <div className="component-breakdown__item">
          <dt>Volatility</dt>
          <dd>{components.volatility_ratio.toFixed(1)}× normal swing</dd>
        </div>
        <div className="component-breakdown__item">
          <dt>Market relative</dt>
          <dd>
            {components.market_excess_pp > 0 ? "+" : ""}
            {components.market_excess_pp.toFixed(1)}pp vs Nifty
          </dd>
        </div>
        <div className="component-breakdown__item">
          <dt>Volume</dt>
          <dd>{components.volume_ratio.toFixed(1)}× normal volume</dd>
        </div>
      </div>
    </section>
  );
}

