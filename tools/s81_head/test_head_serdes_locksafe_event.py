import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import head_serdes_locksafe_event as E  # noqa: E402
import head_serdes_locksafe_delta as D  # noqa: E402


def _plan():
    return {"partition_types": {"hd_serdes": {
        "contents": [{"inst": "u_phy", "module": D.OLD, "bind": {"ck": "clk", "rst_n": "rst_n"}}], "pads": [], "sources": [],
        "clock": {"pad_clock": {"pins": [
            {"name": "pma_rck", "cdc_evidence": "x", "xy_um": [1106.016, 148.32]},
            {"name": "pma_tck", "xy_um": [1114.656, 148.32]}]}}},
        "hd_tile": {"contents": []}}}


def test_event_site_and_scope():
    p = _plan()
    site = E.default_site(p)
    assert site == [1123.296, 148.32]
    q = E.apply_event(p, site)
    assert q["partition_types"]["hd_tile"] == p["partition_types"]["hd_tile"]
    t = q["partition_types"]["hd_serdes"]
    pad = [x for x in t["pads"] if x["name"] == "pma_lock"][0]
    assert pad["sites_um"] == [site] and pad["layer"] == "M7" and pad["dir"] == "in"
    assert "ot_pdie_pma_reset_hold" in t["clock"]["pad_clock"]["pins"][0]["cdc_evidence"]


def test_source_top_patch(tmp_path):
    f = tmp_path / "top.sv"
    f.write_text("    input  wire [0:0] a_pma_rck,\n  x\n        .pma_rck(a_pma_rck),\n")
    E.patch_source_top(f, ["a"])
    t = f.read_text()
    assert "    input  wire [0:0] a_pma_lock,\n" in t and ".pma_rck(a_pma_rck),\n        .pma_lock(a_pma_lock),\n" in t
