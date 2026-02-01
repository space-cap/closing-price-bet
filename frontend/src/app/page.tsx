import Link from 'next/link';

export default function Home() {
    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <h1 className="dashboard-title">🇰🇷 KR Market Dashboard</h1>
            </header>

            <main>
                <div className="grid-3">
                    <Link href="/dashboard/kr" style={{ textDecoration: 'none' }}>
                        <div className="card">
                            <div className="card-header">
                                <h2 className="card-title">📊 시장 개요</h2>
                            </div>
                            <p className="card-subtitle">
                                KOSPI/KOSDAQ 지수, Market Gate, 수급 현황
                            </p>
                        </div>
                    </Link>

                    <Link href="/dashboard/kr/vcp" style={{ textDecoration: 'none' }}>
                        <div className="card">
                            <div className="card-header">
                                <h2 className="card-title">🔍 VCP 시그널</h2>
                            </div>
                            <p className="card-subtitle">
                                변동성 수축 패턴 + 수급 분석 시그널
                            </p>
                        </div>
                    </Link>

                    <Link href="/dashboard/kr/closing-bet" style={{ textDecoration: 'none' }}>
                        <div className="card">
                            <div className="card-header">
                                <h2 className="card-title">🎯 종가베팅 V2</h2>
                            </div>
                            <p className="card-subtitle">
                                12점 점수 시스템 기반 종가베팅 시그널
                            </p>
                        </div>
                    </Link>
                </div>

                <div style={{ marginTop: 'var(--spacing-xl)' }}>
                    <h2 style={{ marginBottom: 'var(--spacing-md)', color: 'var(--text-secondary)' }}>
                        빠른 시작
                    </h2>
                    <div className="card">
                        <pre style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                            {`# 1. 백엔드 서버 실행
uv sync
uv run python flask_app.py

# 2. 프론트엔드 실행
cd frontend
npm install
npm run dev

# 3. 스크리너 실행
uv run python screener.py
uv run python market_gate.py`}
                        </pre>
                    </div>
                </div>
            </main>
        </div>
    );
}
