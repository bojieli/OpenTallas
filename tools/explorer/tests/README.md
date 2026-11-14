# Explorer UI and API tests

Playwright (Python) + pytest against a running Explorer server (default `http://127.0.0.1:8770`).  No pytest-playwright
needed: `conftest.py` has its own session browser (headless Chromium, software WebGL) and a per-test `page` fixture.

## Run

    W0=/srv/opentallas-scratch2/claude/explorer-2-work
    export PLAYWRIGHT_BROWSERS_PATH=$W0/rt/pw LD_LIBRARY_PATH=$W0/rt/libroot/usr/lib/x86_64-linux-gnu
    cd tools/explorer && nice -n 10 $W0/rt/venv/bin/python -I -m pytest tests -q

Quick subsets: `tests/test_api.py tests/test_static.py` (no browser, seconds), `-k shell`, `-m "not slow"`
(skips the layout / element / sweep / screenshot tests, which need WebGL canvases: 5-20 s each).  Use `-x` to stop at the first failure,
`--durations=15` for the slowest tests.  The full run takes about 30-35 minutes on software GL on the loaded epyc8 (load ~120); run it with nohup and a log file.

## Environment

| variable | default | meaning |
|---|---|---|
| `EXPLORER_URL` | `http://127.0.0.1:8770` | server under test |
| `EXPLORER_SHOTS` | `tests/_shots` (git-ignored) | screenshots (`<view>-<theme>.png`) and `dead-controls-<scenario>.json` |
| `EXPLORER_SRC` | the parent of `tests/` | `tools/explorer` directory for the static checks |

## Files

* `helpers.py` URL / HTTP / wait helpers (`goto`, `wait_settled`, `wait_engine`, `eng`, `store`, `shot`), well-known nodes (`SIGNED_TYPE`, `ROUTED_TYPE`, ...), `pick_node` / `pick_instance` (read the closure and compose APIs at run time).
* `conftest.py` browser + `page` fixture.  Every test fails when the page logged a console error, a page error, a failed request or an HTTP >= 400 response.
  Opt out with `@pytest.mark.allow_errors` (everything) or `@pytest.mark.allow_errors('HTTP 404', '/api/v1/node/')` (only messages containing one of the strings).
* `test_api.py`, `test_static.py` no browser: API contract, ETag/304/gzip, path traversal; colour tokens, labelled icon buttons, module imports.
* `test_shell.py` rail/keys, die switcher, breadcrumb, history, deep links, panels (collapse/resize/persist), focus mode, theme, search, help, freshness, status bar, old URL forms.
* `test_overview.py`, `test_plan.py`, `test_layout.py`, `test_element.py` per view, on s81, hbm and qwen_kvsys.
* `test_buttons.py` the no-dead-control sweep (see its docstring); `test_screens.py` the PNGs.
* `test_dataflow.py`, `test_token.py`, `test_closure.py` mount-clean tests with a TODO list of the assertions to add (REQUIREMENTS.md sections G, H, I).
  When the placeholders are replaced, add the real assertions next to the existing ones; the sweep and the screenshots already include these views.

## Notes

* Never assert timing tighter than the software GL allows; poll app state (`otx.eng.mode`, `otx.eng.pending.size`, `otx.store.get()`).
* Each test opens its own browser context (fresh localStorage); the browser itself is shared.
