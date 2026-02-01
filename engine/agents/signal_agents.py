# engine/agents/signal_agents.py
"""
🎯 Phoenix NICE Signal Agents
5개 분석 에이전트: Technical, OnChain, Sentiment, Macro, Institutional
"""

import math
from typing import Dict, List


class MathLib:
    """기술적 분석 수학 도우미"""
    
    @staticmethod
    def sma(data: List[float], window: int) -> float:
        if len(data) < window: return data[-1] if data else 0
        return sum(data[-window:]) / window
    
    @staticmethod
    def std(data: List[float], window: int) -> float:
        if len(data) < window: return 0
        avg = sum(data[-window:]) / window
        var = sum((x - avg) ** 2 for x in data[-window:]) / window
        return math.sqrt(var)
    
    @staticmethod
    def ema(data: List[float], window: int) -> float:
        if len(data) < window: return data[-1] if data else 0
        alpha = 2 / (window + 1)
        ema = data[0]
        for p in data[1:]:
            ema = (p * alpha) + (ema * (1 - alpha))
        return ema
    
    @staticmethod
    def rsi(prices: List[float], window: int = 14) -> float:
        if len(prices) < window + 1: return 50
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-window:]) / window
        avg_loss = sum(losses[-window:]) / window
        
        if avg_loss == 0: return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))


class TechnicalAgent:
    """기술적 분석 에이전트: RSI, MACD, Bollinger Bands"""
    
    def __init__(self):
        self.name = "technical"
        self.weight = 0.3
    
    def analyze(self, candles: List[Dict] = None, market_data: Dict = None) -> Dict:
        # 캔들 데이터가 없으면 market_data 기반 간이 분석
        if not candles and market_data:
            return self._simple_analysis(market_data)
        
        if not candles or len(candles) < 5:
            return {"score": 50, "details": "데이터 부족"}
        
        closes = [c.get('close', c.get('price', 0)) for c in candles]
        
        # RSI
        current_rsi = MathLib.rsi(closes)
        
        # Bollinger Bands
        ma20 = MathLib.sma(closes, 20)
        std = MathLib.std(closes, 20)
        upper = ma20 + (std * 2)
        lower = ma20 - (std * 2)
        curr_price = closes[-1]
        
        # MACD
        ema12 = MathLib.ema(closes, 12)
        ema26 = MathLib.ema(closes, 26)
        macd = ema12 - ema26
        
        score = 50
        if current_rsi < 30: score += 25
        elif current_rsi > 70: score -= 25
        
        if curr_price < lower: score += 15
        elif curr_price > upper: score -= 15
        
        if macd > 0: score += 10
        else: score -= 10
        
        return {
            "score": int(max(0, min(100, score))),
            "details": f"RSI:{current_rsi:.1f} MACD:{macd:.0f}"
        }
    
    def _simple_analysis(self, market_data: Dict) -> Dict:
        """market_data만으로 간이 분석"""
        change_rate = market_data.get('change_rate', 0)
        
        score = 50
        if change_rate > 5: score += 20
        elif change_rate < -5: score -= 20
        elif change_rate > 2: score += 10
        elif change_rate < -2: score -= 10
        
        return {
            "score": int(max(0, min(100, score))),
            "details": f"변동률:{change_rate:+.2f}%"
        }


class OnChainAgent:
    """온체인 분석 에이전트: 거래량, 대형 거래"""
    
    def __init__(self):
        self.name = "onchain"
        self.weight = 0.2
    
    def analyze(self, candles: List[Dict] = None, market_data: Dict = None) -> Dict:
        if market_data:
            volume = market_data.get('volume_24h', 0)
            # 거래량 임계치 (간이)
            score = 60 if volume > 0 else 40
            return {"score": score, "details": f"Vol: {volume:,.0f}"}
        
        if not candles or len(candles) < 5:
            return {"score": 50, "details": "데이터 부족"}
        
        vols = [c.get('volume', 0) for c in candles]
        avg_vol = MathLib.sma(vols, 20) if len(vols) >= 20 else sum(vols) / len(vols)
        curr_vol = vols[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        
        score = 50
        if vol_ratio > 2.0: score += 25
        elif vol_ratio > 1.5: score += 15
        
        return {"score": min(100, score), "details": f"Vol Ratio: {vol_ratio:.1f}x"}


class SentimentAgent:
    """센티먼트 분석 에이전트: 모멘텀, 공포/탐욕"""
    
    def __init__(self):
        self.name = "sentiment"
        self.weight = 0.15
    
    def analyze(self, candles: List[Dict] = None, market_data: Dict = None) -> Dict:
        if market_data:
            change_rate = market_data.get('change_rate', 0)
            score = int(50 + change_rate * 3)  # 3배 가중
            return {
                "score": max(0, min(100, score)),
                "details": f"Momentum: {change_rate:+.2f}%"
            }
        
        if not candles or len(candles) < 5:
            return {"score": 50, "details": "데이터 부족"}
        
        closes = [c.get('close', c.get('price', 0)) for c in candles]
        ret = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if closes[-5] > 0 else 0
        
        return {
            "score": int(max(0, min(100, 50 + ret * 2))),
            "details": f"Mom(5): {ret:+.1f}%"
        }


class MacroAgent:
    """거시경제 분석 에이전트"""
    
    def __init__(self):
        self.name = "macro"
        self.weight = 0.15
    
    def analyze(self, candles: List[Dict] = None, market_data: Dict = None) -> Dict:
        # 간단한 시장 상태 분석 (실제로는 Fear & Greed Index 등 사용)
        return {"score": 55, "details": "Market: Neutral"}


class InstitutionalAgent:
    """기관 동향 분석 에이전트: 추세 방향"""
    
    def __init__(self):
        self.name = "institutional"
        self.weight = 0.2
    
    def analyze(self, candles: List[Dict] = None, market_data: Dict = None) -> Dict:
        if market_data:
            price = market_data.get('price', 0)
            high = market_data.get('high_24h', price)
            low = market_data.get('low_24h', price)
            
            if high > low:
                position = (price - low) / (high - low)
                score = int(30 + position * 40)  # 30~70 범위
            else:
                score = 50
            
            return {"score": score, "details": f"Price Position: {position*100:.0f}%"}
        
        if not candles or len(candles) < 50:
            return {"score": 50, "details": "데이터 부족"}
        
        closes = [c.get('close', c.get('price', 0)) for c in candles]
        ma50 = MathLib.sma(closes, 50)
        ma20 = MathLib.sma(closes, 20)
        
        score = 70 if ma20 > ma50 else 30
        trend = "Bull" if ma20 > ma50 else "Bear"
        
        return {"score": score, "details": f"Trend: {trend}"}


class SignalAggregator:
    """모든 에이전트 신호 종합"""
    
    def __init__(self):
        self.agents = [
            TechnicalAgent(),
            OnChainAgent(),
            SentimentAgent(),
            MacroAgent(),
            InstitutionalAgent()
        ]
    
    def get_all_signals(self, candles: List[Dict] = None, market_data: Dict = None) -> Dict:
        scores = {}
        weighted_total = 0
        total_weight = 0
        
        for agent in self.agents:
            res = agent.analyze(candles=candles, market_data=market_data)
            scores[agent.name] = res['score']
            weighted_total += res['score'] * agent.weight
            total_weight += agent.weight
        
        avg_score = weighted_total / total_weight if total_weight > 0 else 50
        
        # 신호 결정
        if avg_score >= 70:
            signal = "BUY"
            signal_type = "TYPE A"
        elif avg_score >= 55:
            signal = "BUY"
            signal_type = "TYPE B"
        elif avg_score <= 30:
            signal = "SELL"
            signal_type = "TYPE C"
        else:
            signal = "HOLD"
            signal_type = "TYPE C"
        
        return {
            "agent_scores": scores,
            "weighted_score": int(avg_score),
            "signal": signal,
            "signal_type": signal_type,
            "confidence": min(95, 60 + abs(avg_score - 50))
        }


# ==================== 테스트 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 Signal Agents Test")
    print("=" * 60)
    
    # 테스트 데이터
    market_data = {
        'symbol': 'BTC',
        'price': 130000000,
        'change_rate': 3.5,
        'volume_24h': 1000000000,
        'high_24h': 135000000,
        'low_24h': 125000000
    }
    
    aggregator = SignalAggregator()
    result = aggregator.get_all_signals(market_data=market_data)
    
    print(f"\n📊 BTC 분석 결과:")
    for agent, score in result['agent_scores'].items():
        print(f"   {agent}: {score}/100")
    print(f"\n   종합점수: {result['weighted_score']}/100")
    print(f"   신호: {result['signal']} ({result['signal_type']})")
    print(f"   신뢰도: {result['confidence']}%")
