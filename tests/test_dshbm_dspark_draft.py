"""DS HBM DSpark draft record (results/rtl/dshbm_dspark_draft_20261004): the parts pass, the composition replays."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/rtl/dshbm_dspark_draft_20261004"


def test_parts_pass_and_chain_is_exact():
    ch = json.loads((REC / "chain.json").read_text())
    fs = json.loads((REC / "fullshape.json").read_text())
    assert ch["status"] == "pass" and fs["status"] == "pass"
    for name in ("dspark", "forced"):
        d = ch["drafters"][name]
        assert d["exact"] and len(d["steps"]) == 5
        assert all(s["markov_bias_mismatches"] == 0 and s["argmax_rtl"] == s["argmax_golden"] for s in d["steps"])
    assert ch["drafters"]["dspark"]["drafts_equal_golden"]
    assert ch["dhead5"]["mismatches"] == 0 and all(x["mismatches"] == 0 and x["equal_to_5col"] for x in ch["dhead1"])


def test_composition_replays():
    import argparse
    import dshbm_dspark_draft_chain as D
    rec = json.loads((REC / "composition.json").read_text())
    new = D.cmd_compose(argparse.Namespace(chain=REC / "chain.json", fullshape=REC / "fullshape.json"))
    assert new["rows"] == rec["rows"] and new["collective_count"] == rec["collective_count"]
    dflt = [r for r in rec["rows"] if r["authoritative_default"]]
    assert len(dflt) == 8
    for r in dflt:
        for v in ("as_built", "per_step_head"):
            assert abs(r[v]["step_us"] - (r["verify_p6_us"] + r[v]["draft_us"] + r["seed_commit_us"])) < 0.02


def test_successor_rows():
    import uarch_model as u
    s = u.hbm_mtp_both_drafts_measured()
    assert len(s["rows"]) == 8 and s["collective_count"]["draft"] == 23
