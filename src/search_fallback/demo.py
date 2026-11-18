"""Offline demo with fake providers: shows the CAPTCHA hand-off and the paid fallback."""
from .chain import Blocked, CaptchaRequired, Chain, NeedsHuman, Provider


class Fake(Provider):
    def __init__(self, name, behaviour):
        self.name, self.behaviour = name, list(behaviour)

    def search(self, query, **kw):
        b = self.behaviour.pop(0) if self.behaviour else "ok"
        if b == "captcha":
            raise CaptchaRequired("https://example.test/sorry")
        if b == "blocked":
            raise Blocked("HTTP 429")
        return [f"{self.name} answer for {query!r}"]


def main():
    chain = Chain([Fake("app-browser", ["captcha", "ok"]), Fake("real-browser", ["blocked"]), Fake("paid-api", [])])
    r = chain.run("coffee shops in Exampleville")
    print("1st run:", r)
    if isinstance(r, NeedsHuman):
        print("-> a person solves the CAPTCHA at", r.url, "then:")
        print("2nd run:", chain.resume("coffee shops in Exampleville", r))


if __name__ == "__main__":
    main()
