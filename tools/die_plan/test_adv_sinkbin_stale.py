"""pytest: ADV-SINKBIN-STALE (CB-TAPBINS repeat class: KV-SINKBINS pv, QC st_a, QC STB-SPLIT)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_sinkbin_stale as A  # noqa: E402


def stb(hard_children=True):
    """an st_b-like type 600 x 1300 um: 4 station children u_r4..u_r7 (151.2 um) hardened by the split row"""
    t = {"outline_um": [622.08, 1339.2], "clock": {"tap_mode": "density", "sink_bins_file": "sink_bins/stb.json"},
         "hard_cores": []}
    if hard_children:
        t["hard_cores"] = [{"inst": f"u_r{4 + i}", "origin_um": [200.0, 100.0 + 300.0 * i], "outline_um": [151.2, 151.2]}
                           for i in range(4)]
    return t


def bins_doc(tn, frac_inside):
    """1000 sinks: frac_inside of them in bins centred inside u_r4..u_r7, the rest in the free glue column x=50"""
    n_in = int(round(1000 * frac_inside))
    rows = [[275.4, 175.4 + 300.0 * (i % 4), 1] for i in range(n_in)] + [[54.0, 54.0 + (i % 100) * 10.8, 1]
                                                                          for i in range(1000 - n_in)]
    return {"bin_um": 10.8, "n": 1000, "bins": rows, "type": tn}


def test_stb_split_children_inside_flags_and_flattened_is_clean():
    r = A.judge_type("stb", stb(), bins_doc("stb", 0.30))
    assert r["is_inside"] and round(r["frac_in"], 2) == 0.30 and r["by_core"][0][0].startswith("u_r")
    r0 = A.judge_type("stb", stb(hard_children=False), bins_doc("stb", 0.30))   # before the split: flattened, legit sinks
    assert not r0["hit"]
    assert not A.judge_type("stb", stb(), bins_doc("stb", 0.04))["hit"]          # <= 5 %: not stale


def test_edge_bins_beside_a_core_and_off_outline():
    t = stb()
    doc = {"bin_um": 10.8, "bins": [[205.0, 105.0, 900], [54.0, 54.0, 100]], "type": "stb"}  # centre 5 um inside the edge
    assert not A.judge_type("stb", t, doc)["is_inside"]
    doc = {"bin_um": 10.8, "bins": [[700.0, 54.0, 100], [54.0, 54.0, 900]], "type": "stb"}   # 10 % off the outline
    r = A.judge_type("stb", t, doc)
    assert r["is_inside"] and r["outside"] == 100


def test_predates_split_rename_and_param_variant_sharing_geometry():
    t = stb()
    types = {"stb__pv1": t, "stb__pv2": json.loads(json.dumps(t))}
    assert A.judge_type("stb__pv1", t, bins_doc("stb", 0.0), types=types)["predates"]          # parent gone: pre-split
    assert not A.judge_type("stb__pv1", t, bins_doc("stb__pv2", 0.0), types=types)["hit"]      # same geometry: shared
    types["stb__pv2"]["outline_um"] = [700.0, 1339.2]
    assert A.judge_type("stb__pv1", t, bins_doc("stb__pv2", 0.0), types=types)["predates"]     # re-shaped sibling
    r = A.judge_type("stb", t, bins_doc("stb", 0.0), bins_time=1000.0, row_time=2000.0)        # row after the bins
    assert r["predates"] and "older than the type's row" in r["predates"][0]


def test_fanout_from_kit_newer_than_bins_only():
    t, doc = stb(), bins_doc("stb", 0.0)
    kit = {"max_sinks": 4076, "max_tap": "clk_t69", "mtime": 2000.0}
    assert A.judge_type("stb", t, doc, bins_time=1000.0, kit=kit)["is_fanout"]
    r = A.judge_type("stb", t, doc, bins_time=3000.0, kit=kit)                                 # kit measured older bins
    assert not r["is_fanout"] and r["old_kit"]
    assert not A.judge_type("stb", t, doc, bins_time=1000.0, kit=dict(kit, max_sinks=960))["hit"]


def test_findings_end_to_end_and_never_raises(tmp_path):
    (tmp_path / "sink_bins").mkdir()
    (tmp_path / "sink_bins" / "stb.json").write_text(json.dumps(bins_doc("stb", 0.40)))
    raw = {"partition_types": {"stb": stb(), "nobins": {"outline_um": [10, 10], "clock": {}}}}
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(raw))
    ls = A.findings(raw, str(plan), kit_sinks={})
    assert ls[0].startswith("WARN ADV-SINKBIN-STALE stb stb.json: INSIDE") and "1 of 1 types" in ls[-1]
    assert A.findings(None, None)[0].startswith("WARN ADV-SINKBIN-STALE not checked")


def test_nobins_and_count_report_only_then_block(tmp_path, monkeypatch):
    (tmp_path / "sink_bins").mkdir()
    doc = bins_doc("have", 0.0)
    doc["n"] = 1000
    (tmp_path / "sink_bins" / "have.json").write_text(json.dumps(doc))
    ge = lambda b: {"outline_um": [1000, 1000], "clock": {"tap_mode": "grid+explicit", "added_taps": [{"name": "clk_t1", "xy": [5, 5]}],
                                                       **({"sink_bins_file": "sink_bins/have.json"} if b else {})}}
    raw = {"partition_types": {"nob": ge(False), "have": ge(True),
                               "hardt": {"hard": True, "outline_um": [1, 1], "clock": {"tap_mode": "density"}},
                               "grid": {"outline_um": [1, 1], "clock": {"tap_mode": "grid+explicit"}}}}
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(raw))
    kit = {"have": {"sinks": 1500, "max_sinks": 900, "max_tap": "clk", "mtime": 9e9}}
    monkeypatch.delenv(A.BLOCK_ENV, raising=False)
    ls = A.findings(raw, str(plan), kit_sinks=kit)
    nb = [x for x in ls if " NOBINS " in x]
    assert nb and nb[0].startswith("WARN") and "nob" in nb[0] and "hardt" not in nb[0] and "grid," not in nb[0]
    assert any(" COUNT " in x and "have 1,000->1,500" in x for x in ls)
    monkeypatch.setenv(A.BLOCK_ENV, "1")
    assert [x for x in A.findings(raw, str(plan), kit_sinks=kit) if " NOBINS " in x][0].startswith("FAIL")
