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
 
def getAvailableColumns(engine) -> list:
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
    if not years:
        return None, None
    year_list = [int(y.strip()) for y in years.split(",")]
    if len(year_list) == 1:
        return year_list[0], year_list[0]
    elif len(year_list) == 2:
        return year_list[0], year_list[1]
    raise HTTPException(status_code=400, detail="Years format: YEAR or START_YEAR,END_YEAR")

def parseDateRange(date_str: str) -> tuple:
    if len(date_str) == 4:
        return f"{date_str}-01-01", f"{date_str}-12-31"
    elif len(date_str) == 7:
        year, month = int(date_str[:4]), int(date_str[5:7])
        last_day = pd.Timestamp(year=year, month=month, day=1).days_in_month
        return f"{date_str}-01", f"{date_str}-{last_day:02d}"
    return date_str, date_str

def categorizeColumns(columns: list) -> tuple:
    historical_fields = {}
    historical_cols = set()
    current_year = datetime.now().year
    
    for col in columns:
        parts = col.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            year = int(parts[1])
            # Only accept reasonable years: 1990 to current year + 5
            if 1990 <= year <= (current_year + 5):
                field_name = parts[0]
                historical_fields.setdefault(field_name, []).append(year)
                historical_cols.add(col)
    
    temporal_cols = {"TICKER", "NOME", "TIME"}
    fundamental_cols = []
    
    for col in columns:
        if col in temporal_cols or col in historical_cols:
            continue
        
        # Also exclude columns that look like they have invalid year suffixes
        parts = col.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            year = int(parts[1])
            # Skip columns with invalid years
            if not (1990 <= year <= (current_year + 5)):
                continue
        
        fundamental_cols.append(col)
    
    fundamental_cols = sorted(fundamental_cols)
    
    return historical_fields, fundamental_cols

def filterValidHistoricalColumns(cols: list, available_columns: set) -> list:
    valid_cols = []
    for col in cols:
        if col in ["`TICKER`", "`NOME`"]:
            valid_cols.append(col)
        else:
            # Extract field and year from column name
            col_clean = col.replace("`", "")
            parts = col_clean.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                year = int(parts[1])
                # Only include columns with valid years
                if 1900 <= year <= 2100 and col_clean in available_columns:
                    valid_cols.append(col)
            elif col_clean in available_columns:
                valid_cols.append(col)
    return valid_cols

def filterValidFundamentalColumns(cols: list, available_columns: set) -> list:
    valid_cols = []
    for col in cols:
        col_clean = col.replace("`", "")
        # Reject columns that end with year-like patterns that are invalid
        parts = col_clean.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            year = int(parts[1])
            # Skip if year is outside valid range
            if not (1900 <= year <= 2100):
                continue
        valid_cols.append(col)
    return valid_cols

def buildQuery(cols: list, where_clause: str, order_by: str = "") -> str:
    order = f" ORDER BY {order_by}" if order_by else ""
    return f"SELECT {', '.join(cols)} FROM b3_stocks WHERE {where_clause}{order}"

def executeQuery(engine, query: str, params: dict) -> pd.DataFrame:
    with engine.connect() as connection:
        result = connection.execute(query, params)
        return pd.DataFrame(result.fetchall(), columns=result.keys())

def normalizeColumns(data: pd.DataFrame, order: list) -> pd.DataFrame:
    columns = list(data.columns)
    orderedColumns = [col for col in order if col in columns]
    remainingColumns = sorted([col for col in columns if col not in orderedColumns])
    newOrder = orderedColumns + remainingColumns
    return data[newOrder]

def parseSearchTerms(search: str) -> list:
    if not search:
        return []
    return [s.strip().upper() for s in search.split(",") if s.strip()]

def buildMultiTickerWhereClause(search_terms: list) -> tuple:
    if not search_terms:
        return "1=1", {}
    
    conditions = []
    params = {}
    
    for i, term in enumerate(search_terms):
        conditions.append(f"(UPPER(`TICKER`) = :ticker_{i} OR UPPER(`NOME`) LIKE :nome_{i})")
        params[f"ticker_{i}"] = term
        params[f"nome_{i}"] = f"%{term}%"
    
    where_clause = " OR ".join(conditions)
    return where_clause, params