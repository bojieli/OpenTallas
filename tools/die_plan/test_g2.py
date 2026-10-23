"""G2 probe generation tests (no OpenROAD run).   python3 -m pytest -q tools/die_plan/"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import g2  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())

LOG = """
[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Overflow
---------------------------------------------------------------------------------------
M2              113413          1000            0.88%             0 /  0 /  0
M8               20000          4000           20.00%             1 /  0 /  3
Total           133413          5000            3.75%             1 /  0 /  3
[INFO GRT-0018] Total wirelength: 94217 um
OT_REACH clk max 717.1 p90 717.1 n 2
#stdCellPinNoAp        = 2
[INFO DRT-0166] Complete pin access.
OT_DONE
"""


def test_parse():
    r = g2.parse_grt(LOG)
    assert r["total_overflow"] == 3 and r["layers"]["M8"]["overflow"] == 3 and r["wirelength_um"] == 94217
    assert r["reach"]["clk"]["max_um"] == 717.1 and r["pin_access_no_ap"] == {"stdCell": 0, "stdCellPin": 2} or \
        r["pin_access_no_ap"]["stdCellPin"] == 2
    assert r["done"] and r["pin_access_done"]


def test_die_probe_files():
    P = schema.Plan(PAIR)
    with tempfile.TemporaryDirectory() as d:
        out = g2.die_probe(P, d)
        tcl = (out / "probe.tcl").read_text()
        assert "clk_tap_pfa" in tcl and "rst_tap_pfb" in tcl
        assert tcl.count("create_obstruction") > 2 * 7          # partitions on M1-M7 + PG stripes
        assert "set_routing_layers -signal M8-M9" in tcl
        meta = json.loads((out / "probe.json").read_text())
        assert meta["taps"] == 2 and meta["pg_stripes"] > 100


def test_part_probe_files_and_worst():
    P = schema.Plan(PAIR)
    R, summ = check.run(PAIR)
    sel = g2.worst_types(P, summ, 1)
    assert len(sel) == 1 and sel[0][0] in ("fa", "fb")
    with tempfile.TemporaryDirectory() as d:
        out = g2.part_probe(P, "fa", d)
        meta = json.loads((out / "probe.json").read_text())
        # boundary flops for din (64), x_o (277), r_i (71) + one station per bit of fz (65)
        assert meta["flops"] == 64 + 277 + 71 + 65
        v = (out / "probe.v").read_text()
        assert "st_fz_64_0" in v and "CLK" not in v
        assert (out / "io.tcl").read_text().count("place_pin") == 64 + 277 + 71 + 64 + 65 + 2   # fz_i from die IO: no epoch
