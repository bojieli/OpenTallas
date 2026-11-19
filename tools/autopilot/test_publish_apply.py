"""LATENCY-R 11-18 (COORD 11-18 optimistic launch): publish_apply apply / bind-fail."""
import json
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import publish_apply as PA  # noqa: E402


def coord(tmp_path, die_extra=None):
    c = tmp_path / "coord"
    (c / "autopilot").mkdir(parents=True)
    (c / "lanes/handoff").mkdir(parents=True)
    d = {"src": "/x/old", "event": "E0", "plan_sha256": "s1", "hold_event_items": {"s1": ["cbn_q00", "cbn_q00__cl1", "sle_fe_v1", "slw_st_a_v1"]},
         "owner_lane": "QC-PLAN-R3"}
    d.update(die_extra or {})
    (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"qc": d}}))
    return c


def test_types_from_log_matches_whole_plan_item_names():
    items = ["cbn_q00", "cbn_q00__cl1", "sle_fe_v1", "slw_st_a_v1"]
    log = "BIND ERROR cbn_q00__cl1: port mismatch\nLATCHECK FAIL lane 7 in slw_st_a_v1 (u_lane7)\nok sle_fe_v1x"
    assert PA.types_from_log(log, items) == ["cbn_q00__cl1", "slw_st_a_v1"]


def test_bind_fail_record_holds_only_named_types():
    r = PA.bind_fail_record({"plan_sha256": "s1"}, ["a", "b"], "QC-PLAN-R3", "n3-bind", "x")
    assert r["items"] == ["a", "b"] and r["release"] == ["result:QC-PLAN-R3:n3-bind"] and r["cancel_running"] and r["plan_sha"] == "s1"


def test_bind_fail_dry_prints_patch(tmp_path, capsys, monkeypatch):
    c = coord(tmp_path)
    monkeypatch.setattr(PA.HR, "add_record", lambda cfg, die, rec: rec)
    a = types.SimpleNamespace(coord=str(c), die="qc", lane="QC-PLAN-R3", id="n3", types="sle_fe_v1", log=None, reason="", dry=True)
    assert PA.cmd_bind_fail(a) == 0
    patch = json.loads(capsys.readouterr().out)
    assert patch[0]["path"] == "/dies/qc/hold_records" and patch[0]["value"][0]["items"] == ["sle_fe_v1"]


def test_bind_fail_with_no_named_type_holds_nothing(tmp_path):
    c = coord(tmp_path)
    log = tmp_path / "b.log"
    log.write_text("die-wide elab error")
    a = types.SimpleNamespace(coord=str(c), die="qc", lane="L", id="n3", types="", log=str(log), reason="", dry=False)
    assert PA.cmd_bind_fail(a) == 2


def test_apply_is_optimistic_commits_starts_the_advisory_gate_and_posts(tmp_path):
    c = coord(tmp_path)
    cand = tmp_path / "cand.json"
    cand.write_text(json.dumps({"die": "qc", "tree": "/x/new", "manifest_hash": "a" * 64, "plan": "/p", "plan_sha256": "s2", "hosts": ["epyc9"]}))
    seen = {}

    def apply_fn(C, obj, src, ev, pilot_item=None, optimistic=None):
        seen.update(optimistic=optimistic, obj=obj)
        rcpt = Path(C) / "lanes/handoff/qc_atomic_apply_1.json"
        rcpt.write_text("{}")
        return {"applied": "qc", "event": "N3", "source": "/x/new", "receipt": str(rcpt), "warnings": ["ADVISORY publish_gate: none"], "gen_hosts": ["epyc9"]}
    calls = []

    def run(argv, **k):
        calls.append(argv)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    a = types.SimpleNamespace(coord=str(c), candidate=str(cand), expect_source="/x/old", expect_event="E0", lane="QC-PLAN-R3", pilot_item=None, no_gate=False)
    assert PA.cmd_apply(a, run=run, apply_fn=apply_fn, commit_fn=lambda C, r: "ok") == 0
    assert seen["optimistic"] is True and seen["obj"]["optimistic"] is True
    gate = [x for x in calls if x[0] == "systemd-run"][0]
    assert "--expect-source" in gate and gate[gate.index("--expect-source") + 1] == "/x/new" and gate[gate.index("--expect-event") + 1] == "N3"
    gc = json.loads((c / "lanes/handoff/qc_atomic_apply_1.gate_candidate.json").read_text())
    assert gc["optimistic"] is True
    p = [x for x in calls if x[0] == "bash"][0]
    assert p[2] == "QC-PLAN-R3" and "APPLIED-OPTIMISTIC" in p[3] and "advisory warning" in p[3]


def test_apply_starts_background_precheck_on_first_gen_host(tmp_path):
    """PRECHECK-1119: the estimator runs after the apply on the die's first gen host; --no-precheck turns it off"""
    obj = {"die": "qc", "tree": "/x/new", "plan": "physical/p.json", "hosts": ["epyc9"]}
    res = {"applied": "qc", "event": "N3", "gen_hosts": ["epyc8", "epyc9"]}
    pa = PA.precheck_argv(obj, res, "QC-PLAN-R3", now=5)
    assert pa[:7] == ["timeout", "60", "ssh", "-n", "-o", "ControlPath=none", "epyc8"] and "systemd-run" in pa
    assert pa[pa.index("--plan") + 1] == "/x/new/physical/p.json" and pa[pa.index("--tools") + 1] == "/x/new/tools/die_plan"
    assert pa[pa.index("--owner") + 1] == "QC-PLAN-R3" and pa[pa.index("--unit") + 1] == "precheck-qc-5"
    assert pa[pa.index("--kit-hosts") + 1] == ",".join(res.get("gen_hosts") or obj.get("config", {}).get("gen_hosts") or pa[6:7])
    assert PA.precheck_argv({"die": "qc"}, {}, "L") is None
    c = coord(tmp_path)
    cand = tmp_path / "cand.json"
    cand.write_text(json.dumps(dict(obj, manifest_hash="a" * 64, plan_sha256="s2")))

    def apply_fn(C, o, src, ev, pilot_item=None, optimistic=None):
        rcpt = Path(C) / "lanes/handoff/qc_atomic_apply_2.json"
        rcpt.write_text("{}")
        return dict(res, source="/x/new", receipt=str(rcpt), warnings=[])
    for off in (False, True):
        calls = []

        def run(argv, **k):
            calls.append(argv)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        a = types.SimpleNamespace(coord=str(c), candidate=str(cand), expect_source="/x/old", expect_event="E0", lane="QC-PLAN-R3",
                                  pilot_item=None, no_gate=True, no_precheck=off, skip_bind_check=True)
        assert PA.cmd_apply(a, run=run, apply_fn=apply_fn, commit_fn=lambda C, r: "ok") == 0
        assert bool([x for x in calls if x[0] == "timeout" and "precheck_hook.py" in " ".join(x)]) is (not off)
        post = [x for x in calls if x[0] == "bash"][0][3]
        assert ("precheck precheck-qc-" in post) is (not off) and ("precheck off" in post) is off
