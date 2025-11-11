import time
from typing import Any, Dict, Tuple


class TTLCache:
    """简单的内存TTL缓存，用于减少重复网络请求。

    cache[key] = (expire_ts, value)
    """

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        expire, value = item
        if time.time() > expire:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any):
        expire_ts = time.time() + self.ttl
        self._store[key] = (expire_ts, value)