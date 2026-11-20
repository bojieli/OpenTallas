"""tests for tools/route_results.py (kept next to the source so ot-push-main selects it): builds a fake kit tree and checks stage counts, gate pass/fail and failure classes."""
import importlib.util
import json
import os
import time
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("route_results", Path(__file__).resolve().parent / "route_results.py")
rr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rr)

NOW = time.mktime((2026, 11, 19, 21, 30, 0, 0, 0, -1))
SINCE = time.mktime((2026, 11, 19, 21, 0, 0, 0, 0, -1))
UNTIL = time.mktime((2026, 11, 19, 22, 0, 0, 0, 0, -1))
IN = time.mktime((2026, 11, 19, 21, 20, 0, 0, 0, -1))
OLD = time.mktime((2026, 11, 19, 3, 0, 0, 0, 0, -1))


def _write(p, text, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    os.utime(p, (t, t))


def kit(root, die_dir, item, stages=(), signoff=None, route_drc=0, log_only=None, log_text="", log_t=IN, stage_t=IN):
    """stages: stage names with json+log; signoff: dict for signoff.json; log_only: stage with a log and no json."""
    k = root / "runs" / die_dir / "kit-wave" / die_dir / "ev" / "items" / item / "gen" / item
    base = k / "run" / "logs" / "asap7" / ("dp_" + item) / "base"
    for st in stages:
        f = rr.STAGE_FILE[st]
        body = json.dumps({"detailedroute__route__drc_errors": route_drc}) if st == "route" else "{}"
        _write(base / (f + ".json"), body, stage_t)
        _write(base / (f + ".log"), "ok\n", stage_t)
    if log_only:
        _write(base / (rr.STAGE_FILE[log_only] + ".log"), log_text, log_t)
    if signoff is not None:
        _write(k / "signoff" / "signoff.json", json.dumps(signoff), stage_t)
    return k


def so(drc=0, setup=-10.0, hold=5.0, gates=None):
    d = {"verdict": "SIGNED", "route": {"drc": drc}, "checks": {"setup_tt": {"wns_ps": setup}, "hold_ff": {"wns_ps": hold}}}
    if gates is not None:
        d["profile_gates"] = gates
    return d


def table(root, live="", wave=frozenset(), cancel=()):
    recs = rr.collect([str(root)], live=live)
    for r in recs:
        r["cancel_sig"] = r["cancel_sig"] or r["kit"] in cancel
    return rr.aggregate(recs, SINCE, UNTIL, NOW, rr.STALE_MIN * 60, wave)


def test_pass_and_failure_classes(tmp_path):
    full = ("cts", "grt", "route")
    kit(tmp_path, "s81", "col_pass", full, so())
    kit(tmp_path, "s81", "col_setup", full, so(setup=-60.0))
    kit(tmp_path, "s81", "col_hold", full, so(hold=-3.0))
    kit(tmp_path, "s81", "col_drc", full, so(drc=4))
    kit(tmp_path, "s81", "col_edge", full, so(setup=-42.0, hold=0.0))      # exactly on both thresholds passes
    t = table(tmp_path)["s81"]
    assert (t["cts"], t["grt"], t["route"], t["signoff"]) == (5, 5, 5, 5)
    assert t["pass"] == 2 and t["setup"] == 1 and t["hold"] == 1 and t["drc"] == 1 and t["ended"] == 5


def test_profile_gates_win_over_raw_values(tmp_path):
    kit(tmp_path, "s81", "col_g", ("cts", "grt", "route"), so(setup=-28.0, hold=-122.0, gates={"drc": "PASS", "setup_tt": "PASS", "hold_ff": "FAIL"}))
    t = table(tmp_path)["s81"]
    assert t["hold"] == 1 and t["pass"] == 0


def test_route_drc_without_signoff_and_pending(tmp_path):
    kit(tmp_path, "s81", "col_a", ("cts", "grt", "route"), None, route_drc=12)
    kit(tmp_path, "s81", "col_b", ("cts", "grt", "route"), None, route_drc=0)
    t = table(tmp_path)["s81"]
    assert t["drc"] == 1 and t["pending"] == 1 and t["route"] == 2 and t["signoff"] == 0


def test_crash_congestion_and_running(tmp_path):
    kit(tmp_path, "qwen_compute", "slw_cong", ("cts",), None, log_only="grt", log_text="[ERROR GRT-0116] Global routing finished with congestion\n")
    kit(tmp_path, "qwen_compute", "slw_crash", ("cts", "grt"), None, log_only="route", log_text="Segmentation fault\n")
    kit(tmp_path, "qwen_compute", "slw_dead", ("cts",), None, log_only="grt", log_text="progress\n", log_t=NOW - 2.5 * 3600)
    kit(tmp_path, "qwen_compute", "slw_live", ("cts",), None, log_only="grt", log_text="progress\n", log_t=NOW - 60)
    t = table(tmp_path)["qc"]
    assert t["congestion"] == 1
    assert t["crash"] == 1 and t["dead"] == 1     # signature = real crash; idle log with no record = dead; the live one is not counted
    assert t["cts"] == 4 and t["grt"] == 1 and t["ended"] == 3


def test_window_excludes_old_builds(tmp_path):
    kit(tmp_path, "s81_head", "hd_old", ("cts", "grt", "route"), so(), stage_t=OLD)
    kit(tmp_path, "s81_head", "hd_new", ("cts", "grt", "route"), so(setup=-80.0))
    t = table(tmp_path)["head"]
    assert t["signoff"] == 1 and t["setup"] == 1 and t["pass"] == 0


def test_die_mapping():
    assert rr.die_of("/r/runs/s81/kit-wave/s81/e/items/slice_station__t7/gen/k") == "s81"
    assert rr.die_of("/r/runs/s81_head/kit-wave/s81_head/e/items/hd_host_e/gen/k") == "head"
    assert rr.die_of("/r/runs/qwen_kvsys/kit-wave/qwen_kvsys/e/items/kv3_hg/gen/k") == "kv"
    assert rr.die_of("/srv/x/claude/s81-geom-opus-d8g/d8i/tree6/kits/col_h9_r1__t1/gen/k") == "s81"
    assert rr.die_of("/srv/x/claude/unknown/thing") == "other"


def test_render_has_table_and_rate(tmp_path):
    kit(tmp_path, "s81", "col_p", ("cts", "grt", "route"), so())
    kit(tmp_path, "s81", "col_f", ("cts", "grt", "route"), so(hold=-1.0))
    out = rr.render(table(tmp_path), SINCE, UNTIL)
    assert "ROUTE-RESULTS" in out and "| s81 | 2 | 2 | 2 | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |" in out
    assert "failed 1" in out and "50%" in out


def test_live_build_is_running_not_crashed(tmp_path):
    k = kit(tmp_path, "s81", "col_live", ("cts",), None, log_only="grt", log_text="Segmentation fault\n")
    assert table(tmp_path, live=str(k) + "/run")["s81"]["crash"] == 0
    assert table(tmp_path)["s81"]["crash"] == 1


def test_walk_skips_kit_internals_but_finds_all_builds(tmp_path):
    k = kit(tmp_path, "s81", "col_a", ("cts",))
    (k / "rtl" / "deep").mkdir(parents=True)
    (k / "macros" / "logs" / "asap7" / "dp_x" / "base").mkdir(parents=True)   # inside a kit but not under run/: ignored
    assert len(rr.find_bases(str(tmp_path))) == 1


def test_cancelled_by_signal_or_wave_is_not_a_crash(tmp_path):
    k1 = kit(tmp_path, "s81", "col_sig", ("cts",), None, log_only="grt", log_text="Segmentation fault\n")
    kit(tmp_path, "s81", "col_wave", ("cts",), None, log_only="grt", log_text="progress\n", log_t=IN)
    kit(tmp_path, "s81", "col_dead", ("cts",), None, log_only="grt", log_text="progress\n", log_t=NOW - 2.5 * 3600)
    wave = {("s81", "ev", "col_wave", None)}
    t = table(tmp_path, wave=wave, cancel={str(k1)})["s81"]
    assert t["cancelled"] == 2 and t["crash"] == 0 and t["dead"] == 1


def test_wave_attempt_must_match(tmp_path):
    k = tmp_path / "runs" / "s81" / "kit-wave" / "s81" / "ev" / "items" / "col_x" / "attempt_3" / "gen" / "col_x"
    rec = {"kit": str(k), "cancel_sig": False}
    assert rr.is_cancelled(rec, {("s81", "ev", "col_x", 3)})
    assert not rr.is_cancelled(rec, {("s81", "ev", "col_x", 2)})


def test_cancel_dirs_and_wave_state_parse(tmp_path):
    log = tmp_path / "signals.log"
    log.write_text("2026-11-19T23:56:21-0800 signal 15 from pid 1 (python3 x) -> ot-run pid 5 host h1 tag t WAITING dir /srv/a/gen/k1: \n"
                   "2026-11-19T23:56:22-0800 SPILL-DROP /srv/b on h1\n")
    assert rr.cancel_dirs(str(log)) == {"/srv/a/gen/k1"}
    st = tmp_path / "state.json"
    st.write_text(json.dumps({"items": {"hbm|NE_io|bab": {"status": "CANCELLED", "event": "d44v", "attempt": 16},
                                        "hbm|NW_io|bcd": {"status": "RUNNING", "event": "d44v", "attempt": 1}}}))
    assert rr.wave_cancelled(str(st)) == {("hbm", "d44v", "NE_io", 16)}


def test_fast_roots_only_wave_runs_and_active_dirs(tmp_path):
    c = tmp_path / "opentallas-scratch2" / "claude"
    for d in ("kw43/runs", "kw45", "old-private", "live-private", "new-private"):
        (c / d).mkdir(parents=True)
    os.utime(c / "old-private", (OLD - 5 * 86400, OLD - 5 * 86400))
    roots = rr.fast_roots(SINCE, live="cwd " + str(c / "live-private") + "/run", srv=str(tmp_path))
    names = {os.path.relpath(r, c) for r in roots}
    assert "kw43/runs" in names and "live-private" in names and "new-private" in names
    assert "old-private" not in names
