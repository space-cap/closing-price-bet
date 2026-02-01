#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Gate - 시장 상태 분석
KOSPI 200 섹터 ETF 분석 기반 시장 건강도 측정
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    print("yfinance 설치 필요: pip install yfinance")
    yf = None


# 섹터 ETF 목록 (KOSPI 200 기반)
SECTOR_ETFS = {
    "반도체": "091160.KS",      # KODEX 반도체
    "2차전지": "305720.KS",     # KODEX 2차전지산업
    "자동차": "091180.KS",      # KODEX 자동차
    "바이오": "244580.KS",      # KODEX 바이오
    "금융": "091170.KS",        # KODEX 은행
    "철강": "117700.KS",        # KODEX 철강
    "건설": "117680.KS",        # KODEX 건설
    "화학": "117690.KS",        # KODEX 화학
    "IT": "091160.KS",          # KODEX 반도체 (대표)
    "에너지": "117460.KS",      # KODEX 에너지화학
}

# 지수 티커
INDEX_TICKERS = {
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "USD/KRW": "KRW=X",
    "VIX": "^VIX",
}


class MarketGate:
    """시장 진입 조건 분석기"""
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def analyze(self) -> Dict:
        """
        시장 상태 분석
        
        Returns:
            {
                "gate": "GREEN" | "YELLOW" | "RED",
                "score": 0-100,
                "kospi": {...},
                "kosdaq": {...},
                "sectors": [...],
                "analysis": {...},
            }
        """
        print("=" * 60)
        print("🚦 Market Gate 분석 시작")
        print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        if yf is None:
            print("❌ yfinance 모듈이 필요합니다.")
            return {"gate": "YELLOW", "score": 50, "error": "yfinance not installed"}
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "gate": "YELLOW",
            "score": 50,
            "kospi": {},
            "kosdaq": {},
            "usd_krw": {},
            "sectors": [],
            "analysis": {},
        }
        
        try:
            # 1. 지수 분석
            print("\n[1/3] 지수 분석 중...")
            
            kospi_data = self._analyze_index("KOSPI")
            kosdaq_data = self._analyze_index("KOSDAQ")
            usd_krw_data = self._get_usd_krw()
            
            result["kospi"] = kospi_data
            result["kosdaq"] = kosdaq_data
            result["usd_krw"] = usd_krw_data
            
            # 2. 섹터 분석
            print("\n[2/3] 섹터 분석 중...")
            sectors = self._analyze_sectors()
            result["sectors"] = sectors
            
            # 3. 게이트 판단
            print("\n[3/3] 게이트 판단 중...")
            gate, score, analysis = self._determine_gate(
                kospi_data, kosdaq_data, usd_krw_data, sectors
            )
            
            result["gate"] = gate
            result["score"] = score
            result["analysis"] = analysis
            
            # 결과 저장
            output_path = os.path.join(self.data_dir, 'market_gate.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # 결과 출력
            print("\n" + "=" * 60)
            self._print_result(result)
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ 분석 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _analyze_index(self, index_name: str) -> Dict:
        """지수 분석"""
        ticker = INDEX_TICKERS.get(index_name)
        if not ticker:
            return {}
        
        try:
            data = yf.download(ticker, period="6mo", progress=False)
            
            if data.empty:
                return {}
            
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else data.iloc[-1]
            
            close = float(latest['Close'])
            change = close - float(prev['Close'])
            change_pct = (change / float(prev['Close'])) * 100
            
            # 이동평균
            closes = data['Close']
            ma5 = float(closes.tail(5).mean())
            ma20 = float(closes.tail(20).mean())
            ma60 = float(closes.tail(60).mean()) if len(closes) >= 60 else float(closes.mean())
            
            # 이평선 정렬 상태
            if close > ma5 > ma20 > ma60:
                alignment = "정배열"
            elif close < ma5 < ma20 < ma60:
                alignment = "역배열"
            else:
                alignment = "혼조"
            
            # RSI 계산
            delta = closes.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))
            
            return {
                "name": index_name,
                "close": round(close, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "ma5": round(ma5, 2),
                "ma20": round(ma20, 2),
                "ma60": round(ma60, 2),
                "alignment": alignment,
                "rsi": round(float(rsi), 2) if not pd.isna(rsi) else 50.0,
            }
            
        except Exception as e:
            print(f"   {index_name} 분석 오류: {e}")
            return {}
    
    def _get_usd_krw(self) -> Dict:
        """환율 조회"""
        try:
            data = yf.download("KRW=X", period="1mo", progress=False)
            
            if data.empty:
                return {"rate": 1350, "change_pct": 0}
            
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else data.iloc[-1]
            
            rate = float(latest['Close'])
            change_pct = ((rate - float(prev['Close'])) / float(prev['Close'])) * 100
            
            return {
                "rate": round(rate, 2),
                "change_pct": round(change_pct, 2),
            }
            
        except Exception as e:
            return {"rate": 1350, "change_pct": 0}
    
    def _analyze_sectors(self) -> List[Dict]:
        """섹터별 분석"""
        sectors = []
        
        for sector_name, ticker in list(SECTOR_ETFS.items())[:6]:  # 주요 6개만
            try:
                data = yf.download(ticker, period="3mo", progress=False)
                
                if data.empty:
                    continue
                
                latest = data.iloc[-1]
                prev = data.iloc[-2] if len(data) > 1 else data.iloc[-1]
                
                close = float(latest['Close'])
                change_pct = ((close - float(prev['Close'])) / float(prev['Close'])) * 100
                
                # 이평선
                closes = data['Close']
                ma20 = float(closes.tail(20).mean())
                
                # 점수 (MA20 대비 위치 기반)
                score = ((close - ma20) / ma20 * 100) + 50
                score = max(0, min(100, score))
                
                sectors.append({
                    "name": sector_name,
                    "ticker": ticker,
                    "close": round(close, 0),
                    "change_pct": round(change_pct, 2),
                    "vs_ma20": round((close / ma20 - 1) * 100, 2),
                    "score": round(score, 1),
                })
                
            except Exception as e:
                continue
        
        # 점수순 정렬
        sectors.sort(key=lambda x: x['score'], reverse=True)
        
        return sectors
    
    def _determine_gate(
        self,
        kospi: Dict,
        kosdaq: Dict,
        usd_krw: Dict,
        sectors: List[Dict]
    ) -> tuple:
        """게이트 판단"""
        score = 50.0
        reasons = []
        
        # KOSPI 분석 (±20점)
        if kospi:
            if kospi.get('alignment') == "정배열":
                score += 10
                reasons.append("KOSPI 정배열")
            elif kospi.get('alignment') == "역배열":
                score -= 15
                reasons.append("KOSPI 역배열")
            
            rsi = kospi.get('rsi', 50)
            if rsi > 70:
                score -= 5
                reasons.append("KOSPI RSI 과매수")
            elif rsi < 30:
                score += 5
                reasons.append("KOSPI RSI 과매도 반등 기대")
            
            if kospi.get('change_pct', 0) > 1:
                score += 5
            elif kospi.get('change_pct', 0) < -1:
                score -= 5
        
        # KOSDAQ 분석 (±10점)
        if kosdaq:
            if kosdaq.get('alignment') == "정배열":
                score += 5
            elif kosdaq.get('alignment') == "역배열":
                score -= 10
        
        # 환율 분석 (±10점)
        if usd_krw:
            rate = usd_krw.get('rate', 1350)
            if rate > 1450:
                score -= 15
                reasons.append("환율 위험 (>1450)")
            elif rate > 1400:
                score -= 10
                reasons.append("환율 경고 (>1400)")
            elif rate < 1300:
                score += 5
                reasons.append("환율 안정 (<1300)")
        
        # 섹터 분석 (±10점)
        if sectors:
            strong_sectors = sum(1 for s in sectors if s['score'] > 60)
            weak_sectors = sum(1 for s in sectors if s['score'] < 40)
            
            if strong_sectors >= 4:
                score += 10
                reasons.append(f"강세 섹터 {strong_sectors}개")
            elif weak_sectors >= 4:
                score -= 10
                reasons.append(f"약세 섹터 {weak_sectors}개")
        
        # 최종 점수 (0-100)
        score = max(0, min(100, score))
        
        # 게이트 판단
        if score >= 70:
            gate = "GREEN"
        elif score >= 40:
            gate = "YELLOW"
        else:
            gate = "RED"
        
        analysis = {
            "reasons": reasons,
            "kospi_alignment": kospi.get('alignment', ''),
            "kosdaq_alignment": kosdaq.get('alignment', ''),
            "usd_krw_rate": usd_krw.get('rate', 0),
            "strong_sectors": [s['name'] for s in sectors if s['score'] > 60][:3],
            "weak_sectors": [s['name'] for s in sectors if s['score'] < 40][:3],
        }
        
        return gate, round(score, 1), analysis
    
    def _print_result(self, result: Dict):
        """결과 출력"""
        gate = result.get('gate', 'YELLOW')
        score = result.get('score', 50)
        
        gate_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(gate, "🟡")
        
        print(f"\n{gate_emoji} Market Gate: {gate} (점수: {score}/100)")
        
        # KOSPI
        kospi = result.get('kospi', {})
        if kospi:
            print(f"\n📈 KOSPI: {kospi.get('close', 0):,.2f} ({kospi.get('change_pct', 0):+.2f}%)")
            print(f"   이평선: {kospi.get('alignment', '')} | RSI: {kospi.get('rsi', 50):.1f}")
        
        # KOSDAQ
        kosdaq = result.get('kosdaq', {})
        if kosdaq:
            print(f"\n📈 KOSDAQ: {kosdaq.get('close', 0):,.2f} ({kosdaq.get('change_pct', 0):+.2f}%)")
            print(f"   이평선: {kosdaq.get('alignment', '')}")
        
        # 환율
        usd_krw = result.get('usd_krw', {})
        if usd_krw:
            print(f"\n💱 USD/KRW: {usd_krw.get('rate', 0):,.2f} ({usd_krw.get('change_pct', 0):+.2f}%)")
        
        # 섹터
        sectors = result.get('sectors', [])
        if sectors:
            print("\n📊 섹터:")
            for s in sectors[:5]:
                emoji = "🟢" if s['score'] > 60 else ("🔴" if s['score'] < 40 else "🟡")
                print(f"   {emoji} {s['name']}: {s['change_pct']:+.2f}% (점수: {s['score']:.0f})")
        
        # 분석 결과
        analysis = result.get('analysis', {})
        reasons = analysis.get('reasons', [])
        if reasons:
            print(f"\n📋 분석: {' | '.join(reasons)}")


if __name__ == "__main__":
    gate = MarketGate()
    result = gate.analyze()
