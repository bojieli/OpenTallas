"""Command line of the hardwired-decode-chip runtime.

    python3 -m runtime.hdc targets
    python3 -m runtime.hdc generate --target qwen3-rom --chat "Reply with OK."
    python3 -m runtime.hdc generate --target v41-rom --ids 0,3563,3745,418,170,16,3564,3582 --max-tokens 3
    python3 -m runtime.hdc serve --target qwen3-rom --target v41-rom --port 8000

``generate`` streams the tokens as the chip writes them, then prints the
chip's counters.  ``serve`` starts the OpenAI-compatible endpoint
(runtime/hdc/server.py) until interrupted.
"""

from __future__ import annotations

import argparse
import json
import sys
import time


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m runtime.hdc", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("targets", help="list the chip targets")
    g = sub.add_parser("generate", help="run one request on a simulated chip")
    g.add_argument("--target", default="qwen3-rom")
    src = g.add_mutually_exclusive_group(required=True)
    src.add_argument("--chat", help="one user message, rendered with the model's chat template")
    src.add_argument("--prompt", help="raw text prompt")
    src.add_argument("--ids", help="comma-separated token ids (reduced vocabulary)")
    g.add_argument("--max-tokens", type=int, default=16)
    g.add_argument("--ignore-eos", action="store_true")
    g.add_argument("--clock-mhz", type=float, help="override the modelled clock")
    g.add_argument("--json", action="store_true", help="print the request record as JSON")
    s = sub.add_parser("serve", help="OpenAI-compatible endpoint")
    s.add_argument("--target", action="append", help="repeatable; default qwen3-rom")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--max-tokens", type=int, default=16, help="default max_tokens")
    a = ap.parse_args(argv)

    from runtime.hdc.targets import TARGETS
    if a.cmd == "targets":
        for t in TARGETS.values():
            clk = t.modelled_clock()
            print(f"{t.name:12s} {t.architecture:42s} model={t.model_id:32s} "
                  f"clock={clk['hz'] / 1e6:.1f} MHz ({clk['limiter']})  {t.status}")
        return 0

    from runtime.hdc.runtime import HdcRuntime
    from runtime.hdc.tokenizer import ModelTokenizer
    if a.cmd == "generate":
        rt = HdcRuntime(a.target, clock_hz=a.clock_mhz * 1e6 if a.clock_mhz else None)
        tok = ModelTokenizer(rt.target)
        ids = ([int(x) for x in a.ids.split(",")] if a.ids else
               tok.encode_chat([{"role": "user", "content": a.chat}]) if a.chat else tok.encode(a.prompt))
        print(f"[{rt.target.name}] prompt ids {ids}", file=sys.stderr)
        t0 = time.time()
        req = rt.submit(ids, a.max_tokens, stop_eos=not a.ignore_eos)
        out = []
        for t in req.tokens():
            out.append(t)
            print(f"[{rt.target.name}] token {t} {tok.decode([t])!r}", file=sys.stderr, flush=True)
        req.result()
        rec = rt.request_stats(req)
        rec["text"] = tok.decode(out)
        rec["wall_seconds"] = round(time.time() - t0, 2)
        rec["counters"] = rt.counters()
        rt.close()
        if a.json:
            print(json.dumps(rec, indent=2))
        else:
            print(rec["text"])
            print(f"[{rec['target']}] {rec['generated_tokens']} tokens {rec['token_ids']} status={rec['status']} "
                  f"chip_cycles={rec['chip_cycles']} at {rec['clock_hz'] / 1e6:.1f} MHz = "
                  f"{rec['modelled_seconds'] * 1e3:.3f} ms ({rec['modelled_tokens_per_second']:.0f} tokens/s "
                  f"modelled; simulated in {rec['wall_seconds']} s)", file=sys.stderr)
        return 0 if rec["status"] in ("eos", "length") else 1

    from runtime.hdc.server import serve
    rts = [HdcRuntime(t) for t in (a.target or ["qwen3-rom"])]
    httpd = serve(rts, a.host, a.port, a.max_tokens)
    print(f"serving {[r.target.name for r in rts]} on http://{a.host}:{a.port}/v1", file=sys.stderr, flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    httpd.shutdown()
    for r in rts:
        r.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
