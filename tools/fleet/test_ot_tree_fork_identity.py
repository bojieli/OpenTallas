"""FORK-IDENTITY-1122 (COORD 20:5x, OPUS-FIX-KV-PV-R7 78159f8a): ot-tree-fork --src-host matched an EDITED epyc8 fork to the local
seal copy by manifest hash and forked the unedited tree.  The manifest route is now taken only when SRC provably holds the manifest
content; an edited fork takes the plain fetch of SRC itself, and a source that cannot be checked is refused."""
import hashlib, importlib.machinery, importlib.util, json, pathlib, subprocess, sys

import pytest

H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_tree_fork_identity", str(H / "ot-tree-fork"))
TF = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_tree_fork_identity", l)); l.exec_module(TF)
HASH = "a" * 64


def fake_ssh(probe, verify="OT_VERIFY ok", rc_probe=0):
    calls = []

    def ssh(host, cmd, timeout=600):
        calls.append(cmd)
        if "src-manifest.sha256" in cmd:
            return 0, HASH + "\n"
        if "OT_PROBE" in cmd:
            return rc_probe, probe
        if "python3 -I -c" in cmd:
            return 0, verify + "\n"
        return 0, ""
    return ssh, calls


def route(monkeypatch, tmp_path, ssh):
    seen = []
    monkeypatch.setattr(TF, "ssh_out", ssh)
    monkeypatch.setattr(TF, "check_dst", lambda s, d: "")
    monkeypatch.setattr(TF, "hash_lock", lambda *a, **k: seen.append("manifest route") or None)
    monkeypatch.setattr(TF, "same_tree", lambda *a, **k: seen.append("manifest route") or "/local/seal")
    lines = []
    TF.fork_remote("epyc8", "/src/tree", str(tmp_path / "dst"), dry=True, out=lines.append)
    return seen, lines


def test_edited_fork_never_takes_the_manifest_route(monkeypatch, tmp_path):
    ssh, _ = fake_ssh("OT_FORK\nOT_WRITABLE\nOT_PROBE\n")
    seen, lines = route(monkeypatch, tmp_path, ssh)
    assert seen == [] and any("TREE-FORK EDITED" in x and "fork" in x for x in lines) and any("(no manifest)" in x for x in lines)


def test_writable_tree_modified_takes_plain_fetch(monkeypatch, tmp_path):
    ssh, _ = fake_ssh("OT_WRITABLE\nOT_PROBE\n", verify="OT_VERIFY modified physical/die_plan/kv/plan.json")
    seen, lines = route(monkeypatch, tmp_path, ssh)
    assert seen == [] and any("plan.json" in x for x in lines)


def test_writable_tree_matching_and_sealed_tree_keep_reuse(monkeypatch, tmp_path):
    for probe in ("OT_WRITABLE\nOT_PROBE\n", "OT_PROBE\n"):
        ssh, _ = fake_ssh(probe)
        seen, lines = route(monkeypatch, tmp_path, ssh)
        assert seen and not any("EDITED" in x for x in lines)


def test_probe_failure_refuses(monkeypatch, tmp_path):
    ssh, _ = fake_ssh("", rc_probe=255)
    with pytest.raises(TF.Refused):
        route(monkeypatch, tmp_path, ssh)


def test_verify_script_detects_an_edit(tmp_path):
    t = tmp_path / "t"; (t / "p").mkdir(parents=True)
    (t / "p" / "plan.json").write_text("{}")
    files = {"p/plan.json": hashlib.sha256(b"{}").hexdigest()}
    m = {"main_sha": "x", "scope": [], "overlay": [], "files": files}
    m["manifest_hash"] = TF.manifest_core_hash(m)
    (t / ".src-manifest.json").write_text(json.dumps(m))
    run = lambda: subprocess.run([sys.executable, "-I", "-c", TF.VERIFY_PY, str(t), m["manifest_hash"]], capture_output=True, text=True).stdout
    assert run().strip() == "OT_VERIFY ok"
    (t / "p" / "plan.json").write_text('{"row": 1}')
    assert run().strip() == "OT_VERIFY modified p/plan.json"
