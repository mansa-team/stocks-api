from imports import *

from main.api import Service as API_Service
from main.rag import Service as RAG_Service

def mysql_connectiontest():
    mysql_engine = create_engine(f"mysql+pymysql://{Config.MYSQL['USER']}:{Config.MYSQL['PASSWORD']}@{Config.MYSQL['HOST']}/{Config.MYSQL['DATABASE']}")
    
    try:
        start_time = time.time()
        
        with mysql_engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.close()
        
        latency = (time.time() - start_time) * 1000
        
        print(f"MySQL connected! ({latency:.2f}ms)")
        return True
        
    except Exception as e:
        print(f"MySQL connection failed: {e}")
        return False
    
def initialize(module, config):
    print("=" * 30)
    print(f"Configuring {module}")
    print("=" * 30)

    if module == "STOCKS_API":
        if config['HOST'] in LOCALHOST_ADDRESSES and mysql_connectiontest():
            if config['API.ROUTE'] == 'TRUE':
                pass
                #API_Service.initialize(config['PORT'])
                pass
            if config['RAG.ROUTE'] == 'TRUE':
                pass
                #RAG_Service.initialize(config['PORT'])

        #$ Stocks API connection test
        try:
            start_time = time.time()
            response = requests.get(f"http://{config['HOST']}:{config['PORT']}/health", timeout=5)
            latency = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return print(f"Stocks API connected to http://{config['HOST']}:{config['PORT']}! ({latency:.2f}ms)")
            else: return print(f"Stocks API returned status {response.status_code}")
                                
        except requests.exceptions.Timeout:
            return print(f"Stocks API connection timeout (5s)")
        except requests.exceptions.ConnectionError:
            return print(f"Cannot connect to Stocks API: {config['HOST']}:{config['PORT']}")
        except Exception as e:
            print(f"Stocks API connection failed: {e}")

if __name__ == "__main__":
    if Config.STOCKS_API['ENABLED'] == "TRUE":
        initialize("STOCKS_API", Config.STOCKS_API)