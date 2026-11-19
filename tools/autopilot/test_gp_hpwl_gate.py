"""PLACE-HPWL gate (FABLE-PD-S81-STRIP fix 1): gp_noconverge.py --hpwl-gate, its PRE_RESIZE hook and the gen_phys switch.
Numbers are the S81 strip leaves of 11-16: t47 table minimum 1.100241e7 um, GPL exit measured 2.578385e7 (2.34 x);
t28 1.944146e7 / 1.958761e7 (1.008 x).
11-19: growth is counted from the first row at overflow <= 0.30 (t47: the 0.2222 row, 1.159559e7 -> 2.22 x)."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import gp_noconverge as G  # noqa: E402

LOG = """[INFO GPL-0100] Timing-driven iteration 1/2, virtual: true.
        0 |   0.6650 |  1.104271e+07 |   +0.00% |  2.10e-14 |
      340 |   0.4659 |  1.100241e+07 |   -0.45% |  1.65e-07 |
      370 |   0.2222 |  1.159559e+07 |   +4.29% |  6.07e-07 |
[INFO GPL-0101]    Iter: 379, overflow: 0.189, keep resizer changes at: 0.25, HPWL: 13723756489
Iteration |   Area    | Resized | Buffers | Nets repaired | Remaining
        0 |     +0.0% |       0 |       0 |             0 |    169924
      390 |   0.2189 |  2.229109e+07 |  +46.22% |  5.43e-07 |
      442 |   0.0991 |  2.578317e+07 |          |  2.81e-06 |
"""


def test_table_minimum_ignores_resizer_rows():
    assert G.hpwl_min(LOG) == pytest.approx(1.100241e7)
    assert G.hpwl_min("no table") is None


def test_t47_divergence_stops_t28_passes():
    v, why = G.hpwl_gate(LOG, 2.578385e7)
    assert v == "STOP" and "PLACE-HPWL" in why and "2.22 x" in why and "run minimum 1.1002e+07" in why
    v, why = G.hpwl_gate(LOG, 1.02 * 1.100241e7)
    assert v == "OK"
    assert G.hpwl_gate(LOG, 1.5e7, ratio=1.3)[0] == "OK"          # 1.29 x the converged row (was 1.36 x the run minimum)
    assert G.hpwl_gate(LOG, 1.55e7, ratio=1.3)[0] == "STOP"       # 1.34 x
    assert G.hpwl_gate("", 2.6e7)[0] == "OK"                     # nothing to judge: unchanged flow


def test_cli_exit_code_and_marker(tmp_path, capsys):
    log = tmp_path / "3_3_place_gp.log"
    log.write_text(LOG)
    mk = tmp_path / "FAIL_PLACE_HPWL"
    assert G.main(["--hpwl-gate", str(log), "--exit-hpwl", "2.578385e7", "--marker", str(mk)]) == 3
    assert "PLACE-HPWL" in mk.read_text()
    assert G.main(["--hpwl-gate", str(log), "--exit-hpwl", "1.1e7"]) == 0
    assert G.main(["--hpwl-gate", str(tmp_path / "missing.log"), "--exit-hpwl", "1e7"]) == 0
    assert "NOT RUN" in capsys.readouterr().out


def test_hook_measures_and_calls_checker():
    t = (HERE.parent / "die_plan" / "gp_noconverge_gate.tcl").read_text()
    assert "OT_GPL_HPWL_RATIO" in t and "--hpwl-gate $gpnc_log --exit-hpwl $gphw_um" in t
    assert "FAIL_PLACE_HPWL" in t and "error $gphw_out" in t


def test_gen_phys_ratio_default_s81_only(monkeypatch):
    import gen_phys as P
    monkeypatch.delenv("OT_GPL_HPWL_RATIO", raising=False)
    assert P.gpl_hpwl_ratio("s81") == 1.3
    assert P.gpl_hpwl_ratio("qwen_kvsys") is None and P.gpl_hpwl_ratio(None) is None
    assert P.gpl_hpwl_ratio("s81_head") is None          # HEAD-PLAN-R4 11-17: S81 by exact name, not the s81 prefix
    monkeypatch.setenv("OT_GPL_HPWL_RATIO", "1.5")
    assert P.gpl_hpwl_ratio("hbm") == 1.5
    monkeypatch.setenv("OT_GPL_HPWL_RATIO", "0")
    assert P.gpl_hpwl_ratio("s81") is None
    monkeypatch.setenv("OT_GPL_HPWL_RATIO", "0.9")
    with pytest.raises(ValueError):
        P.gpl_hpwl_ratio("s81")


def test_install_emits_ratio_for_s81(tmp_path, monkeypatch):
    import gen_phys as P
    monkeypatch.delenv("OT_GPL_HPWL_RATIO", raising=False)
    monkeypatch.delenv("OT_PLACE_MAX_FANOUT", raising=False)
    cfg = P.install_gp_noconverge_gate(tmp_path, [], "s81")
    assert "export OT_GPL_HPWL_RATIO = 1.3" in cfg
    assert (tmp_path / "gp_noconverge.py").is_file() and (tmp_path / "gp_noconverge_gate.tcl").is_file()
    assert not any("OT_GPL_HPWL_RATIO" in c for c in P.install_gp_noconverge_gate(tmp_path, [], "qwen_kvsys"))


def test_gpl_overflow_default_s81_only(tmp_path, monkeypatch):
    import gen_phys as P
    for k in ("OT_GPL_OVERFLOW", "OT_GPL_HPWL_RATIO", "OT_PLACE_MAX_FANOUT"):
        monkeypatch.delenv(k, raising=False)
    assert P.gpl_overflow("s81") == 0.2 and P.gpl_overflow("qwen_kvsys") is None
    assert "export GLOBAL_PLACEMENT_ARGS = -overflow 0.2" in P.install_gp_noconverge_gate(tmp_path, [], "s81")
    assert not any("GLOBAL_PLACEMENT_ARGS" in c for c in P.install_gp_noconverge_gate(tmp_path, [], "hbm"))
    monkeypatch.setenv("OT_GPL_OVERFLOW", "0")
    assert P.gpl_overflow("s81") is None
    monkeypatch.setenv("OT_GPL_OVERFLOW", "0.15")
    assert P.gpl_overflow("hbm") == 0.15
    monkeypatch.setenv("OT_GPL_OVERFLOW", "1.5")
    with pytest.raises(ValueError):
        P.gpl_overflow("s81")
