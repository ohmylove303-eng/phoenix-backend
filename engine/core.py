import time
import logging
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.state import save_state
from engine.collectors.bithumb import fetch_bithumb_market

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [PHOENIX ENGINE] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("PhoenixCore")

def run_engine():
    """
    Main Loop for Phoenix Engine.
    "The Factory that never sleeps."
    """
    logger.info("Phoenix Engine Starting... 🚀")
    
    cycle_count = 0
    
    try:
        while True:
            cycle_start = time.time()
            
            # 1. Collect Data
            # logger.info("Collecting Market Data...")
            market_data = fetch_bithumb_market()
            
            if not market_data:
                logger.warning("No data collected. Retrying in 2s...")
                time.sleep(2)
                continue
                
            # 2. Analyze (Simple Sorting/Filtering for MVP)
            # In Phase 2, we can add indicators here.
            top_gainers = sorted(market_data, key=lambda x: x['change_rate'], reverse=True)[:10]
            top_volume = sorted(market_data, key=lambda x: x['volume'], reverse=True)[:10]
            
            # 3. Construct Global State
            state = {
                'status': 'ONLINE',
                'cycle': cycle_count,
                'market_summary': {
                    'total_coins': len(market_data),
                    'total_volume': sum(x['volume'] for x in market_data)
                },
                'tickers': market_data, # Full List
                'top_gainers': top_gainers,
                'top_volume': top_volume
            }
            
            # 4. Save State Atomically
            save_state(state)
            
            duration = time.time() - cycle_start
            logger.info(f"Cycle #{cycle_count} Completed in {duration:.3f}s | Coins: {len(market_data)}")
            
            cycle_count += 1
            
            # Rate Limit (aim for 1 update per 1.5s total)
            sleep_time = max(0.5, 1.5 - duration)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Engine Stopping... (User Interrupt)")
    except Exception as e:
        logger.critical(f"Engine Crash: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_engine()
