#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VCP + 수급 스크리너
외인/기관 수급 분석 기반 종목 선정
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

try:
    from pykrx import stock
except ImportError:
    print("pykrx 설치 필요: pip install pykrx")
    stock = None

from config import TrendThresholds, MarketGateConfig, ScreenerConfig


class SmartMoneyScreener:
    """외인/기관 수급 분석 스크리너"""
    
    def __init__(self, config: ScreenerConfig = None):
        self.config = config or ScreenerConfig()
        self.thresholds = TrendThresholds()
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def run_screening(self, max_stocks: int = 50) -> pd.DataFrame:
        """
        수급 스크리닝 실행
        
        Args:
            max_stocks: 분석할 최대 종목 수
            
        Returns:
            분석 결과 DataFrame
        """
        print("=" * 60)
        print("🔍 Smart Money Screener 시작")
        print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        if stock is None:
            print("❌ pykrx 모듈이 필요합니다.")
            return pd.DataFrame()
        
        # 1. 거래일 확인
        today = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
        
        results = []
        
        # KOSPI + KOSDAQ 종목 조회
        for market in ["KOSPI", "KOSDAQ"]:
            print(f"\n[{market}] 종목 조회 중...")
            
            try:
                # 전체 종목 목록
                tickers = stock.get_market_ticker_list(today, market=market)
                
                if not tickers:
                    # 오늘 데이터가 없으면 이전 거래일 시도
                    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                    tickers = stock.get_market_ticker_list(yesterday, market=market)
                
                print(f"   종목 수: {len(tickers)}개")
                
                # 상위 N개만 분석
                for i, ticker in enumerate(tickers[:max_stocks // 2]):
                    if i % 10 == 0:
                        print(f"   진행률: {i}/{min(len(tickers), max_stocks // 2)}")
                    
                    try:
                        result = self._analyze_stock(ticker, market, start_date, today)
                        if result:
                            results.append(result)
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"   오류: {e}")
                continue
        
        # DataFrame 생성
        if not results:
            print("\n⚠️ 분석된 종목이 없습니다.")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        
        # 점수 기반 정렬
        df = df.sort_values('supply_score', ascending=False)
        
        # 결과 저장
        output_path = os.path.join(self.data_dir, 'screening_result.csv')
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ 스크리닝 완료: {len(df)}개 종목")
        print(f"   결과 저장: {output_path}")
        
        return df
    
    def _analyze_stock(
        self, 
        ticker: str, 
        market: str,
        start_date: str,
        end_date: str
    ) -> Optional[Dict]:
        """개별 종목 분석"""
        try:
            # 종목명
            name = stock.get_market_ticker_name(ticker)
            
            # 제외 조건 (ETF, 스팩 등)
            if any(kw in name for kw in ['스팩', 'ETF', 'ETN', '리츠']):
                return None
            
            # OHLCV 데이터
            ohlcv = stock.get_market_ohlcv(start_date, end_date, ticker)
            if ohlcv.empty or len(ohlcv) < 20:
                return None
            
            # 시가총액 체크
            latest = ohlcv.iloc[-1]
            
            # 수급 데이터
            supply = stock.get_market_net_purchases_of_equities(
                start_date, end_date, ticker
            )
            
            if supply.empty:
                return None
            
            # 외국인/기관 순매매 집계
            foreign_5d = supply['외국인합계'].tail(5).sum() if '외국인합계' in supply.columns else 0
            foreign_20d = supply['외국인합계'].tail(20).sum() if '외국인합계' in supply.columns else 0
            inst_5d = supply['기관합계'].tail(5).sum() if '기관합계' in supply.columns else 0
            inst_20d = supply['기관합계'].tail(20).sum() if '기관합계' in supply.columns else 0
            
            # 연속 매수일 계산
            foreign_consecutive = self._count_consecutive_buys(supply, '외국인합계')
            inst_consecutive = self._count_consecutive_buys(supply, '기관합계')
            
            # 수급 점수 계산 (0-100)
            supply_score = self._calculate_supply_score(
                foreign_5d, foreign_20d, inst_5d, inst_20d,
                foreign_consecutive, inst_consecutive
            )
            
            # 수급 단계 판단
            stage = self._determine_stage(foreign_5d, inst_5d)
            
            # 기술적 지표
            close_prices = ohlcv['종가']
            change_pct = ((latest['종가'] - ohlcv['종가'].iloc[-2]) / ohlcv['종가'].iloc[-2]) * 100
            
            # VCP 패턴 체크
            is_vcp = self._check_vcp_pattern(ohlcv)
            
            return {
                'ticker': ticker,
                'name': name,
                'market': market,
                'close': int(latest['종가']),
                'change_pct': round(change_pct, 2),
                'volume': int(latest['거래량']),
                'trading_value': int(latest.get('거래대금', 0)),
                
                # 수급
                'foreign_5d': int(foreign_5d),
                'foreign_20d': int(foreign_20d),
                'foreign_consecutive': foreign_consecutive,
                'inst_5d': int(inst_5d),
                'inst_20d': int(inst_20d),
                'inst_consecutive': inst_consecutive,
                
                # 점수
                'supply_score': supply_score,
                'stage': stage,
                'is_double_buy': foreign_5d > 0 and inst_5d > 0,
                'is_vcp': is_vcp,
            }
            
        except Exception as e:
            return None
    
    def _count_consecutive_buys(self, df: pd.DataFrame, column: str) -> int:
        """연속 매수일 계산"""
        if column not in df.columns:
            return 0
        
        count = 0
        for val in df[column].iloc[::-1]:
            if val > 0:
                count += 1
            else:
                break
        return count
    
    def _calculate_supply_score(
        self,
        foreign_5d: int,
        foreign_20d: int,
        inst_5d: int,
        inst_20d: int,
        foreign_consecutive: int,
        inst_consecutive: int,
    ) -> float:
        """수급 점수 계산 (0-100)"""
        score = 50.0  # 기준점
        
        # 외국인 점수 (최대 ±25점)
        if foreign_5d > self.thresholds.foreign_strong_buy:
            score += 15
        elif foreign_5d > self.thresholds.foreign_buy:
            score += 10
        elif foreign_5d > 0:
            score += 5
        elif foreign_5d < self.thresholds.foreign_strong_sell:
            score -= 15
        elif foreign_5d < self.thresholds.foreign_sell:
            score -= 10
        
        # 기관 점수 (최대 ±15점)
        if inst_5d > self.thresholds.inst_strong_buy:
            score += 10
        elif inst_5d > self.thresholds.inst_buy:
            score += 5
        elif inst_5d < self.thresholds.inst_strong_sell:
            score -= 10
        
        # 연속 매수 보너스
        score += min(foreign_consecutive, 5) * 2
        score += min(inst_consecutive, 5) * 1
        
        # 쌍끌이 보너스
        if foreign_5d > 0 and inst_5d > 0:
            score += 10
        
        return max(0, min(100, score))
    
    def _determine_stage(self, foreign_5d: int, inst_5d: int) -> str:
        """수급 단계 판단"""
        if foreign_5d > self.thresholds.foreign_strong_buy and inst_5d > 0:
            return "강한매집"
        elif foreign_5d > self.thresholds.foreign_buy:
            return "매집"
        elif foreign_5d > 0:
            return "약매집"
        elif foreign_5d < self.thresholds.foreign_strong_sell:
            return "강한분산"
        elif foreign_5d < self.thresholds.foreign_sell:
            return "분산"
        elif foreign_5d < 0:
            return "약분산"
        else:
            return "중립"
    
    def _check_vcp_pattern(self, ohlcv: pd.DataFrame) -> bool:
        """VCP (변동성 수축 패턴) 체크"""
        if len(ohlcv) < 60:
            return False
        
        try:
            # 최근 60일 데이터
            recent = ohlcv.tail(60)
            
            # 변동폭 계산 (각 20일 구간)
            ranges = []
            for i in range(0, 60, 20):
                segment = recent.iloc[i:i+20]
                if len(segment) >= 20:
                    high = segment['고가'].max()
                    low = segment['저가'].min()
                    ranges.append((high - low) / low * 100)
            
            if len(ranges) < 3:
                return False
            
            # 변동폭이 점점 줄어드는지 확인
            return ranges[0] > ranges[1] > ranges[2]
            
        except:
            return False
    
    def generate_signals(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """시그널 생성"""
        if df.empty:
            return []
        
        # 조건 필터링
        filtered = df[
            (df['supply_score'] >= 70) &  # 점수 70점 이상
            (df['stage'].isin(['강한매집', '매집', '약매집']))  # 매집 단계
        ]
        
        # 상위 N개
        top = filtered.head(top_n)
        
        signals = []
        for _, row in top.iterrows():
            signals.append({
                'ticker': row['ticker'],
                'name': row['name'],
                'market': row['market'],
                'close': row['close'],
                'change_pct': row['change_pct'],
                'supply_score': row['supply_score'],
                'stage': row['stage'],
                'foreign_5d': row['foreign_5d'],
                'inst_5d': row['inst_5d'],
                'is_double_buy': row['is_double_buy'],
                'is_vcp': row['is_vcp'],
                'signal_time': datetime.now().isoformat(),
            })
        
        # 저장
        if signals:
            output_path = os.path.join(self.data_dir, 'signals.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(signals, f, ensure_ascii=False, indent=2)
        
        return signals


if __name__ == "__main__":
    screener = SmartMoneyScreener()
    results = screener.run_screening(max_stocks=50)
    
    if not results.empty:
        print("\n📊 상위 10개 종목:")
        print(results[['name', 'close', 'supply_score', 'stage', 'is_double_buy']].head(10))
