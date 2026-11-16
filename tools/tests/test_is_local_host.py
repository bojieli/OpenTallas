"""FLOW-HEALTH-1 11-15 (COORD): the ingest and the counter's per-host scan read local paths for the host they run on (no ssh to itself)"""
import importlib.util
import pathlib
import sys

T = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(T))
import release_tree_plan as rtp  # noqa: E402

spec = importlib.util.spec_from_file_location("ssi", str(T / "signed_store_ingest.py"))
ssi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssi)


def test_is_local_host(tmp_path, monkeypatch):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/fleet_hosts.tsv").write_text("intel2\tmy-node\t1.1.1.1\tno\nepyc9\tother-node\t1.1.1.2\tyes\n")
    monkeypatch.setattr(rtp, "COORD_DIR", tmp_path)
    monkeypatch.setattr(rtp.os, "uname", lambda: type("U", (), {"nodename": "my-node"})())
    assert rtp.is_local_host("intel2") and rtp.is_local_host("my-node") and rtp.is_local_host("local") and rtp.is_local_host("localhost")
    assert not rtp.is_local_host("epyc9")


def test_host_cmd_is_local_or_ssh(monkeypatch):
    monkeypatch.setattr(ssi.rtp, "is_local_host", lambda h: h == "hub")
    assert ssi.host_cmd("hub", "echo hi") == ["bash", "-c", "echo hi"]
    assert ssi.host_cmd("epyc7", "echo hi")[-2:] == ["epyc7", "echo hi"]
    assert ssi.host_cmd("epyc7", "echo hi")[0] == "ssh"


def test_scan_host_for_this_machine_does_not_ssh(monkeypatch):
    calls = []
    monkeypatch.setattr(rtp, "is_local_host", lambda h: True)
    monkeypatch.setattr(rtp, "sh", lambda cmd, t, **kw: calls.append(cmd) or type("R", (), {"returncode": 0, "stdout": "OT_WALK_RC=0\n[]\n", "stderr": ""})())
    monkeypatch.setattr(rtp, "sh_ssh", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ssh used for the local host")))
    assert rtp.scan_host("intel2") == []
    assert calls and calls[0][0] == "bash"
