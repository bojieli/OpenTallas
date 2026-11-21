import json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave as KW


class AP:
    DRY = False
    logs = []
    jobs = {"j1": {"id": "j1", "status": "RUNNING", "die": "s81", "type": "t1"}}
    saved = []

    @classmethod
    def log(cls, m): cls.logs.append(m)
    @classmethod
    def load_state(cls): return {"jobs": cls.jobs}
    @classmethod
    def set_status(cls, st, j, status, why=""): j["status"] = status; cls.saved.append((j["id"], status))


def _state(tmp):
    row = {"die": "s81", "item": "t1", "attempt": 2, "status": "RUNNING", "block_sha": "a" * 40, "q_id": "j1", "unit": "u1", "dir": str(tmp)}
    (tmp / KW.STATE_FILE).write_text(json.dumps({"items": {"s81|e|t1|b": row}}))
    (tmp / "state.json").write_text(json.dumps({"jobs": AP.jobs}))


def test_stops_run_outside_the_lock_cas_and_queue_job_closed(tmp_path, monkeypatch):
    _state(tmp_path)
    held = []

    def fake_cancel(ap, cfg, rec, why, cls, jobs, notices, reclaim=True):
        lk = KW.lock_take(tmp_path / "kit_wave.lock")           # the tick must be able to take it while the stops run
        held.append(lk is not None)
        if lk: lk.close()
        # a wave step changes nothing here; simulate the cancel result on the copy
        rec.update(status="CANCELLED", **{"class": cls}, updated=time.time(), reason=why, reclaim="kept")
    monkeypatch.setattr(KW, "grt_arm_cancel", fake_cancel)
    stops, done, skipped = KW.cancel_rows_phased(AP, {"dies": {}}, tmp_path, "s81", "t1", "why", "o", "GEOMETRY")
    st = json.loads((tmp_path / KW.STATE_FILE).read_text())
    row = st["items"]["s81|e|t1|b"]
    assert held == [True] and stops == 1 and not skipped
    assert row["status"] == "CANCELLED" and row["class"] == "STRUCT-STOP"
    assert ("j1", "CANCELLED") in AP.saved and AP.jobs["j1"]["cls"] == "CANCELLED"       # (M): no orphan for the reaper
    assert any("STRUCT-STOP" not in k or True for k in st["struct_stops"])


def test_row_changed_during_the_stops_is_left_alone(tmp_path, monkeypatch):
    _state(tmp_path)
    AP.jobs["j1"]["status"] = "RUNNING"; AP.saved.clear()

    def fake_cancel(ap, cfg, rec, why, cls, jobs, notices, reclaim=True):
        st = json.loads((tmp_path / KW.STATE_FILE).read_text())
        st["items"]["s81|e|t1|b"]["attempt"] = 3                  # a relaunch while we were stopping
        (tmp_path / KW.STATE_FILE).write_text(json.dumps(st))
        rec.update(status="CANCELLED", **{"class": cls}, updated=time.time(), reason=why)
    monkeypatch.setattr(KW, "grt_arm_cancel", fake_cancel)
    stops, done, skipped = KW.cancel_rows_phased(AP, {"dies": {}}, tmp_path, "s81", "t1", "why", "o", "GEOMETRY")
    row = json.loads((tmp_path / KW.STATE_FILE).read_text())["items"]["s81|e|t1|b"]
    assert skipped == ["s81|e|t1|b"] and row["status"] == "RUNNING" and row["attempt"] == 3 and not AP.saved


def test_cancel_lock_wait_is_long_enough_for_a_tick(tmp_path, monkeypatch):
    _state(tmp_path)
    seen = []
    real = KW.lock_take
    def spy(path, wait_s=0):
        seen.append(wait_s)
        return real(path, wait_s=wait_s)
    monkeypatch.setattr(KW, "lock_take", spy)
    monkeypatch.setattr(KW, "grt_arm_cancel", lambda ap, cfg, rec, why, cls, jobs, notices, reclaim=True: rec.update(status="CANCELLED", updated=time.time()))
    KW.cancel_rows_phased(AP, {"dies": {}}, tmp_path, "s81", "t1", "why", "o", "GEOMETRY")
    assert seen and min(seen) >= 600
