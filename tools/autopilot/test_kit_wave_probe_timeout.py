"""PROBE-TIMEOUT-1124: a systemctl / ssh TimeoutExpired in the wave driver is INFRA (uncharged backoff retry, no fail_key), and place_wait survives a slow probe."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

TB = ("Traceback (most recent call last) TimeoutExpired: Command '['systemctl', '--user', 'is-active', 'kwp-2d139fd01ff11b141a5a']' "
      "timed out after 60 seconds")


def test_probe_timeout_is_infra_and_requeues_free():
    cls, why = KW.classify("pipeline", TB)
    assert cls == "INFRA" and "probe timeout" in why
    assert KW.probe_timeout_line("TimeoutExpired: Command '['ssh', '-o', 'BatchMode=yes', 'epyc9', 'ls']' timed out after 30 seconds")
    assert KW.probe_timeout_line("TimeoutExpired: Command '['timeout', '300', 'ssh', 'x']' timed out")
    assert not KW.probe_timeout_line("TimeoutExpired: Command '['openroad', '-exit', 'x.tcl']' timed out")      # a tool's own timeout stays a tool failure
    rec = {"status": "FAIL", "class": cls, "reason": why, "dir": "/nonexistent"}
    assert KW.infra_retry_kind(rec) == "probe-timeout"
    assert KW.is_host_fail(cls, why) or cls == "INFRA"


def test_unit_probe_retries_then_unknown(monkeypatch):
    calls = []

    def fake(argv, **kw):
        calls.append(kw.get("timeout"))
        if len(calls) < 3:
            raise subprocess.TimeoutExpired(argv, kw.get("timeout"))
        return subprocess.CompletedProcess(argv, 0, stdout="active\n", stderr="")
    monkeypatch.setattr(KW.subprocess, "run", fake)
    monkeypatch.setattr(KW.time, "sleep", lambda s: None)
    assert KW.unit_probe("kwp-x") == "active" and calls == [60, 120, 240]
    calls.clear()

    def slow(argv, **kw):
        calls.append(kw.get("timeout"))
        raise subprocess.TimeoutExpired(argv, kw.get("timeout"))
    monkeypatch.setattr(KW.subprocess, "run", slow)
    assert KW.unit_probe("kwp-x") is None and len(calls) == 3
