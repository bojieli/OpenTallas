"""FABLE-FLOW-1400: apply bind preflight, derive-asbuilt, BIND-FAIL rows (TOOLS-DECOUPLE)"""
import hashlib, json, sys, types
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW
import publish_apply as PA


def cfg_with(bind_fail=None, item_bind=None):
    d = {"kit_rtl": {"mode": "bind", "bind_out": "/b/die"}, "item_inputs": {}}
    if item_bind:
        d["item_inputs"]["t2"] = {"kit_rtl": {"bind_out": item_bind}}
    if bind_fail is not None:
        d["bind_fail"] = bind_fail
    return {"dies": {"qc": d}}


def test_bind_fail_blocks_until_the_bind_changes():
    rec = {"id": "bindfail-x", "bind": "/b/die", "items": ["t1", "t2"], "at": 100.0}
    cfg = cfg_with([rec], item_bind="/b/other")
    assert KW.bind_fail_active(cfg, "qc", "t1") == rec
    assert KW.bind_fail_active(cfg, "qc", "t2") is None            # t2 builds on another bind now: the record is inert for it
    assert KW.bind_fail_active(cfg, "qc", "t3") is None
    blocked, why, _ = KW.fail_key_gate(cfg, {}, "qc", "t1")
    assert blocked and "BIND-FAIL bindfail-x" in why
    cfg["dies"]["qc"]["kit_rtl"]["bind_out"] = "/b/new"             # a new bind: launches again
    assert KW.fail_key_gate(cfg, {}, "qc", "t1")[0] is False


def test_cancelled_rows_of_a_failed_bind_are_fail_bind_fail_not_infra():
    cfg = cfg_with([{"id": "bindfail-x", "bind": "/b/die", "items": ["t1"], "at": 100.0}])
    st = {"items": {"a": {"die": "qc", "item": "t1", "attempt": 3, "status": "CANCELLED", "class": "INFRA", "updated": 200.0},
                    "b": {"die": "qc", "item": "t1", "attempt": 2, "status": "CANCELLED", "class": "INFRA", "updated": 10.0},     # ended before the record
                    "c": {"die": "qc", "item": "t9", "attempt": 1, "status": "CANCELLED", "class": "INFRA", "updated": 200.0}}}
    log = []
    assert KW.mark_bind_fail_rows(cfg, st, log.append, now=300.0) == 1
    a = st["items"]["a"]
    assert a["status"] == "FAIL" and a["class"] == "BIND-FAIL" and a["bind_fail"] == "bindfail-x" and log
    assert st["items"]["b"]["class"] == "INFRA" and st["items"]["c"]["class"] == "INFRA"


def test_bind_fail_records_name_the_bind_each_type_builds_on():
    cfg = cfg_with(item_bind="/b/other")
    recs = PA.bind_fail_records(cfg, "qc", ["t1", "t2", "t3"], "QC-L", "b7", now=5.0)
    assert recs == [{"id": "bindfail-b7", "bind": "/b/die", "items": ["t1", "t3"], "at": 5.0, "lane": "QC-L"},
                    {"id": "bindfail-b7", "bind": "/b/other", "items": ["t2"], "at": 5.0, "lane": "QC-L"}]


def cand(bind=True):
    kr = {"mode": "bind", "bind_out": "/b/x", "asbuilt": "/t/a.json"} if bind else {"mode": "inputs"}
    return {"die": "qc", "tree": "/t", "plan": "/t/p.json", "config": {"gen_hosts": ["h1", "h2"], "kit_rtl": kr}}


def test_bind_check_refuses_a_stale_candidate_and_passes_a_matching_one():
    def run_with(out, rc=0):
        calls = []

        def run(argv, **k):
            calls.append(argv)
            return types.SimpleNamespace(returncode=rc, stdout=out, stderr="")
        return run, calls
    run, calls = run_with('AP_JSON {"checked": 133, "stale": ["cbf_q00"], "diff": {"clock_table_sha256": ["dcdadbc1", "d080395e"]}}')
    ok, txt = PA.bind_check(cand(), run=run)
    assert ok is False and "1/133" in txt and "derive-asbuilt" in txt and calls[0][0] == "ssh" and "h1" in calls[0]
    run, _ = run_with('AP_JSON {"checked": 133, "stale": [], "diff": {}}')
    assert PA.bind_check(cand(), run=run)[0] is True
    assert PA.bind_check(cand(bind=False))[0] is None
    run, calls = run_with("", rc=255)
    ok, txt = PA.bind_check(cand(), run=run)
    assert ok is False and len(calls) == 2 and "no candidate host answered" in txt     # fail closed, every host tried


def test_apply_refuses_before_any_write_when_the_bind_check_fails(tmp_path):
    c = tmp_path / "cand.json"
    c.write_text(json.dumps(cand()))
    a = types.SimpleNamespace(candidate=str(c), expect_source="/old", expect_event="E", lane="L", pilot_item=None, coord=str(tmp_path), no_gate=True,
                              skip_bind_check=False, bind_check_fn=lambda obj, run=None: (False, "stale"))
    called = []
    assert PA.cmd_apply(a, apply_fn=lambda *x, **k: called.append(1)) == 4 and not called


def test_derive_asbuilt_takes_the_tables_the_bind_used(tmp_path):
    tree = tmp_path / "tree"
    rt = tree / "physical/die_plan/qc/runtime"
    rt.mkdir(parents=True)
    files = {"sc_N4.json": b"sc4", "r8_N4.json": b"r84", "ex_N4_0.json": b"ex0", "sc_N2.json": b"sc2"}
    for n, b in files.items():
        (rt / n).write_bytes(b)
    sha = {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}
    old = "/srv/x/kw45/src_old/physical/die_plan/qc/runtime/"
    bind = tmp_path / "bind"
    bind.mkdir()
    (bind / "INPUTS_ISOLATED.json").write_text(json.dumps({"source_manifest": old + "a.json", "sidecar": old + "sc_N4.json", "sidecar_sha256": sha["sc_N4.json"],
                                                           "r8": old + "r8_N4.json", "r8_sha256": sha["r8_N4.json"],
                                                           "extra_tables": [{"copy": old + "ex_N4_0.json", "sha256": sha["ex_N4_0.json"]}]}))
    ab = rt / "a.json"
    ab.write_text(json.dumps({"base": "../../../..", "clock_landing_table": "physical/die_plan/qc/runtime/sc_N2.json", "land_r8": "x", "land_r8_extra": ["y"]}))
    out = rt / "a_frombind.json"
    d = PA.derive_asbuilt(str(bind), str(ab), str(tree), str(out))
    assert d["clock_landing_table"] == "physical/die_plan/qc/runtime/sc_N4.json" and d["land_r8"] == "physical/die_plan/qc/runtime/r8_N4.json"
    assert d["land_r8_extra"] == ["physical/die_plan/qc/runtime/ex_N4_0.json"] and json.loads(out.read_text())["base"] == "../../../.."
    (rt / "r8_N4.json").write_bytes(b"changed")
    try:
        PA.derive_asbuilt(str(bind), str(ab), str(tree), str(out))
        raise AssertionError("a table that differs from the one the bind used was accepted")
    except SystemExit as e:
        assert "DERIVE refuse" in str(e)
