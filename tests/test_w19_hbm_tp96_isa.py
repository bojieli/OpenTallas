"""W19 B1: the TP-96 V4.1 HBM-comparator token record (results/rtl/w19_hbm_tp96_isa.json) and its program."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = json.loads((ROOT / "results/rtl/w19_hbm_tp96_isa.json").read_text())
REF = json.loads((ROOT / "results/rtl/w17_v41_1m_reference_token.json").read_text())
FULL = "gather:L0-39:head"


def test_sources_are_pinned_at_the_recording_commit():
    run = REC["runs"][FULL]
    for name, digest in run["source_sha256"].items():
        blob = subprocess.run(["git", "show", f"{run['source_commit']}:{name}"], cwd=ROOT, capture_output=True,
                              check=True).stdout
        assert hashlib.sha256(blob).hexdigest() == digest, name


def test_full_token_is_bit_exact_against_the_1m_reference():
    assert REC["status"] == "pass" and not REC["failed_runs"]
    res = REC["runs"][FULL]["result"]
    assert (res["context"], res["seed"]) == (REF["context"], REF["seed"])
    assert res["state_check"]["match"] and res["state_check"]["state_sha256"] == REF["state"]["state_sha256"]
    assert [l["layer"] for l in res["layers"]] == list(range(40))
    for lay in res["layers"]:
        assert lay["verdict"] == "pass" and lay["defect"] is None, lay["layer"]
        assert all(r["bit_exact"] for r in lay["regions"]), lay["layer"]
        assert {r["region"] for r in lay["regions"]} >= {f"L{lay['layer']}.attn", f"block{lay['layer']}"}
    h = res["head"]
    assert h["verdict"] == "pass" and h["tokens_agree_all_ranks"]
    assert h["next_token"] == REF["next_token"] == 21946
    assert h["logits_sha256"] == REF["logits_sha256"]


def test_program_matches_the_record():
    prog = json.loads((ROOT / "results/rtl/w19_hbm_tp96_program.json").read_text())
    res = REC["runs"][FULL]["result"]
    assert prog["tp"] == 96 and prog["variant"] == "gather"
    colls = [sum(op["kind"] in ("all_gather", "all_reduce", "topk_merge", "kv_gather") for op in lay["ops"])
             for lay in prog["layers"]]
    assert colls[:40] == [l["collectives"] for l in res["layers"]]
    # every mv op's row split covers its rows exactly once
    for lay in prog["layers"]:
        for op in lay["ops"]:
            if op["kind"] == "mv" and op["fn"] != "wo_a_part":
                spans = sorted((a, b) for a, b in op["rows"] if b > a)
                assert spans[0][0] == 0 and spans[-1][1] == op["n"] or op["tag"].startswith("wq_b"), op["tag"]
                assert all(spans[i][1] == spans[i + 1][0] for i in range(len(spans) - 1)), op["tag"]


def test_mtp_verify_pass_is_bit_exact_per_position():
    rec = json.loads((ROOT / "results/rtl/w19_hbm_tp96_isa_mtp.json").read_text())
    run = rec["runs"]["mtp:gather:L0-39:head"]
    res = run["result"]
    gold = json.loads((ROOT / "results/rtl/w19_mtp_golden/mtp_head.json").read_text())
    assert rec["status"] == "pass" and len(res["positions"]) == 6
    assert [l["layer"] for l in res["layers"]] == list(range(40))
    for lay in res["layers"]:
        assert lay["verdict"] == "pass" and lay["union_matches_golden"], lay["layer"]
        assert all(p["verdict"] == "pass" for p in lay["positions"]), lay["layer"]
    h = res["head"]
    assert h["verdict"] == "pass" and all(h["logits_bit_exact"])
    assert h["targets"] == gold["targets"] and h["position0_token"] == REF["next_token"]
    assert gold["logits_sha256"][0] == REF["logits_sha256"]
    assert abs(res["mean_union_experts"] - gold["mean_union_experts"]) < 1e-9


def test_sm_real_operands_are_exact():
    for name in ("w19_sm_real_ops.json", "w19_sm_real_ops_oreduce.json", "w19_sm_real_ops_mtp.json"):
        rec = json.loads((ROOT / "results/rtl" / name).read_text())
        assert rec["status"] == "pass", name
        assert all(c["exact"] for cs in rec["cases"].values() for c in cs), name


def test_grouped_o_reduce_token_is_bit_exact():
    rec = json.loads((ROOT / "results/rtl/w19_hbm_tp96_isa_oreduce.json").read_text())
    res = rec["runs"]["oreduce:L0-39:head"]["result"]
    assert rec["status"] == "pass" and res["variant"] == "oreduce"
    assert all(l["verdict"] == "pass" for l in res["layers"]) and len(res["layers"]) == 40
    assert res["head"]["verdict"] == "pass" and res["head"]["logits_sha256"] == REF["logits_sha256"]
    prog = json.loads((ROOT / "results/rtl/w19_hbm_tp96_program_oreduce.json").read_text())
    assert not any(op["tag"] == "o_gather" for lay in prog["layers"] for op in lay["ops"])


def test_grouped_o_reduce_mtp_verify_is_bit_exact():
    rec = json.loads((ROOT / "results/rtl/w19_hbm_tp96_isa_mtp_oreduce.json").read_text())
    res = rec["runs"]["mtp:oreduce:L0-39:head"]["result"]
    assert rec["status"] == "pass" and res["variant"] == "oreduce" and len(res["layers"]) == 40
    assert all(l["verdict"] == "pass" and l["union_matches_golden"] for l in res["layers"])
    assert res["head"]["verdict"] == "pass" and all(res["head"]["logits_bit_exact"])
