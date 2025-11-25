# Brazilian Stocks Market API

A full on API for more than 40 fundamentalist data in the Brazillian Stock Market, using an API Key system to deliver amazing performance and usuability for our users.

Built for commercial use and to the [Mansa](https://github.com/mansa-team) project and possibly Retrieval-Augmented Generation (RAG) prompting.

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/heitorrosa/stocks-api
    cd stocks-api
    ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create environment configuration:
   ```env
    #
    #$ DATABASE CONFIGURATION
    #
    MYSQL_USER=user
    MYSQL_PASSWORD=password
    MYSQL_HOST=localhost
    MYSQL_DATABASE=database

    #
    #$ STOCKS API
    #
    STOCKSAPI_ENABLED=TRUE

    # STOCKSAPI_HOST should be set if youre going to use an external server for the API Server, make sure to set STOCKSAPI_ENABLE=FALSE if youre going this route
    STOCKSAPI_HOST=localhost
    STOCKSAPI_PORT=3200

    STOCKSAPI_RAG.ROUTE=TRUE
    STOCKSAPI_API.ROUTE=TRUE

    STOCKSAPI_RAG.KEY=key
   ```

4. Run the Python Server
    ```bash
        python src/__init__.py
    ```
    
## API Endpoints

### Standard API Routes (`STOCKSAPI_API.ROUTE`)
Indented for general porpouse and use, mainly focused for selling porpouses and with an dedicated KEY system using MySQL.

### RAG Routes (`STOCKSAPI_RAG.ROUTE`)
A private route intended for the RAG that will be used to enchance the models and improve the performance of the Chatbot. With a special KEY defined in the .env using `STOCKSAPI_RAG.KEY`.

### Historical Data
Query financial metrics across multiple years:
```bash
curl -H "X-API-Key: KEY" "http://localhost:3200/api/rag/historical?ticker=PETR4&fields=DY,LUCRO%20LIQUIDO&years=2020,2024"
```
**Allowed fields:** `DESPESAS`, `DY`, `LUCRO LIQUIDO`, `MARGEM BRUTA`, `MARGEM EBIT`, `MARGEM EBITDA`, `MARGEM LIQUIDA`, `RECEITA LIQUIDA`

### Fundamental Data
Query current valuations and metrics by date range:
```bash
curl -H "X-API-Key: KEY" "http://localhost:3200/api/rag/fundamental?ticker=VALE3&fields=ROE,P/L,PRECO&dates=2024-01-01,2024-12-31"
```
**Allowed fields:** `P/L`, `P/VP`, `ROE`, `ROA`, `PRECO`, `DY`, `MARGEM BRUTA`, `MARGEM EBIT`, `MARG. LIQUIDA`, and 30+ more fundamentals.

## License
GPL 3.0 MODIFIED Mansa Team's License. See LICENSE for details.
