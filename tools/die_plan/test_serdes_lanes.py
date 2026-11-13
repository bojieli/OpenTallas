"""HARD-S81-SERDES-1 11-13: type key serdes_lanes (gen_phys.serdes_lanes_cfg_tcl, serdes_lanes.tcl)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402

T2 = {"blocks": [[4.32, 4.32, 850.0, 944.0], [850.0, 470.0, 2010.0, 944.0], [2010.0, 330.0, 2881.44, 944.0],
                 [4.32, 944.0, 244.0, 1222.56], [2491.5, 944.0, 2881.44, 1222.56]],
      "chains": [{"name": "u_lpin", "rows": 3, "kind": "pt", "a_um": [2815.0, 175.0], "b_um": [1960.0, 330.0]},
                 {"name": "u_txl", "rows": 6, "kind": "txl", "a_um": [1800.0, 440.0], "b_um": [1367.0, 936.0]},
                 {"name": "u_lrxi", "rows": 5, "kind": "rxi", "a_um": [1367.0, 946.0], "b_um": [1300.0, 440.0]},
                 {"name": "u_lrxo", "rows": 3, "kind": "pt", "a_um": [1750.0, 90.0], "b_um": [2840.0, 62.0]}]}


def test_cfg_text_is_the_proof_kit_cfg():
    txt = gen_phys.serdes_lanes_cfg_tcl(T2)
    assert "{u_txl 6 txl 1800.000 440.000 1367.000 936.000}" in txt
    assert "{u_lrxi 5 rxi 1367.000 946.000 1300.000 440.000}" in txt
    assert txt.count("\n    {") == 9 and txt.startswith("# GENERATED")


def test_hop_over_reach_is_refused():
    bad = {"blocks": [], "chains": [{"name": "u_lrxo", "rows": 2, "kind": "pt", "a_um": [0.0, 0.0], "b_um": [1300.0, 0.0]}]}
    with pytest.raises(ValueError, match="over the 405 um reach"):
        gen_phys.serdes_lanes_cfg_tcl(bad)


def test_empty_block_is_refused():
    with pytest.raises(ValueError, match="empty rectangle"):
        gen_phys.serdes_lanes_cfg_tcl({"blocks": [[5, 5, 5, 9]], "chains": []})


def test_hooks_ship_with_the_tool():
    d = Path(gen_phys.__file__).resolve().parent
    body = (d / "serdes_lanes.tcl").read_text()
    assert "OT_SERDES_LANES" in body and "dbBlockage_create" in body
    assert "dbBlockage_destroy" in (d / "serdes_lanes_release.tcl").read_text()
