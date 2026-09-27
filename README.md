# Test Framework

Playwright + pytest suites covering:

- **`test_loan_calculator.py`** — UI/end-to-end tests for the Loan Planner web app (`loan-calculator.html`), driven through a real browser.
- **`test_posts_api.py`** — API tests against JSONPlaceholder's `POST /posts`, covering boundary and invalid-input handling.

Every run produces a report, screenshots (UI suite only), and logs — no extra flags needed once set up.

## 1. Setup

```bash
pip install -r requirements.txt
playwright install
```

`playwright install` downloads the browser binaries (Chromium, Firefox, WebKit) that the UI suite needs. The API suite doesn't need a browser, but it's harmless to have them installed.

## 2. Running the tests

Run everything:

```bash
pytest
```

Run just one file:

```bash
pytest test_loan_calculator.py -v
pytest test_posts_api.py -v
```

Watch the UI suite in a real browser window instead of headless:

```bash
pytest test_loan_calculator.py --headed
```

## 3. Where the deliverables land

| Deliverable | Location | Notes |
|---|---|---|
| **HTML report** | `reports/report.html` | One self-contained file — open it directly in a browser. Every test, its status, and duration are listed; failures include the full traceback inline. |
| **Screenshots** | `test-results/<test-name>/test-failed-1.png` | UI suite only, captured automatically on failure (`--screenshot=only-on-failure` in `pytest.ini`). |
| **Video** | `test-results/<test-name>/video.webm` | UI suite only, kept automatically on failure (`--video=retain-on-failure`). |
| **Trace** | `test-results/<test-name>/trace.zip` | UI suite only, kept on failure. Open with `playwright show-trace test-results/<test-name>/trace.zip` to step through a failed run screenshot-by-screenshot with DOM snapshots and network calls. |
| **Logs** | `logs/test_run.log` | Every test's pass/fail/xfail outcome and duration, plus full tracebacks for failures. The API suite additionally logs each request payload and response for every test — since there's no browser there to screenshot, the log is that suite's evidence trail. |

`reports/`, `logs/`, and `test-results/` are created automatically on the first run if they don't exist — nothing to set up manually.

## 4. Project files

```
.
├── conftest.py                    # logging setup, shared across all test files
├── pytest.ini                     # report/screenshot/video/tracing configuration
├── requirements.txt
├── loan-calculator.html           # the app under test
├── test_loan_calculator.py        # UI suite
├── test_posts_api.py              # API suite
├── reports/                       # generated: HTML report
├── logs/                          # generated: test_run.log
└── test-results/                  # generated: screenshots, video, traces
```

## 5. Known findings

`test_posts_api.py::test_malformed_json_body` is marked `xfail(strict=True)`. JSONPlaceholder doesn't reject malformed JSON cleanly — it throws an unhandled `body-parser` exception that surfaces as a raw `500` with a stack trace in the response body, instead of a `4xx`. This is documented as a discovered defect rather than silently passed or silently left broken; see the `reason=` string on that test for detail.

## 6. Troubleshooting

- **`Chart is not defined` / similar in the browser console**: not applicable — `loan-calculator.html` has no external JS dependencies, so nothing to fetch over the network.
- **`--headed`/`--browser` flag not recognized**: `pytest-playwright` isn't installed, or `playwright install` wasn't run. Redo step 1.
- **API suite fails with connection/DNS errors**: your network (or a sandboxed CI runner) may be blocking `jsonplaceholder.typicode.com`. Run from an environment with normal internet access.
- **`pytest.ini` errors about `[]` parametrization**: don't add multi-word values (e.g. a log format string with spaces) directly into `addopts` — `pytest.ini` splits on whitespace with no quoting support. Configure anything like that in `conftest.py` instead, as already done here for log formatting.

