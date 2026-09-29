import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Seller Insight AI",
  description: "멀티플랫폼 판매·광고 데이터 통합 분석 대시보드",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
