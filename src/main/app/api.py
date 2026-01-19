import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

from main.app.query import *

class API:
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = int(port)
        self.app = FastAPI(title=service_name, version="1.0.0")
        self._db_engine = create_engine(
            f"mysql+pymysql://{Config.MYSQL['USER']}:{Config.MYSQL['PASSWORD']}@{Config.MYSQL['HOST']}/{Config.MYSQL['DATABASE']}",
            poolclass=None, echo=False
        )

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
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
        async def getHistorical(search: str = Query(None), fields: str = Query(None), dates: str = Query(None), api_key: str = Depends(verifyAPIKey)):
            return await queryHistorical(self._db_engine, search, fields, dates)
        
        @self.app.get("/api/fundamental")
        async def getFundamental(search: str = Query(None), fields: str = Query(None), dates: str = Query(None), api_key: str = Depends(verifyAPIKey)):
            return await queryFundamental(self._db_engine, search, fields, dates)
    
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="critical")