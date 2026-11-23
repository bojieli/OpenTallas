"""CTS-NDR-1123: OT_CTS_NO_NDR=1 -> CTS_ARGS -apply_ndr none (GRT-0273 family lever), reachable by wave item_env glob keys."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "autopilot"))

import gen_phys as G  # noqa: E402
import kit_wave as KW  # noqa: E402


def test_lines_follow_env():
    assert G.cts_ndr_lines({}) == []
    assert G.cts_ndr_lines({"OT_CTS_NO_NDR": "0"}) == []
    (line,) = G.cts_ndr_lines({"OT_CTS_NO_NDR": "1"})
    assert line.startswith("export CTS_ARGS = ") and "-apply_ndr none" in line
    assert "-sink_clustering_enable -repair_clock_nets" in line


def test_family_glob_reaches_item_env():
    d = {"item_env": {"ot_s81sl_leaf__*": {"OT_CTS_NO_NDR": "1"}, "col_h9_r0_*": {"OT_CTS_NO_NDR": "1", "OT_X": "a"},
                      "col_h9_r0_p2__t1": {"OT_X": "b"}, "serdes__*": {"OT_CTS_NO_NDR": "1"}}}
    assert KW.item_env_entry(d, "ot_s81sl_leaf__t25__cl55642d17")["OT_CTS_NO_NDR"] == "1"
    e = KW.item_env_entry(d, "col_h9_r0_p2__t1")
    assert e["OT_CTS_NO_NDR"] == "1" and e["OT_X"] == "b"          # exact key wins its own keys, glob keys merge
    assert KW.item_env_entry(d, "serdes__t2")["OT_CTS_NO_NDR"] == "1"
    assert "OT_CTS_NO_NDR" not in KW.item_env_entry(d, "col_h10_r0_p1__t1")
