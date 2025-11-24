import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imports import *

from main import api
from main import rag

class Service:
    instances = {}
    
    def __init__(self, service_name: str, port: int, enable_api: bool = False, enable_rag: bool = False):
        self.service_name = service_name
        self.port = int(port)
        self.enable_api = enable_api
        self.enable_rag = enable_rag
        self.app = FastAPI(
            title=service_name,
            version="1.0.0",
            description=f"{service_name}"
        )
        self._setupRoutes()
    
    def _setupRoutes(self):  
        @self.app.get("/health")
        async def health():
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "service": self.service_name,
                    "port": self.port,
                    "api_routes": self.enable_api,
                    "rag_routes": self.enable_rag,
                    "timestamp": str(time.time())
                }
            )
        
        @self.app.get("/")
        async def root():
            return "Mansa (Stocks API)"
    
        if self.enable_api:
            api.setupRoutes(self.app)
            pass

        if self.enable_rag:
            rag.setupRoutes(self.app)
            pass

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="critical")
    
    @classmethod
    def initialize(cls, service_name: str, port: int, enable_api: bool = False, enable_rag: bool = False):
        key = f"{service_name}_{port}"
        
        if key not in cls.instances:
            instance = cls(service_name, port, enable_api, enable_rag)

            thread = threading.Thread(target=instance.run, daemon=True)
            thread.start()
            
            cls.instances[key] = instance
        
        return cls.instances[key]