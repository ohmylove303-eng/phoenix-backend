# engine/agents/signal_agents.py
"""
🎯 Phoenix V4 - 5 Signal Agents
NICE v4를 넘어서는 5레이어 분석 시스템
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List
from datetime import datetime
import os

logger = logging.getLogger(__name__)


# ============================================================================
# Layer 1: TECHNICAL AGENT (기술 분석)
# ============================================================================

class TechnicalAgent:
    """기술적 분석 에이전트 - RSI, MACD, Bollinger Bands, EMA"""
    
    def __init__(self):
        self.name = "Technical Agent"
        self.weight = 0.20  # 20%
    
    async def analyze(self, symbol: str) -> Dict:
        """기술 분석 실행"""
        try:
            # Upbit에서 OHLCV 데이터 가져오기
            url = "https://api.upbit.com/v1/candles/minutes/60"
            params = {"market": f"KRW-{symbol}", "count": 100}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return self._fallback_score()
                    data = await resp.json()
            
            if not data:
                return self._fallback_score()
            
            # 가격 데이터 추출
            closes = [c['trade_price'] for c in reversed(data)]
            
            # RSI 계산
            rsi = self._calculate_rsi(closes)
            
            # MACD 계산
            macd, signal, histogram = self._calculate_macd(closes)
            
            # 볼린저밴드
            upper, middle, lower = self._calculate_bollinger(closes)
            
            current_price = closes[-1]
            
            # 점수 계산 (0-100)
            score = 50
            
            # RSI 기반
            if rsi < 30:
                score += 20  # 과매도 = 매수 기회
            elif rsi > 70:
                score -= 15  # 과매수 = 주의
            
            # MACD 기반
            if histogram > 0:
                score += 15
            elif histogram < 0:
                score -= 10
            
            # 볼린저 기반
            if current_price < lower * 1.02:
                score += 15  # 하단 = 매수 기회
            elif current_price > upper * 0.98:
                score -= 10  # 상단 = 주의
            
            score = max(0, min(100, score))
            
            return {
                "score": int(score),
                "rsi": round(rsi, 1),
                "macd": round(macd, 2),
                "histogram": round(histogram, 2),
                "bollinger_position": "상단" if current_price > upper * 0.95 else "하단" if current_price < lower * 1.05 else "중간",
                "agent_name": self.name
            }
            
        except Exception as e:
            logger.warning(f"TechnicalAgent error: {e}")
            return self._fallback_score()
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        
        gains, losses = [], []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            gains.append(max(diff, 0))
            losses.append(abs(min(diff, 0)))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: List[float]) -> tuple:
        if len(prices) < 26:
            return (0, 0, 0)
        
        ema12 = self._ema(prices, 12)
        ema26 = self._ema(prices, 26)
        macd = ema12 - ema26
        signal = self._ema([macd], 9)
        return (macd, signal, macd - signal)
    
    def _ema(self, prices: List[float], period: int) -> float:
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = price * multiplier + ema * (1 - multiplier)
        return ema
    
    def _calculate_bollinger(self, prices: List[float], period: int = 20) -> tuple:
        if len(prices) < period:
            return (0, 0, 0)
        
        import math
        sma = sum(prices[-period:]) / period
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)
        return (sma + 2 * std, sma, sma - 2 * std)
    
    def _fallback_score(self) -> Dict:
        return {"score": 50, "rsi": 50, "macd": 0, "histogram": 0, "bollinger_position": "중간", "agent_name": self.name}


# ============================================================================
# Layer 2: ONCHAIN AGENT (온체인 분석)
# ============================================================================

class OnChainAgent:
    """온체인 데이터 에이전트 - 거래량, Whale 활동"""
    
    def __init__(self):
        self.name = "OnChain Agent"
        self.weight = 0.20  # 20%
    
    async def analyze(self, symbol: str) -> Dict:
        """온체인 분석 실행"""
        try:
            url = "https://api.upbit.com/v1/candles/minutes/60"
            params = {"market": f"KRW-{symbol}", "count": 24}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return self._fallback_score()
                    data = await resp.json()
            
            if not data:
                return self._fallback_score()
            
            # 거래량 분석
            volumes = [c['candle_acc_trade_volume'] for c in data]
            current_volume = volumes[0]
            avg_volume = sum(volumes[1:]) / len(volumes[1:]) if len(volumes) > 1 else 1
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # 가격 변화
            price_change = (data[0]['trade_price'] - data[-1]['trade_price']) / data[-1]['trade_price'] * 100 if data else 0
            
            score = 50
            
            # 거래량 급증 + 가격 상승 = 강한 매수 신호
            if volume_ratio > 1.5:
                if price_change > 0:
                    score += 25
                else:
                    score -= 15
            
            # 거래량 증가
            if volume_ratio > 1.2:
                score += 10
            
            score = max(0, min(100, score))
            
            return {
                "score": int(score),
                "volume_ratio": round(volume_ratio, 2),
                "price_change_24h": round(price_change, 2),
                "whale_activity": "활발" if volume_ratio > 1.5 else "보통" if volume_ratio > 1 else "저조",
                "agent_name": self.name
            }
            
        except Exception as e:
            logger.warning(f"OnChainAgent error: {e}")
            return self._fallback_score()
    
    def _fallback_score(self) -> Dict:
        return {"score": 50, "volume_ratio": 1.0, "price_change_24h": 0, "whale_activity": "알 수 없음", "agent_name": self.name}


# ============================================================================
# Layer 3: SENTIMENT AGENT (심리 분석)
# ============================================================================

class SentimentAgent:
    """감정 분석 에이전트 - Fear & Greed Index"""
    
    def __init__(self):
        self.name = "Sentiment Agent"
        self.weight = 0.15  # 15%
    
    async def analyze(self, symbol: str) -> Dict:
        """심리 분석 실행"""
        try:
            # Fear & Greed Index 가져오기
            url = "https://api.alternative.me/fng/?limit=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return self._fallback_score()
                    data = await resp.json()
            
            fng_value = int(data['data'][0]['value'])
            fng_class = data['data'][0]['value_classification']
            
            # 점수 계산 (역발상)
            score = 50
            
            if fng_value < 25:  # 극도의 공포
                score = 85  # 강한 매수 신호
            elif fng_value < 40:  # 공포
                score = 70
            elif fng_value < 60:  # 중립
                score = 50
            elif fng_value < 75:  # 탐욕
                score = 35
            else:  # 극도의 탐욕
                score = 20  # 매도 신호
            
            return {
                "score": int(score),
                "fear_greed_index": fng_value,
                "fear_greed_class": fng_class,
                "market_sentiment": "공포" if fng_value < 40 else "중립" if fng_value < 60 else "탐욕",
                "agent_name": self.name
            }
            
        except Exception as e:
            logger.warning(f"SentimentAgent error: {e}")
            return self._fallback_score()
    
    def _fallback_score(self) -> Dict:
        return {"score": 50, "fear_greed_index": 50, "fear_greed_class": "Neutral", "market_sentiment": "알 수 없음", "agent_name": self.name}


# ============================================================================
# Layer 4: MACRO AGENT (매크로 분석)
# ============================================================================

class MacroAgent:
    """거시경제 에이전트 - BTC 도미넌스, VIX"""
    
    def __init__(self):
        self.name = "Macro Agent"
        self.weight = 0.20  # 20%
    
    async def analyze(self, symbol: str) -> Dict:
        """매크로 분석 실행"""
        try:
            # CoinGecko Global 데이터
            url = "https://api.coingecko.com/api/v3/global"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return self._fallback_score()
                    data = await resp.json()
            
            btc_dominance = data['data']['market_cap_percentage']['btc']
            market_cap_change_24h = data['data']['market_cap_change_percentage_24h_usd']
            
            score = 50
            
            # BTC 도미넌스 분석
            if symbol == "BTC":
                if btc_dominance > 50:
                    score += 15  # BTC 강세
                elif btc_dominance < 40:
                    score -= 10
            else:
                # 알트코인은 도미넌스 낮을 때 강세
                if btc_dominance < 45:
                    score += 15
                elif btc_dominance > 55:
                    score -= 10
            
            # 전체 시장 추세
            if market_cap_change_24h > 2:
                score += 15
            elif market_cap_change_24h > 0:
                score += 5
            elif market_cap_change_24h < -2:
                score -= 10
            
            score = max(0, min(100, score))
            
            return {
                "score": int(score),
                "btc_dominance": round(btc_dominance, 2),
                "market_cap_change_24h": round(market_cap_change_24h, 2),
                "market_trend": "상승" if market_cap_change_24h > 1 else "하락" if market_cap_change_24h < -1 else "횡보",
                "agent_name": self.name
            }
            
        except Exception as e:
            logger.warning(f"MacroAgent error: {e}")
            return self._fallback_score()
    
    def _fallback_score(self) -> Dict:
        return {"score": 50, "btc_dominance": 50, "market_cap_change_24h": 0, "market_trend": "알 수 없음", "agent_name": self.name}


# ============================================================================
# Layer 5: INSTITUTIONAL AGENT (기관 분석)
# ============================================================================

class InstitutionalAgent:
    """기관투자자 에이전트 - ETF 유입, 기관 자금"""
    
    def __init__(self):
        self.name = "Institutional Agent"
        self.weight = 0.25  # 25% (가장 중요)
    
    async def analyze(self, symbol: str) -> Dict:
        """기관 분석 실행"""
        try:
            # CoinGecko에서 시장 데이터
            symbol_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
                'XRP': 'ripple', 'ADA': 'cardano', 'AVAX': 'avalanche-2'
            }
            coin_id = symbol_map.get(symbol.upper(), symbol.lower())
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            params = {"localization": "false", "tickers": "false", "community_data": "false"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return self._fallback_score()
                    data = await resp.json()
            
            market_data = data.get('market_data', {})
            
            # 24시간 가격 변화
            price_change_24h = market_data.get('price_change_percentage_24h', 0)
            # 7일 가격 변화
            price_change_7d = market_data.get('price_change_percentage_7d', 0)
            # 시가총액 순위
            market_cap_rank = market_data.get('market_cap_rank', 100)
            
            score = 50
            
            # 시가총액 상위 = 기관 관심
            if market_cap_rank <= 10:
                score += 15
            elif market_cap_rank <= 30:
                score += 10
            
            # 가격 추세 (기관 매집 신호)
            if price_change_24h > 3 and price_change_7d > 5:
                score += 20  # 지속 상승 = 기관 매집
            elif price_change_24h > 0:
                score += 10
            elif price_change_24h < -5:
                score -= 15  # 급락 = 기관 이탈
            
            score = max(0, min(100, score))
            
            return {
                "score": int(score),
                "price_change_24h": round(price_change_24h, 2),
                "price_change_7d": round(price_change_7d, 2),
                "market_cap_rank": market_cap_rank,
                "institutional_interest": "높음" if score >= 70 else "보통" if score >= 50 else "낮음",
                "agent_name": self.name
            }
            
        except Exception as e:
            logger.warning(f"InstitutionalAgent error: {e}")
            return self._fallback_score()
    
    def _fallback_score(self) -> Dict:
        return {"score": 50, "price_change_24h": 0, "price_change_7d": 0, "market_cap_rank": 100, "institutional_interest": "알 수 없음", "agent_name": self.name}


# ============================================================================
# SIGNAL AGGREGATOR (5 Agent 통합)
# ============================================================================

class SignalAggregator:
    """5개 에이전트 신호를 통합하여 최종 신호 생성"""
    
    def __init__(self):
        self.technical = TechnicalAgent()
        self.onchain = OnChainAgent()
        self.sentiment = SentimentAgent()
        self.macro = MacroAgent()
        self.institutional = InstitutionalAgent()
    
    async def get_all_signals(self, symbol: str) -> Dict:
        """모든 에이전트 신호 병렬 수집"""
        
        # 병렬 실행
        results = await asyncio.gather(
            self.technical.analyze(symbol),
            self.onchain.analyze(symbol),
            self.sentiment.analyze(symbol),
            self.macro.analyze(symbol),
            self.institutional.analyze(symbol),
            return_exceptions=True
        )
        
        agent_results = {
            "technical": results[0] if not isinstance(results[0], Exception) else {"score": 50},
            "onchain": results[1] if not isinstance(results[1], Exception) else {"score": 50},
            "sentiment": results[2] if not isinstance(results[2], Exception) else {"score": 50},
            "macro": results[3] if not isinstance(results[3], Exception) else {"score": 50},
            "institutional": results[4] if not isinstance(results[4], Exception) else {"score": 50}
        }
        
        # 가중 평균 점수 계산
        weights = {
            "technical": 0.20,
            "onchain": 0.20,
            "sentiment": 0.15,
            "macro": 0.20,
            "institutional": 0.25
        }
        
        weighted_score = sum(
            agent_results[agent]["score"] * weights[agent]
            for agent in agent_results
        )
        
        # Type A/B/C 판정
        signal_type = self._determine_signal_type(weighted_score, agent_results)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "agent_scores": {agent: agent_results[agent]["score"] for agent in agent_results},
            "agent_details": agent_results,
            "weighted_score": round(weighted_score, 1),
            "signal_type": signal_type,
            "recommendation": self._get_recommendation(signal_type, weighted_score)
        }
    
    def _determine_signal_type(self, score: float, agents: Dict) -> Dict:
        """Type A/B/C 판정"""
        
        # 개별 에이전트 점수 확인
        tech_score = agents["technical"]["score"]
        onchain_score = agents["onchain"]["score"]
        institutional_score = agents["institutional"]["score"]
        
        # Type A: 강한 신호 (신뢰도 75%)
        if score >= 75 and tech_score >= 70 and institutional_score >= 65:
            return {
                "type": "A",
                "confidence": 75,
                "color": "green",
                "action": "강력 매수",
                "kelly_max": 0.04  # 4%
            }
        
        # Type B: 중간 신호 (신뢰도 60%)
        elif score >= 60 and tech_score >= 55:
            return {
                "type": "B",
                "confidence": 60,
                "color": "yellow",
                "action": "조건부 매수",
                "kelly_max": 0.02  # 2%
            }
        
        # Type C: 약한 신호 (신뢰도 45%)
        elif score >= 45:
            return {
                "type": "C",
                "confidence": 45,
                "color": "orange",
                "action": "관망",
                "kelly_max": 0.01  # 1%
            }
        
        # 위험: 매도 고려
        else:
            return {
                "type": "WAIT",
                "confidence": 30,
                "color": "red",
                "action": "매도 또는 대기",
                "kelly_max": 0.0
            }
    
    def _get_recommendation(self, signal_type: Dict, score: float) -> Dict:
        """거래 추천 생성"""
        
        recommendations = {
            "A": {
                "단타": {"kelly": "4%", "time": "5-30분", "target": "+2%", "stop": "-1%"},
                "단기": {"kelly": "3%", "time": "30분-2시간", "target": "+3%", "stop": "-1.5%"},
                "중기": {"kelly": "2%", "time": "2시간-1일", "target": "+5%", "stop": "-2%"}
            },
            "B": {
                "단기": {"kelly": "2%", "time": "30분-2시간", "target": "+2%", "stop": "-1%"},
                "중기": {"kelly": "1.5%", "time": "2시간-1일", "target": "+3%", "stop": "-1.5%"}
            },
            "C": {
                "중기": {"kelly": "1%", "time": "2시간-1일", "target": "+2%", "stop": "-1%"}
            },
            "WAIT": {}
        }
        
        return recommendations.get(signal_type["type"], {})


# 테스트
if __name__ == "__main__":
    async def test():
        aggregator = SignalAggregator()
        result = await aggregator.get_all_signals("BTC")
        
        print("=" * 60)
        print(f"🎯 {result['symbol']} 종합 분석 결과")
        print("=" * 60)
        
        print("\n📊 Agent Scores:")
        for agent, score in result["agent_scores"].items():
            print(f"  {agent:15s}: {score}/100")
        
        print(f"\n🎯 Weighted Score: {result['weighted_score']}/100")
        print(f"📈 Signal Type: {result['signal_type']['type']} ({result['signal_type']['confidence']}%)")
        print(f"💡 Action: {result['signal_type']['action']}")
    
    asyncio.run(test())
