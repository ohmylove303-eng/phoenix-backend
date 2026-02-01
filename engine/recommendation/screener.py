# engine/recommendation/screener.py
"""
🎯 코인 추천 시스템
- 메이저 5종 추천
- 시간대별 단타 (09:00, 16:00, 19:00, 21:30)
- 매집 탐지 기반 추천
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import requests

# 상위 폴더 임포트
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.robust_collector import RobustDataCollector
from agents.signal_agents import SignalAggregator

logger = logging.getLogger(__name__)


class CoinScreener:
    """코인 스크리닝 및 추천 시스템"""
    
    # 메이저 코인 목록
    MAJOR_COINS = ['BTC', 'ETH', 'XRP', 'SOL', 'ADA']
    
    # 확장 코인 목록 (단타/스캘핑용)
    EXTENDED_COINS = [
        'BTC', 'ETH', 'XRP', 'SOL', 'ADA', 'DOGE', 'AVAX', 'DOT', 
        'MATIC', 'ATOM', 'LINK', 'UNI', 'FIL', 'NEAR', 'APT',
        'SHIB', 'ARB', 'OP', 'INJ', 'TIA'
    ]
    
    # 유동성 시간대 (한국 시간 기준)
    LIQUIDITY_TIMES = ['09:00', '16:00', '19:00', '21:30']
    
    def __init__(self):
        self.collector = RobustDataCollector()
        self.aggregator = SignalAggregator()
        logger.info("✅ CoinScreener 초기화 완료")
    
    def get_major_recommendations(self, top_n: int = 5) -> List[Dict]:
        """
        메이저 코인 5종 추천
        - 기술적 분석 점수 기반
        """
        logger.info("📊 메이저 코인 분석 중...")
        
        results = []
        
        for symbol in self.MAJOR_COINS:
            try:
                data = self.collector.collect_with_fallback(symbol)
                signal = self.aggregator.get_all_signals(market_data=data)
                
                results.append({
                    'symbol': symbol,
                    'type': '메이저',
                    'price': data.get('price', 0),
                    'change_rate': data.get('change_rate', 0),
                    'volume_24h': data.get('volume_24h', 0),
                    'score': signal['weighted_score'],
                    'signal': signal['signal'],
                    'agent_scores': signal['agent_scores'],
                    'recommendation': self._get_recommendation_text(signal['weighted_score'])
                })
            except Exception as e:
                logger.warning(f"메이저 분석 오류 ({symbol}): {e}")
        
        # 점수순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_n]
    
    def get_scalp_recommendations(self, time_slot: str = None, top_n: int = 5) -> List[Dict]:
        """
        단타/스캘핑 추천
        시간대별 유동성 기반:
        - 09:00: 아시아 장 시작
        - 16:00: 유럽 장 시작
        - 19:00: 저녁 유동성
        - 21:30: 미국 장 전
        
        선정 로직:
        1. 상승률 > 거래량 순으로 10개 선정
        2. 매집 흔적 있는 5개 필터링
        """
        if time_slot is None:
            now = datetime.now()
            time_slot = now.strftime('%H:%M')
        
        logger.info(f"📈 단타 추천 분석 중 (시간대: {time_slot})...")
        
        all_coins = []
        
        # 1단계: 모든 코인 데이터 수집
        for symbol in self.EXTENDED_COINS:
            try:
                data = self.collector.collect_with_fallback(symbol)
                
                all_coins.append({
                    'symbol': symbol,
                    'price': data.get('price', 0),
                    'change_rate': data.get('change_rate', 0),
                    'volume_24h': data.get('volume_24h', 0),
                    'data': data
                })
            except Exception as e:
                logger.warning(f"스캔 오류 ({symbol}): {e}")
        
        # 2단계: 상승률 + 거래량 점수 계산 후 Top 10
        for coin in all_coins:
            coin['momentum_score'] = self._calculate_momentum_score(coin)
        
        # 상승률 순 정렬 후 상위 10개
        sorted_by_momentum = sorted(all_coins, key=lambda x: x['momentum_score'], reverse=True)
        top_10 = sorted_by_momentum[:10]
        
        # 3단계: 매집 흔적 분석 후 Top 5
        for coin in top_10:
            coin['accumulation'] = self._detect_accumulation(coin['data'])
            signal = self.aggregator.get_all_signals(market_data=coin['data'])
            coin['score'] = signal['weighted_score']
            coin['signal'] = signal['signal']
            coin['agent_scores'] = signal['agent_scores']
        
        # 매집 흔적 + 점수 기준 정렬
        sorted_final = sorted(top_10, key=lambda x: (x['accumulation']['detected'], x['score']), reverse=True)
        
        results = []
        for coin in sorted_final[:top_n]:
            results.append({
                'symbol': coin['symbol'],
                'type': '단타',
                'time_slot': time_slot,
                'price': coin['price'],
                'change_rate': coin['change_rate'],
                'volume_24h': coin['volume_24h'],
                'momentum_score': coin['momentum_score'],
                'score': coin['score'],
                'signal': coin['signal'],
                'agent_scores': coin['agent_scores'],
                'accumulation': coin['accumulation'],
                'recommendation': self._get_recommendation_text(coin['score'])
            })
        
        return results
    
    def get_swing_recommendations(self, period: str = 'short', top_n: int = 5) -> List[Dict]:
        """
        스윙 추천 (단기/중기/장기)
        
        period:
        - 'short': 단기 (1-3일)
        - 'medium': 중기 (1주-1개월)
        - 'long': 장기 (1개월+)
        """
        logger.info(f"📊 스윙 추천 분석 중 ({period})...")
        
        results = []
        
        for symbol in self.EXTENDED_COINS:
            try:
                data = self.collector.collect_with_fallback(symbol)
                signal = self.aggregator.get_all_signals(market_data=data)
                accumulation = self._detect_accumulation(data)
                
                # 투자 기간별 가중치 조정
                if period == 'short':
                    # 단기: 모멘텀 + 기술적 분석 중시
                    adjusted_score = signal['weighted_score'] * 0.7 + (30 if accumulation['detected'] else 0)
                elif period == 'medium':
                    # 중기: 매집 + 기술적 균형
                    adjusted_score = signal['weighted_score'] * 0.5 + (50 if accumulation['detected'] else 0)
                else:  # long
                    # 장기: 펀더멘털 + 온체인 중시
                    adjusted_score = signal['agent_scores'].get('onchain', 50) * 0.6 + signal['agent_scores'].get('institutional', 50) * 0.4
                
                results.append({
                    'symbol': symbol,
                    'type': f'스윙-{period}',
                    'price': data.get('price', 0),
                    'change_rate': data.get('change_rate', 0),
                    'score': round(adjusted_score),
                    'base_score': signal['weighted_score'],
                    'signal': signal['signal'],
                    'agent_scores': signal['agent_scores'],
                    'accumulation': accumulation,
                    'recommendation': self._get_recommendation_text(adjusted_score)
                })
            except Exception as e:
                logger.warning(f"스윙 분석 오류 ({symbol}): {e}")
        
        # 조정된 점수순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_n]
    
    def _calculate_momentum_score(self, coin: Dict) -> float:
        """모멘텀 점수 계산 (상승률 + 거래량)"""
        score = 0
        
        # 상승률 점수 (가중치 70%)
        change = coin.get('change_rate', 0)
        if change > 10:
            score += 50
        elif change > 5:
            score += 40
        elif change > 2:
            score += 30
        elif change > 0:
            score += 20
        else:
            score += max(0, 10 + change)  # 하락 시 감점
        
        # 거래량 점수 (가중치 30%)
        volume = coin.get('volume_24h', 0)
        if volume > 100_000_000_000:  # 1000억 이상
            score += 30
        elif volume > 10_000_000_000:  # 100억 이상
            score += 20
        elif volume > 1_000_000_000:   # 10억 이상
            score += 10
        
        return score
    
    def _detect_accumulation(self, data: Dict) -> Dict:
        """
        매집 탐지
        - 거래량 급증
        - 가격 안정 또는 소폭 상승
        - 세력 매집 패턴
        """
        change_rate = abs(data.get('change_rate', 0))
        volume = data.get('volume_24h', 0)
        price = data.get('price', 0)
        
        # 매집 신호 점수
        accumulation_score = 0
        signals = []
        
        # 1. 거래량 대비 가격 변동 작음 (매집 징후)
        if volume > 10_000_000_000 and change_rate < 3:
            accumulation_score += 30
            signals.append("대량 거래 + 가격 안정")
        
        # 2. 소폭 상승 + 거래량 증가 (초기 매집)
        change = data.get('change_rate', 0)
        if 0 < change < 5:
            accumulation_score += 20
            signals.append("소폭 상승 추세")
        
        # 3. 고가 대비 하락 후 반등 (세력 매집)
        high = data.get('high_24h', price)
        low = data.get('low_24h', price)
        if high > 0 and low > 0:
            retracement = (high - price) / (high - low) if high != low else 0
            if 0.3 < retracement < 0.6:
                accumulation_score += 25
                signals.append("피보나치 0.5 지지")
        
        return {
            'detected': accumulation_score >= 40,
            'score': accumulation_score,
            'strength': '강함' if accumulation_score >= 60 else '보통' if accumulation_score >= 40 else '약함',
            'signals': signals
        }
    
    def _get_recommendation_text(self, score: float) -> str:
        """점수 기반 추천 텍스트"""
        if score >= 80:
            return "🟢 강력 매수"
        elif score >= 70:
            return "🟢 매수"
        elif score >= 60:
            return "🟡 매수 고려"
        elif score >= 40:
            return "⚪ 관망"
        elif score >= 30:
            return "🟠 매도 고려"
        else:
            return "🔴 매도"


# ==================== 테스트 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 CoinScreener Test")
    print("=" * 60)
    
    screener = CoinScreener()
    
    # 1. 메이저 추천
    print("\n📊 메이저 코인 추천:")
    major = screener.get_major_recommendations()
    for coin in major:
        print(f"   {coin['symbol']}: {coin['score']}점 - {coin['recommendation']}")
    
    # 2. 단타 추천
    print("\n📈 단타 추천 (현재 시간대):")
    scalp = screener.get_scalp_recommendations()
    for coin in scalp:
        acc = "🟢" if coin['accumulation']['detected'] else "⚪"
        print(f"   {coin['symbol']}: {coin['score']}점 | 매집: {acc} | {coin['recommendation']}")
