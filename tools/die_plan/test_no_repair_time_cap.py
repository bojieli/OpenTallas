"""WF-1 11-14 (OWNER: delete the conservative limits): no repair wall-clock cap ends a post-GRT repair or kills the GRT stage with exit 21."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def code(rel):
    return "\n".join(ln for ln in (ROOT / rel).read_text().splitlines() if not ln.strip().startswith("#"))


def test_hold_guard_wall_cap_only_logs():
    for rel in ("tools/die_plan/hold_guard_grt.tcl", "tools/orfs_hold_mm.tcl"):
        t = code(rel)
        assert "OT_HOLD_TIMELOG" in t and "NO CAP" in t, rel
        assert not re.search(r"hold repair over[^\n]*\n\s*break", t), rel
        assert "NEEDS_RTL stage=grt reason=hold repair over" not in t and 'ot_hold_window_report "hold repair over' not in t, rel


def test_grt_wrapper_does_not_stop_the_stage_for_hold_structural():
    t = code("physical/common_flow/grt183_make.sh")
    m = re.search(r"ff_check\(\) \{.*?\n\}", t, re.S)
    assert m and "gstop=hold_structural" not in m.group(0) and "OT_HOLD_STRUCTURAL_LOGGED" in m.group(0)
    assert "gstop=timecap" not in t


def test_ff_check_behaviour(tmp_path):
    import subprocess
    body = re.search(r"ff_check\(\) \{.*?\n\}", (ROOT / "physical/common_flow/grt183_make.sh").read_text(), re.S).group(0)
    ff = tmp_path / "failfast_rules.py"
    for line, want_stop in (("OT_HOLD_STRUCTURAL stage=grt failfast class=HOLD_STRUCTURAL: x", False), ("OT_DRT_NO_PROGRESS stage=route x", True)):
        ff.write_text(f"print({line!r})\n")
        script = f'W={tmp_path}; T0=0; FF={ff}\n{body}\ngstop=""\nff_check; echo "rc=$? gstop=$gstop"\n'
        out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30).stdout
        assert (f"rc=0 gstop=drt_no_progress" in out) == want_stop, out
