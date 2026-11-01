"""Central configuration: paths, limits and switches. Every loop in Waris is bounded from here."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

# --- paths ---
RULES_DIR = ROOT / "data" / "rules"
CASES_DIR = ROOT / "data" / "cases"
PORTAL_DB = ROOT / "data" / "portals" / "portals.db"
STATE_DIR = ROOT / "data" / "state"
CHECKPOINT_DB = STATE_DIR / "checkpoints.db"   # short-term memory (graph state), keyed by thread_id = case_id
CASE_FILE_DB = STATE_DIR / "case_files.db"     # long-term memory (family answers, past results)
CHROMA_DIR = ROOT / ".cache" / "chroma"
TRACE_DIR = ROOT / "traces"

# --- LLM ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
USE_LLM = os.getenv("WARIS_USE_LLM", "1") == "1"
LLM_TIMEOUT = float(os.getenv("WARIS_LLM_TIMEOUT", "60"))
LLM_TEMPERATURE = float(os.getenv("WARIS_LLM_TEMPERATURE", "0"))
LLM_SEED = int(os.getenv("WARIS_LLM_SEED", "0"))
LETTER_LLM = os.getenv("WARIS_LETTER_LLM", "1") == "1"          # let the LLM write the letter's opening paragraph (validated)
JUDGE_MODEL = os.getenv("WARIS_JUDGE_MODEL", "llama3.2")          # a different model from the one that writes: no self-marking

# --- ablations (experiments): comma-separated switches, e.g. WARIS_ABLATE=no_verifier,no_grading ---
ABLATE: set[str] = {x.strip() for x in os.getenv("WARIS_ABLATE", "").split(",") if x.strip()}

# --- portals ---
PORTAL_URL = os.getenv("PORTAL_URL", "http://127.0.0.1:8001")

# --- limits (safety rule 6: never unbounded) ---
MAX_ROUNDS = int(os.getenv("WARIS_MAX_ROUNDS", "6"))            # Verifier send-back rounds / case
MAX_REQUERY = int(os.getenv("WARIS_MAX_REQUERY", "2"))          # RAG re-queries / asset / need
MAX_TRACER_STEPS = int(os.getenv("WARIS_MAX_TRACER_STEPS", "8"))
MAX_LLM_CALLS = int(os.getenv("WARIS_MAX_LLM_CALLS", "40"))     # per case
TOOL_TIMEOUT = float(os.getenv("WARIS_TOOL_TIMEOUT", "10"))
TOOL_RETRIES = 2

SMALL_AMOUNT_INR = 500_000     # illustrative 'small claim' ceiling used to pick between rule variants

# --- identity-match policy (tuned on dev set only; see docs) ---
W_NAME, W_DOB, W_CITY = 0.5, 0.3, 0.2
ACCEPT_AT = 0.85     # strong  -> accept
ASK_AT = 0.60        # medium  -> ALWAYS ask the family; below -> reject
MIN_NAME = 0.80     # below this the name itself does not match
