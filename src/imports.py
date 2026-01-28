import os
import sys
import json
import time
import threading
import logging

from datetime import datetime
from dotenv import load_dotenv

import requests
import pandas as pd
import numpy as np

from sqlalchemy import create_engine, text, QueuePool
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

load_dotenv()

LOCALHOST_ADDRESSES = ['localhost', '127.0.0.1', '0.0.0.0', 'None', None]
class Config:
    MYSQL = {
        'USER': os.getenv('MYSQL_USER'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD'),
        'HOST': os.getenv('MYSQL_HOST'),
        'DATABASE': os.getenv('MYSQL_DATABASE'),
    }
    
    STOCKS_API = {
        'ENABLED': os.getenv('STOCKSAPI_ENABLED'),
        'HOST': os.getenv('STOCKSAPI_HOST'),
        'PORT': os.getenv('STOCKSAPI_PORT'),
        'KEY.SYSTEM': os.getenv('STOCKSAPI_KEY.SYSTEM'),
        'KEY': os.getenv('STOCKSAPI_PRIVATE.KEY'),
    }

dbEngine = create_engine(
    f"mysql+pymysql://{Config.MYSQL['USER']}:{Config.MYSQL['PASSWORD']}@{Config.MYSQL['HOST']}/{Config.MYSQL['DATABASE']}",
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=False,
    connect_args={'charset': 'utf8mb4'}
)