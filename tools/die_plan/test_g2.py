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
        assert meta["flops"] == 64 + 277 + 71 + 65 + 2          # + clk / arst_n tap buffers
        v = (out / "probe.v").read_text()
        assert "st_fz_64_0" in v and "CLK" not in v
        assert (out / "io.tcl").read_text().count("place_pin") == 64 + 277 + 71 + 64 + 65 + 2   # fz_i from die IO: no epoch


def test_assembly_die_flow():
    import gen_phys
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "views").mkdir()
        kd = gen_phys.write_assembly(PAIR, d, str(Path(d) / "views"))
        kd = Path(d) / "die"
        tcl = (kd / "die_flow.tcl").read_text()
        assert "place_macro -macro_name pfb -location {1434.24 0} -orientation R0 -exact" in tcl and "detailed_route" in tcl
        v = (kd / "die_top_struct.v").read_text()
        assert "endmodule :" not in v and "w_x" in v
        assert (kd / "seams.json").is_file() and (kd / "abut_audit.py").is_file() and (kd / "run_die.sh").is_file()


def test_coincident_taps_split():
    import copy
    import gen_phys
    raw = copy.deepcopy(PAIR)
    t = raw["partition_types"][0] if isinstance(raw["partition_types"], list) else next(iter(raw["partition_types"].values()))
    ck = t.setdefault("clock", {}).setdefault("tap_um", [700.0, 1800.0])
    t.setdefault("reset", {})["tap_um"] = list(ck)
    P = schema.Plan(raw)
    tn = t.get("name") or next(iter(P.types))
    a, b = gen_phys.tap_points(P, tn)
    assert a != b and abs(a[1] - b[1]) > 8


def test_seam_audit_catches_or11810():
    """OR#11810: an M4 pin touching an M5 pin counts as 'abutted' on images without #11814; the seam audit must FAIL it
    and PASS the same-layer seam.  Needs docker + openroad/orfs:asap7lock (skipped otherwise)."""
    import shutil
    import subprocess
    import pytest
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        src = HERE / "examples" / "abut_layer_bug"
        for f in ("blk.lef", "t.v", "t.tcl", "seams.json"):
            shutil.copy(src / f, d)
        shutil.copy(HERE / "abut_audit.py", d)
        cmd = ("source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl >/dev/null 2>&1; "
               "ODB=/w/t.odb SEAMS=/w/seams.json OUT=/w/a.json DRC=/none openroad -python -exit /w/abut_audit.py; "
               "chmod -R a+rwX /w")
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        a = json.loads((Path(d) / "a.json").read_text())
        assert a["ok"] == 1 and a["fails"] == {"abut_no_same_layer_overlap": 1}


def test_pins_avoid_partition_pg_stripes():
    P = schema.Plan(PAIR)
    n = 0
    for pid in P.ports:
        for bit, ln, c in P.port_pins(pid):
            assert not schema.pg_blocked(ln, c), (pid, bit, ln, c)
            n += 1
    assert n > 500
    # band geometry: M6 VDD 1.968 +- 0.144 / VSS 2.352 +- 0.144 must be blocked, a mid-gap track free
    assert schema.pg_blocked("M6", 1.968) and schema.pg_blocked("M6", 2.352) and not schema.pg_blocked("M6", 4.0)


def test_spread_uniform_at_budget_density():
    """PLAN-HBM 10-23: a window sized at exactly the 6/um budget must pass the G0 face check (the old spreader packed
    pins up to 1.2x the window average)."""
    import copy
    import check
    raw = copy.deepcopy(PAIR)
    pr = next(p for p in raw["ports"] if p["id"] == "x")
    n = pr["width"] + 1                                   # + epoch
    lo = 1800.0
    pr["window_um"] = [lo, lo + n / 6.0]                  # exactly 6 pins/um over 2 layers
    P = schema.Plan(raw)
    pins = sorted(c for _, _, c in P.port_pins("x"))
    assert len(pins) == n
    win = 10.0
    mx = max(sum(1 for c in pins if a <= c < a + win) for a in pins)
    assert mx <= 6 * win + 4, mx                          # check.py allowance: 2 pins per layer
    R, summ = check.run(raw)
    assert not [f for f in R.errors() if f["check"] == "faces"], R.errors()
    # uniform: per layer most gaps are the window average (1/3 um) to within one track; the rest sit at PG bands
    for ln in pr["layers"]:
        cs = sorted(c for _, l, c in P.port_pins("x") if l == ln)
        gaps = [b - a for a, b in zip(cs, cs[1:])]
        near = sum(1 for g in gaps if abs(g - 1 / 3.0) <= 0.065)
        assert near >= 0.6 * len(gaps), (ln, near, len(gaps))


def test_window_for_fits_after_pg_bands():
    L = {x["name"]: x for x in schema.ASAP7_LAYERS}
    for lo in (2.0, 4.1, 100.3):
        for n in (1, 2, 9, 141):
            hi = schema.window_for(lo, n, ["M7", "M5"])
            port = dict(id="t", width=n, window_um=[lo, hi], layers=["M7", "M5"], epoch=False)
            assert len(schema.pin_positions(port, L)) == n
