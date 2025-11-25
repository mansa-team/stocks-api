import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

APIKey_Header = APIKeyHeader(name="X-API-Key", auto_error=False)
async def verifyAPIKey(APIKey: str = Depends(APIKey_Header)):
    require_key = Config.STOCKS_API['KEY.SYSTEM'] == 'TRUE'
    
    if not require_key:
        return None
    
    validKey = Config.STOCKS_API['KEY']

    if not validKey:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured"
        )
    
    if APIKey is None or APIKey != validKey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    return APIKey
class Service:
    instances = {}
    
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = int(port)
        self.app = FastAPI(
            title=service_name,
            version="1.0.0",
            description=f"{service_name}"
        )
        self.setupRoutes()
    
    def setupRoutes(self):  
        @self.app.get("/health")
        async def health():
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "service": self.service_name,
                    "port": self.port,
                    "timestamp": str(time.time())
                }
            )
        
        @self.app.get("/")
        async def root():
            return {"message": "Mansa (Stocks API)"}

        #
        #$ API Routes
        #
        @self.app.get("/api/keytest")
        async def getRAGkeytest(APIKey: str = Depends(verifyAPIKey)):
            return {"message": "API", "secured": True}
    
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