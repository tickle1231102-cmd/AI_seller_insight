import type { Metadata } from "next";
import { Noto_Sans_KR } from "next/font/google";
import "./globals.css";

const notoSansKr = Noto_Sans_KR({
  weight: ["400", "500", "700", "900"],
  display: "swap",
  preload: false,
  variable: "--font-kr",
});

export const metadata: Metadata = {
  title: "Seller Insight AI",
  description: "멀티플랫폼 판매·광고 데이터 통합 분석 대시보드",
};

// 저장된 테마(없으면 시스템 설정)를 첫 페인트 전에 적용해 깜빡임을 막는다.
const themeScript = `try{var t=localStorage.getItem("theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className={notoSansKr.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
