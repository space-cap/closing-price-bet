import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'KR Market Dashboard',
    description: '한국 주식 시장 AI 분석 대시보드',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="ko">
            <body>{children}</body>
        </html>
    );
}
