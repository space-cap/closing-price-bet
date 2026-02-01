"""
포지션 사이저 - R값 기반 자금 관리
"""

from typing import Optional
from engine.config import SignalConfig, Grade


class PositionSizer:
    """R값 기반 포지션 계산기"""
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig()
        self.capital: float = 100_000_000  # 기본 자본금 1억
        self.r_ratio: float = 0.005        # R 비율 0.5%
    
    def set_capital(self, capital: float):
        """자본금 설정"""
        self.capital = capital
    
    def calculate_position(
        self,
        entry_price: float,
        stop_price: float,
        grade: Grade,
    ) -> dict:
        """
        포지션 계산
        
        Args:
            entry_price: 진입가
            stop_price: 손절가
            grade: 종목 등급
            
        Returns:
            {
                "r_value": R 금액,
                "risk_per_share": 주당 리스크,
                "quantity": 매수 수량,
                "position_value": 포지션 금액,
                "position_pct": 자본 대비 비율(%),
            }
        """
        # 기본 R 금액
        base_r = self.capital * self.r_ratio
        
        # 등급별 배팅 조절
        grade_config = self.config.grade_configs.get(grade)
        if grade_config:
            r_multiplier = grade_config.r_multiplier
        else:
            r_multiplier = 1.0
        
        r_value = base_r * r_multiplier
        
        # C등급은 매매 안함
        if grade == Grade.C:
            return {
                "r_value": 0,
                "risk_per_share": 0,
                "quantity": 0,
                "position_value": 0,
                "position_pct": 0,
            }
        
        # 주당 리스크 (진입가 - 손절가)
        risk_per_share = entry_price - stop_price
        
        if risk_per_share <= 0:
            return {
                "r_value": r_value,
                "risk_per_share": 0,
                "quantity": 0,
                "position_value": 0,
                "position_pct": 0,
            }
        
        # 매수 수량 = R 금액 / 주당 리스크
        quantity = int(r_value / risk_per_share)
        
        # 포지션 금액
        position_value = quantity * entry_price
        
        # 자본 대비 비율
        position_pct = (position_value / self.capital) * 100 if self.capital > 0 else 0
        
        return {
            "r_value": r_value,
            "risk_per_share": risk_per_share,
            "quantity": quantity,
            "position_value": position_value,
            "position_pct": round(position_pct, 2),
        }
    
    def calculate_stop_loss(self, entry_price: float) -> float:
        """손절가 계산"""
        return entry_price * (1 - self.config.stop_loss_pct)
    
    def calculate_target_price(self, entry_price: float) -> float:
        """목표가 계산"""
        return entry_price * (1 + self.config.take_profit_pct)
    
    def calculate_risk_reward(
        self,
        entry_price: float,
        stop_price: float,
        target_price: float
    ) -> float:
        """리스크 대비 수익률 (R:R)"""
        risk = entry_price - stop_price
        reward = target_price - entry_price
        
        if risk <= 0:
            return 0
        
        return round(reward / risk, 2)
