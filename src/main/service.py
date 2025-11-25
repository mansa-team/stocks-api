import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

APIKey_Header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verifyAPIKey(APIKey: str = Depends(APIKey_Header)):
    if Config.STOCKS_API['KEY.SYSTEM'] == 'FALSE':
        return None
    
    validKey = Config.STOCKS_API.get('KEY')
    if not validKey:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    if APIKey is None or APIKey != validKey:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    return APIKey

class Service:
    instances = {}
    
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = int(port)
        self.app = FastAPI(title=service_name, version="1.0.0")
        self.setupRoutes()
    
    def setupRoutes(self):
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": self.service_name,
                "port": self.port,
                "timestamp": str(time.time())
            }
        
        @self.app.get("/")
        async def root():
            return {"message": "Mansa (Stocks API)"}
        
        @self.app.get("/api/key")
        async def api_key_test(api_key: str = Depends(verifyAPIKey)):
            return {"message": "API", "secured": True}
        
        @self.app.get("/api/historical")
        async def get_historical(
            search: str = Query(...),
            fields: str = Query(...),
            years: str = Query(...),
            api_key: str = Depends(verifyAPIKey)
        ):
            return await self.queryHistorical(search, fields, years)
        
        @self.app.get("/api/fundamental")
        async def get_fundamental(
            search: str = Query(...),
            fields: str = Query(...),
            dates: str = Query(...),
            api_key: str = Depends(verifyAPIKey)
        ):
            return await self.queryFundamental(search, fields, dates)
    
    async def queryHistorical(self, search: str, fields: str, years: str):
        try:
            field_list = [f.strip() for f in fields.split(",")]
            year_list = [int(y.strip()) for y in years.split(",")]
            
            if len(year_list) == 1:
                year_start = year_end = year_list[0]
            elif len(year_list) == 2:
                year_start, year_end = year_list
            else:
                raise HTTPException(status_code=400, detail="Years format: YEAR or START_YEAR,END_YEAR")
            
            # Build column selection
            cols = ["`TICKER`", "`NOME`"]
            cols.extend([f"`{field} {year}`" for field in field_list for year in range(year_start, year_end + 1)])
            
            query = text(f"""
                SELECT {', '.join(cols)}
                FROM b3_stocks
                WHERE UPPER(`TICKER`) = UPPER(:search) OR UPPER(`NOME`) LIKE CONCAT('%', UPPER(:search), '%')
                LIMIT 1
            """)
            
            df = self._execute_query(query, {"search": search})
            
            if df.empty:
                raise HTTPException(status_code=404, detail=f"No data found for: {search}")
            
            return {
                "search": search,
                "fields": field_list,
                "years": [year_start, year_end],
                "type": "historical",
                "data": json.loads(df.to_json(orient="records"))
            }
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching historical data: {str(e)}")
    
    async def queryFundamental(self, search: str, fields: str, dates: str):
        try:
            field_list = [f.strip() for f in fields.split(",")]
            date_list = [d.strip() for d in dates.split(",")]
            
            if len(date_list) == 1:
                date_start = date_end = date_list[0]
                single_date = True
            elif len(date_list) == 2:
                date_start, date_end = date_list
                single_date = False
            else:
                raise HTTPException(status_code=400, detail="Dates format: DATE or START_DATE,END_DATE")
            
            # Build column selection
            cols = ["`TICKER`", "`NOME`", "`TIME`"]
            cols.extend([f"`{field}`" for field in field_list])
            
            if single_date:
                # Handle partial dates: 2025 -> 2025-01-01 to 2025-12-31, 2025-11 -> 2025-11-01 to 2025-11-30
                if len(date_start) == 4:  # Year only
                    actual_start = f"{date_start}-01-01"
                    actual_end = f"{date_start}-12-31"
                elif len(date_start) == 7:  # Year-Month
                    # Get last day of the month using calendar
                    year, month = int(date_start[:4]), int(date_start[5:7])
                    last_day = pd.Timestamp(year=year, month=month, day=1).days_in_month
                    actual_start = f"{date_start}-01"
                    actual_end = f"{date_start}-{last_day:02d}"
                else:  # Full date
                    actual_start = actual_end = date_start
                
                query = text(f"""
                    SELECT {', '.join(cols)}
                    FROM b3_stocks
                    WHERE (UPPER(`TICKER`) = UPPER(:search) OR UPPER(`NOME`) LIKE CONCAT('%', UPPER(:search), '%'))
                    AND DATE(`TIME`) BETWEEN DATE(:date_start) AND DATE(:date_end)
                    ORDER BY `TIME` DESC
                """)
                params = {
                    "search": search,
                    "date_start": actual_start,
                    "date_end": actual_end
                }
            else:
                query = text(f"""
                    SELECT {', '.join(cols)}
                    FROM b3_stocks
                    WHERE (UPPER(`TICKER`) = UPPER(:search) OR UPPER(`NOME`) LIKE CONCAT('%', UPPER(:search), '%'))
                    AND DATE(`TIME`) BETWEEN DATE(:date_start) AND DATE(:date_end)
                    ORDER BY `TIME` DESC
                """)
                params = {
                    "search": search,
                    "date_start": date_start,
                    "date_end": date_end
                }
            
            df = self._execute_query(query, params)
            
            if df.empty:
                raise HTTPException(status_code=404, detail=f"No data found for: {search}")
            
            # Convert TIME to string
            if 'TIME' in df.columns:
                df['TIME'] = pd.to_datetime(df['TIME']).astype(str)
            
            return {
                "search": search,
                "fields": field_list,
                "dates": [date_start, date_end],
                "type": "fundamental",
                "data": json.loads(df.to_json(orient="records"))
            }
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching fundamental data: {str(e)}")
    
    def _execute_query(self, query: str, params: dict) -> pd.DataFrame:
        engine = create_engine(
            f"mysql+pymysql://{Config.MYSQL['USER']}:{Config.MYSQL['PASSWORD']}@{Config.MYSQL['HOST']}/{Config.MYSQL['DATABASE']}"
        )
        with engine.connect() as connection:
            result = connection.execute(query, params)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="critical")
    
    @classmethod
    def initialize(cls, service_name: str, port: int):
        key = f"{service_name}_{port}"
        if key not in cls.instances:
            instance = cls(service_name, port)
            thread = threading.Thread(target=instance.run, daemon=True)
            thread.start()
            cls.instances[key] = instance
        return cls.instances[key]