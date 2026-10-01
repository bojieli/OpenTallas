"""Fusion audit (tools/fusion_audit.py -> results/uarch/fusion_audit.json): the record regenerates from its tool, is
source-pinned, and its levels are ordered (each adopted level never slows the token)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/uarch/fusion_audit.json"


def _rec():
    return json.loads(REC.read_text())


def test_record_is_source_pinned():
    r = _rec()
    assert r["schema"] == "opentallas.uarch.fusion_audit.v1"
    for p, h in r["source_sha256"].items():
        import hashlib
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p


def test_levels_are_monotone_and_classes_are_marked():
    r = _rec()["v41_rom"]
    for key in ("ar_levels", "mtp_pass_levels"):
        lv = r["rows"][key]
        chain = ["L0_unfused_us", "L1_lane_local_us", "L2_delivery_only_us", "L2_delivery_plus_element_epilogue_us",
                 "L3_stream_reductions_us", "L5_plus_piggyback_us", "L5_plus_piggyback_and_hops_us"]
        for a, b in zip(chain, chain[1:]):
            assert lv[b] <= lv[a] + 1e-6, (key, a, b)
        # the in-order stream unit is an EXPOSURE of the model's free interleaving, never a gain
        assert lv["L4_in_order_pipelined_exposure_us"] >= lv["L1_lane_local_us"]
    cls = {c["candidate"]: c["cls"] for c in r["ranked"]["candidates"]}
    assert cls["C: norm scalar after the matvec"] == "C" and cls["C: online softmax"] == "C"
    for c in _rec()["v41_hbm"]["candidates"]:
        assert c["cls"] in ("A", "B", "B*", "C")


def test_record_regenerates_from_its_tool(tmp_path):
    out = tmp_path / "fa.json"
    subprocess.run([sys.executable, str(ROOT / "tools/fusion_audit.py"), "--out", str(out)], check=True, cwd=ROOT,
                   capture_output=True)
    assert json.loads(out.read_text()) == _rec()
