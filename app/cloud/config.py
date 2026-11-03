import base64
import json
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_anon_key: str
    cors_origins: tuple[str, ...]

    @property
    def configured(self):
        return bool(self.supabase_url and self.supabase_anon_key)

def settings():
    url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    key = os.getenv('SUPABASE_ANON_KEY', '').strip()
    valid_key = bool(key) and not key.startswith('sb_secret_')
    if key.count('.') == 2:
        try:
            payload = key.split('.')[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
            valid_key = valid_key and claims.get('role') == 'anon'
        except (ValueError, TypeError, AttributeError):
            valid_key = False
    try:
        parts = urlsplit(url)
        hosted = parts.scheme == 'https' and bool(re.fullmatch(r'[a-z0-9-]+\.supabase\.(co|in)', parts.hostname or '')) and parts.port in (None, 443)
        local = os.getenv('ALLOW_LOCAL_SUPABASE', '').lower() == 'true' and parts.scheme in ('http', 'https') and parts.hostname in ('localhost', '127.0.0.1', '::1')
        valid_url = (hosted or local) and not parts.username and not parts.password and parts.path in ('', '/') and not parts.query and not parts.fragment
    except ValueError:
        valid_url = False
    origins = tuple(x.strip() for x in (os.getenv('CORS_ORIGINS') or os.getenv('ALLOWED_ORIGINS', '')).split(',') if x.strip() and x.strip() != '*')
    # Fail closed and redact the entire pair, including accidentally supplied privileged keys.
    return Settings(url if valid_url and valid_key else '', key if valid_url and valid_key else '', origins)
