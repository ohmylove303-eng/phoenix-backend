# engine/analysis/candles.py
"""
🕯️ 캔들 데이터 수집 모듈
Upbit/Bithumb에서 시간대별 OHLCV 데이터 수집
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CandleCollector:
    """캔들 데이터 수집기 - 다중 소스 폴백"""
    
    TIMEFRAME_MAP = {
        '1m': {'upbit': 'minutes/1', 'count': 60},
        '5m': {'upbit': 'minutes/5', 'count': 60},
        '15m': {'upbit': 'minutes/15', 'count': 60},
        '30m': {'upbit': 'minutes/30', 'count': 60},
        '1h': {'upbit': 'minutes/60', 'count': 48},
        '4h': {'upbit': 'minutes/240', 'count': 48},
        '1d': {'upbit': 'days', 'count': 60},
        '1w': {'upbit': 'weeks', 'count': 52},
        '1M': {'upbit': 'months', 'count': 24},
    }
    
    def __init__(self):
        self.upbit_base = "https://api.upbit.com/v1/candles"
        self.bithumb_base = "https://api.bithumb.com/public/candlestick"
    
    def get_candles(self, symbol: str, timeframe: str = '1h', count: int = 100) -> List[Dict]:
        """
        캔들 데이터 조회 - Upbit 우선, Bithumb 폴백
        
        Args:
            symbol: 코인 심볼 (BTC, ETH 등)
            timeframe: 시간대 (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
            count: 캔들 개수
        
        Returns:
            OHLCV 리스트 [{"time": unix, "open": float, "high": float, "low": float, "close": float, "volume": float}]
        """
        
        # 1차: Upbit
        candles = self._fetch_upbit(symbol, timeframe, count)
        if candles:
            return candles
        
        # 2차: Bithumb
        candles = self._fetch_bithumb(symbol, timeframe, count)
        if candles:
            return candles
        
        # 폴백: 빈 리스트
        logger.warning(f"캔들 데이터 수집 실패: {symbol}/{timeframe}")
        return []
    
    def _fetch_upbit(self, symbol: str, timeframe: str, count: int) -> Optional[List[Dict]]:
        """Upbit에서 캔들 조회"""
        try:
            tf_config = self.TIMEFRAME_MAP.get(timeframe, {'upbit': 'minutes/60', 'count': 48})
            market = f"KRW-{symbol.upper()}"
            
            url = f"{self.upbit_base}/{tf_config['upbit']}"
            params = {
                'market': market,
                'count': min(count, 200)  # Upbit 최대 200개
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Lightweight Charts 포맷으로 변환
                candles = []
                for c in reversed(data):  # 시간순 정렬
                    candles.append({
                        'time': int(datetime.fromisoformat(c['candle_date_time_kst'].replace('T', ' ')).timestamp()),
                        'open': float(c['opening_price']),
                        'high': float(c['high_price']),
                        'low': float(c['low_price']),
                        'close': float(c['trade_price']),
                        'volume': float(c['candle_acc_trade_volume'])
                    })
                
                logger.info(f"✅ Upbit 캔들 수집 성공: {symbol}/{timeframe} ({len(candles)}개)")
                return candles
                
        except Exception as e:
            logger.warning(f"Upbit 캔들 오류: {e}")
        
        return None
    
    def _fetch_bithumb(self, symbol: str, timeframe: str, count: int) -> Optional[List[Dict]]:
        """Bithumb에서 캔들 조회"""
        try:
            # Bithumb 시간대 매핑
            bithumb_tf_map = {
                '1m': '1m', '5m': '5m', '10m': '10m', '30m': '30m',
                '1h': '1h', '6h': '6h', '12h': '12h', '1d': '24h'
            }
            
            tf = bithumb_tf_map.get(timeframe, '1h')
            url = f"{self.bithumb_base}/{symbol.upper()}_KRW/{tf}"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == '0000' and data.get('data'):
                    raw_candles = data['data'][-count:]
                    
                    candles = []
                    for c in raw_candles:
                        candles.append({
                            'time': int(c[0] / 1000),  # ms -> s
                            'open': float(c[1]),
                            'close': float(c[2]),
                            'high': float(c[3]),
                            'low': float(c[4]),
                            'volume': float(c[5])
                        })
                    
                    logger.info(f"✅ Bithumb 캔들 수집 성공: {symbol}/{timeframe} ({len(candles)}개)")
                    return candles
                    
        except Exception as e:
            logger.warning(f"Bithumb 캔들 오류: {e}")
        
        return None


# 테스트
if __name__ == "__main__":
    collector = CandleCollector()
    
    # BTC 1시간봉 테스트
    candles = collector.get_candles('BTC', '1h', 24)
    
    print(f"\n📊 BTC 1시간봉 ({len(candles)}개)")
    if candles:
        latest = candles[-1]
        print(f"   시가: ₩{latest['open']:,.0f}")
        print(f"   고가: ₩{latest['high']:,.0f}")
        print(f"   저가: ₩{latest['low']:,.0f}")
        print(f"   종가: ₩{latest['close']:,.0f}")
