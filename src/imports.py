import os
import math
import json
import time
import requests

from dotenv import load_dotenv

import pandas as pd
import numpy as np

import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy import types

import uvicorn
from fastapi import FastAPI, HTTPException, Query

load_dotenv()
"""
Load the .env files to determine if the specified module is initialized when the project is initialized, making maintance and redundancy easier for the developer.

For example:
    You can set the host ip address of some specific module to be ran by other developer, making the management and computational distribution easier across the project. With each developer running a part of the project and making developing each module easier than having a monolithic repository.
"""

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
        'API.ROUTE': os.getenv('STOCKSAPI_API.ROUTE'),
        'RAG.ROUTE': os.getenv('STOCKSAPI_RAG.ROUTE'),
    }