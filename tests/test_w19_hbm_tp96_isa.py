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
