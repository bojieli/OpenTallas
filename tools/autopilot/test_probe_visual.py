"""VIS-REOWN 11-24: PROBE-THROUGH kits feed lanes/VISUAL-QUEUE.tsv (probe_visual + kit_wave.visual_queue_publish)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import probe_visual as PV
import kit_wave as K

HDR = "# h\ndie\ttype\tfamily\tvis_lane\trender_paths\tverdict\tcause_class\tstructural_row\trow_status\tupdated\n"


def coord(tmp, rows, results=()):
    c = tmp / "coord"
    (c / "lanes").mkdir(parents=True)
    (c / "lanes" / "VIS-COVERAGE.tsv").write_text(HDR + "".join(f"{d}\t{t}\t{t}\tV\t-\tv\tc\tsr\t{s}\tu\n" for d, t, s in rows))
    for lane, spec, d in results:
        p = c / "autopilot" / "private_specs" / lane / spec
        p.mkdir(parents=True)
        (p / "result.json").write_text(json.dumps(d))
    return c


def test_private_probe_kits_with_a_render_are_listed_newest_per_type(tmp_path):
    c = coord(tmp_path, [("KV", "kv3_pv", "PROBE-THROUGH"), ("KV", "kv3_hg", "DRAFT"), ("QC", "glue", "PROBE-PASS")], [
        ("L", "a1", dict(die="qwen_kvsys", item="kv3_pv", stage="place", verdict="PASS", geom_dir="e7:/k/geom", kit="e7:/k/gen/kv3_pv")),
        ("L", "a2", dict(die="qwen_kvsys", item="kv3_pv", stage="grt", verdict="FAIL", geom_dir="e8:/k2/geom", kit="e8:/k2/gen/kv3_pv")),
        ("L", "b", dict(die="qwen_kvsys", item="kv3_hg", stage="place", verdict="PASS", geom_dir="e7:/g")),           # DRAFT: not a probe row
        ("L", "c", dict(die="qwen_compute", item="glue", stage="grt", verdict="PASS", geom_dir="e7:/g")),             # PROBE-PASS: reviewed
        ("L", "d", dict(die="qwen_kvsys", item="kv3_pv_v9", stage="gen", verdict="FAIL")),                             # no render
    ])
    os.utime(c / "autopilot/private_specs/L/a1/result.json", (time.time() - 100, time.time() - 100))
    rows = PV.rows_for_queue(str(c), {}, lambda r: "")
    assert [(r[1], r[3], r[4], r[7]) for r in rows] == [("kv3_pv", "a2", "WAIT-VISUAL-PROBE-GRT-FAILED", "e8")]
    assert rows[0][5] == "e8:/k2/gen/kv3_pv/run/layout_review" and rows[0][6] == "e8:/k2/geom/auto_geom.png"


def test_wave_records_and_variants_of_probe_rows(tmp_path):
    c = coord(tmp_path, [("S81", "s81sl_leaf__t1", "PROBE-THROUGH")])
    items = {"x": dict(die="s81", item="ot_s81sl_leaf__t1", attempt=2, status="ENQUEUED", geom_dir="e9:/w/geom", kit="e9:/w/gen"),
             "y": dict(die="s81", item="ot_s81sl_leaf__t1", attempt=1, status="SIGNED", geom_dir="e9:/v/geom"),
             "z": dict(die="s81", item="ot_s81sl_leaf__t1", attempt=3, status="FAIL", geom_dir="e9:/z/geom")}
    rows = PV.rows_for_queue(str(c), items, K.review_kit_location)
    assert [(r[1], r[3], r[4]) for r in rows] == [("ot_s81sl_leaf__t1", "2", "WAIT-VISUAL-PROBE-GRT")]
    assert PV.rows_for_queue(str(c), items, K.review_kit_location, listed={("s81", "ot_s81sl_leaf__t1")}) == []


def test_no_coverage_table_means_no_probe_rows(tmp_path):
    assert PV.rows_for_queue(str(tmp_path / "none"), {}, lambda r: "") == []


def test_publish_appends_probe_rows_and_keeps_the_wave_count(tmp_path, monkeypatch):
    c = coord(tmp_path, [("QC", "cbf_q01", "PROBE-THROUGH")], [
        ("L", "s", dict(die="qwen_compute", item="cbf_q01", stage="place", verdict="PASS", geom_dir="e8:/q/geom", kit="e8:/q/gen/cbf_q01"))])
    monkeypatch.setattr(K.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(K.subprocess, "run", lambda *a, **k: None)
    assert K.visual_queue_publish({"dies": {}}, {"items": {}}) == 0
    body = (c / "lanes" / "VISUAL-QUEUE.tsv").read_text().splitlines()
    assert len(body) == 2 and body[1].split("\t")[1:5] == ["cbf_q01", body[1].split("\t")[2], "s", "WAIT-VISUAL-PROBE-PLACE"]
    (c / "lanes" / "VISUAL-QUEUE.tsv").unlink()
    K.visual_queue_publish({"dies": {}, "probe_visual_feed": False}, {"items": {}})
    assert len((c / "lanes" / "VISUAL-QUEUE.tsv").read_text().splitlines()) == 1
