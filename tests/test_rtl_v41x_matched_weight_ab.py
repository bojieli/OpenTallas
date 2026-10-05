"""Matched weight-source A/B on the V4.1x two-package all-unit bench (W_HBM=0 vs 1).

The parser tests are synthetic; the record test validates the committed result:
both arms pass every check on identical images before any delta is reported.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_v41x_matched_weight_ab.json"
REFERENCE = ROOT / "results/rtl/hdc_v41x_array_allunit_b2_o1fast_full.json"
OWN = ("tools/rtl_v41x_matched_weight_ab.py", "rtl/test/tb_v41x_matched_weight_ab.sv",
       "rtl/test/v41x_matched_weight_ab_harness.cpp")


def tool():
    spec = importlib.util.spec_from_file_location("ab", ROOT / "tools/rtl_v41x_matched_weight_ab.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


MAN = {"token_steps": 3, "packages": 2, "lm_head_packages": 1, "generated_tokens": 1,
       "golden_argmax": [2815, 3537, 2047]}


def log(whbm, extra=""):
    q = (51360, 665760) if whbm else (0, 0)
    lines = [
        "TOK user=0 pos=0 token=2815 cycle=400000",
        "ABTOK pos=0 cycle=400000 qe_issues=10,0 qrom_reads=100,0 qgate_wait=%d,0 qgate_low=5,0" % (7 * whbm),
        "TOK user=0 pos=1 token=3537 cycle=800000",
        "ABTOK pos=1 cycle=800000 qe_issues=10,10 qrom_reads=100,100 qgate_wait=%d,%d qgate_low=5,5"
        % (7 * whbm, 9 * whbm),
        "TOK user=0 pos=2 token=2047 cycle=1200000",
        "ABTOK pos=2 cycle=1200000 qe_issues=20,10 qrom_reads=200,100 qgate_wait=%d,%d qgate_low=9,5"
        % (8 * whbm, 9 * whbm),
    ]
    for n in (1, 0):
        lines.append(f"NODE node={n} busy=1 side_wait=0 tx_wait=0 starved=1 jobs=3 state_mismatch=0")
        lines.append(f"HBM_NODE node={n} q_bad=0 q_words={q[0]} q_reads={q[1]} q_fault=0 idx_records=3 "
                     f"idx_writes=36 idx_read_stalls=0 idx_writer_stalls=0 idx_refresh=99")
    lines += ["IDXHBM_USERS read=1 wrote=1",
              "HDC41_ARRAY nodes=2 users=1 generated=1 mismatches=0 logit_mismatch=0 lm_head_checks=3 "
              "state_mismatch=0 total_cycles=1200000", "USERS_DONE 1", "LINK_STALLS 102", "PASS",
              "ABNODE node=0 qe_issues=20 qrom_reads=200 qgate_wait=%d qgate_low=9" % (8 * whbm),
              "ABNODE node=1 qe_issues=10 qrom_reads=100 qgate_wait=%d qgate_low=5" % (9 * whbm)]
    if whbm:
        for n in (0, 1):
            lines.append(f"ABWHBM node={n} sector_reads=5 activates=2 row_hits=3 row_conflicts=0 refreshes=4 "
                         f"req_backpressure_cycles=0 rd_lat_sum_ps=50 rd_lat_max_ps=20 fetched=5 consumed=5 "
                         f"fault_why=0")
    lines.append("ABPROBE_DONE whbm=%d" % whbm)
    return "\n".join(lines) + "\n" + extra


@pytest.mark.parametrize("whbm", (0, 1))
def test_parse_passes_a_clean_arm(whbm):
    r = tool().parse(log(whbm), whbm, MAN)
    assert r["pass"], r["checks"]
    assert r["cycles_per_token_step"] == [400000, 400000, 400000]
    assert r["qgate_wait_per_token_step"] == ([7, 9, 1] if whbm else [0, 0, 0])


@pytest.mark.parametrize("bad", ("MISMATCH user=0 pos=1 got=1 gold=2\n", "FAIL\n",
                                 "QSTREAM_FAIL fault=01 bad=1 words=1 reads=1\n"))
def test_parse_fails_on_any_bench_failure(bad):
    assert not tool().parse(log(1, bad), 1, MAN)["pass"]


def test_parse_rejects_a_mislabelled_arm():
    """A W_HBM=0 arm that shows weight-HBM traffic (or the reverse) is not the arm it claims to be."""
    m = tool()
    assert not m.parse(log(1), 0, MAN)["pass"]
    assert not m.parse(log(0), 1, MAN)["pass"]


@pytest.mark.skipif(not RECORD.exists(), reason="A/B record not committed")
def test_matched_weight_ab_record():
    rec = json.loads(RECORD.read_text())
    ref = json.loads(REFERENCE.read_text())
    assert rec["schema"] == "opentallas.rtl.hdc_v41x_matched_weight_ab.v1"
    assert "not chip throughput" in rec["claim_boundary"]
    # identical program and images for both arms, and they are the reference gate's images
    assert rec["reference_record"]["image_match"] == {"files_compared": 30, "identical": 30, "differing": []}
    for k, v in ref["image_sha256"].items():
        assert rec["image_sha256"][k] == v, k
    eq = rec["images"]["weight_equivalence"]
    assert eq["pass"] and eq["word_mismatches"] == 0 and eq["hbm_sectors_consumed_by_decode"] == eq["hbm_sectors"]
    for name in OWN[1:]:
        assert rec["source_sha256"][name] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), name
    # the campaign ran with source_sha256[OWN[0]]; the committed tool is the one that combined the arms
    assert rec["combine_tool_sha256"] == hashlib.sha256((ROOT / OWN[0]).read_bytes()).hexdigest()
    a, b = rec["arms"]["A"], rec["arms"]["B"]
    assert (a["whbm"], b["whbm"]) == (0, 1)
    for arm in (a, b):
        assert arm["image_sha256"] == rec["image_sha256"] and arm["source_sha256"] == rec["source_sha256"]
        assert len(arm["binary_sha256"]) == 64 and len(arm["run"]["log_sha256"]) == 64
    if rec["status"] != "pass":
        assert rec["delta"] is None and rec["failure"]
        return
    assert all(rec["matching"].values())
    for arm in (a, b):
        assert arm["pass"] and all(arm["checks"].values())
        assert [t["token"] for t in arm["tokens"]] == [2815, 3537, 2047]
        s = arm["summary"]
        assert s["token_mismatches"] == s["logit_mismatches"] == s["state_mismatches"] == 0
        assert s["lm_head_checks"] == 3 and s["total_cycles"] == arm["token_cycles"][-1]
        assert all(h["q_fault"] == h["q_bad"] == 0 for h in arm["hbm_node"])
    # arm B is the reference gate's configuration: same token cycles
    assert b["token_cycles"] == [t["cycle"] for t in ref["observed"]["tokens"]]
    assert all(h["q_reads"] == 0 for h in a["hbm_node"]) and all(p["qgate_wait"] == 0 for p in a["probe"])
    d = rec["delta"]
    assert sum(x["delta_cycles"] for x in d["per_token_step"]) == d["total"]["delta_cycles"]
    for x, ca, cb in zip(d["per_token_step"], a["cycles_per_token_step"], b["cycles_per_token_step"]):
        assert (x["A_cycles"], x["B_cycles"], x["delta_cycles"]) == (ca, cb, cb - ca)
    t = d["total"]
    assert t["delta_cycles"] == t["B_cycles"] - t["A_cycles"]
    assert abs(t["delta_percent"] - 100 * t["delta_cycles"] / t["A_cycles"]) < 1e-3
    assert d["B_weight_hbm"]["sector_reads"] == sum(h["q_reads"] for h in b["hbm_node"])
