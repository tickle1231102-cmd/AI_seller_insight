import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const pretendard = localFont({
  src: "./fonts/PretendardVariable.woff2",
  weight: "45 920",
  display: "swap",
  variable: "--font-pretendard",
});

export const metadata: Metadata = {
  title: "Seller Insight AI",
  description: "멀티플랫폼 판매·광고 데이터 통합 분석 대시보드",
};

// 처음 방문하면 시스템 테마와 무관하게 라이트. 사용자가 저장한 선택만 우선한다.
const themeScript = `var t="light";try{var saved=localStorage.getItem("theme");if(saved==="light"||saved==="dark")t=saved}catch(e){}document.documentElement.dataset.theme=t;`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" data-theme="light" className={pretendard.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
