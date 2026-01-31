import requests
import logging
import time

logger = logging.getLogger("PhoenixBithumb")

def fetch_bithumb_market():
    """
    Fetches snapshot of ALL KRW market tickers from Bithumb.
    Returns a list of standardized dict objects.
    """
    url = "https://api.bithumb.com/public/ticker/ALL_KRW"
    
    try:
        # 2-second timeout to ensure no blocking behavior cascades, 
        # though the Engine runs in a loop so blocking is less critical than in API.
        res = requests.get(url, timeout=3).json()
        
        if res.get('status') != '0000':
            logger.warning(f"Bithumb API Error: {res.get('status')}")
            return []
            
        data = res.get('data', {})
        market_list = []
        
        date = data.pop('date', None) # Remove timestamp key
        
        for symbol, info in data.items():
            try:
                # Standardize Data Structure
                ticker = {
                    'symbol': symbol,
                    'price': float(info['closing_price']),
                    'open': float(info['opening_price']),
                    'high': float(info['max_price']),
                    'low': float(info['min_price']),
                    'volume': float(info['acc_trade_value_24H']), # Using Trade Value (KRW) for better ranking
                    'change_rate': float(info['fluctate_rate_24H']),
                    'change_amt': float(info['fluctate_24H']),
                    'exchange': 'Bithumb'
                }
                market_list.append(ticker)
            except Exception as e:
                continue # Skip bad records
                
        # Sort by 24h Trade Value (Volume) Descending
        market_list.sort(key=lambda x: x['volume'], reverse=True)
        
        return market_list
        
    except Exception as e:
        logger.error(f"Fetch Failed: {e}")
        return []

if __name__ == "__main__":
    # Test Run
    print("Fetching Bithumb Data...")
    start = time.time()
    data = fetch_bithumb_market()
    print(f"Fetched {len(data)} coins in {time.time() - start:.4f}s")
    if data:
        print("Top 3:", data[:3])
