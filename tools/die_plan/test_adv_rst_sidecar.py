"""pytest: ADV-RST-SIDECAR (sidecar tap index measured against the plan collector tree; QC-SLECTL-RRL class)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_rst_sidecar as A  # noqa: E402


def lc():
    return {"collector_tree": {"root": [0.0, 0.0], "relays": [
                {"q": "rst_n_a", "xy": [100.0, 100.0], "d": "rst_root_n", "depth": 1},
                {"q": "rst_n_b", "xy": [1500.0, 100.0], "d": "rst_root_n", "depth": 1},
                {"q": "rst_n_t0", "xy": [110.0, 120.0], "d": "rst_n_a", "depth": 2},
                {"q": "rst_n_t1", "xy": [1510.0, 120.0], "d": "rst_n_b", "depth": 2}]},
            "collector_local_sources": [{"name": "busx", "xy_um": [120.0, 130.0], "pin_xy_um": [118.0, 125.0]}],
            "collector_children": [{"index": 0, "xy_um": [1500.0, 140.0]}]}


def plan(l):
    return {"partition_types": {"t": {"clock": {"landing_contract": l}}}}


def test_renumbered_tap_flags_raw_and_status():
    r = A.judge_type(lc(), {"local_sources": [{"name": "busx", "tap": 1}], "children": [{"node": "rst_n_t1"}]})
    assert (r["raw"], r["status"], r["child"], r["missing"]) == (1, 1, 0, 0) and r["worst"] > 1300 and r["reattach"] == 1


def test_synced_sidecar_passes():
    r = A.judge_type(lc(), {"local_sources": [{"name": "busx", "tap": 0}], "children": [{"node": "rst_n_t1"}]})
    assert (r["raw"], r["status"], r["child"], r["missing"]) == (0, 0, 0, 0)


def test_child_far_and_missing_node():
    r = A.judge_type(lc(), {"local_sources": [{"name": "busx", "tap": 9}], "children": [{"node": "rst_n_t0"}]})
    assert r["missing"] == 1 and r["child"] == 1 and r["reattach"] == 1    # rst_n_t1 (same depth) is in reach


def test_no_near_relay_is_split_out():
    l = lc(); l["collector_children"] = [{"index": 0, "xy_um": [800.0, 900.0]}]
    r = A.judge_type(l, {"local_sources": [{"name": "busx", "tap": 0}], "children": [{"node": "rst_n_t0"}]})
    assert r["child"] == 1 and (r["reattach"], r["nonear"]) == (0, 1)


def test_findings_summary_and_never_raises():
    ls = A.findings(plan(lc()), "p", None, sidecar_obj={"collector": {"types": {"t": {"local_sources": [{"name": "busx", "tap": 1}]}}}})
    assert ls[0].startswith("WARN ADV-RST-SIDECAR t: 1 reset copy") and "summary 1 of 1 types" in ls[-1]
    assert "NOT-RUN" in A.findings(plan(lc()), "p", None)[0]
    assert A.findings(None, "p", None, sidecar="x")[0].startswith("WARN ADV-RST-SIDECAR not checked")


def test_sidecar_from_asbuilt_table(tmp_path):
    sc = tmp_path / "zz_sidecar_x.json"
    sc.write_text('{"collector": {"types": {"t": {"local_sources": [{"name": "busx", "tap": 1}]}}}}')
    ab = tmp_path / "asbuilt_run.json"
    ab.write_text('{"clock_landing_table": "zz_sidecar_x.json"}')
    ls = A.findings(plan(lc()), "p", str(tmp_path), asbuilt=str(ab))
    assert "1 reset copy" in ls[0] and str(sc) in ls[-1]
