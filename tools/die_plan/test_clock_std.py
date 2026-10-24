"""CLK-STD tests (owner 10-23 industry multi-source CTS): structured zero-skew spine + seam sharing (fixes 1, 6),
density taps (fix 2), distance+load assignment / GRT-RC window balance hooks (fixes 3, 4), die-STA tap-wire re-apply.
    python3 -m pytest -q tools/die_plan/test_clock_std.py"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema as S  # noqa: E402
import spine  # noqa: E402
import taps  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _plan(**clock):
    raw = copy.deepcopy(EX)
    raw["clock"].update(clock)
    return raw


def test_zst_merge_equal_and_snake():
    # reachable: merge point on the path, both sides equal
    xy, D, la, lb, pa, pb = spine.zst_merge(((0.0, 0.0), 0.0), ((100.0, 0.0), 40.0))
    assert abs((la + 0.0) - (lb + 40.0)) < 1e-9 and la + lb == 100.0 and pa == pb == 0.0 and xy == (70.0, 0.0)
    # unreachable: b is deeper than a + the whole path -> merge at b, a's leg snakes
    xy, D, la, lb, pa, pb = spine.zst_merge(((0.0, 0.0), 0.0), ((10.0, 0.0), 50.0))
    assert xy == (10.0, 0.0) and lb == 0.0 and la == 50.0 and pa == 40.0 and D == 50.0


def test_zst_tree_every_tap_same_length():
    P = S.Plan(_plan())
    for tn in P.types:                           # several taps per partition (pitch 300 -> 3 x 3)
        P.types[tn]["clock"]["tap_pitch_um"] = 300.0
    tr = spine.zst_tree(P)
    lens = [v["length_um"] for r in tr["taps"].values() for v in r.values()]
    assert len(lens) == 4 * 9 and max(lens) - min(lens) < 0.05
    assert abs(lens[0] - tr["path_um"]) < 0.05
    # every partition has one entry node (its clock port feeds its own tap sub-tree)
    assert set(tr["part_entry"]) == set(P.parts)
    # legs ride the die layers: horizontal M8, vertical M9; repeaters every <= rep_um
    segs = [s for n in tr["nodes"] for s in n.get("segments", [])]
    assert {s["layer"] for s in segs} <= {"M8", "M9"} and tr["layers"] == {"H": "M8", "V": "M9"}
    for n in tr["nodes"]:
        if n.get("leg_um", 0) > P.rep_um:
            assert n["repeaters"] >= 1
    # branch table in the zst model: no branch mismatch (offset 0 for every grid tap)
    tab = spine.branch_table(P)
    assert tab["model"] == "zst"
    assert all(abs(v["offset_ps"]) < 0.01 for r in tab["parts"].values() for v in r["taps"].values())


def test_seam_aware_bisection_keeps_heavy_seam_together():
    P = S.Plan(_plan())
    bits = spine.seam_bits(P)
    assert bits and all(len(k) == 2 for k in bits)
    # force the heaviest seam to pm1|pm2: the first cut must not separate them
    bits = {k: 1 for k in bits}
    bits[frozenset(("pm1", "pm2"))] = 10_000
    t = spine.seam_bisect(P, list(P.parts), bits)

    def leaves(x):
        return {x} if not isinstance(x, tuple) else leaves(x[0]) | leaves(x[1])
    halves = [leaves(t[0]), leaves(t[1])]
    assert any({"pm1", "pm2"} <= h for h in halves)
    # the seam report: heavier sharing for the neighbours under one branch
    tr = spine.zst_tree(P)
    for sm in tr["seams"]:
        assert 0.0 <= sm["shared_frac"] <= 1.0 and abs(sm["shared_um"] + sm["unshared_um"] - tr["path_um"]) < 0.05


def test_density_taps_prune_macros_and_split_dense():
    raw = _plan(tap_mode="density")
    t = raw["partition_types"]["mid"]
    # a hard core covering the lower-left 432 x 432 quadrant: no tap inside it
    t["hard_cores"] = [dict(inst="u_core", origin_um=[0.0, 0.0], outline_um=[432.0, 432.0],
                            track_offset_um=[0.0, 0.0])]
    P = S.Plan(raw)
    assert S.tap_mode(P, "mid") == "density"
    tl = taps.density_taps(P, "mid")
    for _, x, y, _ in tl:
        assert not (0.0 < x < 432.0 and 0.0 < y < 432.0)
    assert S.tap_grid(P, "mid")[0][0] == "clk" and len(S.tap_grid(P, "mid")) == len(tl)
    # dense type: 200k cells x 0.12 flops = 24k sinks over 4 grid cells -> cells split (cap 1500)
    raw2 = _plan(tap_mode="density")
    raw2["partition_types"]["src"]["cells"] = 200000
    P2 = S.Plan(raw2)
    tl2 = taps.density_taps(P2, "src")
    assert len(tl2) > len(S._grid_taps(P2, "src"))
    assert max(e for *_, e in tl2) <= 1500 * 1.01 or len(tl2) >= 16
    # an empty type (no cells, no planned sinks in most cells) keeps fewer taps than the grid but at least one
    raw3 = _plan(tap_mode="density")
    raw3["partition_types"]["sink"]["cells"] = 0
    P3 = S.Plan(raw3)
    tl3 = taps.density_taps(P3, "sink")
    assert 1 <= len(tl3) <= len(S._grid_taps(P3, "sink"))
    rep = taps.density_report(P2, "src")
    assert rep["mode"] == "density" and rep["n"] == len(tl2)


def test_kit_and_assembly_carry_clock_std():
    with tempfile.TemporaryDirectory() as d:
        raw = _plan(tap_mode="density")
        kits = gen_phys.write_phys(raw, Path(d) / "k", proof=True)
        kd = kits[0]
        cfg = (kd / "config.mk").read_text()
        assert "export OT_TAP_WINDOW_PS = 20" in cfg and "export OT_TAP_RC = grt" in cfg
        assert "export OT_TAP_MAX_SINKS = 1500" in cfg
        assert (kd / "tap_wire.tcl").is_file()
        bud = json.loads((kd / "budget.json").read_text())
        assert bud["clock"]["tap_mode"] == "density" and bud["clock"]["density_taps"]["n"] >= 1
        rk = (Path(d) / "k" / "run_kit.sh").read_text()
        assert "tap_wire.tcl" in rk and "tap_wire.tsv" in rk
        mv = Path(d) / "mv"
        gen_phys.write_mock_views(raw, mv)
        ad = gen_phys.write_assembly(raw, Path(d) / "asm", mv)
        sta = (ad / "sta_die.tcl").read_text()
        assert "set_assigned_delay -net -rise -from [get_ports clk]" in sta and "set_assigned_transition" in sta
        assert "tap_wire.tsv]" in sta and ': "branch"}]' in sta
        flow = (ad / "die_flow.tcl").read_text()
        assert "create_ndr -name OT_CLK_2W2S" in flow and "assign_ndr -ndr OT_CLK_2W2S -net clk" in flow
        assert "-clock M7-M9" in flow
        tree = json.loads((ad / "spine_tree.json").read_text())
        assert tree["model"] == "zst" and tree["seams"]


@pytest.mark.skipif(not shutil.which("tclsh"), reason="tclsh not installed")
def test_clock_tcl_complete_and_keys():
    for f in ("clock_taps.tcl", "tap_balance.tcl", "tap_wire.tcl"):
        r = subprocess.run(["tclsh"], input=f"set fh [open {HERE / f}]; puts [info complete [read $fh]]",
                           capture_output=True, text=True)
        assert r.stdout.strip() == "1", f
    ct = (HERE / "clock_taps.tcl").read_text()
    assert "OT_TAP_MIN_SINKS" in ct and "regret" in ct.lower() and "ot_tap_sinks.tsv" in ct
    tb = (HERE / "tap_balance.tcl").read_text()
    assert "estimate_parasitics -global_routing" in tb and "OT_TAP_RC" in tb and ": 20.0}]" in tb
    tw = (HERE / "tap_wire.tcl").read_text()
    assert "arrival_max_rise" in tw and "slew_max_rise" in tw
