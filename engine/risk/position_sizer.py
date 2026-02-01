# engine/risk/position_sizer.py
"""
🎯 Phoenix V4 - Kelly Criterion Position Sizer
과학적 포지션 사이징으로 리스크 관리
"""

from typing import Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Kelly Criterion 기반 포지션 사이징
    
    공식: Kelly % = W - [(1-W) / R]
    
    W = 승률 (Win Rate)
    R = 평균 수익 / 평균 손실 (Risk/Reward Ratio)
    """
    
    def __init__(self, account_size: float = 1000000):
        self.account_size = account_size
        self.default_win_rate = 0.55  # 55% 기본 승률
        self.default_rr_ratio = 1.5   # 1.5:1 손익비
        self.max_risk_per_trade = 0.05  # 최대 5%
    
    def calculate_kelly(self, win_rate: float, rr_ratio: float) -> float:
        """
        Kelly 공식 계산
        
        Args:
            win_rate: 승률 (0-1)
            rr_ratio: 손익비 (Risk/Reward)
        
        Returns:
            Kelly % (0-1)
        """
        if rr_ratio <= 0:
            return 0.0
        
        kelly = win_rate - ((1 - win_rate) / rr_ratio)
        
        # 음수면 0 (거래하지 않음)
        if kelly < 0:
            return 0.0
        
        return kelly
    
    def calculate_half_kelly(self, win_rate: float, rr_ratio: float) -> float:
        """
        Half Kelly (보수적 접근)
        - Kelly의 절반만 사용하여 변동성 감소
        """
        full_kelly = self.calculate_kelly(win_rate, rr_ratio)
        return full_kelly / 2
    
    def calculate_position_size(
        self,
        signal_type: str,
        entry_price: float,
        stop_loss: float = None,
        take_profit: float = None,
        win_rate: float = None,
        account_size: float = None
    ) -> Dict:
        """
        포지션 크기 계산
        
        Args:
            signal_type: "A", "B", "C", "WAIT"
            entry_price: 진입 가격
            stop_loss: 손절가 (선택)
            take_profit: 익절가 (선택)
            win_rate: 승률 (선택, 기본값 사용)
            account_size: 계좌 크기 (선택)
        
        Returns:
            포지션 정보 딕셔너리
        """
        account = account_size or self.account_size
        
        # 신호 타입별 기본 Kelly 비율
        kelly_limits = {
            "A": 0.04,  # 4% (강한 신호)
            "B": 0.02,  # 2% (중간 신호)
            "C": 0.01,  # 1% (약한 신호)
            "WAIT": 0.0  # 거래 안함
        }
        
        max_kelly = kelly_limits.get(signal_type, 0.0)
        
        if max_kelly == 0:
            return {
                "signal_type": signal_type,
                "action": "NO_TRADE",
                "reason": "신호 강도 부족",
                "position_size_krw": 0,
                "quantity": 0,
                "kelly_percent": 0,
                "entry_price": entry_price
            }
        
        # 손절가 기본값 (-2%)
        if stop_loss is None:
            stop_loss = entry_price * 0.98
        
        # 익절가 기본값 (+4%)
        if take_profit is None:
            take_profit = entry_price * 1.04
        
        # 손익비 계산
        potential_loss = abs(entry_price - stop_loss)
        potential_gain = abs(take_profit - entry_price)
        rr_ratio = potential_gain / potential_loss if potential_loss > 0 else 1.5
        
        # 승률 기본값
        win_rate = win_rate or self.default_win_rate
        
        # Half Kelly 계산
        kelly = self.calculate_half_kelly(win_rate, rr_ratio)
        
        # Kelly를 신호 타입 최대값으로 제한
        kelly = min(kelly, max_kelly)
        
        # 절대 최대값 제한 (5%)
        kelly = min(kelly, self.max_risk_per_trade)
        
        # 포지션 크기 계산
        position_size = account * kelly
        quantity = position_size / entry_price if entry_price > 0 else 0
        
        return {
            "signal_type": signal_type,
            "action": "BUY",
            "entry_price": entry_price,
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "position_size_krw": round(position_size, 0),
            "quantity": round(quantity, 6),
            "kelly_percent": round(kelly * 100, 2),
            "max_kelly_percent": max_kelly * 100,
            "risk_reward_ratio": round(rr_ratio, 2),
            "win_rate": win_rate,
            "expected_value": round((win_rate * potential_gain) - ((1 - win_rate) * potential_loss), 2),
            "risk_krw": round(position_size * (potential_loss / entry_price), 0),
            "reward_krw": round(position_size * (potential_gain / entry_price), 0),
            "timestamp": datetime.now().isoformat()
        }
    
    def scale_in_positions(
        self,
        signal_type: str,
        entry_prices: list,
        stop_loss: float,
        take_profit: float,
        account_size: float = None
    ) -> Dict:
        """
        분할 진입 계산 (Scaling Entry)
        
        Args:
            signal_type: 신호 타입
            entry_prices: [진입가1, 진입가2, 진입가3] 3단계
            stop_loss: 공통 손절가
            take_profit: 공통 익절가
            account_size: 계좌 크기
        
        Returns:
            분할 진입 계획
        """
        account = account_size or self.account_size
        
        # 전체 Kelly 계산
        total_position = self.calculate_position_size(
            signal_type=signal_type,
            entry_price=entry_prices[0],
            stop_loss=stop_loss,
            take_profit=take_profit,
            account_size=account
        )
        
        total_kelly = total_position["kelly_percent"] / 100
        total_size = total_position["position_size_krw"]
        
        # 3단계 분할 (40%, 30%, 30%)
        splits = [0.4, 0.3, 0.3]
        
        entries = []
        for i, (price, split) in enumerate(zip(entry_prices, splits)):
            size = total_size * split
            entries.append({
                "entry_number": i + 1,
                "entry_price": price,
                "position_size_krw": round(size, 0),
                "quantity": round(size / price, 6) if price > 0 else 0,
                "percent_of_total": split * 100
            })
        
        return {
            "signal_type": signal_type,
            "strategy": "SCALE_IN",
            "total_kelly_percent": round(total_kelly * 100, 2),
            "total_position_krw": round(total_size, 0),
            "entries": entries,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "timestamp": datetime.now().isoformat()
        }


# 테스트
if __name__ == "__main__":
    sizer = PositionSizer(account_size=10_000_000)  # 1천만원
    
    # Type A 신호 테스트
    result = sizer.calculate_position_size(
        signal_type="A",
        entry_price=145_000_000,  # BTC 1.45억
        stop_loss=142_100_000,    # -2%
        take_profit=150_800_000   # +4%
    )
    
    print("=" * 60)
    print("🎯 Kelly Criterion 포지션 사이징")
    print("=" * 60)
    print(f"신호 타입: {result['signal_type']}")
    print(f"Kelly %: {result['kelly_percent']}%")
    print(f"포지션 크기: {result['position_size_krw']:,.0f} KRW")
    print(f"수량: {result['quantity']:.6f}")
    print(f"손익비: {result['risk_reward_ratio']}")
    print(f"예상 손실: {result['risk_krw']:,.0f} KRW")
    print(f"예상 수익: {result['reward_krw']:,.0f} KRW")
