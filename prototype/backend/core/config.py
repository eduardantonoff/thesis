import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain.embeddings import init_embeddings
from langchain.chat_models import init_chat_model
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv(override=True)

THREAD = os.getenv('THREAD')
USER_ID = os.getenv('USER_ID')
GRAPH_PATH = os.getenv('GRAPH_PATH')
BASE_URL = os.getenv('BASE_URL')
OPENAI_CHAT_MODEL = os.getenv('OPENAI_CHAT_MODEL')
OPENAI_EMBED_MODEL = os.getenv('OPENAI_EMBED_MODEL')
OPENAI_API_PROXY = os.getenv('OPENAI_API_PROXY')

if not all([THREAD, USER_ID, GRAPH_PATH, BASE_URL, OPENAI_API_PROXY]):
    missing = [var for var, val in {
        'THREAD': THREAD, 
        'USER_ID': USER_ID, 
        'GRAPH_PATH': GRAPH_PATH,
        'BASE_URL': BASE_URL,
        'OPENAI_API_PROXY': OPENAI_API_PROXY
    }.items() if not val]
    logger.warning(f"Missing essential environment variables: {', '.join(missing)}")

try:
    embeddings = init_embeddings(
        api_key=OPENAI_API_PROXY, 
        base_url=BASE_URL, 
        model=OPENAI_EMBED_MODEL
    )
    
    llm = init_chat_model(
        api_key=OPENAI_API_PROXY, 
        base_url=BASE_URL, 
        model=OPENAI_CHAT_MODEL
    )
except Exception as e:
    logger.error(f"Failed to initialize AI models: {str(e)}")
    raise

store = InMemoryStore(index={"embed": embeddings, "dims": 1536, "fields": ["memory", "type"]})
checkpointer = MemorySaver()

CONFIG: Dict[str, Any] = {
    'configurable': {
        'thread_id': THREAD, 
        'recursion_limit': 3, 
        'user_id': USER_ID
    }
}

graph_data: Optional[Dict[str, Any]] = None
try:
    if os.path.exists(GRAPH_PATH):
        with open(GRAPH_PATH, "r") as f:
            graph_data = json.load(f)
        logger.info(f"Successfully loaded graph data from {GRAPH_PATH}")
    else:
        logger.error(f"Graph file not found at {GRAPH_PATH}")
except Exception as e:
    logger.error(f"Error loading graph data: {str(e)}")