import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

#
#$ Utility Functions
#
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
 
def getAvailableColumns(engine) -> list:
    """Fetch all available columns with caching"""
    if not hasattr(getAvailableColumns, '_cache') or getAvailableColumns._cache is None:
        try:
            with engine.connect() as connection:
                result = connection.execute(text("SHOW COLUMNS FROM b3_stocks"))
                getAvailableColumns._cache = [row[0] for row in result.fetchall()]
                return getAvailableColumns._cache
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching database columns: {str(e)}")
    return getAvailableColumns._cache

def parseYearInput(years: str) -> tuple:
    """Parse year input and return (start_year, end_year)"""
    if not years:
        return None, None
    year_list = [int(y.strip()) for y in years.split(",")]
    if len(year_list) == 1:
        return year_list[0], year_list[0]
    elif len(year_list) == 2:
        return year_list[0], year_list[1]
    raise HTTPException(status_code=400, detail="Years format: YEAR or START_YEAR,END_YEAR")

def parseDateRange(date_str: str) -> tuple:
    """Parse date string and return (start_date, end_date)"""
    if len(date_str) == 4:
        return f"{date_str}-01-01", f"{date_str}-12-31"
    elif len(date_str) == 7:
        year, month = int(date_str[:4]), int(date_str[5:7])
        last_day = pd.Timestamp(year=year, month=month, day=1).days_in_month
        return f"{date_str}-01", f"{date_str}-{last_day:02d}"
    return date_str, date_str

def categorizeColumns(columns: list) -> tuple:
    """Categorize columns into historical and fundamental"""
    historical_fields = {}
    historical_cols = set()
    
    for col in columns:
        parts = col.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            year = int(parts[1])
            if 1900 <= year <= 2100:
                field_name = parts[0]
                historical_fields.setdefault(field_name, []).append(year)
                historical_cols.add(col)
    
    temporal_cols = {"TICKER", "NOME", "TIME"}
    fundamental_cols = sorted([col for col in columns if col not in temporal_cols and col not in historical_cols])
    
    return historical_fields, fundamental_cols

def buildQuery(cols: list, where_clause: str, order_by: str = "") -> str:
    """Build SQL query"""
    order = f" ORDER BY {order_by}" if order_by else ""
    return f"SELECT {', '.join(cols)} FROM b3_stocks WHERE {where_clause}{order}"

def executeQuery(engine, query: str, params: dict) -> pd.DataFrame:
    """Execute query using shared engine"""
    with engine.connect() as connection:
        result = connection.execute(query, params)
        return pd.DataFrame(result.fetchall(), columns=result.keys())

def normalizeColumns(data: pd.DataFrame, order: list) -> pd.DataFrame:
    """Normalize column order in DataFrame"""
    columns = list(data.columns)
    orderedColumns = [col for col in order if col in columns]
    remainingColumns = sorted([col for col in columns if col not in orderedColumns])
    newOrder = orderedColumns + remainingColumns
    return data[newOrder]

#
#$ API Queries
#
async def queryHistorical(engine, search: str = None, fields: str = None, years: str = None):
    try:
        available_columns = getAvailableColumns(engine)
        historical_fields, _ = categorizeColumns(available_columns)
        
        if not historical_fields:
            raise HTTPException(status_code=400, detail="No historical data available")
        
        field_list_available = sorted(historical_fields.keys())
        field_list = field_list_available if not fields else [f.strip() for f in fields.split(",") if f.strip() in field_list_available]
        
        if not field_list:
            raise HTTPException(status_code=400, detail=f"No valid fields. Available: {field_list_available}")
        
        available_years = sorted(set(year for field in field_list for year in historical_fields[field]))
        year_start, year_end = parseYearInput(years) if years else (available_years[0], available_years[-1])
        
        if year_start not in available_years or year_end not in available_years or year_start > year_end:
            raise HTTPException(status_code=400, detail=f"Invalid years. Available: {available_years}")
        
        cols = ["`TICKER`", "`NOME`"] + [f"`{field} {year}`" for field in field_list for year in range(year_start, year_end + 1) if f"{field} {year}" in available_columns]
        
        if len(cols) == 2:
            raise HTTPException(status_code=400, detail="No valid columns found")
        
        where_clause = "(UPPER(`TICKER`) = UPPER(:search) OR UPPER(`NOME`) LIKE CONCAT('%', UPPER(:search), '%'))" if search else "1=1"
        params = {"search": search} if search else {}
        
        df = executeQuery(engine, text(buildQuery(cols, where_clause, "`TICKER` ASC")), params)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found")
        
        return {
            "search": search or "all",
            "fields": sorted(field_list),
            "years": [year_start, year_end],
            "type": "historical",
            "count": len(df),
            "data": json.loads(df.to_json(orient="records"))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching historical data: {str(e)}")

async def queryFundamental(engine, search: str = None, fields: str = None, dates: str = None):
    try:
        available_columns = getAvailableColumns(engine)
        _, fundamental_cols = categorizeColumns(available_columns)
        
        if not fundamental_cols:
            raise HTTPException(status_code=400, detail="No fundamental data available")
        
        field_list = fundamental_cols if not fields else [f.strip() for f in fields.split(",") if f.strip() in fundamental_cols]
        
        if not field_list:
            raise HTTPException(status_code=400, detail=f"No valid fields. Available: {fundamental_cols}")
        
        cols = ["`TICKER`", "`NOME`", "`TIME`"] + [f"`{field}`" for field in field_list]
        
        if dates:
            date_list = [d.strip() for d in dates.split(",")]
            if len(date_list) == 1:
                actual_start, actual_end = parseDateRange(date_list[0])
                original_date = date_list[0]
            elif len(date_list) == 2:
                actual_start, actual_end = date_list[0], date_list[1]
                original_date = f"{date_list[0]} to {date_list[1]}"
            else:
                raise HTTPException(status_code=400, detail="Dates format: DATE or START_DATE,END_DATE")
            
            where_clause = f"DATE(`TIME`) BETWEEN DATE(:date_start) AND DATE(:date_end)"
            params = {"date_start": actual_start, "date_end": actual_end}
        else:
            where_clause = "1=1"
            params = {}
            original_date = "all"
        
        if search:
            where_clause = f"(UPPER(`TICKER`) = UPPER(:search) OR UPPER(`NOME`) LIKE CONCAT('%', UPPER(:search), '%')) AND {where_clause}"
            params["search"] = search
        
        df = executeQuery(engine, text(buildQuery(cols, where_clause, "`TICKER` ASC, `TIME` DESC")), params)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found")
        
        if 'TIME' in df.columns:
            df['TIME'] = pd.to_datetime(df['TIME']).astype(str)
        
        column_order = ['TIME', 'NOME', 'TICKER', 'SETOR', 'SUBSETOR', 'SEGMENTO', 'ALTMAN Z-SCORE', 'SGR', 'LIQUIDEZ MEDIA DIARIA', 'PRECO', 'PRECO DE BAZIN', 'PRECO DE GRAHAM', 'TAG ALONG', 'RENT 12 MESES', 'RENT MEDIA 5 ANOS', 'DY', 'DY MEDIO 5 ANOS', 'P/L', 'P/VP', 'P/ATIVOS', 'MARGEM BRUTA', 'MARGEM EBIT', 'MARG. LIQUIDA', 'EBIT', 'P/EBIT', 'EV/EBIT', 'DIVIDA LIQUIDA / EBIT', 'DIV. LIQ. / PATRI.', 'PSR', 'P/CAP. GIRO', 'P. AT CIR. LIQ.', 'LIQ. CORRENTE', 'LUCRO LIQUIDO MEDIO 5 ANOS', 'ROE', 'ROA', 'ROIC', 'PATRIMONIO / ATIVOS', 'PASSIVOS / ATIVOS', 'GIRO ATIVOS', 'CAGR DIVIDENDOS 5 ANOS', 'CAGR RECEITAS 5 ANOS', 'CAGR LUCROS 5 ANOS', 'VPA', 'LPA', 'PEG Ratio', 'VALOR DE MERCADO']

        ordered_field_list = [col for col in column_order if col in field_list]
        remaining_fields = [col for col in field_list if col not in column_order]
        field_list = ordered_field_list + sorted(remaining_fields)

        df = normalizeColumns(df, column_order)
        
        return {
            "search": search or "all",
            "fields": field_list,
            "dates": original_date,
            "type": "fundamental",
            "count": len(df),
            "data": json.loads(df.to_json(orient="records"))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching fundamental data: {str(e)}")

class API:
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = int(port)
        self.app = FastAPI(title=service_name, version="1.0.0")
        self._db_engine = create_engine(
            f"mysql+pymysql://{Config.MYSQL['USER']}:{Config.MYSQL['PASSWORD']}@{Config.MYSQL['HOST']}/{Config.MYSQL['DATABASE']}",
            poolclass=None, echo=False
        )
        self.setupRoutes()
    
    def setupRoutes(self):
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "service": self.service_name, "port": self.port, "timestamp": str(time.time())}
        
        @self.app.get("/")
        async def root():
            return {"message": "Mansa (Stocks API)"}
        
        @self.app.get("/api/key")
        async def APIKeyTest(api_key: str = Depends(verifyAPIKey)):
            return {"message": "API", "secured": True}
        
        @self.app.get("/api/historical")
        async def getHistorical(search: str = Query(None), fields: str = Query(None), years: str = Query(None), api_key: str = Depends(verifyAPIKey)):
            return await queryHistorical(self._db_engine, search, fields, years)
        
        @self.app.get("/api/fundamental")
        async def getFundamental(search: str = Query(None), fields: str = Query(None), dates: str = Query(None), api_key: str = Depends(verifyAPIKey)):
            return await queryFundamental(self._db_engine, search, fields, dates)
    
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="critical")