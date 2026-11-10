"""KW-FIX-44 11-09 (COORD KW44-5): ot-run-sealed seals autopilot's route / finish submissions (signoff_chain.py: route,
sign-off, late ECO, routed LEC) with declared inputs: K (the sealed place output), the sha-pinned admission tool bundle
and the KWCHILD records.  Opt-in by conf "ap_goals", narrowed by "ap_pilot"; everything else passes through."""
import base64
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

M = SourceFileLoader("ot_run_sealed_ap", str(Path(__file__).with_name("ot-run-sealed"))).load_module()

K = "/srv/opentallas-scratch2/claude/kw27-wave-1109/runs/s81/kit-wave/s81/e9/items/ot_s81sl_leaf__t25/attempt_3/gen/ot_s81sl_leaf__t25"
R = "/srv/opentallas-scratch2/claude/kw27-wave-1109/runs/s81/kit-wave/s81/e9/runner/run_kit.sh"
META = {"dir": "/srv/opentallas-scratch2/claude/autopilot/admission_tools/c5077de0f0a08fd1bc7c", "sha256": "c5077de0" * 8,
        "source_host": "hub", "chain": "x", "preflight": "y"}
BOOT = "import base64\nprint('ADMISSION_TOOLS READY '+meta['sha256'])\n"


def ap_argv(goal="route", kit=K, extra=(), late=True):
    enc = base64.b64encode(json.dumps(META).encode()).decode()
    return (["--mem", "48", "--threads", "16", "--dir", kit, "--stage", kit, "--stage", R] + list(extra)
            + ["--", "python3", "-c", BOOT, enc] + ([] if late else ["--no-late-eco"]) + [R, kit, goal, "48", "16"])


def conf(**kw):
    c = {"enabled": True, "dirs": ["/srv/opentallas-scratch2/claude/kw27-wave-1109/runs/"], "hosts": ["epyc2"],
         "backend": "/wave/ot-run", "sealed_backend": "/sb/ot-run", "capacity_passthru": False, "stages": ["place"]}
    c.update(kw)
    return c


def ok(h, runner, k, bundle=None):
    return True, ["/srv/x/child_rec"] + (["BUNDLE_OK"] if bundle else [])


def spec_of(argv):
    return json.load(open(argv[argv.index("--job") + 1]))


def test_ap_call_parses_the_bootstrap_shape():
    a = ap_argv()
    cmd = a[a.index("--") + 1:]
    runner, k, goal, meta = M.ap_call(cmd, ("route",))
    assert (runner, k, goal, meta["sha256"]) == (R, K, "route", META["sha256"])
    cmd2 = ap_argv(late=False)
    assert M.ap_call(cmd2[cmd2.index("--") + 1:], ("route",))[2] == "route"            # --no-late-eco skipped
    assert M.ap_call(cmd, ("finish",)) is None                                          # goal not opted in
    assert M.ap_call(["python3", "-c", "print(1)", "e30=", R, K, "route", "48", "16"], ("route",)) is None   # not the bootstrap
    assert M.ap_call(["bash", "-c", "bash r k place 48 16"], ("route",)) is None


def test_default_conf_passes_autopilot_through_unchanged(tmp_path, monkeypatch):
    out, why = M.decide(ap_argv(), conf(spec_dir=str(tmp_path)), check=ok)
    assert out[0] == "/wave/ot-run" and why == "not a place call"
    monkeypatch.setenv("OT_RUN_SEALED_BACKEND", "/ap/kw10/ot-run")                       # autopilot keeps its backend
    out, _ = M.decide(ap_argv(), conf(spec_dir=str(tmp_path)), check=ok)
    assert out == ["/ap/kw10/ot-run"] + ap_argv()


def test_route_is_sealed_with_declared_inputs(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_RUN_SEALED_BACKEND", "/ap/kw10/ot-run")
    out, why = M.decide(ap_argv(extra=["--priority", "die", "--crit"]),
                        conf(spec_dir=str(tmp_path), ap_goals=["route", "finish"]), check=ok)
    assert why == f"SEALED on epyc2: {K}"
    assert out[:9] == ["/sb/ot-run", "--mem", "48", "--threads", "16", "--hosts", "epyc2", "--job", out[8]]
    assert "--crit" in out and out[out.index("--priority") + 1] == "die"
    assert out[out.index("--") + 1:] == ap_argv()[ap_argv().index("--") + 1:]           # the command is unchanged
    s = spec_of(out)
    assert s["name"] == "ot_s81sl_leaf__t25-route" and s["work"] == {"at": K, "seed": [{"path": K}]}
    assert s["inputs"][0] == {"path": META["dir"], "at": META["dir"]}                    # bundle on the host: no fetch
    assert {"path": R} in s["inputs"] and {"path": "/srv/x/child_rec"} in s["inputs"]
    assert "BUNDLE_OK" not in json.dumps(s["inputs"])
    assert s["tools_sha256"] == META["sha256"] and s["return"] == {"to": K, "paths": ["."]}
    assert [p["path"] for p in s["publish"]] == ["run", "signoff"]


def test_bundle_missing_on_host_is_fetched_from_the_hub(tmp_path):
    out, _ = M.decide(ap_argv(), conf(spec_dir=str(tmp_path), ap_goals=["route"]),
                      check=lambda h, r, k, b=None: (True, []))
    assert spec_of(out)["inputs"][0] == {"path": META["dir"], "at": META["dir"], "host": "hub"}


def test_pilot_list_narrows_and_dirs_still_apply(tmp_path):
    c = conf(spec_dir=str(tmp_path), ap_goals=["route"], ap_pilot=["kv3_pv_v8/attempt_11/"])
    out, why = M.decide(ap_argv(), c, check=ok)
    assert out[0] == "/wave/ot-run" and why == "not an ap pilot kit"
    c["ap_pilot"] = ["ot_s81sl_leaf__t25/attempt_3/"]
    assert M.decide(ap_argv(), c, check=ok)[1].startswith("SEALED on epyc2")
    other = "/srv/opentallas-scratch2/claude/lane/kit"
    out, why = M.decide(ap_argv(kit=other), conf(spec_dir=str(tmp_path), ap_goals=["route"]), check=ok)
    assert why == "not a pilot dir"


def test_not_ready_host_passes_through(tmp_path):
    out, why = M.decide(ap_argv(), conf(spec_dir=str(tmp_path), ap_goals=["route"]),
                        check=lambda h, r, k, b=None: (False, []))
    assert out[0] == "/wave/ot-run" and why.startswith("kit/runner/ot-job/bwrap not ready")


def test_place_calls_are_unchanged(tmp_path):
    a = ["--mem", "48", "--threads", "16", "--dir", K, "--", "bash", "-c", f"bash {R} {K} place 48 16"]
    out, why = M.decide(a, conf(spec_dir=str(tmp_path), ap_goals=["route"]), check=lambda h, r, k: (True, []))
    s = spec_of(out)
    assert why.startswith("SEALED") and s["name"].endswith("-place") and "tools_sha256" not in s


def test_gap_fallback_knows_the_ap_target():
    a = ap_argv()
    assert M.sealed_target(a[a.index("--") + 1:], conf(ap_goals=["route"])) == (K, "route")
    assert M.sealed_target(a[a.index("--") + 1:], conf()) is None


ROWS = {"epyc2": {"load": 90, "ncpu": 96, "admit": 20, "waiting_gb": 0, "ok": True},
        "intel1": {"load": 10, "ncpu": 112, "admit": 170, "waiting_gb": 0, "ok": True}}


def test_cross_host_fetch_when_no_holder_admits(tmp_path, monkeypatch):
    """COORD 13:0x: K's holder (epyc2) cannot admit 48 GB, intel1 can -> sealed on intel1, every input fetched from
    epyc2 (bundle from the hub), K copied back to epyc2 after"""
    monkeypatch.setattr(M, "status_rows", lambda b: ROWS)
    monkeypatch.setattr(M, "row_admits", lambda r, mem: bool(r) and r["admit"] >= int(mem))
    seen = []
    c = conf(spec_dir=str(tmp_path), ap_goals=["route"], ap_fetch_hosts=["epyc2", "intel1"])
    out, why = M.decide(ap_argv(), c, check=lambda h, r, k, b=None: (True, ["/srv/x/child_rec"]),
                        fetch=lambda h, b, k: (seen.append((h, k)), (True, []))[1])
    assert why == f"SEALED on intel1: {K} (inputs fetched from epyc2)" and seen == [("intel1", K)]
    assert out[out.index("--hosts") + 1] == "intel1"
    s = spec_of(out)
    assert s["work"]["seed"] == [{"path": K, "host": "epyc2"}]
    assert s["inputs"][0]["host"] == "hub"                                               # bundle not on intel1
    assert {"path": R, "host": "epyc2"} in s["inputs"] and {"path": "/srv/x/child_rec", "host": "epyc2"} in s["inputs"]
    assert s["copy_back"] == {"from": "intel1", "to": "epyc2", "path": K}
    assert s["return"] == {"to": K, "paths": ["."]}


def test_no_fetch_when_holder_admits_or_not_configured(tmp_path, monkeypatch):
    rows = dict(ROWS, epyc2=dict(ROWS["epyc2"], admit=100))
    monkeypatch.setattr(M, "status_rows", lambda b: rows)
    monkeypatch.setattr(M, "row_admits", lambda r, mem: bool(r) and r["admit"] >= int(mem))
    c = conf(spec_dir=str(tmp_path), ap_goals=["route"], ap_fetch_hosts=["intel1"])
    out, why = M.decide(ap_argv(), c, check=ok, fetch=lambda h, b, k: (True, []))
    assert why == f"SEALED on epyc2: {K}" and "copy_back" not in spec_of(out)
    monkeypatch.setattr(M, "status_rows", lambda b: ROWS)
    out, why = M.decide(ap_argv(), conf(spec_dir=str(tmp_path), ap_goals=["route"]), check=ok)
    assert why == f"SEALED on epyc2: {K}"                                                # opt-in only
    out, why = M.decide(ap_argv(), c, check=ok, fetch=lambda h, b, k: (False, []))       # fetch host not ready
    assert why == f"SEALED on epyc2: {K}"


def test_job_root_on_scratch3_when_scratch2_is_under_the_floor(tmp_path, monkeypatch):
    """COORD 14:3x: a sealed job's dir may sit on scratch3: spec root + ot-run --dir name it; opt-in by conf job_roots"""
    monkeypatch.setattr(M, "status_rows", lambda b: ROWS)
    monkeypatch.setattr(M, "row_admits", lambda r, mem: bool(r) and r["admit"] >= int(mem))
    r3 = "/srv/opentallas-scratch3/claude/ot-jobs"
    c = conf(spec_dir=str(tmp_path), ap_goals=["route"], ap_fetch_hosts=["intel1"], job_roots=True,
             job_root_of=lambda h: r3)
    out, why = M.decide(ap_argv(), c, check=lambda h, r, k, b=None: (True, []), fetch=lambda h, b, k: (True, []))
    assert out[out.index("--hosts") + 1] == "intel1" and out[out.index("--dir") + 1] == r3
    assert out.index("--dir") < out.index("--")
    assert spec_of(out)["root"] == r3
    c.pop("job_roots")
    out, _ = M.decide(ap_argv(), c, check=lambda h, r, k, b=None: (True, []), fetch=lambda h, b, k: (True, []))
    assert "root" not in spec_of(out) and "--dir" not in out[:out.index("--")]


def test_holder_that_admits_is_preferred_over_the_first_host(tmp_path, monkeypatch):
    rows = dict(ROWS, epyc7={"load": 120, "ncpu": 96, "admit": 5, "waiting_gb": 400, "ok": True},
                epyc2=dict(ROWS["epyc2"], admit=200))
    monkeypatch.setattr(M, "status_rows", lambda b: rows)
    monkeypatch.setattr(M, "row_admits", lambda r, mem: bool(r) and r["admit"] >= int(mem))
    c = conf(spec_dir=str(tmp_path), ap_goals=["route"], hosts=["epyc7", "epyc2"], ap_fetch_hosts=["intel1"])
    out, why = M.decide(ap_argv(), c, check=ok, fetch=lambda h, b, k: (True, []))
    assert why == f"SEALED on epyc2: {K}" and "copy_back" not in spec_of(out)


def test_job_root_shell_picks_first_root_with_room():
    assert M.JOB_ROOTS[0].startswith("/srv/opentallas-scratch2/") and M.JOB_ROOTS[1].startswith("/srv/opentallas-scratch3/")
    assert "-ge 60" in M.JOB_ROOT_SH and "JOBROOT=" in M.JOB_ROOT_SH and "break" in M.JOB_ROOT_SH


def test_not_admitted_signature():
    assert M.not_admitted(["ot-run: -> epyc7 (will queue)\n", "ot-run: NOT RUN on epyc7: ot-heavy exit 75\n"])
    assert not M.not_admitted(["ot-heavy: admitted on x\n", "ot-run: NOT RUN on epyc7: ot-heavy exit 75\n"])
    assert not M.not_admitted(["ot-run: RAN on epyc7 (unit u): exit 1\n"])
    assert M.with_max_wait(["b", "--max-wait", "9", "--hosts", "h", "--", "x"], 600) == ["b", "--hosts", "h", "--max-wait", "600", "--", "x"]


def test_rehand_moves_a_waiter_that_was_not_admitted(tmp_path, monkeypatch):
    """COORD 15:5x: a sealed job not admitted in rehand_after_s on its host is placed again with that host excluded"""
    monkeypatch.setattr(M, "status_rows", lambda b: ROWS)
    monkeypatch.setattr(M, "row_admits", lambda r, mem: bool(r) and r["admit"] >= int(mem))
    monkeypatch.setattr(M, "log", lambda c, m: None)
    c = conf(spec_dir=str(tmp_path), ap_goals=["route"], hosts=["epyc2", "intel1"], rehand_after_s=600)
    monkeypatch.setattr(M.sys, "argv", ["ot-run-sealed"] + ap_argv())
    first, _ = M.decide(ap_argv(), dict(c, hosts=["epyc2"]), check=ok)
    assert first[first.index("--hosts") + 1] == "epyc2"
    calls = []

    def fake_run(a, conf_, orig):
        calls.append(a)
        if len(calls) == 1:
            M.LAST_OUT[:] = ["ot-run: NOT RUN on epyc2: ot-heavy exit 75\n"]
            return 75
        M.LAST_OUT[:] = ["ot-heavy: admitted on x\n"]
        return 0
    monkeypatch.setattr(M, "run_sealed", fake_run)
    real = M.decide
    monkeypatch.setattr(M, "decide", lambda a, cf, exclude=(): real(a, cf, check=ok, exclude=exclude))
    rc, last = M.rehand(first, c, "SEALED")
    assert rc == 0 and len(calls) == 2
    assert calls[0][calls[0].index("--max-wait") + 1] == "600"
    assert last[last.index("--hosts") + 1] == "intel1"


def test_rehand_off_by_default_and_never_unsealed(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "log", lambda c, m: None)
    c = conf(spec_dir=str(tmp_path), ap_goals=["route"])
    first, _ = M.decide(ap_argv(), c, check=ok)
    seen = []
    monkeypatch.setattr(M, "run_sealed", lambda a, cf, o: (seen.append(a), 0)[1])
    rc, _ = M.rehand(first, c, "SEALED")
    assert rc == 0 and "--max-wait" not in seen[0][:seen[0].index("--")]
