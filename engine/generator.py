"""
시그널 생성기 (Main Engine)
- Collector로부터 데이터 수집
- Scorer로 점수 계산
- PositionSizer로 자금 관리
- 최종 Signal 생성
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
import time
import sys
import os
import json

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import SignalConfig, Grade
from engine.models import Signal, ScoreDetail, ChecklistDetail, ScreenerResult
from engine.collectors import KRXCollector, EnhancedNewsCollector
from engine.scorer import Scorer
from engine.position_sizer import PositionSizer
from engine.llm_analyzer import LLMAnalyzer


class SignalGenerator:
    """종가베팅 시그널 생성기"""
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig()
        self.scorer = Scorer(self.config)
        self.position_sizer = PositionSizer(self.config)
        self.llm_analyzer = LLMAnalyzer()
    
    async def run(self, capital: float = 100_000_000) -> ScreenerResult:
        """
        스크리너 실행
        
        Args:
            capital: 투자 자본금
            
        Returns:
            ScreenerResult
        """
        start_time = time.time()
        self.position_sizer.set_capital(capital)
        
        print("=" * 60)
        print("🚀 종가베팅 V2 스크리너 시작")
        print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   자본금: {capital:,.0f}원")
        print("=" * 60)
        
        signals: List[Signal] = []
        total_candidates = 0
        
        try:
            async with KRXCollector(self.config) as collector:
                async with EnhancedNewsCollector(self.config) as news_collector:
                    
                    # 1. 상승률 상위 종목 수집
                    print("\n[1/4] 상승률 상위 종목 조회 중...")
                    
                    kospi_stocks = await collector.get_top_gainers("KOSPI", 20)
                    kosdaq_stocks = await collector.get_top_gainers("KOSDAQ", 30)
                    
                    all_stocks = kospi_stocks + kosdaq_stocks
                    total_candidates = len(all_stocks)
                    
                    print(f"      KOSPI: {len(kospi_stocks)}개, KOSDAQ: {len(kosdaq_stocks)}개")
                    print(f"      총 {total_candidates}개 종목 분석 대상")
                    
                    if not all_stocks:
                        print("⚠️  분석 대상 종목이 없습니다.")
                        return ScreenerResult(
                            date=date.today(),
                            total_candidates=0,
                            filtered_count=0,
                            signals=[],
                            processing_time_ms=0,
                        )
                    
                    # 2. 각 종목별 상세 데이터 수집
                    print("\n[2/4] 종목별 상세 데이터 수집 중...")
                    
                    for i, stock in enumerate(all_stocks):
                        progress = f"[{i+1}/{len(all_stocks)}]"
                        print(f"  {progress} {stock.code} {stock.name}...", end="", flush=True)
                        
                        try:
                            # 차트 데이터
                            charts = await collector.get_chart_data(stock.code, 60)
                            
                            # 수급 데이터
                            supply = await collector.get_supply_data(stock.code)
                            
                            # 뉴스 데이터
                            news_list = await news_collector.get_stock_news(
                                stock.code, 
                                limit=5, 
                                name=stock.name
                            )
                            
                            # LLM 분석 (뉴스가 있을 때만)
                            llm_result = None
                            if news_list:
                                llm_result = await self.llm_analyzer.analyze_news(
                                    stock.name, 
                                    news_list
                                )
                            
                            # 점수 계산
                            score, checklist = self.scorer.calculate(
                                stock, charts, news_list, supply, llm_result
                            )
                            
                            # 등급 결정
                            grade = self.scorer.determine_grade(stock, score)
                            
                            # C등급 제외
                            if grade == Grade.C:
                                print(f" ❌ C등급")
                                continue
                            
                            # 포지션 계산
                            entry_price = stock.close
                            stop_price = self.position_sizer.calculate_stop_loss(entry_price)
                            target_price = self.position_sizer.calculate_target_price(entry_price)
                            
                            position = self.position_sizer.calculate_position(
                                entry_price, stop_price, grade
                            )
                            
                            # 시그널 생성
                            signal = Signal(
                                stock_code=stock.code,
                                stock_name=stock.name,
                                market=stock.market,
                                sector=stock.sector or "",
                                signal_date=date.today(),
                                signal_time=datetime.now(),
                                grade=grade,
                                score=score,
                                checklist=checklist,
                                news_items=[
                                    {"title": n.title, "source": n.source, "url": n.url}
                                    for n in news_list[:3]
                                ],
                                current_price=stock.close,
                                entry_price=entry_price,
                                stop_price=stop_price,
                                target_price=target_price,
                                r_value=position["r_value"],
                                position_size=position["position_value"],
                                quantity=position["quantity"],
                                r_multiplier=position.get("r_multiplier", 1.0),
                                trading_value=stock.trading_value,
                                change_pct=stock.change_pct,
                            )
                            
                            signals.append(signal)
                            print(f" ✅ {grade.value}등급 ({score.total}점)")
                            
                        except Exception as e:
                            print(f" ⚠️ 오류: {e}")
                            continue
                        
                        # Rate limit
                        await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"\n❌ 스크리너 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 결과 정리
        elapsed_ms = (time.time() - start_time) * 1000
        
        # 등급별/마켓별 통계
        by_grade = {}
        by_market = {}
        
        for s in signals:
            g = s.grade.value if hasattr(s.grade, 'value') else str(s.grade)
            by_grade[g] = by_grade.get(g, 0) + 1
            by_market[s.market] = by_market.get(s.market, 0) + 1
        
        # 등급순으로 정렬 (S > A > B)
        signals.sort(key=lambda x: (
            0 if x.grade == Grade.S else (1 if x.grade == Grade.A else 2),
            -x.score.total
        ))
        
        result = ScreenerResult(
            date=date.today(),
            total_candidates=total_candidates,
            filtered_count=len(signals),
            signals=signals,
            by_grade=by_grade,
            by_market=by_market,
            processing_time_ms=elapsed_ms,
        )
        
        # 결과 출력
        print("\n" + "=" * 60)
        print("📊 스크리닝 결과")
        print("=" * 60)
        print(f"  분석 종목: {total_candidates}개")
        print(f"  시그널: {len(signals)}개")
        print(f"  등급별: {by_grade}")
        print(f"  시장별: {by_market}")
        print(f"  소요시간: {elapsed_ms/1000:.1f}초")
        print("=" * 60)
        
        if signals:
            print("\n🔥 TOP 시그널:")
            for i, s in enumerate(signals[:5]):
                grade_str = s.grade.value if hasattr(s.grade, 'value') else str(s.grade)
                print(f"  {i+1}. [{grade_str}] {s.stock_name} ({s.stock_code})")
                print(f"     점수: {s.score.total}점 | 등락률: +{s.change_pct:.1f}%")
                print(f"     진입가: {s.entry_price:,.0f} | 손절가: {s.stop_price:,.0f}")
        
        return result


async def run_screener(capital: float = 100_000_000, save_result: bool = True) -> ScreenerResult:
    """
    스크리너 실행 함수 (외부 호출용)
    
    Args:
        capital: 투자 자본금
        save_result: 결과 저장 여부
        
    Returns:
        ScreenerResult
    """
    generator = SignalGenerator()
    result = await generator.run(capital)
    
    if save_result and result.signals:
        # 결과 저장
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # 최신 결과
        latest_path = os.path.join(data_dir, 'jongga_v2_latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 날짜별 결과
        date_str = result.date.strftime("%Y%m%d")
        dated_path = os.path.join(data_dir, f'jongga_v2_results_{date_str}.json')
        with open(dated_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장됨:")
        print(f"   {latest_path}")
        print(f"   {dated_path}")
    
    return result


if __name__ == "__main__":
    # 직접 실행
    asyncio.run(run_screener())
