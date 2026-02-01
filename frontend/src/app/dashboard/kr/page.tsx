'use client';

import { useEffect, useState } from 'react';
import { krAPI, MarketGateData, KRSignalsResponse } from '@/lib/api';
import Link from 'next/link';

export default function KRDashboard() {
    const [marketGate, setMarketGate] = useState<MarketGateData | null>(null);
    const [signals, setSignals] = useState<KRSignalsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                const [gateData, signalsData] = await Promise.all([
                    krAPI.getMarketGate(),
                    krAPI.getSignals(),
                ]);
                setMarketGate(gateData);
                setSignals(signalsData);
            } catch (err: any) {
                setError(err.message || '데이터를 불러오는데 실패했습니다');
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);

    const getGateEmoji = (gate: string) => {
        switch (gate) {
            case 'GREEN': return '🟢';
            case 'YELLOW': return '🟡';
            case 'RED': return '🔴';
            default: return '⚪';
        }
    };

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="loading">
                    <div className="spinner"></div>
                    <span>데이터 로딩 중...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <div>
                    <Link href="/" style={{ textDecoration: 'none', color: 'inherit' }}>
                        <h1 className="dashboard-title">🇰🇷 KR Market Overview</h1>
                    </Link>
                </div>
                {marketGate && (
                    <div className={`gate-badge gate-${marketGate.gate.toLowerCase()}`}>
                        {getGateEmoji(marketGate.gate)} {marketGate.gate} ({marketGate.score}점)
                    </div>
                )}
            </header>

            {error && (
                <div className="card" style={{ background: 'rgba(255, 69, 58, 0.1)', borderColor: 'var(--accent-red)' }}>
                    <p style={{ color: 'var(--accent-red)' }}>⚠️ {error}</p>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                        백엔드 서버가 실행 중인지 확인해주세요: <code>python flask_app.py</code>
                    </p>
                </div>
            )}

            {/* 휴장일 배너 */}
            {marketGate?.kospi?.is_closed && (
                <div className="card" style={{
                    background: 'rgba(255, 159, 10, 0.1)',
                    borderColor: 'var(--accent-orange)',
                    marginBottom: 'var(--spacing-lg)',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '20px' }}>📅</span>
                        <div>
                            <p style={{ color: 'var(--accent-orange)', fontWeight: 600 }}>
                                마지막 거래일: {marketGate.kospi.last_date}
                            </p>
                            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                ⚠️ 주말/휴일에는 참고용으로만 활용하세요. 장 시작 후 데이터가 업데이트됩니다.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            <main>
                {/* 지수 현황 */}
                <div className="grid-4" style={{ marginBottom: 'var(--spacing-xl)' }}>
                    {marketGate?.kospi?.close && (
                        <div className="card">
                            <div className="stat-label">KOSPI</div>
                            <div className="stat-value">{marketGate.kospi.close.toLocaleString()}</div>
                            <div className={`stat-change ${(marketGate.kospi.change_pct ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                                {(marketGate.kospi.change_pct ?? 0) >= 0 ? '+' : ''}{(marketGate.kospi.change_pct ?? 0).toFixed(2)}%
                            </div>
                            <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                                {marketGate.kospi.alignment || ''}
                            </div>
                        </div>
                    )}

                    {marketGate?.kosdaq?.close && (
                        <div className="card">
                            <div className="stat-label">KOSDAQ</div>
                            <div className="stat-value">{marketGate.kosdaq.close.toLocaleString()}</div>
                            <div className={`stat-change ${(marketGate.kosdaq.change_pct ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                                {(marketGate.kosdaq.change_pct ?? 0) >= 0 ? '+' : ''}{(marketGate.kosdaq.change_pct ?? 0).toFixed(2)}%
                            </div>
                            <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                                {marketGate.kosdaq.alignment || ''}
                            </div>
                        </div>
                    )}

                    {marketGate?.usd_krw?.rate && (
                        <div className="card">
                            <div className="stat-label">USD/KRW</div>
                            <div className="stat-value">{marketGate.usd_krw.rate.toLocaleString()}</div>
                            <div className={`stat-change ${(marketGate.usd_krw.change_pct ?? 0) >= 0 ? 'negative' : 'positive'}`}>
                                {(marketGate.usd_krw.change_pct ?? 0) >= 0 ? '+' : ''}{(marketGate.usd_krw.change_pct ?? 0).toFixed(2)}%
                            </div>
                        </div>
                    )}

                    <div className="card">
                        <div className="stat-label">VCP 시그널</div>
                        <div className="stat-value">{signals?.count || 0}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                            활성 시그널
                        </div>
                    </div>
                </div>

                {/* 네비게이션 탭 */}
                <div className="nav-tabs">
                    <Link href="/dashboard/kr" className="nav-tab active">개요</Link>
                    <Link href="/dashboard/kr/vcp" className="nav-tab">VCP 시그널</Link>
                    <Link href="/dashboard/kr/closing-bet" className="nav-tab">종가베팅 V2</Link>
                </div>

                {/* 섹터 현황 */}
                {marketGate?.sectors && marketGate.sectors.length > 0 && (
                    <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                        <div className="card-header">
                            <h2 className="card-title">📊 섹터 현황</h2>
                        </div>
                        <div className="grid-3">
                            {marketGate.sectors.map((sector, i) => (
                                <div key={i} style={{
                                    padding: 'var(--spacing-sm)',
                                    borderRadius: 'var(--radius-sm)',
                                    background: 'var(--bg-surface-hover)',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                }}>
                                    <span>{sector.name}</span>
                                    <span className={sector.change_pct >= 0 ? 'signal-change positive' : 'signal-change negative'}>
                                        {sector.change_pct >= 0 ? '+' : ''}{sector.change_pct.toFixed(2)}%
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 분석 결과 */}
                {marketGate?.analysis?.reasons && marketGate.analysis.reasons.length > 0 && (
                    <div className="card">
                        <div className="card-header">
                            <h2 className="card-title">📋 Market Gate 분석</h2>
                        </div>
                        <ul style={{ paddingLeft: '20px' }}>
                            {marketGate.analysis.reasons.map((reason, i) => (
                                <li key={i} style={{ marginBottom: '8px', color: 'var(--text-secondary)' }}>
                                    {reason}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </main>
        </div>
    );
}
