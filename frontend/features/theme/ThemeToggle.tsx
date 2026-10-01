"use client";

import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";

const STORAGE_KEY = "theme";
const CHANGE_EVENT = "themechange";

/** layout.tsx 의 인라인 스크립트가 첫 페인트 전에 data-theme 을 넣어둔다. */
const getTheme = (): Theme =>
  document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";

const subscribe = (cb: () => void) => {
  window.addEventListener(CHANGE_EVENT, cb);
  return () => window.removeEventListener(CHANGE_EVENT, cb);
};

const applyTheme = (next: Theme) => {
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {}
  window.dispatchEvent(new Event(CHANGE_EVENT));
};

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getTheme, () => null);

  return (
    <div className="theme-toggle" role="radiogroup" aria-label="화면 테마">
      {(["light", "dark"] as const).map((t) => (
        <button
          key={t}
          role="radio"
          aria-checked={theme === t}
          className={theme === t ? "is-active" : ""}
          onClick={() => applyTheme(t)}
        >
          <span aria-hidden>{t === "light" ? "☀" : "☾"}</span>
          {t === "light" ? "라이트" : "다크"}
        </button>
      ))}
    </div>
  );
}
