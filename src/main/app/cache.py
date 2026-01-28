import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

STOCKS_CACHE = None
CACHE_LOCK = threading.Lock()

def startCacheScheduler(engine):
    def scheduler():
        getCachedStocks(engine)
        while True:
            time.sleep(10*60) # 10 Minutes
            getCachedStocks(engine)

    thread = threading.Thread(target=scheduler, daemon=True)
    thread.start()

def getCachedStocks(engine):
    global STOCKS_CACHE

    try:
        with engine.connect() as conn:
            df = pd.read_sql("SELECT * FROM b3_stocks", conn)
            df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

            with CACHE_LOCK:
                STOCKS_CACHE = df
            print(f"[{datetime.now()}] Cache updated: {len(df)} rows")
        
    except Exception as e:
        print(f"Erro: {e}")
            