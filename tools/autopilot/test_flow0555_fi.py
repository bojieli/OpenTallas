"""FLOW-HEALTH-1 11-19 (FABLE-FLOW-0555 F and I): a frozen job (CPU and stage logs) is cancelled and relaunched once as a free infra retry; the FAIL-ROUTE relay
stops after a COORD RULING / ACK, whoever owns the class now, and does not route triage RESULT tables as failures."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import fail_route as fr
import kit_wave as KW

NOW = time.mktime(time.strptime("2026-11-19 06:00", "%Y-%m-%d %H:%M"))


def stamp(minutes_ago):
    from datetime import datetime
    return datetime.fromtimestamp(NOW - minutes_ago * 60, fr.LA).strftime("%Y-%m-%d %H:%M PST")


# ---------------------------------------------------------------- F
def test_a_watcher_heartbeat_log_is_not_stage_progress(tmp_path):
    root = tmp_path / "attempt_10"
    logs = root / "run/logs/asap7/x/base"
    logs.mkdir(parents=True)
    old = time.time() - 3 * 3600
    real = logs / "3_5_place_dp.log"
    real.write_text("placed\n")
    os.utime(real, (old, old))
    (root / "stage_odb_cap.log").write_text("2026-11-19 14:10:47 STAGE-CAP skip ...\n")            # touched every minute by the watcher
    r = subprocess.run([sys.executable, "-I", "-c", KW.HUNG_PROBE, json.dumps([str(root)])], capture_output=True, text=True, cwd="/")
    out = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1])["HUNG_PROBE"][str(root)]
    assert abs(out["log"] - old) < 5, out                                                      # not the fresh heartbeat


def test_hung_judge_says_hung_when_cpu_and_real_logs_are_frozen_for_the_window():
    now = 100000.0
    prog = {"cpu": 10784.0, "log": now - 165 * 60, "pids": 21, "containers": ["epyc8:dpkit-x"]}
    prev = {"cpu": 10784.0, "t": now - 150 * 60}
    hung, w, why = KW._hung_judge(prev, prog, now - 400 * 60, now, 120)
    assert hung and "not grown" in why
    prog["log"] = now - 60                                                                       # a real log written a minute ago: not hung
    assert KW._hung_judge(prev, prog, now - 400 * 60, now, 120)[0] is False


class AP:
    DRY = False
    HUB_NAME = "hubhost"

    def __init__(self):
        self.logs, self.cmds = [], []

    def log(self, m):
        self.logs.append(m)

    def sh(self, cmd, timeout=0):
        self.cmds.append(cmd)
        return 0, "", ""


def test_hung_cancel_relaunches_once_as_a_free_infra_retry(monkeypatch):
    monkeypatch.setattr(KW, "attempt_root", lambda rec: None)
    ap, st, notices = AP(), {"items": {}}, {}
    rec = {"die": "s81", "item": "serdes__t15", "attempt": 10, "unit": "kw-s81-x", "dir": "/nonexistent", "infra_base": 2}
    KW.hung_cancel(ap, rec, "no stage-log output for 165 min and CPU 10784 s not grown", notices, ["epyc8:dpkit-x"], st=st)
    assert rec["status"] == "RETRY-INFRA" and rec["class"] == "INFRA" and rec["infra_base"] == 3 and rec["no_host_at"] == 0
    assert any("free infra retry" in m for m in ap.logs) and "free infra retry" in notices["s81"][0]
    assert any(c[:3] == ["ssh", "-o", "BatchMode=yes"] and "dpkit-x" in c for c in ap.cmds) or any("dpkit-x" in " ".join(c) for c in ap.cmds)
    rec2 = dict(rec, status="RUNNING", attempt=11)
    KW.hung_cancel(ap, rec2, "again frozen", notices, [], st=st)                                # the second hang of the same item: no further free retry
    assert rec2["status"] == "CANCELLED" and rec2["class"] == "HUNG" and "second hang" in notices["s81"][1]
    rec3 = {"die": "s81", "item": "other", "attempt": 1, "unit": "u", "dir": "/nonexistent"}
    KW.hung_cancel(ap, rec3, "frozen", notices, [])                                              # old call shape (no state): unchanged CANCELLED-HUNG
    assert rec3["status"] == "CANCELLED"


# ---------------------------------------------------------------- I
def mk(tmp, queue_lines, fails=(), state_extra=None):
    (tmp / "lanes/posts").mkdir(parents=True, exist_ok=True)
    (tmp / "autopilot").mkdir(exist_ok=True)
    (tmp / "lanes/COORD-REVIEW-QUEUE.md").write_text("\n".join(queue_lines) + "\n")
    items = {f"{k}|b1": {"status": "FAIL"} for k in fails}
    sigs = {k: dict(cls="FLOW", stage="gen", reason="sdc_lint refusal", n=1, last=NOW - 600) for k in fails}
    (tmp / "autopilot/kit_wave_state.json").write_text(json.dumps({"items": items, "fail_sigs": sigs}))


def test_owner_flip_does_not_repost_and_a_coord_ruling_closes_the_class(tmp_path):
    q = [f"- {stamp(30)} STATE [FABLE-FIX-S81-COL -> COORD] alive", f"- {stamp(30)} STATE [DIE-S81-92 -> COORD] alive"]
    mk(tmp_path, q, ["s81|serdes_a__t1"])
    sent = []
    post = lambda p, t: sent.append(t) or True
    st = tmp_path / "st.json"
    s, _, cl = fr.run(tmp_path, st, "post.sh", now=NOW, poster=post)
    cid = next(iter(cl.values()))["cid"]
    assert len(s) == 1
    # the owner lane goes quiet, another lane becomes the pick: the same class must not be posted again to the new owner
    mk(tmp_path, [f"- {stamp(5)} STATE [S81-SERDES-PHY-1116 -> COORD] alive", f"- {stamp(400)} STATE [DIE-S81-92 -> COORD] old"], ["s81|serdes_a__t1"])
    s2, _, _ = fr.run(tmp_path, st, "post.sh", now=NOW + 40 * 60, poster=post)
    assert all(x[0] != "ACTION" for x in s2) and len(sent) <= 2                      # at most the one NEEDS-LANE, never a second NEEDS-ACTION
    q2 = tmp_path / "lanes/COORD-REVIEW-QUEUE.md"
    q2.write_text(q2.read_text() + f"- {stamp(-50)} RULING [COORD -> S81-SERDES-PHY-1116] class {cid} is closed (r400)\n")
    n = len(sent)
    s3, _, _ = fr.run(tmp_path, st, "post.sh", now=NOW + 90 * 60, poster=post)
    s4, _, _ = fr.run(tmp_path, st, "post.sh", now=NOW + 200 * 60, poster=post)
    assert s3 == [] and s4 == [] and len(sent) == n
    assert cid in json.loads(st.read_text())["closed"]


def test_coord_ack_naming_an_item_closes_it(tmp_path):
    mk(tmp_path, [f"- {stamp(30)} STATE [DIE-S81-92 -> COORD] alive"], ["s81|slice_station__t17"])
    sent = []
    post = lambda p, t: sent.append(t) or True
    st = tmp_path / "st.json"
    fr.run(tmp_path, st, "post.sh", now=NOW, poster=post)
    q = tmp_path / "lanes/COORD-REVIEW-QUEUE.md"
    q.write_text(q.read_text() + f"- {stamp(-10)} ACK [COORD -> DIE-S81-92] slice_station__t17 known, r401\n")
    assert fr.run(tmp_path, st, "post.sh", now=NOW + 40 * 60, poster=post)[0] == [] and len(sent) == 1


def test_legacy_state_keyed_owner_cid_is_found(tmp_path):
    mk(tmp_path, [f"- {stamp(5)} STATE [DIE-S81-92 -> COORD] alive"], ["s81|slice_station__t17"])
    sent = []
    st = tmp_path / "st.json"
    s, _, cl = fr.run(tmp_path, st, "post.sh", now=NOW, poster=lambda p, t: sent.append(t) or True)
    cid = next(iter(cl.values()))["cid"]
    d = json.loads(st.read_text())
    d["classes"] = {f"SOME-OTHER-LANE|{cid}": v for v in d["classes"].values()}               # state written when another lane owned it
    st.write_text(json.dumps(d))
    assert fr.run(tmp_path, st, "post.sh", now=NOW + 60, poster=lambda p, t: sent.append(t) or True)[0] == [] and len(sent) == 1


def test_triage_result_tables_are_not_failures_but_a_lane_failure_still_is(tmp_path):
    mk(tmp_path, [f"- {stamp(20)} STATE [DIE-S81-92 -> COORD] alive",
                  f"- {stamp(15)} RESULT [S81-FAILED-TRIAGE-1119 -> COORD] table of 14 rows: 9 FAIL gen, 3 FAIL kit_rtl, 2 REFUSED",
                  f"- {stamp(14)} RESULT [S81-CENSUS-1119 -> COORD] FAIL rows: 4",
                  f"- {stamp(13)} RESULT [S81-SVC-SYNTH-1115 -> COORD] FAIL (cause) waiter",
                  f"- {stamp(12)} RESULT [S81-OTHER-1119 -> COORD] big table of results with many columns and notes and then a FAIL at the very end of the text"])
    sent = []
    s, _, cl = fr.run(tmp_path, tmp_path / "st.json", "post.sh", now=NOW, poster=lambda p, t: sent.append(t) or True)
    assert len(cl) == 1 and "S81-SVC-SYNTH-1115" in sent[0]
    assert "TRIAGE" not in sent[0] and "CENSUS" not in sent[0] and "S81-OTHER-1119" not in sent[0]
