import type { Signal } from "@/types/api";
import { formatPercent, formatSignedPercent, platformLabel } from "@/lib/format";

function describe(s: Signal): string {
  const scope = s.platform === "all" ? "전체" : platformLabel(s.platform);
  switch (s.signal) {
    case "ROAS_DOWN_WITH_SPEND_GROWTH":
      return `${scope}: 광고비 ${formatSignedPercent(s.ad_spend_change as number)} 증가, ROAS ${formatSignedPercent(s.roas_change_pp as number, "%p")}`;
    case "REVENUE_DOWN":
      return `${scope}: 매출 ${formatSignedPercent(s.revenue_change as number)} 감소`;
    case "LOW_ROAS_PLATFORM":
      return `${scope}: ROAS ${formatPercent(s.roas as number)} (전체 ${formatPercent(s.overall_roas as number)}) 대비 저효율`;
    default:
      return `${scope}: ${s.signal}`;
  }
}

export function SignalBadges({ signals }: { signals: Signal[] }) {
  if (signals.length === 0) return null;
  return (
    <section className="signals">
      {signals.map((s, i) => (
        <span key={i} className="badge warn">
          ⚠ {describe(s)}
        </span>
      ))}
    </section>
  );
}
