'use client';

import { useEffect, useState } from 'react';
import { krAPI, JonggaV2Response, Signal } from '@/lib/api';
import Link from 'next/link';

export default function ClosingBetPage() {
    const [data, setData] = useState<JonggaV2Response | null>(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    async function fetchData() {
        try {
            setLoading(true);
            const result = await krAPI.getJonggaV2Latest();
            setData(result);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    const handleRunScreener = async () => {
        try {
            setRunning(true);
            const result = await krAPI.runJonggaV2();
            if (result.status === 'ok') {
                await fetchData();
            } else {
                alert('스크리너 실행 실패: ' + result.message);
            }
        } catch (err) {
            alert('스크리너 실행 실패');
        } finally {
            setRunning(false);
        }
    };

    const getGradeColor = (grade: string) => {
        switch (grade) {
            case 'S': return 'var(--grade-s)';
            case 'A': return 'var(--grade-a)';
            case 'B': return 'var(--grade-b)';
            default: return 'var(--grade-c)';
        }
    };

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="loading">
                    <div className="spinner"></div>
                    <span>종가베팅 V2 데이터 로딩 중...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <div>
                    <Link href="/" style={{ textDecoration: 'none', color: 'inherit' }}>
                        <h1 className="dashboard-title">🎯 종가베팅 V2</h1>
                    </Link>
                    <p className="card-subtitle">12점 점수 시스템 기반 시그널</p>
                </div>
                <button
                    className="btn btn-primary"
                    onClick={handleRunScreener}
                    disabled={running}
                >
                    {running ? '⏳ 실행 중...' : '🚀 스크리너 실행'}
                </button>
            </header>

            {/* 네비게이션 */}
            <div className="nav-tabs">
                <Link href="/dashboard/kr" className="nav-tab">개요</Link>
                <Link href="/dashboard/kr/vcp" className="nav-tab">VCP 시그널</Link>
                <Link href="/dashboard/kr/closing-bet" className="nav-tab active">종가베팅 V2</Link>
            </div>

            {error && (
                <div className="card" style={{ background: 'rgba(255, 69, 58, 0.1)', borderColor: 'var(--accent-red)', marginBottom: 'var(--spacing-lg)' }}>
                    <p style={{ color: 'var(--accent-red)' }}>⚠️ {error}</p>
                </div>
            )}

            {/* 통계 */}
            {data && (
                <div className="grid-4" style={{ marginBottom: 'var(--spacing-xl)' }}>
                    <div className="card">
                        <div className="stat-label">분석 종목</div>
                        <div className="stat-value">{data.total_candidates}</div>
                    </div>
                    <div className="card">
                        <div className="stat-label">시그널 수</div>
                        <div className="stat-value">{data.filtered_count}</div>
                    </div>
                    <div className="card">
                        <div className="stat-label">S등급</div>
                        <div className="stat-value" style={{ color: 'var(--accent-yellow)' }}>
                            {data.by_grade?.S || 0}
                        </div>
                    </div>
                    <div className="card">
                        <div className="stat-label">A등급</div>
                        <div className="stat-value" style={{ color: 'var(--accent-green)' }}>
                            {data.by_grade?.A || 0}
                        </div>
                    </div>
                </div>
            )}

            {/* 시그널 목록 */}
            {data?.signals && data.signals.length > 0 ? (
                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">📋 시그널 목록</h2>
                        <span className="card-subtitle">{data.date}</span>
                    </div>

                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>등급</th>
                                    <th>종목</th>
                                    <th>시장</th>
                                    <th>현재가</th>
                                    <th>등락률</th>
                                    <th>총점</th>
                                    <th>뉴스</th>
                                    <th>거래량</th>
                                    <th>차트</th>
                                    <th>수급</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.signals.map((signal, i) => (
                                    <SignalRow key={i} signal={signal} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="empty-state">
                    <div className="empty-state-icon">📭</div>
                    <p>종가베팅 시그널이 없습니다</p>
                    <p style={{ fontSize: '14px', marginTop: '8px' }}>
                        스크리너를 실행하여 시그널을 생성하세요
                    </p>
                    <button
                        className="btn btn-primary"
                        style={{ marginTop: '16px' }}
                        onClick={handleRunScreener}
                        disabled={running}
                    >
                        {running ? '⏳ 실행 중...' : '🚀 스크리너 실행'}
                    </button>
                </div>
            )}
        </div>
    );
}

function SignalRow({ signal }: { signal: Signal }) {
    const grade = signal.grade || 'C';
    const code = signal.stock_code || '';
    const name = signal.stock_name || code;
    const price = signal.current_price || 0;
    const changePct = signal.change_pct || 0;
    const score = signal.score;

    return (
        <tr>
            <td>
                <div className={`grade-badge grade-${grade.toLowerCase()}`}>
                    {grade}
                </div>
            </td>
            <td>
                <div style={{ fontWeight: 600 }}>{name}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{code}</div>
            </td>
            <td>{signal.market}</td>
            <td style={{ fontWeight: 600 }}>{price.toLocaleString()}</td>
            <td>
                <span className={changePct >= 0 ? 'signal-change positive' : 'signal-change negative'}>
                    {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                </span>
            </td>
            <td>
                <span style={{
                    fontWeight: 700,
                    color: (score?.total || 0) >= 8 ? 'var(--accent-green)' : 'var(--text-primary)'
                }}>
                    {score?.total || 0}/12
                </span>
            </td>
            <td>{score?.news || 0}/3</td>
            <td>{score?.volume || 0}/3</td>
            <td>{score?.chart || 0}/2</td>
            <td>{score?.supply || 0}/2</td>
        </tr>
    );
}
