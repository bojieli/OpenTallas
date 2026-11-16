"""FLOW-HEALTH-1 11-16: the remote gate is placed only on hosts that hold its script, and clones the mirror by IP"""
import importlib.machinery
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    import os
    os.environ.pop("MQ_GATE_REMOTE", None)          # the gate itself runs with the queue environment: test the built-in default
    loader = importlib.machinery.SourceFileLoader("otmq_gr", str(HERE / "ot-merge-queue"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def test_gate_remote_declares_its_script_and_names_no_localhost():
    m = load()
    cmd = m.GATE_REMOTE.format(key="claude/x@abc")
    assert f"--needs {m.GATE_SCRIPT}" in cmd and m.GATE_SCRIPT in cmd.split("--")[-1]
    hosts = re.search(r"--hosts (\S+)", cmd).group(1).split(",")
    assert "localhost" not in hosts and "intel2" not in hosts and hosts == ["epyc2", "epyc9"]


def test_mirror_is_cloned_by_ip_not_by_the_intel2_alias():
    s = (HERE / "ot-gate-remote").read_text()
    assert "M=intel2:" not in s and "ubuntu@185.8.106.226:" in s
    assert 'hostname -s)" = tolerant-swine ] && M=/srv/opentallas-scratch2/git/OpenTallas.git' in s
