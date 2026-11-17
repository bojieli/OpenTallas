"""cts_trunk_reseat.tcl (FABLE-FIX-S81-IFN0-HW 11-16): opt-in clock_tree_synthesis wrapper, loader and geometry."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HELPER = REPO / "physical/common_flow/cts_trunk_reseat.tcl"
MARK = "# CTS-TRUNK-RESEAT (2026-11-16):"


def tcl(script, env=None):
    import os
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_CTS_")}
    e.update(env or {})
    return subprocess.run(["tclsh"], input=script, text=True, capture_output=True, env=e)


def test_off_by_default_and_armed_only_on_opt_in():
    body = f"proc clock_tree_synthesis {{args}} {{ puts \"ORIG $args\"; return 7 }}\nsource {HELPER}\n" \
           "proc ot_ctr_run {} { puts RESEAT }\nputs [clock_tree_synthesis -a 1]\n"
    r = tcl(body)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["ORIG", "-a", "1", "7"]
    r = tcl(body, {"OT_CTS_TRUNK_RESEAT": "1"})
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["OT_CTS_RESEAT armed (OT_CTS_TRUNK_RESEAT=1)", "ORIG -a 1", "RESEAT", "7"]
    # sourcing twice never wraps twice
    r = tcl(body.replace(f"source {HELPER}\n", f"source {HELPER}\nsource {HELPER}\n"), {"OT_CTS_TRUNK_RESEAT": "1"})
    assert r.stdout.splitlines() == ["OT_CTS_RESEAT armed (OT_CTS_TRUNK_RESEAT=1)", "ORIG -a 1", "RESEAT", "7"]


def test_target_leaves_macro_by_the_nearest_edge_inside_the_core():
    body = f"source {HELPER}\nset ot_ctr_core {{0 0 1000 1000}}\nset ot_ctr_rects {{{{100 100 500 300}}}}\n" \
           "puts [ot_ctr_legal 50 50]\nputs [ot_ctr_legal 300 290]\nputs [ot_ctr_legal 110 200]\nputs [ot_ctr_legal 2000 -5]\n" \
           "set ot_ctr_rects {{-10 -10 1010 400}}\nputs [ot_ctr_legal 500 20]\n"
    r = tcl(body)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["50 50", "300 300", "100 200", "1000 0", "500 400"]


def test_loader_standalone_and_repository_lookup(tmp_path):
    tail = MARK + (REPO / "tools/orfs_hold_mm.tcl").read_text().split(MARK, 1)[1]
    for standalone in (True, False):
        root = tmp_path / str(standalone); tools = root / "tools"; tools.mkdir(parents=True)
        script = tools / "orfs_hold_mm.tcl"; script.write_text(tail)
        helper = (tools if standalone else root / "physical/common_flow") / "cts_trunk_reseat.tcl"
        helper.parent.mkdir(parents=True, exist_ok=True)
        helper.write_text("puts ACTUAL_RESEAT_HELPER_LOADED\n")
        r = subprocess.run(["tclsh", str(script)], text=True, capture_output=True)
        assert r.returncode == 0 and "ACTUAL_RESEAT_HELPER_LOADED" not in r.stdout      # opt-in: not even sourced
        import os
        r = subprocess.run(["tclsh", str(script)], text=True, capture_output=True, env=dict(os.environ, OT_CTS_TRUNK_RESEAT="1"))
        assert r.returncode == 0 and "ACTUAL_RESEAT_HELPER_LOADED" in r.stdout
        helper.unlink()
        r = subprocess.run(["tclsh", str(script)], text=True, capture_output=True, env=dict(os.environ, OT_CTS_TRUNK_RESEAT="1"))
        assert r.returncode != 0 and "OT_CTS_RESEAT" in r.stderr                         # asked for and missing: fail closed


def test_kit_stage_ships_the_helper():
    src = (REPO / "tools/die_plan/kit_modes.py").read_text()
    assert '_common_flow("cts_trunk_reseat.tcl")' in src
