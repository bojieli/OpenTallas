"""FLEET-WATCH-2000: GRT flat-overflow / NOPROG-label cancel goes through the wave's cancel-rows (class PLAN design:grt_flat_overflow); lanes, private kits, re-sign and ECO are exempt."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

NOW = 1_000_000_000.0
KIT = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R4A4/items/cbf_q00__c1/attempt_3/gen/cbf_q00__c1"


def row(**kw):
    r = {"host": "h1", "container": "dpkit-cbf_q00-1", "unit": "oth-1", "type": "cbf_q00", "kit": KIT, "work": KIT, "kind": "grt", "stage": "5_1_grt", "age_h": 5.0, "gb": 20.0,
         "verdict": "PROGRESS", "lane": "", "key": "k1", "grt_flat": ""}
    r.update(kw)
    return r


def test_grt_flat_needs_five_iterations_without_a_2_percent_fall():
    assert nw.grt_flat([(5, 12147), (10, 10883), (15, 9842), (20, 9748)])           # 1 % over 5 iterations
    assert not nw.grt_flat([(5, 12147), (10, 10883), (15, 9842), (20, 9000)])       # still falling 8 %
    assert not nw.grt_flat([(5, 100)]) and not nw.grt_flat([(5, 100), (10, 0)]) and not nw.grt_flat([])


def test_wave_identity_and_exemptions():
    assert nw.wave_identity(KIT) == ("qwen_compute", "s29q103S4Q9N46R4A4", "cbf_q00__c1", "3")
    assert nw.grt_flat_candidate(row(grt_flat="flat")) == "flat"
    assert nw.grt_flat_candidate(row(verdict=nw.GRT_LABEL, why="DESIGN-FAIL: x", detail="d")).startswith("NOPROG label")
    assert not nw.grt_flat_candidate(row(grt_flat="flat", age_h=3.0))                # not over 3 h
    assert not nw.grt_flat_candidate(row(grt_flat="flat", lane="GPL-TD-AB"))        # OT_LANE
    assert not nw.grt_flat_candidate(row(grt_flat="flat", kit="/srv/x/opus-kv-hg/k13ci"))   # private kit
    assert not nw.grt_flat_candidate(row(grt_flat="flat", container="dpkit-resign-1"))
    assert not nw.grt_flat_candidate(row(grt_flat="flat", type="eco_2026_i1t"))
    assert not nw.grt_flat_candidate(row(grt_flat="flat", kind="drt"))


def test_pass_lists_first_then_cancels_by_wave_path(tmp_path, monkeypatch):
    monkeypatch.setattr(nw, "COORD", str(tmp_path))
    (tmp_path / "lanes").mkdir()
    calls = []
    cancel = lambda ident, why: (calls.append((ident, why)) or (0, "ok"))
    seen = {}
    rows = [row(grt_flat="flat")]
    mode, cand, done = nw.grt_flat_pass(rows, seen, NOW, post=False, cancel=cancel)
    assert mode == "act" and len(cand) == 1 and not done and not calls            # first pass only lists
    mode, cand, done = nw.grt_flat_pass(rows, seen, NOW + nw.MIN_REPORT_AGE_S + 1, post=False, cancel=cancel)
    assert len(done) == 1 and calls[0][0] == ("qwen_compute", "s29q103S4Q9N46R4A4", "cbf_q00__c1", "3") and nw.GRT_FLAT_CLASS in calls[0][1]
    assert done[0]["class"] == "PLAN design:grt_flat_overflow"
    assert "cbf_q00__c1" in (tmp_path / "lanes/CANCEL-GRT-FLAT.tsv").read_text()
    nw.grt_flat_pass(rows, seen, NOW + 5000, post=False, cancel=cancel)
    assert len(calls) == 1                                                         # once per attempt


def test_a_progressing_sibling_container_keeps_the_unit(tmp_path, monkeypatch):
    monkeypatch.setattr(nw, "COORD", str(tmp_path))
    (tmp_path / "lanes").mkdir()
    seen, calls = {}, []
    rows = [row(grt_flat="flat"), row(container="sib", key="k2")]
    nw.grt_flat_pass(rows, seen, NOW, post=False, cancel=lambda i, w: calls.append(i))
    nw.grt_flat_pass(rows, seen, NOW + 2000, post=False, cancel=lambda i, w: calls.append(i))
    assert not calls


def test_cancel_command_is_cancel_rows_with_event_attempt_and_class_plan():
    got = {}
    class R: returncode, stdout, stderr = 0, "cancel-rows: 1 live row(s)\n", ""
    nw.wave_cancel_rows(("d", "ev", "it", "3"), "why", run=lambda argv, **k: got.setdefault("argv", argv) and R)
    a = got["argv"]
    assert "cancel-rows" in a and a[a.index("--event") + 1] == "ev" and a[a.index("--attempt") + 1] == "3" and a[a.index("--cls") + 1] == "PLAN"
    assert "ot-run" not in " ".join(a)
