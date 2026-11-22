"""FLOW-FLEET-R2 P1: a private run-item driver re-executes itself under systemd-run --user (unit runitem-<item>) unless supervised or opted out."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW      # noqa: E402

PRIV = {"die": "s81", "item": "slice_t5", "private": {"lane": "FAM-X"}}
ARGV = ["python3", "/rt/x/tools/autopilot/kit_wave.py", "run-item", "/w/spec.json", "--goal", "route"]
SSH = "0::/user.slice/user-1000.slice/session-12.scope\n"
ENV = {"PATH": "/bin", "HOME": "/home/u", "OT_LANE": "FAM-X", "KW_FOO": "1", "SECRET": "no", "SSH_CONNECTION": "x"}


def unit(**kw):
    a = dict(env=dict(ENV), cgroup=SSH, cwd="/w")
    a.update(kw)
    return KW.runitem_unit_argv("/w/spec.json", a.pop("sp", PRIV), ARGV, **a)


def test_plain_ssh_shell_gets_a_unit_with_same_args_and_log():
    r = unit(stdout_path="/w/driver.log")
    assert r["unit"] == "runitem-slice_t5" and r["log"] == "/w/driver.log"
    c = r["argv"]
    assert c[:3] == ["systemd-run", "--user", "--quiet"] and "--wait" in c and "--unit=runitem-slice_t5" in c
    assert "--property=StandardOutput=append:/w/driver.log" in c and "--setenv=OT_LANE=FAM-X" in c and "--setenv=KW_FOO=1" in c
    assert not any("SECRET" in x or "SSH_CONNECTION" in x for x in c)
    assert c[-len(ARGV):] == ARGV                      # the same command line, --goal included


def test_log_defaults_beside_the_spec_when_stdout_is_not_a_file():
    assert unit()["log"] == "/w/run-item.log"


def test_already_supervised_or_opted_out_runs_in_place():
    assert unit(env=dict(ENV, INVOCATION_ID="abc")) is None                 # inside a systemd unit (ot-run stage, kit-wave tick unit)
    assert unit(cgroup="0::/user.slice/user@1000.service/app.slice/kw-x.service\n") is None
    assert unit(env=dict(ENV, KW_RUNITEM_NO_UNIT="1")) is None              # env opt-out
    assert unit(env=dict(ENV, KW_RUNITEM_UNIT="runitem-x")) is None         # already the re-executed child
    assert unit(sp={"die": "s81", "item": "t"}) is None                     # a wave spec (its tick already uses a unit)


def test_duplicate_item_gets_a_distinct_unit():
    assert unit(suffix="-123")["unit"] == "runitem-slice_t5-123"
