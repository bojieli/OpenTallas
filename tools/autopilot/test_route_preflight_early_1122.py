"""PREFLIGHT-EARLY-1122 (COORD 21:0x, HEAD w13): the route chain's kit preflight runs at gen (--preflight-only), so a kit the
route chain will refuse fails before place, not hours after it."""
import base64
import json
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW  # noqa: E402
import signoff_chain as SC  # noqa: E402


def test_preflight_only_runs_the_chain_preflight_and_no_runner(tmp_path):
    kit = tmp_path / "k"
    kit.mkdir()
    pf = tmp_path / "kit_preflight.py"
    pf.write_text("# shared preflight\n")
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        return 1 if "fail" in str(kit) else 0
    assert SC.continue_kit(kit, "run_kit.sh", "route", 8, 2, run=run, preflight=pf, preflight_only=True,
                           refresh=None, so_tool=None) == 0
    assert len(calls) == 1 and calls[0][1] == str(pf) and calls[0][2] == str(kit)       # preflight only, never bash runner
    kit2 = tmp_path / "fail"
    kit2.mkdir()
    calls.clear()
    kit = kit2
    rc = SC.continue_kit(kit2, "run_kit.sh", "route", 8, 2, run=run, preflight=pf, preflight_only=True, refresh=None, so_tool=None)
    assert len(calls) == 1 and (rc == 1 or SC.minimal())


def test_route_preflight_cmd_uses_the_admission_bundle():
    class AP:
        ADMISSION_BOOTSTRAP = "print('boot')"
    b = dict(dir="/srv/opentallas-scratch2/claude/x/admission_tools/abc", sha256="abc")
    cmd = KW.route_preflight_cmd(AP, "/w/gen/k", "/w/gen/run_kit.sh", bundle=b)
    argv = shlex.split(cmd)
    assert argv[:3] == ["python3", "-c", "print('boot')"]
    assert json.loads(base64.b64decode(argv[3]))["dir"] == b["dir"]
    assert argv[4:] == ["--preflight-only", "/w/gen/run_kit.sh", "/w/gen/k", "route", "8", "2"]


def test_gen_stage_runs_route_preflight_before_place():
    src = (HERE / "kit_wave.py").read_text()
    i_pf = src.index('rc, txt = run("preflight", otrun(8, 2, W, pf, gh))')
    i_rp = src.index('run("preflight_route", otrun(8, 2, W, _rpc, gh))')
    assert src.index("_rpc = route_preflight_cmd(AP, K, _rpr, hosts=(G,))") < i_rp
    i_adv = src.index('_, rtxt = run("preflight_adv"')
    assert i_pf < i_rp < i_adv


def test_route_preflight_switch():
    assert KW.route_preflight_on({}) is True
    assert KW.route_preflight_on({"KW_ROUTE_PREFLIGHT": "0"}) is False
    assert KW.route_preflight_on({"PYTEST_CURRENT_TEST": "x"}) is False
    assert KW.route_preflight_on({"PYTEST_CURRENT_TEST": "x", "KW_ROUTE_PREFLIGHT": "1"}) is True
