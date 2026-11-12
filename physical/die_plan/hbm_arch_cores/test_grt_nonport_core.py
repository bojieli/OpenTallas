"""KW-FIX-45 11-11: opt-in --grt-nonport-hold for the HBM core kit generator (default unchanged)."""
import importlib.util
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_nph", HERE / "gen_core_kit_hbm.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_chain_after_the_kits_own_pre_grt(tmp_path):
    cfg = ["export X = 1", "export PRE_GLOBAL_ROUTE_TCL = /work/core_grt_pre.tcl"]
    lines = m.grt_nonport_hold_setup(tmp_path, cfg)
    assert lines == ["override export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre_nonport.tcl", "export OT_GRT_NONPORT_HOLD = 1"]
    assert (tmp_path / "grt_pre_nonport.tcl").read_text().splitlines()[1:] == ["source /work/core_grt_pre.tcl",
                                                                              "source /work/grt_nonport_hold.tcl"]
    assert (tmp_path / "grt_nonport_hold.tcl").is_file()


def test_takes_the_last_effective_assignment(tmp_path):
    cfg = ["export PRE_GLOBAL_ROUTE_TCL = /work/a.tcl", "override export PRE_GLOBAL_ROUTE_TCL = /work/b.tcl"]
    m.grt_nonport_hold_setup(tmp_path, cfg)
    assert "source /work/b.tcl" in (tmp_path / "grt_pre_nonport.tcl").read_text()


def test_no_pre_grt_refuses(tmp_path):
    with pytest.raises(SystemExit):
        m.grt_nonport_hold_setup(tmp_path, ["export X = 1"])


def test_flag_default_off_and_only_used_under_the_flag():
    src = (HERE / "gen_core_kit_hbm.py").read_text()
    assert '"--grt-nonport-hold", action="store_true"' in src
    assert src.count("cfg += grt_nonport_hold_setup(kd, cfg)") == 1 and "if a.grt_nonport_hold:" in src
