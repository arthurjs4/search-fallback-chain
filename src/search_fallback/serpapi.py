"""SerpApi (https://serpapi.com) as the paid last resort. The API key comes ONLY from the SERPAPI_KEY environment
variable and is never printed or logged. One search = 1 credit (cached repeats are free)."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from .chain import Blocked, Provider, QuotaExhausted, QuotaGuard

BASE = "https://serpapi.com"
USER_AGENT = "search-fallback-chain/0.1"


def api_key():
    key = os.environ.get("SERPAPI_KEY")
    if not key:
        raise QuotaExhausted("SERPAPI_KEY is not set (create a free account and export it as an environment variable)")
    return key


def _get(path, params):
    key = api_key()
    url = f"{BASE}/{path}?" + urllib.parse.urlencode({**params, "api_key": key})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300].replace(key, "***")
        raise Blocked(f"SerpApi HTTP {e.code}: {body}") from None
    except Exception as e:  # noqa: BLE001
        raise Blocked(str(e).replace(key, "***")) from None


def credits_left():
    d = _get("account.json", {})
    return d.get("plan_searches_left", d.get("total_searches_left"))


class SerpApiProvider(Provider):
    name = "serpapi"
    paid = True

    def __init__(self, reserve=5, engine="google"):
        self.guard = QuotaGuard(credits_left, reserve)
        self.engine = engine

    def search(self, query, location=None, **kw):
        left = self.guard.check()
        params = {"engine": self.engine, "q": query}
        if location:
            params["location"] = location
        data = _get("search.json", params)
        return {"credits_left": (left - 1) if isinstance(left, int) else None,
                "organic": [{"title": r.get("title"), "link": r.get("link")} for r in data.get("organic_results", [])]}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in ("balance", "search"):
        print("usage: python -m search_fallback.serpapi balance | search \"query\" [location]")
        return 2
    try:
        if argv[0] == "balance":
            print(f"credits left this month: {credits_left()}")
        else:
            out = SerpApiProvider().search(argv[1], argv[2] if len(argv) > 2 else None)
            print(json.dumps(out, indent=1))
    except (QuotaExhausted, Blocked) as e:
        print(f"stopped: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
