"""Run untrusted binary extraction in a disposable time-limited process."""
import json
import sys
import resource
from .parsing import extract, ParseError
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
if sys.platform.startswith("linux"):
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
try:
    print(json.dumps({"result": extract(sys.stdin.buffer.read(10 * 1024 * 1024 + 1))}))
except ParseError as exc:
    print(json.dumps({"error": str(exc)}))
except Exception:
    print(json.dumps({"error": "Document processing failed safely."}))
