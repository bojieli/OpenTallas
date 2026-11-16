import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fail_route as fr  # noqa: E402

NOW = time.mktime(time.strptime("2026-11-15 21:00", "%Y-%m-%d %H:%M"))


def stamp(minutes_ago):
    from datetime import datetime
    return datetime.fromtimestamp(NOW - minutes_ago * 60, fr.LA).strftime("%Y-%m-%d %H:%M PST")


def mk(tmp, queue_lines, fails):
    (tmp / "lanes/posts").mkdir(parents=True)
    (tmp / "autopilot").mkdir()
    (tmp / "lanes/COORD-REVIEW-QUEUE.md").write_text("\n".join(queue_lines) + "\n")
    items = {f"{k}|b1": {"status": "FAIL"} for k in fails}
    sigs = {k: dict(cls="FLOW", stage="gen", reason=f"sdc_lint refusal {i}", n=1, last=NOW - 600) for i, k in enumerate(fails)}
    (tmp / "autopilot/kit_wave_state.json").write_text(json.dumps({"items": items, "fail_sigs": sigs}))


def test_route_ack_escalate(tmp_path):
    q = [f"- {stamp(20)} STATE [DIE-S81-92 -> COORD] alive",
         f"- {stamp(10)} STATE [DIE-S81-90 -> COORD] old name, not live" if False else f"- {stamp(400)} STATE [DIE-S81-90 -> COORD] dead"]
    mk(tmp_path, q, ["s81|slice_station__t17", "s81|slice_station__t18", "qwen_kvsys|kv_a"])
    sent = []
    st = tmp_path / "st.json"
    args = (tmp_path, st, "post.sh")
    s, f, cl = fr.run(*args, now=NOW, poster=lambda p, t: sent.append(t) or True)
    assert len(s) == 2 and not f
    s81 = [t for t in sent if "DIE-S81-92" in t]
    assert len(s81) == 1 and "slice_station__t17" in s81[0] and "2 item(s)" in s81[0]
    assert any("-> COORD]" in t and "kv_a" in t for t in sent)       # KV-102 not live: COORD
    # idempotent
    assert fr.run(*args, now=NOW + 60, poster=lambda p, t: sent.append(t) or True)[0] == []
    # 31 min later, no ack: NEEDS-LANE once per class
    s, _, _ = fr.run(*args, now=NOW + 31 * 60, poster=lambda p, t: sent.append(t) or True)
    assert sorted(x[0] for x in s) == ["LANE", "LANE"]
    assert fr.run(*args, now=NOW + 90 * 60, poster=lambda p, t: sent.append(t) or True)[0] == []
    assert sum(t.startswith("NEEDS-LANE") for t in sent) == 2


def test_ack_suppresses_lane(tmp_path):
    mk(tmp_path, [f"- {stamp(5)} STATE [DIE-S81-92 -> COORD] alive"], ["s81|slice_station__t17"])
    sent = []
    st = tmp_path / "st.json"
    fr.run(tmp_path, st, "post.sh", now=NOW, poster=lambda p, t: sent.append(t) or True)
    q = tmp_path / "lanes/COORD-REVIEW-QUEUE.md"
    q.write_text(q.read_text() + f"- {stamp(-20)} ACK [DIE-S81-92 -> COORD] slice_station__t17 cause is the clock tap window\n")
    s, _, _ = fr.run(tmp_path, st, "post.sh", now=NOW + 40 * 60, poster=lambda p, t: sent.append(t) or True)
    assert s == [] and len(sent) == 1


def test_waiter_result_fail_routed(tmp_path):
    mk(tmp_path, [f"- {stamp(20)} STATE [DIE-S81-92 -> COORD] alive",
                  f"- {stamp(15)} RESULT [S81-SVC-SYNTH-1115 -> COORD] FAIL (cause) waiter"], [])
    sent = []
    s, _, _ = fr.run(tmp_path, tmp_path / "st.json", "post.sh", now=NOW, poster=lambda p, t: sent.append(t) or True)
    assert len(s) == 1 and "DIE-S81-92" in sent[0] and "S81-SVC-SYNTH-1115" in sent[0]


def test_fix_lane_is_owner(tmp_path):
    mk(tmp_path, [f"- {stamp(5)} STATE [FABLE-FIX-S81-RINGS -> COORD] alive", f"- {stamp(5)} STATE [QC-DRT-1116 -> COORD] alive"],
       ["s81|ring_a", "qwen_compute|cbn_q00"])
    sent = []
    fr.run(tmp_path, tmp_path / "st.json", "post.sh", now=NOW, poster=lambda p, t: sent.append(t) or True)
    assert any("FABLE-FIX-S81-RINGS, COORD" in t for t in sent) and any("QC-DRT-1116, COORD" in t for t in sent)


def test_s81_family_routing(tmp_path):
    names = ["col_h9_r1__t1", "leaf_a__t2", "boxed_strip__t3", "serdes_x__t1", "slice_station__t17", "dsdv_slice_c1x__t1"]
    mk(tmp_path, [f"- {stamp(5)} STATE [DIE-S81-92 -> COORD] alive"], ["s81|" + n for n in names])
    sent = []
    fr.run(tmp_path, tmp_path / "st.json", "post.sh", now=NOW, poster=lambda p, t: sent.append(t) or True)
    def to(n):
        return next(t for t in sent if n in t).split("->")[1].split(",")[0].strip()
    assert [to(n) for n in names] == ["FABLE-FIX-S81-COL", "FABLE-FIX-S81-RINGS", "FABLE-FIX-S81-STRIP", "S81-SERDES-PHY-1116",
                                      "DIE-S81-92", "DIE-S81-92"]
