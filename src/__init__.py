from imports import *

from main.service import Service as STOCKSAPI_Service

def mysql_connectiontest():
    try:
        start_time = time.time()
        
        with dbEngine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.close()
        
        latency = (time.time() - start_time) * 1000
        
        print(f"MySQL connected! ({latency:.2f}ms)")
        return True
        
    except Exception as e:
        print(f"MySQL connection failed: {e}")
        return False
    
def initialize(module, config):
    print("=" * 60)
    print(f"Configuring {module}\n")

    #
    #$ STOCKS_API
    #
    if module == "STOCKS_API":
        if config['HOST'] in LOCALHOST_ADDRESSES and mysql_connectiontest():
            STOCKSAPI_Service.initialize(
                "Mansa (Stocks API)",
                int(config['PORT']),
            )

    #
    #$ Connection Test
    #
    time.sleep(2)

    if module == "STOCKS_API":
        try:
            start_time = time.time()
            response = requests.get(f"http://{config['HOST']}:{config['PORT']}/health", timeout=5)
            latency = (time.time() - start_time) * 1000

            if response.status_code == 200:
                print(f"Mansa ({module}) connected to http://{config['HOST']}:{config['PORT']}! ({latency:.2f}ms)")
            else: print(f"Mansa ({module}) returned status {response.status_code}")
                                
        except requests.exceptions.Timeout:
            print(f"Mansa ({module}) connection timeout (5s)")
        except Exception as e:
            print(f"Mansa ({module}) connection failed: {e}")

        print("=" * 60, "\n")

if __name__ == "__main__":
    if Config.STOCKS_API['ENABLED'] == "TRUE":
        initialize("STOCKS_API", Config.STOCKS_API)

    while True: time.sleep(1)