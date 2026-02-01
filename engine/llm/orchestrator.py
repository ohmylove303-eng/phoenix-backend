# engine/llm/orchestrator.py
"""
🎯 Phoenix LLM Orchestrator
모델 폴백 체인: Gemini Flash → Gemini Pro → 규칙 기반
"""

import os
import requests
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """LLM 폴백 시스템"""
    
    def __init__(self):
        self.server_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        self.base_url = "https://generativelanguage.googleapis.com"
    
    def synthesize(self, symbol: str, scores: Dict, weighted_score: int, override_key: str = None) -> Dict:
        """CIO Decision 생성"""
        active_key = override_key or self.server_key
        
        if not active_key:
            return self._fallback_synthesis(symbol, scores, weighted_score)
        
        # 프롬프트 생성
        prompt = f"""
        역할: 가상화폐 최고투자책임자(CIO).
        데이터: {symbol} 종합점수 {weighted_score}/100.
        세부점수: 기술적 {scores.get('technical', 50)}, 온체인 {scores.get('onchain', 50)}, 
                  정서 {scores.get('sentiment', 50)}, 거시경제 {scores.get('macro', 50)}, 
                  기관 {scores.get('institutional', 50)}.
        
        임무: 다음 JSON 형식으로 한국어 1줄 요약 분석을 제공하시오.
        형식: {{ "signal": "TYPE A/B/C", "reasoning": "핵심 1줄 코멘트" }}
        규칙: A(>80, 강력매수), B(>60, 매수), C(관망). 변동성과 거래량에 집중.
        """
        
        headers = {'Content-Type': 'application/json'}
        params = {'key': active_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        # 모델 우선순위 체인
        models = ["gemini-1.5-flash", "gemini-pro"]
        
        for model in models:
            try:
                version = "v1beta" if "flash" in model else "v1"
                url = f"{self.base_url}/{version}/models/{model}:generateContent"
                
                response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    raw_text = data['candidates'][0]['content']['parts'][0]['text']
                    
                    # JSON 추출
                    s = raw_text.find('{')
                    e = raw_text.rfind('}')
                    if s != -1 and e != -1:
                        result = json.loads(raw_text[s:e+1])
                        result['model'] = model
                        return result
                    
                    return {"signal": "TYPE C", "reasoning": raw_text[:100], "model": model}
                    
            except Exception as e:
                logger.warning(f"{model} 오류: {e}")
                continue
        
        # 모든 모델 실패 시 폴백
        return self._fallback_synthesis(symbol, scores, weighted_score)
    
    def _fallback_synthesis(self, symbol: str, scores: Dict, weighted_score: int) -> Dict:
        """규칙 기반 폴백"""
        if weighted_score >= 80:
            signal = "TYPE A"
            reasoning = f"{symbol} 강력 매수 신호. 기술적/온체인 지표 모두 긍정적."
        elif weighted_score >= 60:
            signal = "TYPE B"
            reasoning = f"{symbol} 매수 고려. 상승 모멘텀 확인됨."
        else:
            signal = "TYPE C"
            reasoning = f"{symbol} 관망 권고. 명확한 방향성 부재."
        
        return {
            "signal": signal,
            "reasoning": reasoning,
            "model": "rule-based"
        }


# ==================== 테스트 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 LLM Orchestrator Test")
    print("=" * 60)
    
    orchestrator = LLMOrchestrator()
    
    test_scores = {
        'technical': 75,
        'onchain': 60,
        'sentiment': 70,
        'macro': 55,
        'institutional': 65
    }
    
    result = orchestrator.synthesize('BTC', test_scores, 65)
    
    print(f"\n📊 CIO Decision:")
    print(f"   신호: {result['signal']}")
    print(f"   분석: {result['reasoning']}")
    print(f"   모델: {result.get('model', 'unknown')}")
