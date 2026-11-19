"""FABLE-FLOW-1555 (C): the late ECO takes eco_loop.py + post_route_drv from rt/current at run time"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import signoff_chain as SC


def test_late_eco_prefers_rt_current_and_falls_back_loudly(tmp_path, capsys, monkeypatch):
    cur = tmp_path / "rt/tools/die_plan"
    cur.mkdir(parents=True)
    (cur / "eco_loop.py").write_text("def run_loop(kit, record, **k):\n    return {'verdict': 'X', 'tools': str(k['tools'])}\ndef summary(r):\n    return 's'\n")
    res = SC.late_eco("/k", {}, "r", 1, 1, current=lambda: (cur / "eco_loop.py", "abc123"))
    assert res["tools"] == str(cur) and "LATE_ECO_TOOLS rt abc123" in capsys.readouterr().out
    monkeypatch.setattr(SC, "eco_tool", lambda: cur / "eco_loop.py")
    SC.late_eco("/k", {}, "r", 1, 1, current=lambda: (None, "fetch from hub rc 255"))
    assert "LATE_ECO_TOOLS SKIPPED rt/current (fetch from hub rc 255)" in capsys.readouterr().out


def test_current_eco_tool_reads_a_visible_rt_current(tmp_path, monkeypatch):
    rt = tmp_path / "rt"
    (rt / "deadbeef/tools/die_plan").mkdir(parents=True)
    (rt / "deadbeef/tools/die_plan/eco_loop.py").write_text("")
    (rt / "current").symlink_to("deadbeef")
    monkeypatch.setattr(SC, "RT_ROOT", str(rt))
    tool, sha = SC.current_eco_tool()
    assert sha == "deadbeef" and tool.name == "eco_loop.py"
