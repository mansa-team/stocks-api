import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

from main.app.query import queryFundamental, queryHistorical
from main.app.util import verifyAPIKey
from main.app.cache import startCacheScheduler
class API:
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = int(port)
        self.app = FastAPI(title=service_name, version="1.0.0")

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.setupRoutes()
        startCacheScheduler(dbEngine)
    
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
        async def getHistorical(search: str = Query(None), fields: str = Query(None), dates: str = Query(None), api_key: str = Depends(verifyAPIKey)):
            return await queryHistorical(search, fields, dates)
        
        @self.app.get("/api/fundamental")
        async def getFundamental(search: str = Query(None), fields: str = Query(None), dates: str = Query(None), api_key: str = Depends(verifyAPIKey)):
            return await queryFundamental(search, fields, dates)
        
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="critical")