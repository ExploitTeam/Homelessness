import os
from dotenv import load_dotenv
from database.db_manager import *
from parser.modules import *
load_dotenv()
TOKEN = os.getenv("MAX_TOKEN", "")