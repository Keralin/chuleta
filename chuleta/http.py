"""Plain HTTP helpers on urllib, with a small on-disk cache for scraped pages."""

import json
import os
import time
import urllib.request

from . import config


def get_text(url, timeout=20, retries=3, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT, **(headers or {})})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # 5xx, timeouts: back off and retry
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def get_json(url, **kw):
    return json.loads(get_text(url, **kw))


def cached(key, ttl, producer):
    """producer() result cached as JSON under HOME/cache for ttl seconds."""
    os.makedirs(config.CACHE, exist_ok=True)
    path = os.path.join(config.CACHE, "".join(c if c.isalnum() or c in "-_" else "_" for c in key) + ".json")
    try:
        if time.time() - os.path.getmtime(path) < ttl:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except OSError:
        pass
    value = producer()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False)
    return value


def forget(key):
    path = os.path.join(config.CACHE, "".join(c if c.isalnum() or c in "-_" else "_" for c in key) + ".json")
    if os.path.exists(path):
        os.remove(path)
