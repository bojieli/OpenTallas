"""WF-1 11-14: allow-congestion stays on for every global_route / repair call of the GRT stage (S81-CORES-2 hook as the flow default)."""
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SH = (ROOT / "physical/common_flow/grt183_make.sh").read_text()
BLOCK = SH[SH.index("# OT_GRT_ALLOW_CONG_HOOK begin"):SH.index("# OT_GRT_ALLOW_CONG_HOOK end")]
ORFS = "global_route_prelude\n  source_step_tcl PRE GLOBAL_ROUTE\nglobal_route {*}$all_args\n"


def apply(tmp_path, cfg, env=""):
    w, s = tmp_path / "work", tmp_path / "global_route.tcl"
    w.mkdir(exist_ok=True)
    (w / "config.mk").write_text(cfg)
    s.write_text(ORFS)
    r = subprocess.run(["bash", "-c", f'W="{w}"; S="{s}"; {env}\n' + BLOCK], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return w, s


def test_hook_written_and_sourced_when_the_kit_allows_congestion(tmp_path):
    w, s = apply(tmp_path, "export GLOBAL_ROUTE_ARGS = -congestion_iterations 30 -allow_congestion\n")
    assert (w / "grt_allow_cong.tcl").is_file() and "::grt::set_allow_congestion" in (w / "grt_allow_cong.tcl").read_text()
    t = s.read_text()
    assert t.index("OT_GRT_ALLOW_CONG_HOOK") < t.index("source_step_tcl PRE GLOBAL_ROUTE")
    subprocess.run(["bash", "-c", f'W="{w}"; S="{s}"\n' + BLOCK], check=True, capture_output=True, timeout=30)
    assert s.read_text() == t                                    # idempotent


def test_nothing_changes_without_allow_congestion(tmp_path):
    w, s = apply(tmp_path, "export X = 1\n")
    assert s.read_text() == ORFS and not (w / "grt_allow_cong.tcl").exists()


def test_env_flag_enables_it(tmp_path):
    w, s = apply(tmp_path, "export X = 1\n", env="OT_GRT_ALLOW_CONGESTION=1")
    assert "OT_GRT_ALLOW_CONG_HOOK" in s.read_text()


def test_hook_keeps_allow_congestion_on_in_tclsh(tmp_path):
    tcl = shutil.which("tclsh")
    if not tcl:
        return
    w, s = apply(tmp_path, "export GLOBAL_ROUTE_ARGS = -allow_congestion\n")
    prelude = ('namespace eval ::grt {variable ac 0; proc set_allow_congestion {v} {variable ac; set ac $v; puts "AC=$v"}}\n'
               'proc global_route {args} {puts "GR $args"; ::grt::set_allow_congestion 0}\n'
               'proc repair_timing {args} {puts "RT ac=$::grt::ac"}\nproc repair_design {args} {puts "RD ac=$::grt::ac"}\n')
    f = tmp_path / "t.tcl"
    f.write_text(prelude + f"source {w}/grt_allow_cong.tcl\nglobal_route -end_incremental\nrepair_timing\nrepair_design\n")
    r = subprocess.run([tcl, str(f)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "GR -end_incremental -allow_congestion" in r.stdout and "RT ac=1" in r.stdout and "RD ac=1" in r.stdout


def test_repair_antennas_keeps_and_rearms_allow_congestion(tmp_path):
    """KIT-OPS-5 11-14 (FABLE-KVOVF): repair_antennas clears the router state (EST-0005 on the next estimate); the hook arms it before and re-arms it after."""
    tcl = shutil.which("tclsh")
    if not tcl:
        return
    w, s = apply(tmp_path, "export GLOBAL_ROUTE_ARGS = -allow_congestion\n")
    prelude = ('namespace eval ::grt {variable ac 0; proc set_allow_congestion {v} {variable ac; set ac $v}}\n'
               'proc global_route {args} {}\nproc repair_timing {args} {}\nproc repair_design {args} {}\n'
               'proc repair_antennas {args} {puts "RA before ac=$::grt::ac"; set ::grt::ac 0}\n')
    f = tmp_path / "t2.tcl"
    f.write_text(prelude + f"source {w}/grt_allow_cong.tcl\nset ::grt::ac 0\nrepair_antennas -iterations 3\nputs \"AFTER ac=$::grt::ac\"\n")
    r = subprocess.run([tcl, str(f)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "RA before ac=1" in r.stdout and "AFTER ac=1" in r.stdout
