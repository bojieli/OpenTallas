"""FAILFAST-1 (2026-11-12, COORD orphan-leak ruling): a cancel stops its row's containers by exact name and records it.
Root cause found by the orphan census: wave_jobs.STOP_KIT matched containers by the RW mount source under the kit root, but a
container of an ot-job isolated copy mounts <ot-jobs>/<tag>/work, so every stop by root missed it (q_su31 a11, col_h10_r1 a11,
sle_fe_v1 a9 ... ran 60-70 h after their rows were CANCELLED).  Local: a fake `docker` on PATH, no Docker.
    python3 -m pytest -q tools/autopilot/test_cancel_stops_containers.py"""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP  # noqa: E402
import kit_wave as KW  # noqa: E402
import wave_jobs as WJ  # noqa: E402

FAKE_DOCKER = """#!/bin/bash
case "$1" in
  ps) echo $(python3 -I -c "import json;print(' '.join(c['Id'] for c in json.load(open('$FAKE_DIR/containers.json'))))") ;;
  inspect) python3 -I -c "import json,sys;print(json.dumps([c for c in json.load(open('$FAKE_DIR/containers.json')) if c['Id'] in sys.argv[1:]]))" "${@:2}" ;;
  stop) echo "$@" >> $FAKE_DIR/stopped.txt ;;
esac
"""


def container(cid, name, work, origin=None, tmp=None):
    """a docker-inspect record; origin: the kit an ot-job copy at `work` was made from (written to its .ot-job/job.json)"""
    if origin:
        Path(work).parent.mkdir(parents=True, exist_ok=True)
        jd = Path(work).parent / ".ot-job"
        jd.mkdir(exist_ok=True)
        (jd / "job.json").write_text(json.dumps({"spec": {"work": {"at": origin}, "return": {"to": origin}}}))
    return {"Id": cid, "Name": "/" + name, "Mounts": [{"Type": "bind", "Source": str(work), "Destination": "/work", "RW": True}]}


def run_stop(tmp_path, containers, roots, dry=False):
    fd = tmp_path / "fake"
    fd.mkdir(exist_ok=True)
    (fd / "containers.json").write_text(json.dumps(containers))
    d = fd / "bin"
    d.mkdir(exist_ok=True)
    (d / "docker").write_text(FAKE_DOCKER)
    (d / "docker").chmod(0o755 | stat.S_IXUSR)
    env = dict(os.environ, PATH=str(d) + ":" + os.environ["PATH"], FAKE_DIR=str(fd))
    p = subprocess.run([sys.executable, "-I", "-c", WJ.STOP_KIT, json.dumps({"roots": roots, "dry": dry})], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    stopped = (fd / "stopped.txt").read_text().split() if (fd / "stopped.txt").exists() else []
    return json.loads(p.stdout.strip().splitlines()[-1])["containers"], stopped


def test_ot_job_copy_is_found_by_its_original_kit(tmp_path):
    kit = tmp_path / "wave/items/q_su31/attempt_11/gen/q_su31"
    cs = [container("a1", "dpkit-q_su31-111", tmp_path / "ot-jobs/q_su31-route-x-1/work", origin=str(kit))]
    names, stopped = run_stop(tmp_path, cs, [str(tmp_path / "wave/items/q_su31/attempt_11")])
    assert names == ["dpkit-q_su31-111"] and "dpkit-q_su31-111" in stopped              # the bug: the mount source is under no kit root


def test_direct_mount_and_other_attempts(tmp_path):
    root = tmp_path / "wave/items/q_x/attempt_2"
    cs = [container("a1", "direct", root / "gen/q_x"),
          container("a2", "copy-same", tmp_path / "ot-jobs/a/work", origin=str(root / "gen/q_x")),
          container("a3", "copy-other-attempt", tmp_path / "ot-jobs/b/work", origin=str(tmp_path / "wave/items/q_x/attempt_3/gen/q_x")),
          container("a4", "unrelated", tmp_path / "lane/dir/kit")]
    names, stopped = run_stop(tmp_path, cs, [str(root)])
    assert sorted(names) == ["copy-same", "direct"] and "copy-other-attempt" not in stopped and "unrelated" not in stopped


def test_attempt_one_root_does_not_take_later_attempts(tmp_path):
    root = tmp_path / "wave/items/q_x"
    cs = [container("a1", "att1", tmp_path / "ot-jobs/a/work", origin=str(root / "gen/q_x")),
          container("a2", "att4", tmp_path / "ot-jobs/b/work", origin=str(root / "attempt_4/gen/q_x"))]
    names, _ = run_stop(tmp_path, cs, [str(root)])
    assert names == ["att1"]


def test_dry_run_and_missing_job_json_stop_nothing(tmp_path):
    root = tmp_path / "wave/items/q_x/attempt_2"
    cs = [container("a1", "copy", tmp_path / "ot-jobs/a/work", origin=str(root / "gen/q_x")),
          container("a2", "nospec", tmp_path / "ot-jobs/z/work")]                       # no .ot-job/job.json: not matched, no crash
    names, stopped = run_stop(tmp_path, cs, [str(root)], dry=True)
    assert names == ["copy"] and stopped == []
    names, stopped = run_stop(tmp_path, cs, [str(root)])
    assert names == ["copy"] and "nospec" not in stopped


def test_stop_row_containers_helper_calls_stop_on_fleet_once(monkeypatch):
    calls = []
    monkeypatch.setattr(WJ, "stop_on_fleet", lambda sh, hub, roots, hosts=None, dry=False:
                        calls.append((roots, dry)) or {"epyc4": {"containers": ["dpkit-a-1"]}, "epyc7": {"error": "rc 255 x"}})
    names, errs = WJ.stop_row_containers(None, "hub", ["/r2", "/r1", "", "/r1"])
    assert calls == [(["/r1", "/r2"], False)] and names == "epyc4:dpkit-a-1" and "epyc7 not checked" in errs
    assert WJ.stop_row_containers(None, "hub", ["", None]) == ("", "")


def test_queue_cancelled_row_is_collected_and_stopped_and_recorded(tmp_path, monkeypatch):
    d = tmp_path / "ap"
    d.mkdir()
    (d / "state.json").write_text(json.dumps({"jobs": {"j1": {"id": "j1", "kit": "hostA:/k/q_x", "status": "CANCELLED", "updated": 1}}}))
    rec = {"die": "hbm", "item": "q_x", "attempt": 2, "status": "ENQUEUED", "kit": "hostA:/k/q_x"}
    st = {"items": {"hbm|q_x|b1": rec}}
    stops = []
    KW.follow_queue(st, d, {}, stops)
    assert rec["status"] == "CANCELLED" and stops == [(rec, "/k/q_x")]

    class FakeAP:
        DRY = False
        HUB_NAME = "hub"
        sh = None
        logs = []

        def log(self, m):
            self.logs.append(m)
    got = []
    monkeypatch.setattr(WJ, "stop_on_fleet", lambda sh, hub, roots, hosts=None, dry=False:
                        got.append(roots) or {"epyc4": {"containers": ["dpkit-q_x-77"]}})
    fa = FakeAP()
    assert KW.stop_cancelled_rows(fa, stops) == 1
    assert got == [["/k/q_x"]] and rec["stopped_containers"]["names"] == "epyc4:dpkit-q_x-77"
    assert "CANCEL-STOP" in fa.logs[0] and "epyc4:dpkit-q_x-77" in fa.logs[0]
    KW.follow_queue({"items": {"k": dict(rec, status="ENQUEUED")}}, d, {})                 # the old call signature still works


def test_stop_failure_never_blocks_the_cancel(monkeypatch):
    def boom(*a, **k):
        raise OSError("ssh down")
    monkeypatch.setattr(WJ, "stop_on_fleet", boom)

    class FakeAP:
        DRY = False
        HUB_NAME = "hub"
        sh = None
        logs = []

        def log(self, m):
            self.logs.append(m)
    rec = {"item": "q_x"}
    assert KW.stop_cancelled_rows(FakeAP(), [(rec, "/k")]) == 0
    assert "stop failed" in rec["stopped_containers"]["errors"]


def test_autopilot_cancel_stops_and_records(monkeypatch):
    got = []
    monkeypatch.setattr(WJ, "stop_on_fleet", lambda sh, hub, roots, hosts=None, dry=False:
                        got.append(roots) or {"epyc7": {"containers": ["dpkit-col-9"]}})
    monkeypatch.setattr(AP, "log", lambda m: got.append(m))
    j = {"id": "abc", "die": "s81", "type": "col", "path": "/kits/col_x"}
    assert AP.stop_cancelled(j, "explicit cancel") == "epyc7:dpkit-col-9"
    assert got[0] == ["/kits/col_x"] and j["stopped_containers"]["names"] == "epyc7:dpkit-col-9"
    assert any("CANCEL-STOP abc s81/col" in str(x) for x in got)


def test_every_cancel_site_in_the_source_stops_containers():
    """the sites that set a row / job CANCELLED with a possibly running container call a stop helper (grep guard)"""
    ap = Path(AP.__file__).read_text()
    kw = Path(KW.__file__).read_text()
    assert ap.count(" stop_cancelled(j, \"") == 2                                  # explicit cancel, wave no longer wants it
    assert "stop_cancelled_rows(AP, stops)" in kw and "follow_queue(st, ap_dir, notices, stops)" in kw
    assert 'rec["stopped_containers"]' in kw                                    # GRT-ARM records its stop too
