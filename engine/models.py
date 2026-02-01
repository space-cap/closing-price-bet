"""
종가베팅 V2 데이터 모델
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


class SignalStatus(Enum):
    """시그널 상태"""
    PENDING = "pending"     # 대기 중
    ACTIVE = "active"       # 진입 완료
    CLOSED = "closed"       # 청산 완료
    EXPIRED = "expired"     # 만료


@dataclass
class StockData:
    """종목 데이터"""
    code: str
    name: str
    market: str                     # KOSPI / KOSDAQ
    sector: str = ""
    
    # 가격 정보
    close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    change_pct: float = 0.0
    
    # 거래 정보
    volume: int = 0
    trading_value: int = 0          # 거래대금
    marcap: int = 0                 # 시가총액
    
    # 기타
    high_52w: float = 0.0           # 52주 고가
    low_52w: float = 0.0            # 52주 저가


@dataclass
class NewsItem:
    """뉴스 아이템"""
    title: str
    summary: str = ""
    source: str = ""
    url: str = ""
    published_at: Optional[datetime] = None
    relevance: float = 0.0          # 관련도 점수


@dataclass
class SupplyData:
    """수급 데이터"""
    code: str
    
    # 외국인
    foreign_buy_5d: int = 0
    foreign_buy_20d: int = 0
    foreign_consecutive_days: int = 0
    
    # 기관
    inst_buy_5d: int = 0
    inst_buy_20d: int = 0
    inst_consecutive_days: int = 0
    
    # 쌍끌이 여부
    is_double_buy: bool = False


@dataclass
class ChartData:
    """차트 데이터 (일봉)"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class ScoreDetail:
    """점수 상세"""
    news: int = 0           # 뉴스/재료 (0-3)
    volume: int = 0         # 거래대금 (0-3)
    chart: int = 0          # 차트패턴 (0-2)
    candle: int = 0         # 캔들형태 (0-1)
    consolidation: int = 0  # 기간조정 (0-1)
    supply: int = 0         # 수급 (0-2)
    llm_reason: str = ""    # LLM 분석 이유
    
    @property
    def total(self) -> int:
        return self.news + self.volume + self.chart + self.candle + self.consolidation + self.supply
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['total'] = self.total
        return d


@dataclass
class ChecklistDetail:
    """체크리스트 상세"""
    has_news: bool = False              # 뉴스 존재
    news_sources: List[str] = field(default_factory=list)
    is_new_high: bool = False           # 신고가
    is_breakout: bool = False           # 돌파
    supply_positive: bool = False       # 수급 긍정
    volume_surge: bool = False          # 거래량 급증
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Signal:
    """종가베팅 시그널"""
    stock_code: str
    stock_name: str
    market: str
    sector: str
    
    # 시그널 정보
    signal_date: date
    signal_time: datetime
    grade: Any                  # Grade enum
    score: ScoreDetail
    checklist: ChecklistDetail
    
    # 뉴스
    news_items: List[Dict] = field(default_factory=list)
    
    # 가격 정보
    current_price: float = 0.0
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_price: float = 0.0
    
    # 리스크 관리
    r_value: float = 0.0
    position_size: float = 0.0
    quantity: int = 0
    r_multiplier: float = 1.0
    
    # 거래 정보
    trading_value: int = 0
    change_pct: float = 0.0
    
    # 상태
    status: SignalStatus = SignalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "market": self.market,
            "sector": self.sector,
            "signal_date": self.signal_date.isoformat() if isinstance(self.signal_date, date) else self.signal_date,
            "signal_time": self.signal_time.isoformat() if isinstance(self.signal_time, datetime) else self.signal_time,
            "grade": self.grade.value if hasattr(self.grade, 'value') else str(self.grade),
            "score": self.score.to_dict() if hasattr(self.score, 'to_dict') else self.score,
            "checklist": self.checklist.to_dict() if hasattr(self.checklist, 'to_dict') else self.checklist,
            "news_items": self.news_items,
            "current_price": self.current_price,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "target_price": self.target_price,
            "r_value": self.r_value,
            "position_size": self.position_size,
            "quantity": self.quantity,
            "r_multiplier": self.r_multiplier,
            "trading_value": self.trading_value,
            "change_pct": self.change_pct,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }


@dataclass
class ScreenerResult:
    """스크리너 결과"""
    date: date
    total_candidates: int
    filtered_count: int
    signals: List[Signal]
    by_grade: Dict[str, int] = field(default_factory=dict)
    by_market: Dict[str, int] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "total_candidates": self.total_candidates,
            "filtered_count": self.filtered_count,
            "signals": [s.to_dict() for s in self.signals],
            "by_grade": self.by_grade,
            "by_market": self.by_market,
            "processing_time_ms": self.processing_time_ms,
        }
