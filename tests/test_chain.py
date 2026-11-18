import pytest

from search_fallback.chain import (Blocked, CaptchaRequired, Chain, Failed, NeedsHuman, Provider, QuotaExhausted,
                                   QuotaGuard, Result)


class P(Provider):
    def __init__(self, name, *script):
        self.name, self.script, self.calls = name, list(script), 0

    def search(self, query, **kw):
        self.calls += 1
        item = self.script.pop(0) if self.script else "ok"
        if isinstance(item, Exception):
            raise item
        return item


def test_first_provider_answers():
    r = Chain([P("a"), P("b")]).run("q")
    assert isinstance(r, Result) and r.method == "a"


def test_blocked_falls_to_next():
    r = Chain([P("a", Blocked("429")), P("b")]).run("q")
    assert r.method == "b"


def test_captcha_stops_for_human_and_resumes_same_provider():
    a = P("a", CaptchaRequired("u"), "solved")
    chain = Chain([a, P("b")])
    r = chain.run("q")
    assert isinstance(r, NeedsHuman) and r.url == "u" and r.resume_from == 0
    assert chain.run  # no automatic bypass: provider b was not tried
    r2 = chain.resume("q", r)
    assert r2.method == "a" and r2.data == "solved"


def test_second_captcha_moves_on():
    a = P("a", CaptchaRequired("u"), CaptchaRequired("u"))
    chain = Chain([a, P("b")])
    r = chain.run("q")
    r2 = chain.resume("q", r)
    assert r2.method == "b"


def test_all_failed_reports_tried():
    r = Chain([P("a", Blocked("x")), P("b", QuotaExhausted("none"))]).run("q")
    assert isinstance(r, Failed) and len(r.tried) == 2


def test_quota_guard_keeps_reserve():
    g = QuotaGuard(lambda: 5, reserve=5)
    with pytest.raises(QuotaExhausted):
        g.check()
    assert QuotaGuard(lambda: 6, reserve=5).check() == 6
