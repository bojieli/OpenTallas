"""Host interface, runtime and OpenAI-compatible endpoint of the decode chips.

* the campaign record (tools/rtl_host_if_campaign.py) passes for all four
  targets, its generated ids are the decode campaigns' own, and it is current
  against its sources;
* the ASAP7 record of ot_host_if routes the same source;
* live: one /v1/chat/completions request, streamed, through the endpoint into
  the Verilated Qwen3 reticle produces the oracle's tokens 1073, 382, 93
  (skipped without Verilator or the cached Qwen3 tokenizer; set
  OT_SKIP_LIVE_RTL=1 to skip it).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/host_if_campaign.json"
PHYS = ROOT / "results/physical_abi3/asap7/host/ot_host_if/physical.json"
ORACLE = [1073, 382, 93]


def _record():
    return json.loads(RECORD.read_text())


def test_campaign_passes_on_all_three_architectures():
    rec = _record()
    assert rec["status"] == "pass"
    assert set(rec["targets"]) == {"qwen3-rom", "qwen3-hbm", "qwen3-array", "v41-rom"}
    for name, t in rec["targets"].items():
        assert t["pass"], name
        for r in t["requests"]:
            assert r["token_ids"] == r["expected_token_ids"], name
        assert t["counters"]["status"] & 0x17 == 0, name          # no fault, DMA error or event overflow
    assert rec["targets"]["qwen3-rom"]["requests"][0]["token_ids"] == ORACLE
    assert rec["targets"]["v41-rom"]["requests"][0]["token_ids"][0] == 3118
    assert len(rec["targets"]["qwen3-rom"]["requests"]) == 3
    assert len(rec["targets"]["qwen3-array"]["requests"]) == 4
    assert all(v["returncode"] == 0 and not v["messages"] for v in rec["lint"].values())


def test_campaign_endpoint_and_fail_closed_checks():
    t = _record()["targets"]["qwen3-rom"]
    ep = t["endpoint"]
    assert ep["pass"] and ep["streamed_token_ids"] == ORACLE and ep["plain_token_ids"] == ORACLE
    assert ep["finish_reason"] == "stop" and ep["stream_done_marker"] and ep["sampling_request_http_status"] == 400
    assert ep["openai_client"].get("pass", True)
    assert t["fail_closed"]["pass"]


def test_campaign_generated_ids_are_the_decode_campaigns():
    rec = _record()
    q = json.loads((ROOT / "results/rtl/hdc_decode_campaign.json").read_text())["end_to_end"]["generated_tokens"]
    v = json.loads((ROOT / "results/rtl/hdc_v41_decode_campaign.json").read_text())["end_to_end"]["generated_tokens"]
    for name in ("qwen3-rom", "qwen3-hbm", "qwen3-array"):
        assert rec["targets"][name]["requests"][0]["expected_token_ids"] == q
    assert rec["targets"]["v41-rom"]["requests"][0]["expected_token_ids"] == v


def test_campaign_record_is_current():
    for name, digest in _record()["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_physical_record_routes_the_campaign_source():
    phys = json.loads(PHYS.read_text())
    design = phys["design"]
    assert design["top"] == "ot_host_if" and "pnr" in phys["stages_completed"]
    assert design["clock_period_ns"] == 0.9
    rec = _record()
    for src in design["sources"]:
        assert src["sha256"] == rec["input_sha256"][src["path"]], src["path"]
    assert not list(PHYS.parent.rglob("*.v"))


@pytest.mark.skipif(os.environ.get("OT_SKIP_LIVE_RTL") == "1" or not shutil.which("verilator"),
                    reason="live RTL run disabled or Verilator missing")
def test_live_chat_completion_through_the_endpoint_is_the_oracle():
    from runtime.hdc.targets import TARGETS
    if TARGETS["qwen3-rom"].tokenizer_path() is None:
        pytest.skip("Qwen3 tokenizer not cached")
    from runtime.hdc.runtime import HdcRuntime
    from runtime.hdc.server import serve
    rt = HdcRuntime("qwen3-rom")
    httpd = serve([rt], port=0)
    try:
        url = f"http://127.0.0.1:{httpd.server_address[1]}/v1/chat/completions"
        body = {"model": "qwen3-reduced-v1@qwen3-rom", "messages": [{"role": "user", "content": "Reply with OK."}],
                "max_tokens": 8, "temperature": 0, "stream": True}
        raw = urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(),
                                                            {"Content-Type": "application/json"}), timeout=1800)
        events = [ln[6:] for ln in raw.read().decode().splitlines() if ln.startswith("data: ")]
        chunks = [json.loads(e) for e in events if e != "[DONE]"]
        ids = [c["opentallas"]["token_id"] for c in chunks if "token_id" in c.get("opentallas", {})]
        assert ids == ORACLE
        assert events[-1] == "[DONE]" and chunks[-1]["choices"][0]["finish_reason"] == "stop"
        assert chunks[-1]["opentallas"]["token_ids"] == ORACLE
    finally:
        httpd.shutdown()
        rt.close()
