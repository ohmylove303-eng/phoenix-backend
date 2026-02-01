# engine/analysis/technical.py
"""
📊 기술적 분석 모듈
RSI, 피보나치, 매물대, 엘리엇 파동 분석
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """기술적 분석 엔진"""
    
    def __init__(self):
        pass
    
    def analyze(self, candles: List[Dict], symbol: str = '') -> Dict:
        """
        종합 기술 분석 수행
        
        Returns:
            {
                "rsi": {"value": 58, "signal": "중립", "zone": "neutral"},
                "fibonacci": {"levels": {...}, "current_zone": "0.382-0.5"},
                "volume_profile": {"resistance": 120000000, "support": 115000000},
                "elliott": {"wave": 3, "phase": "상승", "target": 125000000},
                "trade_levels": {"buy": 114500000, "sell": 118000000, "stop": 112000000}
            }
        """
        if not candles or len(candles) < 14:
            return self._empty_analysis()
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c.get('volume', 0) for c in candles]
        
        current_price = closes[-1]
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "rsi": self._calculate_rsi(closes),
            "fibonacci": self._calculate_fibonacci(highs, lows, current_price),
            "volume_profile": self._calculate_volume_profile(candles),
            "elliott": self._analyze_elliott(closes, highs, lows),
            "trade_levels": self._calculate_trade_levels(candles),
            "summary": self._generate_summary(closes, highs, lows),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> Dict:
        """RSI 계산"""
        if len(closes) < period + 1:
            return {"value": 50, "signal": "데이터 부족", "zone": "neutral"}
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        # EMA 기반 RSI
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi = round(rsi, 1)
        
        # 신호 판단
        if rsi >= 70:
            signal = "과매수"
            zone = "overbought"
        elif rsi <= 30:
            signal = "과매도"
            zone = "oversold"
        elif rsi >= 60:
            signal = "강세"
            zone = "bullish"
        elif rsi <= 40:
            signal = "약세"
            zone = "bearish"
        else:
            signal = "중립"
            zone = "neutral"
        
        return {"value": rsi, "signal": signal, "zone": zone}
    
    def _calculate_fibonacci(self, highs: List[float], lows: List[float], current: float) -> Dict:
        """피보나치 레벨 계산"""
        high = max(highs)
        low = min(lows)
        diff = high - low
        
        if diff == 0:
            return {"levels": {}, "current_zone": "알 수 없음", "trend": "횡보"}
        
        levels = {
            "0.0": round(high, 0),
            "0.236": round(high - diff * 0.236, 0),
            "0.382": round(high - diff * 0.382, 0),
            "0.5": round(high - diff * 0.5, 0),
            "0.618": round(high - diff * 0.618, 0),
            "0.786": round(high - diff * 0.786, 0),
            "1.0": round(low, 0)
        }
        
        # 현재 가격 위치 판단
        for i, (level, price) in enumerate(levels.items()):
            if current >= price:
                if i == 0:
                    zone = "고점 돌파"
                else:
                    prev_level = list(levels.keys())[i-1]
                    zone = f"{prev_level} - {level}"
                break
        else:
            zone = "저점 이탈"
        
        # 추세 판단
        if current > levels["0.5"]:
            trend = "상승 추세"
        elif current < levels["0.5"]:
            trend = "하락 추세"
        else:
            trend = "중립"
        
        return {
            "levels": levels,
            "current_zone": zone,
            "trend": trend,
            "high": high,
            "low": low
        }
    
    def _calculate_volume_profile(self, candles: List[Dict]) -> Dict:
        """매물대 분석 (간략화)"""
        if not candles:
            return {"resistance": 0, "support": 0, "zones": []}
        
        # 가격대별 거래량 집계
        price_volumes = {}
        
        for c in candles:
            # 가격을 일정 단위로 그룹화
            price_unit = round(c['close'] / 100000) * 100000  # 10만원 단위
            vol = c.get('volume', 0)
            
            if price_unit not in price_volumes:
                price_volumes[price_unit] = 0
            price_volumes[price_unit] += vol
        
        if not price_volumes:
            return {"resistance": 0, "support": 0, "zones": []}
        
        # 상위 거래량 가격대 찾기
        sorted_zones = sorted(price_volumes.items(), key=lambda x: x[1], reverse=True)
        
        current = candles[-1]['close']
        
        # 저항선: 현재가보다 높은 매물대
        resistance_zones = [(p, v) for p, v in sorted_zones if p > current]
        resistance = resistance_zones[0][0] if resistance_zones else 0
        
        # 지지선: 현재가보다 낮은 매물대
        support_zones = [(p, v) for p, v in sorted_zones if p < current]
        support = support_zones[0][0] if support_zones else 0
        
        return {
            "resistance": resistance,
            "support": support,
            "zones": sorted_zones[:5]  # 상위 5개 매물대
        }
    
    def _analyze_elliott(self, closes: List[float], highs: List[float], lows: List[float]) -> Dict:
        """엘리엇 파동 분석 (간략화)"""
        if len(closes) < 20:
            return {"wave": 0, "phase": "분석 불가", "target": 0}
        
        # 간단한 파동 분석 (최근 추세 기반)
        recent_closes = closes[-20:]
        trend_start = recent_closes[0]
        trend_end = recent_closes[-1]
        trend_mid = recent_closes[10]
        
        # 추세 방향
        is_uptrend = trend_end > trend_start
        
        # 파동 위치 추정 (매우 간략화)
        if is_uptrend:
            if trend_end > trend_mid > trend_start:
                wave = 3
                phase = "3파 상승"
            elif trend_end < trend_mid:
                wave = 4
                phase = "4파 조정"
            else:
                wave = 5
                phase = "5파 마무리"
            
            # 목표가 (피보나치 확장)
            diff = max(highs[-20:]) - min(lows[-20:])
            target = round(trend_end + diff * 0.618, 0)
        else:
            if trend_end < trend_mid < trend_start:
                wave = -3  # 하락 3파
                phase = "하락 3파"
            else:
                wave = -4
                phase = "하락 4파 반등"
            
            diff = max(highs[-20:]) - min(lows[-20:])
            target = round(trend_end - diff * 0.382, 0)
        
        return {
            "wave": abs(wave),
            "phase": phase,
            "direction": "상승" if is_uptrend else "하락",
            "target": target
        }
    
    def _calculate_trade_levels(self, candles: List[Dict]) -> Dict:
        """매수/매도 레벨 계산"""
        if not candles:
            return {"buy": 0, "sell": 0, "stop": 0}
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        current = closes[-1]
        
        # ATR 기반 레벨 (Average True Range)
        tr_list = []
        for i in range(1, min(14, len(candles))):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        
        atr = sum(tr_list) / len(tr_list) if tr_list else current * 0.02
        
        # 레벨 계산
        buy = round(current - atr * 0.5, 0)  # 현재가 - 0.5 ATR
        sell = round(current + atr * 1.5, 0)  # 현재가 + 1.5 ATR
        stop = round(current - atr * 2, 0)  # 손절: 2 ATR
        
        return {
            "buy": buy,
            "sell": sell,
            "stop": stop,
            "risk_reward": round((sell - current) / (current - stop), 2) if current != stop else 0
        }
    
    def _generate_summary(self, closes: List[float], highs: List[float], lows: List[float]) -> str:
        """분석 요약 생성"""
        if len(closes) < 5:
            return "데이터 부족"
        
        # 최근 추세
        recent_change = (closes[-1] - closes[-5]) / closes[-5] * 100
        
        if recent_change > 5:
            return "강한 상승세. 추세 추종 매매 고려."
        elif recent_change > 2:
            return "상승 중. 지지선 확인 후 진입 고려."
        elif recent_change < -5:
            return "강한 하락세. 반등 확인 후 진입 권장."
        elif recent_change < -2:
            return "하락 중. 지지선 이탈 주의."
        else:
            return "횡보 구간. 돌파 방향 확인 필요."
    
    def _empty_analysis(self) -> Dict:
        """빈 분석 결과"""
        return {
            "symbol": "",
            "current_price": 0,
            "rsi": {"value": 50, "signal": "데이터 없음", "zone": "neutral"},
            "fibonacci": {"levels": {}, "current_zone": "알 수 없음", "trend": ""},
            "volume_profile": {"resistance": 0, "support": 0, "zones": []},
            "elliott": {"wave": 0, "phase": "분석 불가", "target": 0},
            "trade_levels": {"buy": 0, "sell": 0, "stop": 0},
            "summary": "데이터가 부족합니다.",
            "timestamp": datetime.now().isoformat()
        }


# 테스트
if __name__ == "__main__":
    from candles import CandleCollector
    
    print("📊 기술적 분석 테스트")
    
    collector = CandleCollector()
    analyzer = TechnicalAnalyzer()
    
    candles = collector.get_candles('BTC', '1h', 48)
    result = analyzer.analyze(candles, 'BTC')
    
    print(f"\n📈 BTC 분석 결과:")
    print(f"   현재가: ₩{result['current_price']:,.0f}")
    print(f"   RSI: {result['rsi']['value']} ({result['rsi']['signal']})")
    print(f"   피보나치 위치: {result['fibonacci']['current_zone']}")
    print(f"   엘리엇 파동: {result['elliott']['phase']}")
    print(f"   매수가: ₩{result['trade_levels']['buy']:,.0f}")
    print(f"   매도가: ₩{result['trade_levels']['sell']:,.0f}")
    print(f"   요약: {result['summary']}")
