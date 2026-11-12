"""KW-FIX-45 11-11: opt-in OT_GRT_NONPORT_HOLD chain for gen_phys type kits (default unchanged)."""
import importlib.util
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
src = (HERE / "gen_phys.py").read_text()


def load_helper():
    ns = {"re": __import__("re"), "shutil": __import__("shutil"), "Path": Path, "__file__": str(HERE / "gen_phys.py")}
    start = src.index("def grt_nonport_hold_chain(")
    end = src.index("def macro_ff_repair_stage(")
    exec(compile(src[start:end], "gen_phys_helper", "exec"), ns)
    return ns["grt_nonport_hold_chain"]


def test_chain_takes_the_last_effective_pre_grt_and_appends(tmp_path):
    chain = load_helper()
    kd = tmp_path / "kit"; kd.mkdir()
    (kd / "config.mk").write_text("export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre.tcl\nexport X = 1\n"
                                  "override export PRE_GLOBAL_ROUTE_TCL = /work/macro_ff_pre_grt.tcl\n")
    tools = tmp_path / "tools"; tools.mkdir(); (tools / "grt_nonport_hold.tcl").write_text("# hook\n")
    base = chain(kd, tool_dir=tools)
    assert base == "/work/macro_ff_pre_grt.tcl"
    assert (kd / "grt_pre_nonport.tcl").read_text().splitlines()[1:] == ["source /work/macro_ff_pre_grt.tcl",
                                                                         "source /work/grt_nonport_hold.tcl"]
    assert (kd / "grt_nonport_hold.tcl").read_text() == "# hook\n"
    cfg = (kd / "config.mk").read_text().splitlines()
    assert cfg[-2:] == ["override export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre_nonport.tcl", "export OT_GRT_NONPORT_HOLD = 1"]


def test_no_pre_grt_refuses(tmp_path):
    chain = load_helper()
    kd = tmp_path / "kit"; kd.mkdir()
    (kd / "config.mk").write_text("export X = 1\n")
    with pytest.raises(SystemExit):
        chain(kd, tool_dir=tmp_path)


def test_only_called_under_the_opt_in():
    assert 'if os.environ.get("OT_GRT_NONPORT_HOLD") == "1":' in src
    assert src.count("grt_nonport_hold_chain(kd)") == 1
