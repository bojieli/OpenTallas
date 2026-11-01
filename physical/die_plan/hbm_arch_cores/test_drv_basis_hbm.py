"""HBM-CORES-KITS-20: HBM kits carry the shared core-flow DRV basis (fanout cap + SLEW/CAP margin), opt-out by 0."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
SRC = (HERE / "gen_core_kit_hbm.py").read_text()


def test_defaults_match_kv_basis():
    assert 'ap.add_argument("--max-fanout", type=int, default=64' in SRC
    assert 'ap.add_argument("--slew-margin", type=float, default=20.0' in SRC


def test_config_lines_and_hook():
    assert '"export PRE_RESIZE_TCL = /work/max_fanout.tcl"] if drv_fanout(a)' in SRC
    assert 'f"export SLEW_MARGIN = {a.slew_margin:g}", f"export CAP_MARGIN = {a.slew_margin:g}"' in SRC
    assert '("source /work/max_fanout.tcl\\n" if fo else "")' in SRC


def test_drv_fanout_opt_out():
    spec = importlib.util.spec_from_file_location("g", HERE / "gen_core_kit_hbm.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    assert g.drv_fanout(argparse.Namespace(max_fanout=64)) == 64
    assert g.drv_fanout(argparse.Namespace(max_fanout=0)) == 0
    assert g.drv_fanout(argparse.Namespace()) == 0


def test_grt_hold_pad_hb4_default_on():
    """HBM-CORES-KITS-40 11-01 class C3: every HBM core kit pads GRT hold repair with HB4 (hold_pad_hb4.tcl)."""
    assert 'shutil.copyfile(HOLD_PAD_HB4, kd / "hold_pad_hb4.tcl")' in SRC
    assert '"source /work/hold_pad_hb4.tcl\\n"' in SRC
    spec = importlib.util.spec_from_file_location("g", HERE / "gen_core_kit_hbm.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    assert g.HOLD_PAD_HB4.is_file()
    assert "unset_dont_use" in g.HOLD_PAD_HB4.read_text()
