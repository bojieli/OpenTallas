"""Portable proof staging must preserve exact physical inputs and same-tag qualification."""
import json
import shutil
from pathlib import Path
import pytest
import signed_child_evidence as E
import test_signed_child_etm as T


def fixture(tmp_path):
    kit, lib = T.build(tmp_path)
    source = tmp_path / "view"
    source.mkdir()
    prov = json.loads((lib.parent / "child.provenance.json").read_text())
    for name, path in (("provenance.json", lib.parent / "child.provenance.json"),
                       ("PROVENANCE.json", tmp_path / "child_resign/PROVENANCE.json"),
                       ("signoff.json", tmp_path / "child_resign/signoff/signoff.json"),
                       ("lec.json", tmp_path / "child_resign/lec/lec.json")):
        shutil.copyfile(path, source / name)
    for co in ("tt", "ff"):
        name = f"child_{co}.lib"
        (source / name).write_text(T.LIB)
        (lib.parent / name).write_text(T.LIB)
        prov["export"]["files_sha256"][name] = T.sha(source / name)
    (source / "provenance.json").write_text(json.dumps(prov))
    (lib.parent / "child.provenance.json").unlink()
    return source, lib.parent


def test_relocated_evidence_qualifies_without_changing_physical_inputs(tmp_path):
    source, macros = fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in macros.glob("*.lib")}
    E.stage_signed_child_evidence(source, "child", macros)
    E.stage_signed_child_evidence(source, "child", macros)
    relocated = tmp_path / "relocated"
    macros.rename(relocated)
    shutil.rmtree(source)
    shutil.rmtree(tmp_path / "child_resign")
    assert T.coverage(relocated / "child_tt.lib")["verdict"] == "PASS"
    assert T.coverage(relocated / "child_tt.lib", "flow-other")["verdict"] == "NOT RUN"
    assert {p.name: p.read_bytes() for p in relocated.glob("*.lib")} == before


def test_changed_signoff_is_rejected(tmp_path):
    source, macros = fixture(tmp_path)
    (source / "signoff.json").write_text(json.dumps(dict(verdict="SIGNED", changed=True)))
    with pytest.raises(ValueError, match="signoff hash"):
        E.stage_signed_child_evidence(source, "child", macros)


def test_changed_consumed_library_is_rejected(tmp_path):
    source, macros = fixture(tmp_path)
    (macros / "child_tt.lib").write_text(T.LIB + "\n/* changed */\n")
    with pytest.raises(ValueError, match="consumed library"):
        E.stage_signed_child_evidence(source, "child", macros)
