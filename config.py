"""
Configuration for MISRA C Compliance Checker.
All settings are read from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RULES_FILE = DATA_DIR / "rules.json"
SAMPLE_C_DIR = DATA_DIR / "sample_c_files"

REPORT_PATH = OUTPUT_DIR / "compliance_report.xlsx"
LOG_FILE = OUTPUT_DIR / "execution.log"
LOG_JSON = OUTPUT_DIR / "execution_log.json"

# ── Ollama / LLM ─────────────────────────────────────────────────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
PRIMARY_MODEL: str = os.getenv("MODEL_NAME", "llama3")
LIGHT_MODEL: str = os.getenv("LIGHT_MODEL", "mistral")

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB: str = os.getenv("MONGO_DB", "misra_checker")
MONGO_RULES_COLLECTION: str = "rules"
MONGO_LOGS_COLLECTION: str = "logs"

# ── ChromaDB (optional vector RAG) ───────────────────────────────────────────
USE_CHROMA: bool = os.getenv("USE_CHROMA", "false").lower() == "true"
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / ".chroma"))
CHROMA_COLLECTION: str = "misra_rules"

# ── Parallelism ───────────────────────────────────────────────────────────────
MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))

# ── LLM call behaviour ────────────────────────────────────────────────────────
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))  # 0.0 for deterministic
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))  # Increased for amplification context
LLM_RETRY_ATTEMPTS: int = int(os.getenv("LLM_RETRY_ATTEMPTS", "3"))
LLM_RETRY_DELAY: float = float(os.getenv("LLM_RETRY_DELAY", "2.0"))

# ── Deterministic LLM settings ───────────────────────────────────────────────
LLM_TOP_K: int = int(os.getenv("LLM_TOP_K", "1"))  # Only consider top 1 token
LLM_TOP_P: float = float(os.getenv("LLM_TOP_P", "1.0"))  # Disable nucleus sampling
LLM_REPEAT_PENALTY: float = float(os.getenv("LLM_REPEAT_PENALTY", "1.0"))  # No variance
LLM_SEED: int | None = int(os.getenv("LLM_SEED", "42")) if os.getenv("LLM_SEED") else None

# ── LLM caching for reproducibility ──────────────────────────────────────────
USE_LLM_CACHE: bool = os.getenv("USE_LLM_CACHE", "true").lower() == "true"
LLM_CACHE_DIR: str = str(OUTPUT_DIR / "llm_cache")
