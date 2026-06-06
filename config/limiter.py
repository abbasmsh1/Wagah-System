from slowapi import Limiter
from slowapi.util import get_remote_address

from config.security import get_security_settings

settings = get_security_settings()

# Shared limiter instance. Imported by main.py (to register the app state and
# exception handler) and by routers that decorate sensitive endpoints.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)
