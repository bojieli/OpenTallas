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
