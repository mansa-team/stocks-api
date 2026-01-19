import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *
from main.app.util import *

async def queryHistorical(engine, search: str = None, fields: str = None, dates: str = None):
    try:
        available_columns = getAvailableColumns(engine)
        available_columns_set = set(available_columns)
        historical_fields, _ = categorizeColumns(available_columns)
        
        if not historical_fields:
            raise HTTPException(status_code=400, detail="No historical data available")
        
        field_list_available = sorted(historical_fields.keys())
        field_list = field_list_available if not fields else [f.strip() for f in fields.split(",") if f.strip() in field_list_available]
        
        if not field_list:
            raise HTTPException(status_code=400, detail=f"No valid fields. Available: {field_list_available}")
        
        available_years = sorted(set(year for field in field_list for year in historical_fields[field]))
        year_start, year_end = parseYearInput(dates) if dates else (available_years[0], available_years[-1])
        
        if year_start not in available_years or year_end not in available_years or year_start > year_end:
            raise HTTPException(status_code=400, detail=f"Invalid years. Available: {available_years}")
        
        cols = ["`TICKER`", "`NOME`"] + [f"`{field} {year}`" for field in field_list for year in range(year_start, year_end + 1) if f"{field} {year}" in available_columns_set]
        
        # Filter out invalid year columns
        cols = filterValidHistoricalColumns(cols, available_columns_set)
        
        if len(cols) == 2:
            raise HTTPException(status_code=400, detail="No valid columns found")
        
        search_terms = parseSearchTerms(search)
        where_clause, params = buildMultiTickerWhereClause(search_terms)
        
        df = executeQuery(engine, text(buildQuery(cols, where_clause, "`TICKER` ASC")), params)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found")
        
        # Deduplicate: Keep only the first occurrence of each ticker
        df = df.drop_duplicates(subset=['TICKER'], keep='first')
        
        return {
            "search": search or "all",
            "fields": sorted(field_list),
            "dates": [year_start, year_end],
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
        available_columns_set = set(available_columns)
        _, fundamental_cols = categorizeColumns(available_columns)
        
        if not fundamental_cols:
            raise HTTPException(status_code=400, detail="No fundamental data available")
        
        field_list = fundamental_cols if not fields else [f.strip() for f in fields.split(",") if f.strip() in fundamental_cols]
        
        if not field_list:
            raise HTTPException(status_code=400, detail=f"No valid fields. Available: {fundamental_cols}")
        
        cols = ["`TICKER`", "`NOME`", "`TIME`"] + [f"`{field}`" for field in field_list]
        
        # Filter out invalid columns
        cols = filterValidFundamentalColumns(cols, available_columns_set)
        
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
        
        search_terms = parseSearchTerms(search)
        search_where_clause, search_params = buildMultiTickerWhereClause(search_terms)
        
        if search_terms:
            where_clause = f"({search_where_clause}) AND {where_clause}"
            params.update(search_params)
        
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
