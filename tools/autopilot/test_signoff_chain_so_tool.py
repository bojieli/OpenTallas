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


def test_legacy_route_kit_receives_nominal_bundle(tmp_path):
    kit = tmp_path / "legacy"
    kit.mkdir()
    source = HERE.parent / "die_plan"
    expected = source / "nomcap_libs"
    record = SC.stage_signoff_tool(kit, source=source)
    assert "nomcap_libs" in record["replaced"]
    for path in expected.iterdir():
        assert (kit / "nomcap_libs" / path.name).read_bytes() == path.read_bytes()
    assert SC.stage_signoff_tool(kit, source=source)["replaced"] == []


def test_native_nominal_libraries_are_preserved(tmp_path):
    kit = tmp_path / "native"
    native = kit / "nomcap"
    native.mkdir(parents=True)
    manifest = native / "MANIFEST.json"
    manifest.write_text("kit-pinned manifest")
    record = SC.stage_signoff_tool(kit, source=HERE.parent / "die_plan")
    assert record
    assert manifest.read_text() == "kit-pinned manifest"
    assert not (kit / "nomcap_libs").exists()


def test_stage_signoff_tool_repairs_retained_pin_audit_without_replacing_it(tmp_path):
    source = HERE.parent / "die_plan"
    audit = tmp_path / "pin_audit.py"
    audit.write_text("# retained pin audit\n")
    record = SC.stage_signoff_tool(tmp_path, source=source)
    helper = tmp_path / "native_pin_contract.py"
    assert helper.name in record["replaced"]
    assert helper.read_bytes() == (source / helper.name).read_bytes()
    assert audit.read_text() == "# retained pin audit\n"
    helper.write_text("# kit helper\n")
    assert helper.name not in SC.stage_signoff_tool(tmp_path, source=source)["replaced"]
    assert helper.read_text() == "# kit helper\n"
