"""FLEET-GUARD-1122 (FABLE-FLOW-0600 E1): no test starts real fleet work; fakes and the opt-in still run"""
import os
import subprocess
import sys

import pytest

C = sys.modules[[m for m in sys.modules if m.endswith("conftest") and hasattr(sys.modules[m], "fleet_refusal")][0]]


@pytest.mark.parametrize("argv", [["ssh", "-n", "epyc9", "true"], ["timeout", "60", "nice", "-n", "10", "ssh", "h", "x"],
                                  ["systemd-run", "--user", "true"], ["env", "A=1", "ot-run", "--status"]])
def test_real_fleet_tools_are_refused(argv, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/local/bin:/usr/bin:/bin:" + os.path.expanduser("~/.local/bin"))
    monkeypatch.delenv("OT_TEST_FLEET_OK", raising=False)
    if not C.fleet_refusal(argv):
        pytest.skip(f"{C._program(argv)} not installed here")
    r = subprocess.run(argv, capture_output=True, text=True)              # stubbed: fails like an unreachable host, nothing reaches the fleet
    assert r.returncode == 255 and "FleetUnderTest" in r.stderr
    monkeypatch.setenv("OT_TEST_FLEET_STRICT", "1")
    with pytest.raises(C.FleetUnderTest):
        subprocess.run(argv, capture_output=True)


def test_fake_on_tmp_path_and_opt_in_run(tmp_path, monkeypatch):
    fake = tmp_path / "ssh"
    fake.write_text("#!/bin/sh\necho FAKE $@\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    assert subprocess.run(["ssh", "h", "x"], capture_output=True, text=True).stdout.strip() == "FAKE h x"
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("OT_TEST_FLEET_OK", "1")
    assert C.fleet_refusal(["ssh", "h"]) == ""
    assert C.fleet_refusal(["python3", "-c", "1"]) == "" and C.fleet_refusal(["git", "status"]) == ""
    assert os.environ.get("OT_UNDER_TEST") == "1"
