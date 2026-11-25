"""ADV-ISTA-LEAF (FP-CONVERGE-QC 11-25): pass case + mutant on a synthetic sle_fw-like sc_eo chain."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_ista_leaf as A  # noqa: E402


def plan(leaf):
    e = {"conn": "bus:sc_eo", "from_um": [609.366, 1193.362], "to_um": [0.0, 677.358], "bits": 48,
         "regs_um": [[421.8, 1193.4], [322.4, 1105.2], [322.4, 917.6], [322.4, 730.1], [187.6, 677.4]],
         "leaf_um": leaf, "leg_order": "channel", "channel_um": [320.0, 324.8], "launch": "u_core", "capture": "face sc_eo"}
    return {"partition_types": {"sle_fw_v1": {"outline_um": [622.08, 1831.68],
                                              "buses": [{"name": "sc_eo", "dir": "out", "face": "W", "width": 48}],
                                              "internal_stations": [e]}}}


def test_pass_leaf_at_launch():
    assert A.findings(plan([609.366, 1193.362]), "p.json") == []


def test_mutant_leaf_at_se_corner_fires():
    out = A.findings(plan([622.08, 6.171252]), "p.json")
    assert out[0].startswith("WARN ADV-ISTA-LEAF sle_fw_v1 bus:sc_eo (out W)") and "1200 um" in out[0]
    assert out[-1].startswith("WARN ADV-ISTA-LEAF summary: 1 ")


def test_core_and_knee_entries():
    p = plan([622.08, 6.171252])
    q = copy.deepcopy(p)
    q["partition_types"]["sle_fw_v1"]["internal_stations"][0]["core"] = "u_lane0"      # core chains: other checker
    assert A.findings(q, "p.json") == []
    k = copy.deepcopy(p)
    del k["partition_types"]["sle_fw_v1"]["internal_stations"][0]["leg_order"]         # knee form still flagged
    assert A.findings(k, "p.json")[0].startswith("WARN ADV-ISTA-LEAF sle_fw_v1 bus:sc_eo")
