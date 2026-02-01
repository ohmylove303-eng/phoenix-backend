# engine/analysis/palantir_mini.py
"""
🎯 Enhanced Mini Palantir
API 키 없이도 작동하는 강화된 분석 시스템
"""

import os
import logging
from datetime import datetime
from typing import Dict, List

# 로컬 임포트
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.robust_collector import RobustDataCollector
from agents.signal_agents import SignalAggregator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIModelManager:
    """AI 모델 폴백 시스템"""
    
    def __init__(self):
        self.models = {
            'primary': 'gemini-1.5-flash',
            'fallback1': 'gemini-pro',
            'local': 'rule-based'
        }
    
    def analyze_with_fallback(self, market_data: Dict) -> Dict:
        """AI 분석 실패 시 폴백 전략"""
        
        # 1차: Gemini 시도 (API 키 있을 경우)
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        
        if api_key:
            try:
                return self._analyze_with_gemini(market_data, api_key)
            except Exception as e:
                logger.warning(f"Gemini 실패: {e}")
        
        # 폴백: 규칙 기반 분석 (항상 작동)
        logger.info("규칙 기반 분석 사용")
        return self._rule_based_analysis(market_data)
    
    def _analyze_with_gemini(self, market_data: Dict, api_key: str) -> Dict:
        """Gemini API 호출"""
        import requests
        
        symbol = market_data.get('symbol', 'UNKNOWN')
        price = market_data.get('price', 0)
        change_rate = market_data.get('change_rate', 0)
        
        prompt = f"""
        역할: 가상화폐 분석가
        심볼: {symbol}
        가격: ₩{price:,.0f}
        변동률: {change_rate:+.2f}%
        
        형식: {{ "signal": "BUY/SELL/HOLD", "confidence": 0.7, "reasoning": "한줄요약" }}
        """
        
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {'Content-Type': 'application/json'}
        params = {'key': api_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            # JSON 파싱 시도
            import json
            s = raw_text.find('{')
            e = raw_text.rfind('}')
            if s != -1 and e != -1:
                return json.loads(raw_text[s:e+1])
        
        raise Exception(f"API Error: {response.status_code}")
    
    def _rule_based_analysis(self, market_data: Dict) -> Dict:
        """AI 없이도 작동하는 규칙 기반 분석"""
        change_rate = market_data.get('change_rate', 0)
        price = market_data.get('price', 0)
        high = market_data.get('high_24h', price)
        low = market_data.get('low_24h', price)
        
        # 가격 위치 계산
        price_position = (price - low) / (high - low) if high > low else 0.5
        
        # 신호 결정
        signal = 'HOLD'
        confidence = 0.5
        
        if change_rate > 5 and price_position < 0.3:
            signal = 'BUY'
            confidence = 0.75
        elif change_rate > 2 and price_position < 0.5:
            signal = 'BUY'
            confidence = 0.65
        elif change_rate < -5 and price_position > 0.7:
            signal = 'SELL'
            confidence = 0.7
        elif change_rate < -2:
            signal = 'SELL'
            confidence = 0.6
        
        return {
            'signal': signal,
            'confidence': confidence,
            'method': 'rule-based',
            'reasoning': f"변동률 {change_rate:+.2f}%, 가격위치 {price_position:.0%}"
        }


class EnhancedMiniPalantir:
    """API 키 없이도 작동하는 강화된 Mini Palantir"""
    
    def __init__(self):
        self.data_collector = RobustDataCollector()
        self.signal_aggregator = SignalAggregator()
        self.ai_manager = AIModelManager()
        
        # 설정
        self.watch_list = os.getenv('PHOENIX_WATCHLIST', 'BTC,ETH,XRP,SOL,ADA').split(',')
        self.trading_mode = os.getenv('TRADING_MODE', 'paper')
        
        logger.info("✅ Enhanced Mini Palantir 초기화 완료")
        logger.info(f"   감시 종목: {', '.join(self.watch_list)}")
        logger.info(f"   거래 모드: {self.trading_mode}")
    
    def run_cycle(self) -> List[Dict]:
        """분석 사이클 실행"""
        logger.info("=" * 60)
        logger.info(f"🔄 Mini Palantir 사이클 - {datetime.now().strftime('%H:%M:%S')}")
        logger.info("=" * 60)
        
        results = []
        
        for symbol in self.watch_list:
            try:
                result = self.analyze_single(symbol)
                results.append(result)
                
                # 로그 출력
                logger.info(f"\n📊 {symbol}:")
                logger.info(f"   가격: ₩{result['price']:,.0f}")
                logger.info(f"   변동: {result.get('change_rate', 0):+.2f}%")
                logger.info(f"   신호: {result['signal']} ({result['signal_type']})")
                logger.info(f"   점수: {result['weighted_score']}/100")
                
            except Exception as e:
                logger.error(f"❌ {symbol} 분석 오류: {e}")
                continue
        
        logger.info(f"\n✅ 사이클 완료: {len(results)}/{len(self.watch_list)} 종목")
        return results
    
    def analyze_single(self, symbol: str) -> Dict:
        """단일 심볼 분석"""
        
        # 1. 데이터 수집 (절대 실패 안 함)
        market_data = self.data_collector.collect_with_fallback(symbol)
        
        # 2. 5개 Agent 분석
        agent_result = self.signal_aggregator.get_all_signals(market_data=market_data)
        
        # 3. AI 분석 (폴백 포함)
        ai_result = self.ai_manager.analyze_with_fallback(market_data)
        
        return {
            'symbol': symbol,
            'price': market_data.get('price', 0),
            'change_rate': market_data.get('change_rate', 0),
            'volume_24h': market_data.get('volume_24h', 0),
            'source': market_data.get('source', 'unknown'),
            'agent_scores': agent_result['agent_scores'],
            'weighted_score': agent_result['weighted_score'],
            'signal': agent_result['signal'],
            'signal_type': agent_result['signal_type'],
            'confidence': agent_result['confidence'],
            'ai_analysis': ai_result,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_state(self) -> Dict:
        """전체 상태 반환"""
        results = self.run_cycle()
        
        # Top Gainers
        sorted_by_change = sorted(results, key=lambda x: x.get('change_rate', 0), reverse=True)
        
        # Top Scores
        sorted_by_score = sorted(results, key=lambda x: x.get('weighted_score', 0), reverse=True)
        
        return {
            'status': 'ONLINE',
            'mode': 'PALANTIR_MINI',
            'tickers': results,
            'top_gainers': sorted_by_change[:5],
            'top_scores': sorted_by_score[:5],
            'timestamp': datetime.now().isoformat(),
            '_meta': {
                'total_analyzed': len(results),
                'trading_mode': self.trading_mode
            }
        }


# ==================== 테스트 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 Enhanced Mini Palantir Test")
    print("=" * 60)
    
    palantir = EnhancedMiniPalantir()
    
    # 단일 분석 테스트
    result = palantir.analyze_single('BTC')
    
    print(f"\n📊 BTC 분석 결과:")
    print(f"   가격: ₩{result['price']:,.0f}")
    print(f"   신호: {result['signal']}")
    print(f"   점수: {result['weighted_score']}/100")
    print(f"   Agent 점수: {result['agent_scores']}")
