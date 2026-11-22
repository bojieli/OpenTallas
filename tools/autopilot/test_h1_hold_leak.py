"""H1 (WAVE-OPS-R1 11-22, FABLE-FLOW-0600): kit_wave_edit refuses a hold record that blocks nothing (stops_off die), and a hold_items removal needs --expect-launch N."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave_edit as KE  # noqa: E402

HOLDS = {"leaf_*": "owner=L eta=2026-11-30", "col_*": "owner=L eta=2026-11-30", "svc_*": "owner=L eta=2026-11-30"}
CFG = {"enabled": True, "stops_off": True, "dies": {"s81": {"hold_items": HOLDS}, "hbm": {}}}


def repo(cfg=CFG):
    import tempfile
    d = tempfile.mkdtemp()
    g = lambda *a: subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True)
    g("init", "-q")
    (Path(d) / "autopilot").mkdir()
    (Path(d) / "autopilot/kit_wave.json").write_text(KE.dump(cfg))
    g("add", "-A"); g("commit", "-q", "-m", "init")

    def commit(msg, rel):
        g("add", "--", rel); g("commit", "-q", "-m", msg)
    return d, g, commit


REC = {"id": "r1", "match": ["leaf_*"], "why": "x"}


def test_record_on_stops_off_die_refused():
    d, g, commit = repo()
    with pytest.raises(SystemExit) as e:
        KE.edit(d, [{"op": "add", "path": "/dies/s81/hold_records", "value": [REC]}], "m", commit_cmd=commit)
    assert "NO-OP-HOLD" in str(e.value) and "hold_items" in str(e.value)
    assert json.loads(g("show", "HEAD:autopilot/kit_wave.json").stdout)["dies"]["s81"].get("hold_records") is None


def test_record_on_hbm_allowed_and_stops_on_s81_allowed():
    d, g, commit = repo()
    KE.edit(d, [{"op": "add", "path": "/dies/hbm/hold_records", "value": [REC]}], "m", commit_cmd=commit)          # hbm keeps every stop
    assert json.loads(g("show", "HEAD:autopilot/kit_wave.json").stdout)["dies"]["hbm"]["hold_records"] == [REC]
    d2, g2, commit2 = repo()
    KE.edit(d2, [{"op": "add", "path": "/stops_off", "value": False}, {"op": "add", "path": "/dies/s81/hold_records", "value": [REC]}], "m", commit_cmd=commit2)
    assert "hold_records" in json.loads(g2("show", "HEAD:autopilot/kit_wave.json").stdout)["dies"]["s81"]


def test_untouched_old_record_is_not_judged():
    cfg = json.loads(json.dumps(CFG)); cfg["dies"]["s81"]["hold_records"] = [REC]
    d, g, commit = repo(cfg)
    KE.edit(d, [{"op": "add", "path": "/max_inflight", "value": 3}], "m", commit_cmd=commit)
    assert json.loads(g("show", "HEAD:autopilot/kit_wave.json").stdout)["max_inflight"] == 3


def probe_of(n):
    return lambda coord, old, new, die: {f"item{i}" for i in range(n)} if die == "s81" else set()


def rm(*keys):
    return [{"op": "remove", "path": f"/dies/s81/hold_items/{k}"} for k in keys]


def test_removing_hold_keys_needs_expect_launch(monkeypatch, capsys):
    monkeypatch.setattr(KE, "LAUNCH_PROBE", probe_of(4))
    d, g, commit = repo()
    with pytest.raises(SystemExit) as e:
        KE.edit(d, rm("leaf_*"), "m", commit_cmd=commit)
    assert "--expect-launch" in str(e.value) and "4 row(s)" in str(e.value)
    assert "leaf_*" in json.loads(g("show", "HEAD:autopilot/kit_wave.json").stdout)["dies"]["s81"]["hold_items"]


def test_wrong_expect_refused_right_expect_commits(monkeypatch, capsys):
    monkeypatch.setattr(KE, "LAUNCH_PROBE", probe_of(4))
    d, g, commit = repo()
    with pytest.raises(SystemExit) as e:
        KE.edit(d, rm("leaf_*"), "m", commit_cmd=commit, expect_launch=3)
    assert "--expect-launch 3 but 4" in str(e.value)
    KE.edit(d, rm("leaf_*"), "m", commit_cmd=commit, expect_launch=4)
    assert "leaf_*" not in json.loads(g("show", "HEAD:autopilot/kit_wave.json").stdout)["dies"]["s81"]["hold_items"]


def test_zero_launch_release_still_needs_expect_zero(monkeypatch):
    monkeypatch.setattr(KE, "LAUNCH_PROBE", probe_of(0))
    d, g, commit = repo()
    with pytest.raises(SystemExit):
        KE.edit(d, rm("svc_*"), "m", commit_cmd=commit)
    KE.edit(d, rm("svc_*"), "m", commit_cmd=commit, expect_launch=0)


def test_dry_run_prints_count_without_expect(monkeypatch, capsys):
    monkeypatch.setattr(KE, "LAUNCH_PROBE", probe_of(2))
    d, g, commit = repo()
    KE.edit(d, rm("col_*"), "m", dry=True, commit_cmd=lambda *a: pytest.fail("committed"))
    assert "LAUNCHABLE 2" in capsys.readouterr().out


def test_adding_holds_and_other_edits_need_no_expect(monkeypatch):
    monkeypatch.setattr(KE, "LAUNCH_PROBE", lambda *a: pytest.fail("probe ran for a non-release edit"))
    d, g, commit = repo()
    KE.edit(d, [{"op": "add", "path": "/dies/s81/hold_items/new_*", "value": "owner=L eta=2026-12-01"}], "m", commit_cmd=commit)
    KE.edit(d, [{"op": "replace", "path": "/enabled", "value": False}], "m", commit_cmd=commit)


def test_removed_hold_keys_pure():
    new = json.loads(json.dumps(CFG)); del new["dies"]["s81"]["hold_items"]["col_*"]
    assert KE.removed_hold_keys(CFG, new) == {"s81": ["col_*"]}
    assert KE.removed_hold_keys(CFG, CFG) == {}
    assert KE.removed_hold_keys(CFG, {"dies": {}}) == {"s81": ["col_*", "leaf_*", "svc_*"]}


def test_audit_counts_launched_rows_matching_a_record():
    import hold_records as HR
    cfg = {"dies": {"s81": {"hold_records": [{"id": "r1", "keys": ["leaf_*"]}], "hold_items": {}}}}
    f = HR.audit(cfg, [("s81", "leaf_t1"), ("s81", "svc_t2")])
    leak = [x for x in f if x["code"] == "HOLD-LEAK"]
    assert len(leak) == 1 and leak[0]["items"] == ["leaf_t1"] and HR.summarize(f)["HOLD-LEAK"] == 1
    assert not [x for x in HR.audit(cfg, [("s81", "svc_t2")]) if x["code"] == "HOLD-LEAK"]
