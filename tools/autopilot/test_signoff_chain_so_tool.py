"""FABLE-CLOSURE 1935 lever 5: sign-off uses the current signoff.py family, staged copy + rename, sha logged"""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import signoff_chain as SC


def test_stage_signoff_tool_replaces_the_kit_copy_and_logs(tmp_path, capsys):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "signoff.py").write_text("# old kit copy\n")
    (kit / "kit_hook.tcl").write_text("keep\n")
    rec = SC.stage_signoff_tool(kit, source=HERE.parent / "die_plan")
    assert rec and "signoff.py" in rec["replaced"] and rec["kit_copy_was"] != rec["signoff_py"]
    assert (kit / "signoff.py").read_bytes() == (HERE.parent / "die_plan" / "signoff.py").read_bytes()
    assert (kit / "kit_hook.tcl").read_text() == "keep\n"
    assert not list(kit.glob(".so_stage.*"))
    assert json.loads((kit / "signoff_tool.jsonl").read_text().splitlines()[-1])["signoff_py"] == rec["signoff_py"]
    assert "SIGNOFF_TOOL given: signoff.py" in capsys.readouterr().out


def test_stage_signoff_tool_opt_out(tmp_path, capsys):
    (tmp_path / "signoff.py").write_text("# kit\n")
    (tmp_path / ".keep_kit_signoff").touch()
    assert SC.stage_signoff_tool(tmp_path, source=HERE.parent / "die_plan") is None
    assert (tmp_path / "signoff.py").read_text() == "# kit\n"
    assert "SIGNOFF_TOOL KIT copy kept" in capsys.readouterr().out
