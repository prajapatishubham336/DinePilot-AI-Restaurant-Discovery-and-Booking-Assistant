import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Local development: read .env. In production the real environment variables are used.
load_dotenv(BASE_DIR / '.env', override=True)


def _get(name: str, default: str = '') -> str:
    return os.getenv(name, default).strip()


GROQ_API_KEY = _get('GROQ_API_KEY')
GROQ_MODEL = _get('GROQ_MODEL', 'openai/gpt-oss-20b')

# Nominatim policy requires an identifying User-Agent (put your real contact/email).
OSM_USER_AGENT = _get('OSM_USER_AGENT', 'DinePilotAI/1.0 (contact: you@example.com)')
NOMINATIM_URL = _get('NOMINATIM_URL', 'https://nominatim.openstreetmap.org/search')
DEFAULT_COUNTRY = _get('DEFAULT_COUNTRY', 'in')  # ISO code to prefer; '' = worldwide

_extra = _get('OVERPASS_URL')
OVERPASS_URLS = ([_extra] if _extra else []) + [
    'https://overpass-api.de/api/interpreter',
    'https://lz4.overpass-api.de/api/interpreter',
    'https://z.overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
]

DB_PATH = Path(_get('DB_PATH', str(BASE_DIR / 'data' / 'dinepilot.db')))
ADMIN_PASSWORD = _get('ADMIN_PASSWORD')  # protects the Bookings page when set
