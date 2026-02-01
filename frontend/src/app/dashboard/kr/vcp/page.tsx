'use client';

import { useEffect, useState } from 'react';
import { krAPI, KRSignalsResponse, Signal } from '@/lib/api';
import Link from 'next/link';

export default function VCPSignalsPage() {
    const [data, setData] = useState<KRSignalsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                const result = await krAPI.getSignals();
                setData(result);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);

    const handleRunScreener = async () => {
        try {
            setLoading(true);
            await fetch('/api/run-command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'screener' }),
            });
            // 새로고침
            window.location.reload();
        } catch (err) {
            alert('스크리너 실행 실패');
        }
    };

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="loading">
                    <div className="spinner"></div>
                    <span>VCP 시그널 로딩 중...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <div>
                    <Link href="/" style={{ textDecoration: 'none', color: 'inherit' }}>
                        <h1 className="dashboard-title">🔍 VCP 시그널</h1>
                    </Link>
                    <p className="card-subtitle">변동성 수축 패턴 + 수급 분석</p>
                </div>
                <button className="btn btn-primary" onClick={handleRunScreener}>
                    🔄 스크리너 실행
                </button>
            </header>

            {/* 네비게이션 */}
            <div className="nav-tabs">
                <Link href="/dashboard/kr" className="nav-tab">개요</Link>
                <Link href="/dashboard/kr/vcp" className="nav-tab active">VCP 시그널</Link>
                <Link href="/dashboard/kr/closing-bet" className="nav-tab">종가베팅 V2</Link>
            </div>

            {error && (
                <div className="card" style={{ background: 'rgba(255, 69, 58, 0.1)', borderColor: 'var(--accent-red)' }}>
                    <p style={{ color: 'var(--accent-red)' }}>⚠️ {error}</p>
                </div>
            )}

            {/* 시그널 목록 */}
            {data?.signals && data.signals.length > 0 ? (
                <div className="grid-2">
                    {data.signals.map((signal, i) => (
                        <SignalCard key={i} signal={signal} />
                    ))}
                </div>
            ) : (
                <div className="empty-state">
                    <div className="empty-state-icon">📭</div>
                    <p>시그널이 없습니다</p>
                    <p style={{ fontSize: '14px', marginTop: '8px' }}>
                        스크리너를 실행하여 시그널을 생성하세요
                    </p>
                </div>
            )}
        </div>
    );
}

function SignalCard({ signal }: { signal: Signal }) {
    const code = signal.ticker || signal.stock_code || '';
    const name = signal.name || signal.stock_name || code;
    const price = signal.close || signal.current_price || 0;
    const changePct = signal.change_pct || 0;
    const supplyScore = signal.supply_score || 0;
    const stage = signal.stage || '';
    const isDoubleBuy = signal.is_double_buy || false;

    return (
        <div className="signal-card">
            <div className="signal-header">
                <div className="signal-name">{name}</div>
                <span className="signal-code">{code}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="signal-price">{price.toLocaleString()}원</div>
                <div className={`signal-change ${changePct >= 0 ? 'positive' : 'negative'}`}>
                    {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    background: 'var(--bg-surface-hover)',
                    fontSize: '12px',
                }}>
                    점수: {supplyScore}
                </span>

                {stage && (
                    <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        background: stage.includes('매집') ? 'rgba(48, 209, 88, 0.2)' : 'var(--bg-surface-hover)',
                        color: stage.includes('매집') ? 'var(--accent-green)' : 'var(--text-secondary)',
                        fontSize: '12px',
                    }}>
                        {stage}
                    </span>
                )}

                {isDoubleBuy && (
                    <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        background: 'rgba(255, 159, 10, 0.2)',
                        color: 'var(--accent-orange)',
                        fontSize: '12px',
                    }}>
                        🔥 쌍끌이
                    </span>
                )}
            </div>
        </div>
    );
}
