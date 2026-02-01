# engine/analysis/onchain.py
"""
📊 온체인 분석 모듈
유통량, 주포 포진, 프렉탈 분석
"""

import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OnchainAnalyzer:
    """온체인 데이터 분석"""
    
    # 코인별 총 공급량 (하드코딩 - 실시간 업데이트 필요시 API 연동)
    MAX_SUPPLY = {
        'BTC': 21_000_000,
        'ETH': None,  # 무한
        'XRP': 100_000_000_000,
        'SOL': 580_000_000,
        'ADA': 45_000_000_000,
        'DOGE': None,  # 무한
        'AVAX': 720_000_000,
        'DOT': 1_420_000_000,
        'MATIC': 10_000_000_000,
        'ATOM': 292_000_000,
        'LINK': 1_000_000_000,
        'UNI': 1_000_000_000,
        'NEAR': 1_000_000_000,
        'APT': 1_000_000_000,
        'ARB': 10_000_000_000,
    }
    
    def __init__(self):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        logger.info("✅ OnchainAnalyzer 초기화 완료")
    
    def analyze(self, symbol: str, market_data: Dict = None) -> Dict:
        """
        종합 온체인 분석
        
        Returns:
            {
                "supply": {"circulating": X, "total": Y, "ratio": 85.2},
                "whale_activity": {"status": "매집", "confidence": 75, "signals": [...]},
                "fractal": {"position": "상승 2파", "target": 130000000, "risk": "중간"},
                "recommendation": {"action": "매수", "entry": X, "stop": Y, "target": Z}
            }
        """
        # 공급량 분석
        supply = self._analyze_supply(symbol, market_data)
        
        # 주포 활동 분석 (규칙 기반)
        whale = self._analyze_whale_activity(symbol, market_data)
        
        # 프렉탈 분석
        fractal = self._analyze_fractal(symbol, market_data)
        
        # 종합 추천
        recommendation = self._generate_recommendation(symbol, supply, whale, fractal, market_data)
        
        return {
            "symbol": symbol,
            "supply": supply,
            "whale_activity": whale,
            "fractal": fractal,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_supply(self, symbol: str, market_data: Dict = None) -> Dict:
        """유통량 분석"""
        try:
            # CoinGecko에서 시가총액/유통량 가져오기
            gecko_id = self._get_coingecko_id(symbol)
            
            resp = requests.get(
                f"{self.coingecko_base}/coins/{gecko_id}",
                params={"localization": "false", "tickers": "false", "community_data": "false"},
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                market = data.get("market_data", {})
                
                circulating = market.get("circulating_supply", 0)
                total = market.get("total_supply") or self.MAX_SUPPLY.get(symbol.upper(), 0)
                max_supply = market.get("max_supply") or self.MAX_SUPPLY.get(symbol.upper())
                
                if max_supply and max_supply > 0:
                    ratio = round(circulating / max_supply * 100, 1)
                elif total and total > 0:
                    ratio = round(circulating / total * 100, 1)
                else:
                    ratio = 100  # 무한 공급 코인
                
                return {
                    "circulating": circulating,
                    "total": total,
                    "max_supply": max_supply,
                    "ratio": ratio,
                    "status": self._get_supply_status(ratio)
                }
            
        except Exception as e:
            logger.warning(f"Supply 분석 오류 ({symbol}): {e}")
        
        # 폴백: 기본값
        max_supply = self.MAX_SUPPLY.get(symbol.upper(), 0)
        return {
            "circulating": 0,
            "total": max_supply,
            "max_supply": max_supply,
            "ratio": 0,
            "status": "데이터 없음"
        }
    
    def _get_supply_status(self, ratio: float) -> str:
        """유통량 비율 상태"""
        if ratio >= 95:
            return "거의 완전 유통 (희소성 높음)"
        elif ratio >= 80:
            return "높은 유통률"
        elif ratio >= 50:
            return "중간 유통률"
        elif ratio >= 20:
            return "낮은 유통률 (주의)"
        else:
            return "매우 낮은 유통률 (고위험)"
    
    def _analyze_whale_activity(self, symbol: str, market_data: Dict = None) -> Dict:
        """
        주포(고래) 활동 분석
        규칙 기반 추정 (실제 온체인 API 없이)
        """
        signals = []
        confidence = 50
        status = "관망"
        
        if not market_data:
            return {
                "status": status,
                "confidence": confidence,
                "signals": ["데이터 없음"],
                "description": "시장 데이터가 없어 분석 불가"
            }
        
        change_rate = market_data.get('change_rate', 0)
        volume_24h = market_data.get('volume_24h', 0)
        high = market_data.get('high_24h', 0)
        low = market_data.get('low_24h', 0)
        price = market_data.get('price', 0)
        
        # 규칙 1: 거래량 급증 + 가격 안정 = 매집
        if volume_24h > 0 and abs(change_rate) < 2:
            signals.append("대량 거래 + 가격 안정 (매집 징후)")
            confidence += 15
            status = "매집"
        
        # 규칙 2: 소폭 상승 + 거래량 증가 = 초기 매집
        if 0 < change_rate < 3:
            signals.append("소폭 상승 (조용한 매집 가능성)")
            confidence += 10
            if status != "매집":
                status = "매집"
        
        # 규칙 3: 급등 후 하락 = 배분 (매도)
        if change_rate < -5:
            signals.append("급격한 하락 (이익 실현 가능성)")
            confidence += 10
            status = "배분 (매도)"
        
        # 규칙 4: 높은 변동성 = 관망
        if high and low and price:
            volatility = (high - low) / price * 100 if price else 0
            if volatility > 10:
                signals.append(f"높은 변동성 ({volatility:.1f}%)")
                status = "관망"
        
        # 규칙 5: 거래량 급감 = 관심 감소
        # (실제로는 이전 거래량과 비교 필요)
        
        if not signals:
            signals.append("뚜렷한 신호 없음")
        
        # 상태별 설명
        descriptions = {
            "매집": "세력이 조용히 물량을 확보하는 것으로 추정됩니다.",
            "배분 (매도)": "세력이 보유 물량을 매도하는 것으로 추정됩니다.",
            "관망": "세력의 뚜렷한 움직임이 감지되지 않습니다."
        }
        
        return {
            "status": status,
            "confidence": min(confidence, 95),
            "signals": signals,
            "description": descriptions.get(status, "분석 중")
        }
    
    def _analyze_fractal(self, symbol: str, market_data: Dict = None) -> Dict:
        """
        프렉탈 분석
        과거 패턴과 현재 위치 비교 (간략화)
        """
        if not market_data:
            return {
                "position": "분석 불가",
                "phase": 0,
                "target": 0,
                "risk": "알 수 없음",
                "description": "데이터 없음"
            }
        
        price = market_data.get('price', 0)
        change_rate = market_data.get('change_rate', 0)
        high_24h = market_data.get('high_24h', price)
        low_24h = market_data.get('low_24h', price)
        
        # 간단한 프렉탈 위치 추정 (ATH 대비)
        # 실제로는 과거 데이터와 패턴 매칭 필요
        
        # 현재 가격이 24시간 레인지 어디에 있는지
        if high_24h != low_24h:
            position_in_range = (price - low_24h) / (high_24h - low_24h) * 100
        else:
            position_in_range = 50
        
        # 프렉탈 위치 판단
        if change_rate > 5:
            position = "상승 3파 (강세)"
            phase = 3
            target = round(price * 1.15, 0)  # +15% 목표
            risk = "낮음"
        elif change_rate > 2:
            position = "상승 1파 (초기)"
            phase = 1
            target = round(price * 1.08, 0)
            risk = "중간"
        elif change_rate > 0:
            position = "상승 5파 (마무리)"
            phase = 5
            target = round(price * 1.05, 0)
            risk = "높음 (조정 임박)"
        elif change_rate > -3:
            position = "조정 A파"
            phase = -1
            target = round(price * 0.95, 0)
            risk = "중간"
        elif change_rate > -5:
            position = "조정 B파 (반등)"
            phase = -2
            target = round(price * 1.03, 0)
            risk = "중간"
        else:
            position = "조정 C파 (하락)"
            phase = -3
            target = round(price * 0.90, 0)
            risk = "높음"
        
        return {
            "position": position,
            "phase": phase,
            "target": target,
            "risk": risk,
            "position_in_range": round(position_in_range, 1),
            "description": f"현재 {position} 구간으로 추정됩니다. 목표가: ₩{target:,.0f}"
        }
    
    def _generate_recommendation(self, symbol: str, supply: Dict, whale: Dict, fractal: Dict, market_data: Dict = None) -> Dict:
        """종합 거래 추천"""
        price = market_data.get('price', 0) if market_data else 0
        
        if not price:
            return {
                "action": "관망",
                "entry": 0,
                "stop": 0,
                "target": 0,
                "reason": "가격 데이터 없음"
            }
        
        # 점수 계산
        score = 50  # 기본 점수
        reasons = []
        
        # 공급량 점수
        if supply.get('ratio', 0) >= 80:
            score += 10
            reasons.append("높은 유통률 (희소성)")
        
        # 주포 활동 점수
        if whale.get('status') == "매집":
            score += 20
            reasons.append("세력 매집 추정")
        elif whale.get('status') == "배분 (매도)":
            score -= 15
            reasons.append("세력 매도 추정")
        
        # 프렉탈 점수
        phase = fractal.get('phase', 0)
        if phase in [1, 3]:  # 상승 초기/중기
            score += 15
            reasons.append(f"프렉탈: {fractal.get('position')}")
        elif phase == 5:  # 상승 마무리
            score -= 10
            reasons.append("프렉탈: 조정 임박")
        elif phase < 0:  # 조정 중
            if phase == -2:  # B파 반등
                score += 5
                reasons.append("조정 중 반등 구간")
            else:
                score -= 10
                reasons.append("조정 진행 중")
        
        # 액션 결정
        if score >= 75:
            action = "🟢 강력 매수"
        elif score >= 60:
            action = "🟢 매수"
        elif score >= 45:
            action = "⚪ 관망"
        elif score >= 35:
            action = "🟠 매도 고려"
        else:
            action = "🔴 매도"
        
        # 가격 레벨 계산
        entry = round(price * 0.99, 0)  # 현재가 -1%
        stop = round(price * 0.95, 0)   # 현재가 -5%
        target = fractal.get('target', round(price * 1.10, 0))
        
        return {
            "action": action,
            "entry": entry,
            "stop": stop,
            "target": target,
            "score": score,
            "reasons": reasons,
            "reason": " | ".join(reasons) if reasons else "특이사항 없음"
        }
    
    def _get_coingecko_id(self, symbol: str) -> str:
        """심볼을 CoinGecko ID로 변환"""
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'XRP': 'ripple',
            'SOL': 'solana',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'AVAX': 'avalanche-2',
            'DOT': 'polkadot',
            'MATIC': 'matic-network',
            'ATOM': 'cosmos',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'NEAR': 'near',
            'APT': 'aptos',
            'ARB': 'arbitrum',
            'SHIB': 'shiba-inu',
            'OP': 'optimism',
            'INJ': 'injective-protocol',
            'TIA': 'celestia',
            'FIL': 'filecoin',
        }
        return mapping.get(symbol.upper(), symbol.lower())
    
    def get_stats(self, symbol: str) -> Dict:
        """
        주요 통계 (거래량, 시가총액, 성과)
        """
        try:
            gecko_id = self._get_coingecko_id(symbol)
            
            resp = requests.get(
                f"{self.coingecko_base}/coins/{gecko_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false"
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                market = data.get("market_data", {})
                
                # 가격 변화 (성과)
                price_change = market.get("price_change_percentage_24h_in_currency", {})
                
                return {
                    "symbol": symbol,
                    "name": data.get("name", symbol),
                    "volume_24h": market.get("total_volume", {}).get("krw", 0),
                    "market_cap": market.get("market_cap", {}).get("krw", 0),
                    "market_cap_rank": market.get("market_cap_rank", 0),
                    # 성과
                    "performance": {
                        "24h": round(market.get("price_change_percentage_24h", 0), 2),
                        "7d": round(market.get("price_change_percentage_7d", 0), 2),
                        "14d": round(market.get("price_change_percentage_14d", 0), 2),
                        "30d": round(market.get("price_change_percentage_30d", 0), 2),
                        "60d": round(market.get("price_change_percentage_60d", 0), 2),
                        "200d": round(market.get("price_change_percentage_200d", 0), 2),
                        "1y": round(market.get("price_change_percentage_1y", 0), 2),
                    },
                    "ath": market.get("ath", {}).get("krw", 0),
                    "ath_change_percentage": round(market.get("ath_change_percentage", {}).get("krw", 0), 2),
                    "atl": market.get("atl", {}).get("krw", 0),
                    "last_updated": data.get("last_updated", ""),
                    "source": "CoinGecko"
                }
            
        except Exception as e:
            logger.warning(f"Stats 조회 오류 ({symbol}): {e}")
        
        return {
            "symbol": symbol,
            "error": "데이터 조회 실패",
            "source": "CoinGecko"
        }


# 테스트
if __name__ == "__main__":
    print("📊 온체인 분석 테스트")
    
    analyzer = OnchainAnalyzer()
    
    # 테스트 데이터
    test_data = {
        'price': 116000000,
        'change_rate': 1.5,
        'volume_24h': 500000000000,
        'high_24h': 118000000,
        'low_24h': 114000000
    }
    
    result = analyzer.analyze('BTC', test_data)
    
    print(f"\n🔗 BTC 온체인 분석:")
    print(f"   유통량: {result['supply']['ratio']}%")
    print(f"   주포 상태: {result['whale_activity']['status']}")
    print(f"   프렉탈: {result['fractal']['position']}")
    print(f"   추천: {result['recommendation']['action']}")
