"""FLOW-OPS-1300 item 13b: event_paths ages handoff json by the date in its name (a checkout rewrites mtimes) and never protects through a delete / retire receipt."""
import datetime, importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))
sp = importlib.util.spec_from_file_location("build_protected_live", os.path.join(HERE, "build_protected_live.py"))
b = importlib.util.module_from_spec(sp); sp.loader.exec_module(b)


def _w(d, name, path):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w") as f:
        json.dump({"src": path}, f)


def test_event_paths_name_date_and_receipts(tmp_path):
    now = datetime.datetime(2026, 11, 21, 18, 30).timestamp()
    h = str(tmp_path / "lanes/handoff")
    P = "/srv/opentallas-scratch2/claude/kw45/src_kv_pin_x_%s"
    _w(h, "HG2C_D10_ADOPT_candidate_1116.json", P % "old")        # 5 days old by name, fresh mtime
    _w(h, "S81_D8J6_source_candidate_1121.json", P % "new")       # today
    _w(h, "put_qwen_compute_20261120-004922.candidate.json", P % "ymd")
    _w(h, "E9_DELETE_GUARD_REAL_PASS_1121.json", P % "deleted")   # a delete receipt, today
    _w(h, "KV7yhr_portable_ctx2_PASS.json", P % "nodate")         # no date: mtime rules
    for f in os.listdir(h):
        os.utime(os.path.join(h, f), (now - 3600, now - 3600))
    out = set()
    b.event_paths(str(tmp_path), out, os.path.normpath, now=now)
    assert P % "new" in out and P % "ymd" in out and P % "nodate" in out
    assert P % "old" not in out
    assert P % "deleted" not in out


def test_name_age_h():
    now = datetime.datetime(2026, 11, 21, 18, 0).timestamp()
    assert b.name_age_h("X_1121.json", now) == 0.0
    assert b.name_age_h("X_1117.json", now) == 90.0
    assert b.name_age_h("KV7yhr_portable_ctx2_PASS.json", now) is None
    assert b.name_age_h("src_bind_1120155451.json", now) is None       # mmddHHMMSS is not a bare date token
    assert b.name_age_h("Y_0105.json", now) > 24 * 300                  # January: last year
