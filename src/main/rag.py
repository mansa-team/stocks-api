import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

RAG_APIKeyHeader = APIKeyHeader(name="X-API-Key", auto_error=False)
async def verifyRAGkey(ragAPIKey: str = Depends(RAG_APIKeyHeader)):
    validKey = Config.STOCKS_API['RAG.KEY']

    if not validKey:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG API key not configured"
        )
    
    if ragAPIKey is None or ragAPIKey != validKey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing RAG API key"
        )
    
def setupRoutes(app):
    @app.get("/rag/keytest")
    async def getRAGkeytest(ragAPIKey: str = Depends(verifyRAGkey)):
        return {"message": "RAG", "secured": True}