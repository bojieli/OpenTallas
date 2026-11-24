"""KITWAVE-BINDOUT 11-24 (FABLE FLOW REVIEW #2): a private --bind-out kit on a plan other than the wave's takes the as-built manifest and the
clock-landing sidecar its bind read (provenance_bind.json), read on the GEN host that holds the bind, and so passes the kit_topology bind check
(KV-ALLFIX hand-patched 65 A5t3 specs that kept the wave asbuilt / --clock-landing and died KIT_TOPOLOGY_BIND_STALE)."""
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW                       # noqa: E402
from test_flow_privspec_r1 import D, I, wave_cfg, _no_plan_probe   # noqa: E402,F401

FAKE_KT = (
    "import hashlib, json\nfrom pathlib import Path\n"
    "def has_topology(raw, tn, ab=None):\n    return True\n"
    "def bind_matches(raw, tn, out, ab=None, plan_path=None):\n"          # the real first check: the bind's asbuilt_sha256 vs the kit's as-built
    "    old = json.loads((Path(out) / 'native_topology.json').read_text())\n"
    "    return bool(ab) and old.get('asbuilt_sha256') == hashlib.sha256(Path(ab).read_bytes()).hexdigest()\n")


@pytest.fixture
def private_plan(tmp_path, monkeypatch):
    """an A5t3-like private tree on the gen host: plan, as-built manifest naming its own sidecar, and a strict bind made from that manifest"""
    pr = tmp_path / "grow" / "tree" / "physical" / "die_plan" / D / "plan_of_record"
    pr.mkdir(parents=True)
    plan = pr / "plan_allfix_A5t3.json"
    plan.write_text(json.dumps({"partition_types": {I: {}}}))
    side = pr / "eW_sidecar_A5t3.json"
    side.write_text("{}")
    ab = pr / "asbuilt_allfix_A5t3.json"
    ab.write_text(json.dumps({"clock_landing_table": str(side)}))
    bo = tmp_path / "grow" / "gate_A5t3" / "bind"
    bo.mkdir(parents=True)
    (bo / "provenance_bind.json").write_text(json.dumps({"provenance": {"manifest": str(ab), "plan": str(plan)}}))
    (bo / "native_topology.json").write_text(json.dumps({"asbuilt_sha256": hashlib.sha256(ab.read_bytes()).hexdigest()}))
    rt = tmp_path / "rt_die_plan"
    rt.mkdir()
    (rt / "kit_topology.py").write_text(FAKE_KT)
    monkeypatch.setenv("OT_BIND_PROBE_RT", str(rt))
    calls = []

    def remote(host, hub, bind_out, src):                # the gen host = this machine, reached through the real probe code
        calls.append(host)
        return KW.bind_landing_remote(host, hub, bind_out, src, run=lambda argv, **k: subprocess.run(
            [sys.executable, "-I", "-c", KW._bind_landing_probe_py(), shlex.split(argv[-1])[-1]], **k))
    monkeypatch.setattr(KW, "BIND_LANDING_REMOTE", remote)
    return dict(plan=str(plan), ab=str(ab), side=str(side), bind=str(bo), calls=calls)


def local_rpy(host, code, args, timeout=600):
    r = subprocess.run([sys.executable, "-I", "-", json.dumps(args)], input=code, capture_output=True, text=True)
    return json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("AP_JSON ")][-1][8:])


def cfg_with_landing():
    c = wave_cfg()
    c["dies"][D]["gen_args"] = ["--clock-landing", "/srv/x/src_kv/physical/die_plan/qwen_kvsys/plan_of_record/eW_sidecar.json"]
    return c


def test_private_bind_out_on_another_plan_reaches_kit_topology_without_bind_stale(private_plan):
    c = cfg_with_landing()
    wave_ab = c["dies"][D]["kit_rtl"]["asbuilt"]
    sp = KW.private_spec(c, D, I, "intel2", plan=private_plan["plan"], bind_out=private_plan["bind"], host="epyc11")
    assert private_plan["calls"] == ["epyc11"]                       # read on the gen host, not the spec host
    assert sp["kit_rtl"]["bind_out"] == private_plan["bind"]
    assert sp["kit_rtl"]["asbuilt"] == private_plan["ab"] != wave_ab
    assert "--clock-landing" in sp["gen_args"]
    if True:
        assert sp["gen_args"][sp["gen_args"].index("--clock-landing") + 1] == private_plan["side"]
    assert sp["private"]["bind_landing"]["read_on"] == "epyc11"
    assert KW.private_bind_stale(sp, I, local_rpy) == ("", "")      # the kit_topology bind check passes: no KIT_TOPOLOGY_BIND_STALE
    other = Path(private_plan["ab"]).with_name("asbuilt_wave_d29.json")   # the pre-fix spec: the wave as-built kept -> exactly the death seen
    other.write_text(json.dumps({"clock_landing_table": "eW_sidecar.json"}))
    v = KW.private_bind_stale(dict(sp, kit_rtl=dict(sp["kit_rtl"], asbuilt=str(other))), I, local_rpy)
    assert v[0] == "STALE" and "KIT_TOPOLOGY_BIND_STALE" in v[1]


def test_unreadable_bind_keeps_the_wave_inputs_and_says_so(private_plan, monkeypatch, capsys):
    monkeypatch.setattr(KW, "BIND_LANDING_REMOTE", lambda *a: {})
    c = cfg_with_landing()
    sp = KW.private_spec(c, D, I, "intel2", plan=private_plan["plan"], bind_out="/nowhere/bind", host="epyc11")
    assert sp["kit_rtl"]["asbuilt"] == c["dies"][D]["kit_rtl"]["asbuilt"]
    assert sp["private"]["bind_landing"]["read_on"].startswith("unreadable")
    assert "KW_BIND_LANDING_UNREADABLE /nowhere/bind" in capsys.readouterr().err


def test_bind_naming_a_missing_asbuilt_fails_loudly(private_plan, monkeypatch):
    """BINDOUT-LOUD-1124: the bind names the as-built it read, and that file is gone: never the wave's"""
    monkeypatch.setattr(KW, "BIND_LANDING_REMOTE", lambda *a: {})
    Path(private_plan["ab"]).unlink()
    with pytest.raises(KW.BindLandingMissing, match="which is missing"):
        KW.private_spec(cfg_with_landing(), D, I, "intel2", plan=private_plan["plan"], bind_out=private_plan["bind"], host="epyc11")


def test_bind_asbuilt_without_sidecar_fails_loudly(private_plan, monkeypatch):
    Path(private_plan["ab"]).write_text(json.dumps({}))
    with pytest.raises(KW.BindLandingMissing, match="clock_landing_table"):
        KW.private_spec(cfg_with_landing(), D, I, "intel2", plan=private_plan["plan"], bind_out=private_plan["bind"], host="epyc11")


def test_run_item_repairs_a_spec_written_by_an_old_rt(private_plan):
    """S81-ALLFIX-INT 11:3x: private-spec from the bind rt (pre KITWAVE-BINDOUT) kept the wave as-built / --clock-landing"""
    c = cfg_with_landing()
    sp = KW.private_spec(c, D, I, "intel2", plan=private_plan["plan"], bind_out=private_plan["bind"], host="epyc11")
    old = dict(sp, kit_rtl=dict(sp["kit_rtl"], asbuilt=c["dies"][D]["kit_rtl"]["asbuilt"]), gen_args=list(c["dies"][D]["gen_args"]))
    rec = KW.runitem_bind_landing(old)
    assert rec and old["kit_rtl"]["asbuilt"] == private_plan["ab"]
    assert old["gen_args"][old["gen_args"].index("--clock-landing") + 1] == private_plan["side"]
    assert old["private"]["bind_landing_repair"]["asbuilt"]["bind"] == private_plan["ab"]
    assert KW.runitem_bind_landing(old) is None                      # already right: unchanged
    assert KW.runitem_bind_landing(dict(old, private=None)) is None  # a wave spec is never touched


def test_private_spec_does_not_read_stdin():
    code = ("import sys, subprocess; sys.path.insert(0, %r); import kit_wave as KW; KW.detach_stdin(False); "
            "print(repr(subprocess.run(['cat'], capture_output=True, text=True).stdout))") % str(Path(KW.__file__).parent)
    r = subprocess.run([sys.executable, "-I", "-c", code], input="t2 route\nt3 route\n", capture_output=True, text=True, timeout=120)
    assert r.stdout.strip().splitlines()[-1] == "''", r.stderr[-400:]


def test_spec_host_copy_is_the_fallback(private_plan, monkeypatch):
    monkeypatch.setattr(KW, "BIND_LANDING_REMOTE", lambda *a: {})
    sp = KW.private_spec(cfg_with_landing(), D, I, "intel2", plan=private_plan["plan"], bind_out=private_plan["bind"], host="epyc11")
    assert sp["kit_rtl"]["asbuilt"] == private_plan["ab"] and sp["private"]["bind_landing"]["read_on"] == "local"
