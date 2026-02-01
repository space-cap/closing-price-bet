"""
12점 점수 시스템 (Scorer)
"""

from typing import List, Tuple, Optional, Dict
from engine.config import SignalConfig, Grade
from engine.models import StockData, NewsItem, SupplyData, ChartData, ScoreDetail, ChecklistDetail


class Scorer:
    """종가베팅 점수 계산기 (12점 만점)"""
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig()
    
    def calculate(
        self,
        stock: StockData,
        charts: List[ChartData],
        news_list: List[NewsItem],
        supply: Optional[SupplyData],
        llm_result: Optional[Dict] = None,
    ) -> Tuple[ScoreDetail, ChecklistDetail]:
        """
        점수 계산
        
        Returns:
            (ScoreDetail, ChecklistDetail)
        """
        score = ScoreDetail()
        checklist = ChecklistDetail()
        
        # 1. 뉴스/재료 점수 (0-3)
        news_score, news_sources = self._score_news(news_list, llm_result)
        score.news = news_score
        checklist.has_news = len(news_list) > 0
        checklist.news_sources = news_sources
        
        if llm_result:
            score.llm_reason = llm_result.get('reason', '')
        
        # 2. 거래대금 점수 (0-3)
        score.volume = self._score_volume(stock.trading_value)
        checklist.volume_surge = stock.trading_value >= 500_000_000_000  # 5천억 이상
        
        # 3. 차트패턴 점수 (0-2)
        chart_score, is_new_high, is_breakout = self._score_chart(stock, charts)
        score.chart = chart_score
        checklist.is_new_high = is_new_high
        checklist.is_breakout = is_breakout
        
        # 4. 캔들형태 점수 (0-1)
        score.candle = self._score_candle(stock)
        
        # 5. 기간조정 점수 (0-1)
        score.consolidation = self._score_consolidation(charts)
        
        # 6. 수급 점수 (0-2)
        supply_score, supply_positive = self._score_supply(supply)
        score.supply = supply_score
        checklist.supply_positive = supply_positive
        
        return score, checklist
    
    def _score_news(
        self,
        news_list: List[NewsItem],
        llm_result: Optional[Dict] = None
    ) -> Tuple[int, List[str]]:
        """뉴스/재료 점수 (0-3)"""
        sources = [n.source for n in news_list if n.source]
        
        # LLM 결과가 있으면 그 점수 사용
        if llm_result and 'score' in llm_result:
            llm_score = llm_result.get('score', 0)
            return min(3, llm_score), sources
        
        # 폴백: 키워드 기반 점수
        if not news_list:
            return 0, []
        
        score = 0
        
        for news in news_list:
            title = news.title + news.summary
            
            # 긍정 키워드 체크
            for kw in self.config.positive_keywords:
                if kw in title:
                    score += 1
                    break
            
            # 부정 키워드 체크 (감점)
            for kw in self.config.negative_keywords:
                if kw in title:
                    score -= 1
                    break
        
        # 기본 점수 (뉴스 존재 시)
        if score == 0 and news_list:
            score = 1
        
        return max(0, min(3, score)), sources
    
    def _score_volume(self, trading_value: int) -> int:
        """거래대금 점수 (0-3)"""
        if trading_value >= 1_000_000_000_000:  # 1조 이상
            return 3
        elif trading_value >= 500_000_000_000:   # 5천억 이상
            return 2
        elif trading_value >= 100_000_000_000:   # 1천억 이상
            return 1
        return 0
    
    def _score_chart(
        self,
        stock: StockData,
        charts: List[ChartData]
    ) -> Tuple[int, bool, bool]:
        """차트패턴 점수 (0-2)"""
        score = 0
        is_new_high = False
        is_breakout = False
        
        if not charts or len(charts) < 20:
            return score, is_new_high, is_breakout
        
        # 최근 20일 고가
        recent_high = max(c.high for c in charts[-20:])
        
        # 52주 고가 근처 (5% 이내)
        if stock.high_52w > 0:
            if stock.close >= stock.high_52w * 0.95:
                score += 1
                is_new_high = True
        
        # 최근 20일 고가 돌파
        if stock.close > recent_high:
            score += 1
            is_breakout = True
        
        # 이평선 정배열 체크
        if len(charts) >= 60:
            closes = [c.close for c in charts]
            ma5 = sum(closes[-5:]) / 5
            ma20 = sum(closes[-20:]) / 20
            ma60 = sum(closes[-60:]) / 60
            
            if ma5 > ma20 > ma60:
                score += 1
        
        return min(2, score), is_new_high, is_breakout
    
    def _score_candle(self, stock: StockData) -> int:
        """캔들형태 점수 (0-1)"""
        if stock.close == 0 or stock.open == 0:
            return 0
        
        # 양봉 확인
        body = stock.close - stock.open
        if body <= 0:
            return 0
        
        # 장대양봉 (시가 대비 5% 이상 상승)
        body_pct = (body / stock.open) * 100
        
        # 윗꼬리 짧음 (1% 이내)
        upper_wick = stock.high - stock.close
        upper_wick_pct = (upper_wick / stock.close) * 100 if stock.close > 0 else 0
        
        if body_pct >= 3 and upper_wick_pct <= 1.5:
            return 1
        
        return 0
    
    def _score_consolidation(self, charts: List[ChartData]) -> int:
        """기간조정 점수 (0-1) - 횡보 후 돌파"""
        if not charts or len(charts) < 20:
            return 0
        
        # 최근 20일 변동폭 계산
        recent = charts[-20:-1]  # 오늘 제외
        if not recent:
            return 0
        
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        
        range_high = max(highs)
        range_low = min(lows)
        
        if range_low == 0:
            return 0
        
        # 변동폭이 10% 이내면 횡보
        range_pct = ((range_high - range_low) / range_low) * 100
        
        # 오늘 이 범위를 돌파했는지
        today = charts[-1]
        
        if range_pct <= 15 and today.close > range_high:
            return 1
        
        return 0
    
    def _score_supply(self, supply: Optional[SupplyData]) -> Tuple[int, bool]:
        """수급 점수 (0-2)"""
        if not supply:
            return 0, False
        
        score = 0
        positive = False
        
        # 외국인 5일 순매수
        if supply.foreign_buy_5d > 0:
            score += 1
            positive = True
        
        # 기관 5일 순매수
        if supply.inst_buy_5d > 0:
            score += 1
            positive = True
        
        # 쌍끌이 보너스
        if supply.is_double_buy:
            positive = True
        
        return min(2, score), positive
    
    def determine_grade(self, stock: StockData, score: ScoreDetail) -> Grade:
        """등급 결정"""
        total = score.total
        trading_value = stock.trading_value
        
        # S등급: 10점+ & 거래대금 1조+
        if total >= 10 and trading_value >= 1_000_000_000_000:
            return Grade.S
        
        # A등급: 8점+ & 거래대금 5천억+
        if total >= 8 and trading_value >= 500_000_000_000:
            return Grade.A
        
        # B등급: 6점+ & 거래대금 1천억+
        if total >= 6 and trading_value >= 100_000_000_000:
            return Grade.B
        
        # C등급
        return Grade.C
