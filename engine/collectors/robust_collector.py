# engine/collectors/robust_collector.py
"""
🎯 Phoenix 3-Tier 데이터 수집 시스템
천재들의 사고법 적용: First Principles, 5 Whys, Failure Mode Analysis
"""

import requests
import json
from datetime import datetime
from typing import Dict, Optional
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Tier 1: 공개 API (API 키 불필요) ====================

class PublicAPICollector:
    """API 키 없이 사용 가능한 공개 데이터 소스"""
    
    @staticmethod
    def upbit_public(symbol: str) -> Optional[Dict]:
        """업비트 공개 API"""
        try:
            url = f"https://api.upbit.com/v1/ticker?markets=KRW-{symbol}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()[0]
                return {
                    'source': 'upbit_public',
                    'symbol': symbol,
                    'price': float(data['trade_price']),
                    'volume_24h': float(data['acc_trade_volume_24h']),
                    'change_rate': float(data['signed_change_rate']) * 100,
                    'high_24h': float(data['high_price']),
                    'low_24h': float(data['low_price']),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.debug(f"Upbit API 오류: {e}")
            return None
    
    @staticmethod
    def bithumb_public(symbol: str) -> Optional[Dict]:
        """빗썸 공개 API"""
        try:
            url = f"https://api.bithumb.com/public/ticker/{symbol}_KRW"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == '0000':
                    data = result['data']
                    return {
                        'source': 'bithumb_public',
                        'symbol': symbol,
                        'price': float(data['closing_price']),
                        'volume_24h': float(data['units_traded_24H']),
                        'change_rate': float(data.get('fluctate_rate_24H', 0)),
                        'high_24h': float(data['max_price']),
                        'low_24h': float(data['min_price']),
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            logger.debug(f"Bithumb API 오류: {e}")
            return None
    
    @staticmethod
    def coingecko_free(symbol: str) -> Optional[Dict]:
        """CoinGecko 무료 API"""
        try:
            symbol_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'XRP': 'ripple',
                'SOL': 'solana', 'ADA': 'cardano', 'DOT': 'polkadot',
                'AVAX': 'avalanche-2', 'MATIC': 'matic-network'
            }
            
            coin_id = symbol_map.get(symbol, symbol.lower())
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'krw',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json().get(coin_id, {})
                if data:
                    return {
                        'source': 'coingecko_free',
                        'symbol': symbol,
                        'price': float(data.get('krw', 0)),
                        'volume_24h': float(data.get('krw_24h_vol', 0)),
                        'change_rate': float(data.get('krw_24h_change', 0)),
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            logger.debug(f"CoinGecko API 오류: {e}")
            return None
    
    @staticmethod
    def binance_public(symbol: str) -> Optional[Dict]:
        """바이낸스 공개 API (USD 기준, KRW 변환)"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': f"{symbol}USDT"}
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                usd_to_krw = 1350  # 대략적 환율
                
                return {
                    'source': 'binance_public',
                    'symbol': symbol,
                    'price': float(data['lastPrice']) * usd_to_krw,
                    'volume_24h': float(data['volume']),
                    'change_rate': float(data['priceChangePercent']),
                    'high_24h': float(data['highPrice']) * usd_to_krw,
                    'low_24h': float(data['lowPrice']) * usd_to_krw,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.debug(f"Binance API 오류: {e}")
            return None


# ==================== Tier 2: 웹 스크래핑 (백업) ====================

class WebScrapingCollector:
    """API 실패 시 웹 스크래핑으로 데이터 수집"""
    
    @staticmethod
    def scrape_simple(symbol: str) -> Optional[Dict]:
        """간단한 스크래핑 (BeautifulSoup 필요)"""
        try:
            from bs4 import BeautifulSoup
            
            symbol_map = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'XRP': 'ripple'}
            coin_id = symbol_map.get(symbol, symbol.lower())
            
            url = f"https://www.coingecko.com/en/coins/{coin_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return {
                    'source': 'web_scraping',
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'is_fallback': True
                }
        except Exception as e:
            logger.debug(f"스크래핑 오류: {e}")
            return None


# ==================== Tier 3: 캐시 & 폴백 ====================

class CacheManager:
    """데이터 캐싱 및 폴백 관리"""
    
    def __init__(self, cache_file: str = "data_cache.json"):
        self.cache = {}
        self.cache_file = cache_file
        self.load_cache()
    
    def get_cached(self, symbol: str, max_age_seconds: int = 300) -> Optional[Dict]:
        if symbol in self.cache:
            cached = self.cache[symbol]
            try:
                cached_time = datetime.fromisoformat(cached['timestamp'])
                age = (datetime.now() - cached_time).total_seconds()
                
                if age <= max_age_seconds:
                    logger.info(f"캐시 히트: {symbol} (age: {age:.0f}초)")
                    cached['is_cached'] = True
                    return cached
            except:
                pass
        return None
    
    def set_cache(self, symbol: str, data: Dict):
        self.cache[symbol] = data
        self.save_cache()
    
    def save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.debug(f"캐시 저장 오류: {e}")
    
    def load_cache(self):
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
            logger.info(f"캐시 로드됨: {len(self.cache)} 항목")
        except FileNotFoundError:
            self.cache = {}
        except Exception as e:
            logger.debug(f"캐시 로드 오류: {e}")
            self.cache = {}


# ==================== 통합 데이터 수집기 ====================

class RobustDataCollector:
    """절대 실패하지 않는 데이터 수집 시스템"""
    
    def __init__(self):
        self.public_api = PublicAPICollector()
        self.scraper = WebScrapingCollector()
        self.cache_manager = CacheManager()
        self.retry_config = {
            'max_retries': 2,
            'backoff_factor': 1,
            'timeout': 5
        }
    
    def collect_with_fallback(self, symbol: str) -> Dict:
        """3-Tier 폴백으로 데이터 수집"""
        
        # Step 1: 공개 API 시도 (우선순위 순서)
        api_sources = [
            self.public_api.upbit_public,
            self.public_api.bithumb_public,
            self.public_api.coingecko_free,
            self.public_api.binance_public
        ]
        
        for api_func in api_sources:
            try:
                data = api_func(symbol)
                if data:
                    logger.info(f"✅ {data['source']}에서 데이터 수집 성공: {symbol}")
                    self.cache_manager.set_cache(symbol, data)
                    return data
            except Exception as e:
                continue
        
        # Step 2: 캐시된 데이터 사용 (최대 1시간)
        logger.warning(f"⚠️ 실시간 API 실패, 캐시 사용: {symbol}")
        cached = self.cache_manager.get_cached(symbol, max_age_seconds=3600)
        
        if cached:
            cached['warning'] = 'Using cached data'
            return cached
        
        # Step 3: 최후의 폴백 - 기본값 반환
        logger.error(f"❌ 모든 소스 실패, 기본값 반환: {symbol}")
        return self._emergency_fallback(symbol)
    
    def _emergency_fallback(self, symbol: str) -> Dict:
        """최후의 폴백 값"""
        fallback_prices = {
            'BTC': 130000000, 'ETH': 5000000, 'XRP': 3500,
            'SOL': 350000, 'ADA': 1500
        }
        
        return {
            'source': 'emergency_fallback',
            'symbol': symbol,
            'price': fallback_prices.get(symbol, 100000),
            'volume_24h': 0,
            'change_rate': 0,
            'timestamp': datetime.now().isoformat(),
            'warning': 'EMERGENCY FALLBACK - DATA MAY BE STALE',
            'is_fallback': True
        }
    
    def collect_all(self, symbols: list) -> list:
        """여러 심볼 수집"""
        results = []
        for symbol in symbols:
            data = self.collect_with_fallback(symbol)
            results.append(data)
        return results


# ==================== 테스트 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 Phoenix 3-Tier Data Collector Test")
    print("=" * 60)
    
    collector = RobustDataCollector()
    
    for symbol in ['BTC', 'ETH', 'XRP']:
        print(f"\n📊 {symbol} 수집 중...")
        data = collector.collect_with_fallback(symbol)
        print(f"   소스: {data['source']}")
        print(f"   가격: ₩{data['price']:,.0f}")
        if 'change_rate' in data:
            print(f"   변동: {data['change_rate']:+.2f}%")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료")
