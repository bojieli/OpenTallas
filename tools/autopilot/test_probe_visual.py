"""VIS-REOWN 11-24: PROBE-THROUGH kits feed lanes/VISUAL-QUEUE.tsv (probe_visual + kit_wave.visual_queue_publish).
COORD 10:1x correction: the listed kit is of the type's CURRENT plan (plan sha of its newest launched kit), never the newest mtime."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import probe_visual as PV
import kit_wave as K

HDR = "# h\ndie\ttype\tfamily\tvis_lane\trender_paths\tverdict\tcause_class\tstructural_row\trow_status\tupdated\n"
NOW = time.time()


def coord(tmp, rows, specs=()):
    c = tmp / "coord"
    (c / "lanes").mkdir(parents=True)
    (c / "lanes" / "VIS-COVERAGE.tsv").write_text(HDR + "".join(f"{d}\t{t}\t{t}\tV\t-\tv\tc\tsr\t{s}\tu\n" for d, t, s in rows))
    for lane, name, created, spec, res in specs:
        p = c / "autopilot" / "private_specs" / lane / name
        p.mkdir(parents=True)
        spec = dict(spec, private={"created": created})
        (p / "spec.json").write_text(json.dumps(spec))
        if res is not None:
            (p / "result.json").write_text(json.dumps(res))
    return c


class FakeCache(PV.ShaCache):
    """plan sha = the plan path's last component (no files, no ssh)"""
    def __init__(self):
        super().__init__(path="/nonexistent/x.json", hasher=lambda path, host: "sha_" + os.path.basename(os.path.dirname(path or "x/")))


def spec(item, tree, die="qwen_compute"):
    return dict(die=die, item=item, gen_host="e8", plan=f"/t/{tree}/plan.json")


def test_newest_launched_plan_wins_over_a_newer_mtime_of_an_older_plan(tmp_path):
    c = coord(tmp_path, [("QC", "cbf_q01", "PROBE-THROUGH")], [
        ("L", "old", "2026-11-23 10:00", spec("cbf_q01", "R6V2"), dict(stage="grt", verdict="FAIL", geom_dir="e7:/old/geom", kit="e7:/old/gen")),
        ("L", "new", "2026-11-24 05:24", spec("cbf_q01", "C1h"), dict(stage="place", verdict="PASS", geom_dir="e8:/new/geom", kit="e8:/new/gen"))])
    os.utime(c / "autopilot/private_specs/L/old/spec.json", (NOW, NOW))          # old plan touched last: mtime must not decide
    os.utime(c / "autopilot/private_specs/L/new/spec.json", (NOW - 3600, NOW - 3600))
    rows = PV.rows_for_queue(str(c), {}, lambda r: "", cache=FakeCache())
    assert [(r[1], r[3], r[4]) for r in rows] == [("cbf_q01", "new", "WAIT-VISUAL-PROBE-PLACE@sha_C1h")]


def test_no_render_on_the_current_plan_lists_nothing_not_the_old_plan(tmp_path):
    c = coord(tmp_path, [("QC", "cbf_q01", "PROBE-THROUGH")], [
        ("L", "old", "2026-11-23 10:00", spec("cbf_q01", "R6V2"), dict(stage="grt", verdict="PASS", geom_dir="e7:/old/geom")),
        ("L", "new", "2026-11-24 05:24", spec("cbf_q01", "C1h"), dict(stage="chain_probe", verdict="PASS"))])
    assert PV.rows_for_queue(str(c), {}, lambda r: "", cache=FakeCache()) == []


def test_same_plan_newer_kit_with_render_and_non_probe_rows_skipped(tmp_path):
    c = coord(tmp_path, [("KV", "kv3_pv", "PROBE-THROUGH"), ("KV", "kv3_hg", "DRAFT")], [
        ("L", "a1", "2026-11-24 04:00", spec("kv3_pv", "A5t3", "qwen_kvsys"), dict(stage="place", verdict="PASS", geom_dir="e7:/a1/geom", kit="e7:/a1")),
        ("L", "a2", "2026-11-24 04:30", spec("kv3_pv", "A5t3", "qwen_kvsys"), dict(stage="grt", verdict="FAIL", geom_dir="e8:/a2/geom", kit="e8:/a2")),
        ("L", "b", "2026-11-24 04:30", spec("kv3_hg", "A5t3", "qwen_kvsys"), dict(stage="place", verdict="PASS", geom_dir="e7:/g"))])
    rows = PV.rows_for_queue(str(c), {}, lambda r: "", cache=FakeCache())
    assert [(r[1], r[3], r[4], r[7]) for r in rows] == [("kv3_pv", "a2", "WAIT-VISUAL-PROBE-GRT-FAILED@sha_A5t3", "e8")]


def test_wave_records_of_an_older_event_are_never_candidates(tmp_path):
    c = coord(tmp_path, [("S81", "serdes__t13", "PROBE-THROUGH")])
    items = {"old": dict(die="s81", item="serdes__t13", attempt=1, event="18a2688b741", status="ROUTE-HELD", geom_dir="e9:/o/geom", kit="e9:/o", started=NOW),
             "cur": dict(die="s81", item="serdes__t13", attempt=2, event="891100ef774", status="ENQUEUED", geom_dir="e9:/c/geom", kit="e9:/c", started=NOW - 10)}
    die_cur = {"s81": ("891100ef774", "/t/c8/plan.json", "e8")}
    rows = PV.rows_for_queue(str(c), items, K.review_kit_location, die_cur=die_cur, cache=FakeCache())
    assert [(r[1], r[3], r[4]) for r in rows] == [("serdes__t13", "2", "WAIT-VISUAL-PROBE-GRT@sha_c8")]
    assert PV.rows_for_queue(str(c), {"old": items["old"]}, K.review_kit_location, die_cur=die_cur, cache=FakeCache()) == []


def test_no_coverage_table_means_no_probe_rows(tmp_path):
    assert PV.rows_for_queue(str(tmp_path / "none"), {}, lambda r: "", cache=FakeCache()) == []


def test_publish_appends_probe_rows_and_keeps_the_wave_count(tmp_path, monkeypatch):
    c = coord(tmp_path, [("QC", "cbf_q01", "PROBE-THROUGH")], [
        ("L", "s", "2026-11-24 05:24", spec("cbf_q01", "C1h"), dict(stage="place", verdict="PASS", geom_dir="e8:/q/geom", kit="e8:/q/gen/cbf_q01"))])
    monkeypatch.setattr(K.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(K.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(PV, "file_sha", lambda path, host=None, timeout=20: "sha_test")
    monkeypatch.setattr(PV, "SHA_CACHE", str(tmp_path / "shacache.json"))
    monkeypatch.setattr(PV.ShaCache.__init__, "__defaults__", (str(tmp_path / "shacache.json"), lambda p, h: "sha_test"))
    assert K.visual_queue_publish({"dies": {}}, {"items": {}}) == 0
    body = (c / "lanes" / "VISUAL-QUEUE.tsv").read_text().splitlines()
    assert len(body) == 2 and body[1].split("\t")[4] == "WAIT-VISUAL-PROBE-PLACE@sha_test"
    (c / "lanes" / "VISUAL-QUEUE.tsv").unlink()
    K.visual_queue_publish({"dies": {}, "probe_visual_feed": False}, {"items": {}})
    assert len((c / "lanes" / "VISUAL-QUEUE.tsv").read_text().splitlines()) == 1
