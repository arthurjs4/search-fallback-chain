"""A resilient search pattern: try cheap options first, hand CAPTCHAs to a human, fall back to a paid API.

Order of the chain (each step is a `Provider`):
  1. app browser           free, may get blocked
  2. human solves CAPTCHA  the chain STOPS and asks a person; automation never solves, clicks or bypasses a CAPTCHA
  3. a real browser        a different, less-blocked browser session
  4. paid API              has a monthly quota and a reserve that is never spent

The chain returns which method answered, so every result can be reported with its source.
"""
from dataclasses import dataclass, field
from typing import Callable, List, Optional


class Blocked(Exception):
    """The provider was rate-limited or blocked (HTTP 429/403, 'unusual traffic') and there is no CAPTCHA to solve."""


class CaptchaRequired(Exception):
    """A CAPTCHA page is showing. Only a human may solve it."""

    def __init__(self, url=""):
        super().__init__(f"CAPTCHA at {url}" if url else "CAPTCHA")
        self.url = url


class QuotaExhausted(Exception):
    """The paid API has only its reserve left."""


class Provider:
    name = "provider"
    paid = False

    def search(self, query, **kw):  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class Result:
    method: str
    data: object


@dataclass
class NeedsHuman:
    """Returned when the chain stopped on a CAPTCHA. Ask the person to solve it, then call `resume`."""
    provider: str
    url: str
    resume_from: int


@dataclass
class Failed:
    reason: str
    retry_after_minutes: int = 20
    tried: List[str] = field(default_factory=list)


class Chain:
    def __init__(self, providers: List[Provider], captcha_retries_per_run: int = 1):
        self.providers = providers
        self.captcha_retries_per_run = captcha_retries_per_run
        self.captchas_seen = 0

    def run(self, query, start: int = 0, **kw):
        """Try providers from index `start`. Returns Result, NeedsHuman or Failed."""
        tried = []
        for i in range(start, len(self.providers)):
            p = self.providers[i]
            try:
                return Result(p.name, p.search(query, **kw))
            except CaptchaRequired as e:
                self.captchas_seen += 1
                if self.captchas_seen <= self.captcha_retries_per_run:
                    # leave the CAPTCHA tab open in front and ask a person; do NOT touch it
                    return NeedsHuman(p.name, e.url, resume_from=i)
                tried.append(f"{p.name}: CAPTCHA again")  # second CAPTCHA in a run: move on to the next provider
            except Blocked as e:
                tried.append(f"{p.name}: blocked ({e})")
            except QuotaExhausted as e:
                tried.append(f"{p.name}: {e}")
        return Failed("all providers blocked or out of quota", tried=tried)

    def resume(self, query, needs_human: NeedsHuman, **kw):
        """After a person solved the CAPTCHA: retry from the same provider."""
        return self.run(query, start=needs_human.resume_from, **kw)


class QuotaGuard:
    """Monthly credit counter that refuses to spend the last `reserve` credits."""

    def __init__(self, left_fn: Callable[[], Optional[int]], reserve: int = 5):
        self.left_fn = left_fn
        self.reserve = reserve

    def check(self):
        left = self.left_fn()
        if left is not None and left <= self.reserve:
            raise QuotaExhausted(f"only {left} credits left; {self.reserve} kept in reserve, nothing was searched")
        return left
