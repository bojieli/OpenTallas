"""Cover sealed source checks and the real kernel copy-up path."""
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import row_gate_cow as cow

RT = Path(__file__).resolve().parents[2]
FLEET = runpy.run_path(str(RT / "tools/fleet/ot-tree-fork"))


def sealed(tree, *, external=False):
    tree.mkdir()
    (tree / "physical").mkdir()
    (tree / "physical/base.json").write_text("original\n")
    (tree / "physical/asbuilt.json").write_text("{}\n")
    (tree / "alias").symlink_to(tree / "physical/base.json")
    if external:
        (tree / "physical/die_plan").symlink_to("/etc", target_is_directory=True)
    m = {"main_sha": "test", "scope": {}, "overlay": {}, "files": {
        str(p.relative_to(tree)): FLEET["file_hash"](p)
        for p in tree.rglob("*") if p.is_file()
    }}
    digest = FLEET["manifest_core_hash"](m)
    (tree / ".src-manifest.json").write_text(json.dumps(dict(m, manifest_hash=digest)))
    (tree / ".src-manifest.sha256").write_text(digest)
    FLEET["make_ro_tree"](str(tree))
    return digest


def materialized_view(tmp_path, *, external=False):
    src, view = tmp_path / "source", tmp_path / "view"
    digest = sealed(src, external=external)
    shutil.copytree(src, view, symlinks=True)
    return src, view, digest


def test_copyup_preparation_preserves_lower_and_relocates_links(tmp_path):
    src, view, digest = materialized_view(tmp_path)
    facts = cow.prepare(src, view, RT, "physical/base.json", "physical/asbuilt.json", "TEST",
                        lambda *_: (None, []))
    assert facts["src_manifest_hash"] == digest
    assert (view / "alias").resolve() == view / "physical/base.json"
    (view / "physical/new.json").write_text("candidate\n")
    assert not (src / "physical/new.json").exists()
    assert not (src / ".fork.json").exists()
    assert json.loads((view / ".fork.json").read_text())["method"] == "bwrap-overlay"


def test_unsealed_and_external_plan_links_are_rejected(tmp_path):
    src, view, _ = materialized_view(tmp_path, external=True)
    with pytest.raises(ValueError, match="refused source entries"):
        cow.prepare(src, view, RT, "physical/base.json", "physical/asbuilt.json", "TEST",
                    lambda *_: (None, []))
    src.chmod(0o755)
    with pytest.raises(ValueError, match="immutable sealed"):
        cow.prepare(src, view, RT, "physical/base.json", "physical/asbuilt.json", "TEST",
                    lambda *_: (None, []))


def test_mount_private_lower(tmp_path):
    bwrap = shutil.which("bwrap")
    if not bwrap or subprocess.run([bwrap, "--unshare-user", "--ro-bind", "/", "/", "true"],
                                   capture_output=True).returncode:
        pytest.skip("bubblewrap user namespace unavailable")
    if tmp_path.is_relative_to("/tmp"):
        pytest.skip("test requires pytest --basetemp on scratch, outside inner /tmp")
    src, out = tmp_path / "source", tmp_path / "output"
    sealed(src)
    outside = tmp_path / "outside"
    outside.write_text("unchanged")
    command = """
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
import row_gate_cow as cow
src, out, rt, outside = [Path(p) for p in sys.argv[2:]]
assert cow.mounted(out)
view = out / 'tree'
cow.prepare(src, view, rt, 'physical/base.json', 'physical/asbuilt.json', 'TEST',
            lambda *_: (None, []))
case = view / 'physical/base.json'
case.chmod(0o644)
case.write_text('candidate')
assert (view / 'alias').read_text() == 'candidate'
try:
    outside.write_text('tamper')
except OSError:
    pass
else:
    raise AssertionError('outside path was writable')
(out / 'receipt.json').write_text(case.read_text())
"""
    assert cow.run(["-c", command, str(Path(cow.__file__).parent), str(src), str(out), str(RT), str(outside)],
                   src, out) == 0
    assert (src / "physical/base.json").read_text() == "original\n"
    assert outside.read_text() == "unchanged"
    assert (out / "receipt.json").read_text() == "candidate"
    assert not (out / "tree").exists()


def test_light_choice_falls_back_unless_eligible(tmp_path, monkeypatch):
    """P-POSTPUBLISH-DISK: light = overlay only for a scoped, sealed, yosys-pinned, non-keep gate; every other case = ordinary fork."""
    src = tmp_path / "source"
    sealed(src)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    env = {"OT_BIND_YOSYS": "/bin/true", "PATH": "/usr/bin:/bin"}
    use, why = cow.light_choice(src, RT, "auto", False, env)
    if shutil.which("bwrap"):
        assert use and why == "bwrap-overlay"
    assert cow.light_choice(src, RT, "all", False, env)[0] is False
    assert cow.light_choice(src, RT, "auto", True, env)[0] is False
    assert cow.light_choice(src, RT, "auto", False, {"PATH": "/usr/bin:/bin"})[0] is False
    fork = tmp_path / "fork"
    shutil.copytree(src, fork, symlinks=True)
    fork.chmod(0o755)
    (fork / ".fork.json").write_text("{}")
    assert cow.light_choice(fork, RT, "auto", False, env)[0] is False
    plain = tmp_path / "plain"
    plain.mkdir()
    assert cow.light_choice(plain, RT, "auto", False, env)[0] is False


def test_light_is_on_by_default_and_env_zero_turns_it_off():
    """COORD 11-26: --light is the default; OT_ROW_GATE_LIGHT=0 opts out"""
    src = (Path(__file__).resolve().parent / "row_gate.py").read_text()
    assert 'default=os.environ.get("OT_ROW_GATE_LIGHT") != "0"' in src
    assert "DEFAULT ON" in src
