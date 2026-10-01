export function Hero() {
  return (
    <section className="hero">
      <span className="hero-pill">
        <i aria-hidden />
        쿠팡 · 네이버 리포트를 AI가 한 번에 분석
      </span>
      <h1 className="hero-title">
        흩어진 판매·광고 데이터,
        <br />
        파일 하나로 인사이트까지
      </h1>
      <p className="hero-sub">
        엑셀·CSV 리포트를 올리면 KPI, 플랫폼 비교, 이상 신호와 AI 액션 제안을{" "}
        <br />
        30초 안에 대시보드로 정리해드립니다.
      </p>
    </section>
  );
}

const STEPS = [
  { n: "01", tone: "blue", title: "업로드", desc: "쿠팡·네이버에서 받은 판매/광고 리포트를 그대로 올리세요. 컬럼은 자동 인식됩니다." },
  { n: "02", tone: "purple", title: "자동 분석", desc: "기간별 매출·ROAS·전환율을 정규화하고 플랫폼별로 비교합니다." },
  { n: "03", tone: "green", title: "AI 인사이트", desc: "이상 신호를 감지하고 바로 실행할 수 있는 액션을 제안합니다. 이후 대화로 깊게 질문하세요." },
] as const;

const SAMPLE_KPIS = [
  { label: "총 매출", value: "₩48,210,000", delta: "+12.4%", up: true },
  { label: "ROAS", value: "412%", delta: "+38%p", up: true },
  { label: "광고비", value: "₩11,700,000", delta: "-4.1%", up: false },
  { label: "전환율", value: "3.8%", delta: "+0.6%p", up: true },
];

export function LandingDetails() {
  return (
    <>
      <section id="how" className="steps">
        {STEPS.map((s) => (
          <article key={s.n} className="step-card">
            <span className={`step-num ${s.tone}`}>{s.n}</span>
            <h3>{s.title}</h3>
            <p className="muted">{s.desc}</p>
          </article>
        ))}
      </section>

      <section className="teaser">
        <div className="teaser-row">
          {SAMPLE_KPIS.map((k) => (
            <div key={k.label} className="teaser-card">
              <span className="muted small">{k.label}</span>
              <strong>{k.value}</strong>
              <span className={`delta small ${k.up ? "up" : "down"}`}>{k.delta}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
