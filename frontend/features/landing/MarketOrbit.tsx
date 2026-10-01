"use client";

import Image from "next/image";
import { useEffect, useRef, useState, type CSSProperties } from "react";

const ICONS = ["11st", "ohouse", "smartstore", "coupang", "gmarket", "auction"];
// The supplied reference rotates three entire image planes, not individual bouncing icons.
// Preserve its 60s linear motion, alternating directions, perspective and starting angles.
const LAYERS = [
  { name: "back", size: 2000, angle: 279.05, count: 10, radius: 30, icon: 134 },
  { name: "middle", size: 1000, angle: 304.42, count: 8, radius: 43, icon: 84 },
  { name: "front", size: 800, angle: 48.33, count: 6, radius: 38, icon: 60 },
] as const;

export function MarketOrbit() {
  const root = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  const [inactive, setInactive] = useState(false);

  useEffect(() => {
    const element = root.current;
    if (!element) return;
    let visible = true;
    const update = () => setInactive(!visible || document.hidden);
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; update(); });
    observer.observe(element);
    document.addEventListener("visibilitychange", update);
    update();
    return () => { observer.disconnect(); document.removeEventListener("visibilitychange", update); };
  }, []);

  return <>
    <div ref={root} className="market-orbit" aria-hidden="true" data-paused={paused || inactive}>
      <div className="market-orbit-perspective">
        {LAYERS.map((layer, layerIndex) => <div key={layer.name} className={`market-orbit-frame ${layer.name}`}
          style={{ "--orbit-size": `${layer.size}px`, "--orbit-angle": `${layer.angle}deg` } as CSSProperties}>
          <div className="market-orbit-spin">
            <div className="market-orbit-plane">
              {Array.from({ length: layer.count }, (_, i) => {
                const angle = (i * 360 / layer.count + layerIndex * 13) * Math.PI / 180;
                const radius = layer.radius + (i % 3 - 1) * 3;
                const slug = ICONS[(i + layerIndex * 2) % ICONS.length];
                return <div key={i} className="market-orbit-icon" style={{
                  left: `${(50 + Math.cos(angle) * radius).toFixed(3)}%`,
                  top: `${(50 + Math.sin(angle) * radius).toFixed(3)}%`,
                  width: `${layer.icon + (i % 3 - 1) * 10}px`,
                  transform: `translate(-50%, -50%) rotate(${i * 17 - layer.angle}deg)`,
                }}>
                  <Image src={`/market-icons/${slug}.jpg`} alt="" width={160} height={160} unoptimized loading="eager" draggable={false} />
                </div>;
              })}
            </div>
          </div>
        </div>)}
      </div>
      <div className="market-orbit-shade" />
    </div>
    <button className="market-orbit-toggle" type="button" aria-pressed={paused}
      aria-label={paused ? "배경 애니메이션 재생" : "배경 애니메이션 일시정지"} onClick={() => setPaused(value => !value)}>
      <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
        {paused ? <path d="M5 3v10l8-5z" /> : <path d="M4 3h3v10H4zm5 0h3v10H9z" />}
      </svg>
      <span>배경 {paused ? "재생" : "일시정지"}</span>
    </button>
  </>;
}
