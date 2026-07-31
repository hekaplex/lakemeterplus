"""Compatibility shim.

The observability module's settings fields were folded into the app-wide
`app.config.Settings` class (see satsyil_lakemeterplus/docs/merge-tasks.md
task #9), so there is now exactly one Settings instance and one env-var
parse for the whole merged app. This shim keeps `get_settings()` importable
from its original location so the ~14 observability core/service/route
files that do `from app.observability.core.config import get_settings`
did not need to be individually rewritten.
"""
from functools import lru_cache

from app.config import Settings, settings as _settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return _settings
