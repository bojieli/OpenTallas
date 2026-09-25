#!/usr/bin/env python3
"""Host interface and runtime campaign: requests through the simulated chips.

For every target of runtime/hdc/targets.py -- the Qwen3-8B ROM reticle, the
HBM comparator, the ROM array and the DeepSeek-V4.1 ROM die -- this builds the
Verilated chip (rtl/host/ot_host_if.sv in front of the target's decode
engine, rtl/test/tb_host_*.sv, driven by rtl/test/host_bridge_harness.cpp),
generates the model's program/ROM images, and sends requests through the
runtime (runtime/hdc): descriptors into the submission ring, doorbells, MSI
interrupts, token completions read from the completion ring.  Each request is
the target's reference prompt -- the chat prompt "Reply with OK." rendered
with the model's template, tokenized with the model's Hugging Face tokenizer
and folded into the reduced vocabulary -- and its generated ids must equal the
decode campaign's (results/rtl/hdc_decode_campaign.json,
results/rtl/hdc_v41_decode_campaign.json):

* qwen3-rom: three users at once (the chip interleaves their steps over one
  core, a KV slice each), then an end-to-end request through the
  OpenAI-compatible endpoint (/v1/chat/completions, streamed as server-sent
  events), then the fail-closed descriptor checks (no greedy flag, a slot
  out of range, a request longer than a user context) each answered by an
  error completion;
* qwen3-hbm: two users one after the other (one user's state at a time; the
  engine is cleared between them);
* qwen3-array: a batch of four users through the package controllers;
* v41-rom: one user, three generated tokens (the chip stops at the cap).

Writes results/rtl/host_if_campaign.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.hdc import build as B  # noqa: E402
from runtime.hdc.driver import FLAG_GREEDY  # noqa: E402
from runtime.hdc.targets import TARGETS  # noqa: E402

OUT = ROOT / "results/rtl/host_if_campaign.json"
RTL = ROOT / "rtl/host/ot_host_if.sv"
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH")
MESSAGES = [{"role": "user", "content": "Reply with OK."}]
PY = ["runtime/hdc/__init__.py", "runtime/hdc/targets.py", "runtime/hdc/build.py", "runtime/hdc/device.py",
      "runtime/hdc/driver.py", "runtime/hdc/runtime.py", "runtime/hdc/tokenizer.py", "runtime/hdc/server.py",
      "runtime/hdc/__main__.py", "tools/rtl_host_if_campaign.py"]


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def lint() -> dict:
    out = {}
    for name, params in (("step", ()), ("step_one_context", ("-GENG_CTX=1",)), ("batch", ("-GMODE=1",))):
        r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, *params, "--top-module", "ot_host_if", str(RTL)],
                           capture_output=True, text=True)
        out[name] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:20]}
    return out


def expected(target) -> list[int]:
    if target.images == "v41":
        rec = json.loads((ROOT / "results/rtl/hdc_v41_decode_campaign.json").read_text())
    else:
        rec = json.loads((ROOT / "results/rtl/hdc_decode_campaign.json").read_text())
    return rec["end_to_end"]["generated_tokens"]


def request_record(rt, req, want) -> dict:
    s = rt.request_stats(req)
    s["expected_token_ids"] = want
    s["pass"] = s["token_ids"] == want
    return s


def run_target(name: str, n_users: int, port: int = 0) -> dict:
    from runtime.hdc.runtime import HdcRuntime
    from runtime.hdc.tokenizer import ModelTokenizer
    t = TARGETS[name]
    t0 = time.time()
    rt = HdcRuntime(t)
    tok = ModelTokenizer(t)
    prompt = tok.encode_chat(MESSAGES)
    want = expected(t)
    max_new = len(want) if name == "v41-rom" else 8     # V4.1: the cap; Qwen3: stops at EOS 93
    rec = {"target": name, "architecture": t.architecture, "model": t.model_id, "engine": t.status,
           "tokenizer": str(t.tokenizer_path()).replace(str(Path.home()), "~"),
           "prompt_text": tok.render_chat(MESSAGES), "prompt_token_ids": prompt,
           "clock": t.modelled_clock(), "users": n_users}
    reqs = [rt.submit(prompt, max_new) for _ in range(n_users)]
    rec["requests"] = [request_record(rt, r.result(), want) for r in reqs]
    rec["decoded_text"] = tok.decode(reqs[0].tokens_out)
    if name == "qwen3-rom":
        rec["endpoint"] = endpoint_check(rt, want)
        rec["fail_closed"] = fail_closed(rt, prompt)
    rec["counters"] = rt.counters()
    rt.close()
    rec["wall_seconds"] = round(time.time() - t0, 1)
    rec["pass"] = (all(r["pass"] for r in rec["requests"])
                   and rec.get("endpoint", {}).get("pass", True)
                   and rec.get("fail_closed", {}).get("pass", True)
                   and rec["counters"]["status"] & 0x17 == 0)
    return rec


def endpoint_check(rt, want) -> dict:
    """One streamed and one plain /v1/chat/completions request through HTTP."""
    from runtime.hdc.server import serve
    httpd = serve([rt], port=0)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/v1/chat/completions"
    body = {"model": f"{rt.target.model_id}@{rt.target.name}", "messages": MESSAGES, "max_tokens": 8,
            "temperature": 0, "stream": True}
    raw = urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(),
                                                        {"Content-Type": "application/json"}), timeout=3600).read()
    events = [ln[6:] for ln in raw.decode().splitlines() if ln.startswith("data: ")]
    chunks = [json.loads(e) for e in events if e != "[DONE]"]
    ids = [c["opentallas"]["token_id"] for c in chunks if "token_id" in c.get("opentallas", {})]
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    last = chunks[-1]
    body["stream"] = False
    plain = json.loads(urllib.request.urlopen(urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=3600).read())
    refused = None
    try:
        urllib.request.urlopen(urllib.request.Request(url, json.dumps(dict(body, temperature=0.7)).encode(),
                                                      {"Content-Type": "application/json"}), timeout=60)
    except urllib.error.HTTPError as e:
        refused = e.code
    client = openai_client_check(f"http://127.0.0.1:{httpd.server_address[1]}/v1", body["model"], want)
    httpd.shutdown()
    return {"route": "/v1/chat/completions", "openai_client": client, "stream_events": len(events), "streamed_token_ids": ids,
            "streamed_text": text, "finish_reason": last["choices"][0]["finish_reason"],
            "usage": last.get("usage"), "stream_done_marker": events[-1] == "[DONE]",
            "plain_token_ids": plain["opentallas"]["token_ids"], "plain_content": plain["choices"][0]["message"]["content"],
            "sampling_request_http_status": refused, "expected_token_ids": want,
            "pass": ids == want and plain["opentallas"]["token_ids"] == want and events[-1] == "[DONE]"
                    and last["choices"][0]["finish_reason"] == "stop" and refused == 400
                    and client.get("pass", True)}


def openai_client_check(base_url: str, model: str, want: list[int]) -> dict:
    """The same request from the openai Python client, streamed."""
    try:
        import openai
    except ImportError:
        return {"skipped": "openai package not installed"}
    c = openai.OpenAI(base_url=base_url, api_key="unused")
    ids, text, finish = [], "", None
    for ev in c.chat.completions.create(model=model, messages=MESSAGES, max_tokens=8, temperature=0, stream=True):
        extra = getattr(ev, "model_extra", None) or {}
        if "token_id" in extra.get("opentallas", {}):
            ids.append(extra["opentallas"]["token_id"])
        if ev.choices:
            text += ev.choices[0].delta.content or ""
            finish = ev.choices[0].finish_reason or finish
    return {"openai_version": openai.__version__, "token_ids": ids, "text": text, "finish_reason": finish,
            "pass": ids == want and finish == "stop"}


def fail_closed(rt, prompt) -> dict:
    """Bad descriptors straight into the ring: each must come back as an error completion."""
    out = {}
    done = __import__("threading").Event()

    def probe():
        drv, dev = rt.drv, rt.dev
        cases = [("no_greedy_flag", dict(slot=5, prompt=prompt, max_new=4, flags=0), "unsupported_sampling"),
                 ("slot_out_of_range", dict(slot=200, prompt=prompt, max_new=4), "slot_unavailable"),
                 ("over_context", dict(slot=6, prompt=prompt, max_new=rt.target.ctx_max), "bad_length")]
        for i, (case, kw, status) in enumerate(cases):
            flags = kw.pop("flags", FLAG_GREEDY)
            drv.submit(tag=0xE000 + i, flags=flags, **kw)
            got = []
            for _ in range(200):
                dev.wait_irq(2000)
                got += drv.poll()
                if got:
                    break
            out[case] = {"kind": got[0].kind if got else None, "status": got[0].status if got else None,
                         "expected_status": status,
                         "pass": bool(got) and got[0].kind == "error" and got[0].status == status}
        done.set()
    rt._pending.put(probe)
    done.wait(600)
    out["pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--targets", default="qwen3-rom,qwen3-hbm,qwen3-array,v41-rom")
    a = ap.parse_args()
    names = a.targets.split(",")
    users = {"qwen3-rom": 3, "qwen3-hbm": 2, "qwen3-array": 4, "v41-rom": 1}
    # build everything first (in parallel), then run the targets in parallel
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda f: f(), [lambda n=n: B.build_chip(TARGETS[n]) for n in names]
                    + [lambda n=n: B.build_images(TARGETS[n]) for n in names]))
    with ThreadPoolExecutor(len(names)) as ex:
        recs = list(ex.map(lambda n: run_target(n, users[n]), names))
    srcs = sorted({s for n in names for s in TARGETS[n].sources} | set(B.INCLUDES) | {B.HARNESS})
    result = {
        "schema": "opentallas.host-if-campaign.v1",
        "status": "pass" if all(r["pass"] for r in recs) else "fail",
        "claim_boundary": "functional simulation of the host interface RTL in front of each decode engine "
                          "(Verilator, cycle-accurate; memories behavioural; host memory, DMA latency and the "
                          "interrupt controller modelled by the host bridge).  Modelled seconds and tokens/s "
                          "are chip cycles at the slowest routed block of each engine, not a routed chip.",
        "lint": lint(),
        "targets": {r["target"]: r for r in recs},
        "input_sha256": {s: sha(s) for s in srcs + PY},
    }
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for r in recs:
        print(r["target"], "pass" if r["pass"] else "FAIL", [q["token_ids"] for q in r["requests"]],
              f"{r['wall_seconds']} s")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
