# search-fallback-chain

A small resilience pattern (with working code) for automated searches that get blocked: **browser, then a human solves the CAPTCHA, then a real browser, then a paid API with a quota and a reserve.**

## Why

Search engines block repeated automated queries (HTTP 429/403, "unusual traffic", CAPTCHA). Naive scripts either die or try to defeat the CAPTCHA. This pattern does neither:

1. **App browser** (free). If blocked, go to 2.
2. **CAPTCHA: stop and ask a human.** The automation never fills, clicks, solves or works around a CAPTCHA. It leaves the page open, records what was blocked, and returns `NeedsHuman(url)`. After the person solves it, the same step is retried (`resume`). A second CAPTCHA in the same run means: go on to the next step.
3. **A real browser** (a different, less-blocked session, driven only in a new tab you open).
4. **Paid API** (SerpApi as the example): it has a monthly quota and a **reserve that is never spent**. The API key is read only from the `SERPAPI_KEY` environment variable and is never printed or logged.
5. If everything fails: `Failed(retry_after_minutes=20, tried=[...])`. Close the run with what you have.

Every `Result` carries the method that answered, so you can report the source of each measurement.

Extra rules that come with the pattern: never open the raw search-results URL directly if it is the one that blocks most (use a lighter surface such as a maps listing or an ads preview), batch independent calls, and stop on the first block instead of hammering.

## Install

```bash
pip install .        # Python 3.9+, standard library only
```

## Usage

```python
from search_fallback.chain import Chain, NeedsHuman
from search_fallback.serpapi import SerpApiProvider

chain = Chain([MyBrowserProvider(), MyRealBrowserProvider(), SerpApiProvider(reserve=5)])
r = chain.run("plumber near Exampleville")
if isinstance(r, NeedsHuman):
    print("Please solve the CAPTCHA at", r.url)   # a person does it
    r = chain.resume("plumber near Exampleville", r)
```

Implement `Provider.search(query)` for your browsers; raise `CaptchaRequired(url)` or `Blocked(reason)` when blocked.

```bash
python -m search_fallback.demo                       # offline demo with fake providers
export SERPAPI_KEY=...                               # never commit it
python -m search_fallback.serpapi balance            # credits left (costs nothing)
python -m search_fallback.serpapi search "coffee" "Austin, Texas, United States"
```

## Example output (demo)

```
1st run: NeedsHuman(provider='app-browser', url='https://example.test/sorry', resume_from=0)
-> a person solves the CAPTCHA at https://example.test/sorry then:
2nd run: Result(method='app-browser', data=["app-browser answer for 'coffee shops in Exampleville'"])
```

## Tests

```bash
pip install pytest && pytest
```

## Limitations

- Only the orchestration and the SerpApi provider are included; you write the browser providers.
- Respect each site's terms of service. This is a pattern for being a good citizen (stop, ask, pay), not a way around protections.
- SerpApi pricing and response fields can change; check their docs.

## License

MIT

## Resumo em português

Padrão de resiliência para buscas bloqueadas: navegador, depois um humano resolve o CAPTCHA (a automação nunca contorna), depois um navegador real e por fim uma API paga (SerpApi) com cota e reserva que nunca é gasta. A chave vem só da variável de ambiente `SERPAPI_KEY`. Cada resultado informa qual método respondeu. Só o orquestrador e o provedor SerpApi estão no código; os navegadores você implementa.
