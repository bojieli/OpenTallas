"""pytest: ADV-SINKBIN-AGE (report-only): sink bins older than the type's latest placed DB (C-TAP-LOAD / P-STALE-TABLE)."""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_sinkbin_age as A  # noqa: E402

NOW = datetime.datetime(2026, 11, 27, tzinfo=datetime.timezone.utc)
D1104 = datetime.datetime(2026, 11, 4, tzinfo=datetime.timezone.utc).timestamp()
D1126 = datetime.datetime(2026, 11, 26, tzinfo=datetime.timezone.utc).timestamp()


def plan(*types):
    return {"partition_types": {t: {"outline_um": [100, 100], "clock": {"tap_mode": "density", "sink_bins_file": f"{t}.json"}} for t in types},
            "partitions": [{"name": f"p_{t}", "type": t} for t in types]}


def bins(tmp, name, **doc):
    (tmp / f"{name}.json").write_text(json.dumps(dict(bins=[[1, 1, 5]], **doc)))


def test_provenance_day_before_latest_placement_is_stale(tmp_path):
    bins(tmp_path, "A", source="DIE-QC-70 11-04 wave A attempt_4 3_place.odb all_registers")
    cache = {"placed_bins": {"A": {"ts": D1126, "kit": "h:A-route-x"}}}
    rows, s = A.census(plan("A"), str(tmp_path / "p.json"), str(tmp_path), cache=cache, kit_sinks={})
    assert rows[0]["verdict"] == "STALE" and rows[0]["basis"] == "provenance day"
    assert s["stale"] == 1 and s["stale_by_basis"] == {"provenance day": 1}
    out = A.findings(plan("A"), str(tmp_path / "p.json"), str(tmp_path), cache=cache, kit_sinks={})
    assert out[0].startswith("WARN ADV-SINKBIN-AGE A:") and "older than the type's latest placed DB" in out[0]
    assert "1 of 1 types" in out[-1] and "report-only" in out[-1]


def test_epoch_provenance_newer_than_placement_is_fresh(tmp_path):
    bins(tmp_path, "A", source="wave A kit A-route-h-1795235359", placed_kit="A")
    cache = {"placed_bins": {"A": {"ts": 1795235359 - 7200, "kit": "h:A-route-x"}}}
    rows, _ = A.census(plan("A"), str(tmp_path / "p.json"), str(tmp_path), cache=cache, kit_sinks={})
    assert rows[0]["verdict"] == "FRESH" and rows[0]["basis"] == "provenance epoch"


def test_same_day_placement_is_not_flagged_on_day_granular_stamp(tmp_path):
    bins(tmp_path, "A", source="wave 11-26 A")
    cache = {"placed_bins": {"A": {"ts": D1126 + 3600 * 14, "kit": "k"}}}
    rows, _ = A.census(plan("A"), str(tmp_path / "p.json"), str(tmp_path), cache=cache, kit_sinks={})
    assert rows[0]["verdict"] == "FRESH"


def test_doc_stamp_wins_and_kit_cts_mtime_counts(tmp_path):
    bins(tmp_path, "A", created=D1104, source="wave 11-26")
    rows, _ = A.census(plan("A"), str(tmp_path / "p.json"), str(tmp_path), cache={}, kit_sinks={"A": {"mtime": D1126}})
    assert rows[0]["verdict"] == "STALE" and rows[0]["basis"] == "doc created" and rows[0]["placed_what"] == "kit CTS log"


def test_file_mtime_is_the_weak_fallback(tmp_path):
    bins(tmp_path, "A", source="no stamp here")
    os.utime(tmp_path / "A.json", (D1104, D1104))
    cache = {"placed_bins": {"A": {"ts": D1126, "kit": "k"}}}
    rows, s = A.census(plan("A"), str(tmp_path / "p.json"), str(tmp_path), cache=cache, kit_sinks={})
    assert rows[0]["verdict"] == "STALE" and rows[0]["basis"] == "file mtime" and s["weak_mtime_basis"] == 1


def test_no_placed_record_and_no_bins_are_not_checked(tmp_path):
    bins(tmp_path, "A", source="wave 11-04")
    p = plan("A", "B")
    p["partition_types"]["C"] = {"outline_um": [1, 1], "clock": {"tap_mode": "density"}}
    p["partitions"].append({"name": "pc", "type": "C"})
    rows, s = A.census(p, str(tmp_path / "p.json"), str(tmp_path), cache={}, kit_sinks={})
    v = {r["type"]: r for r in rows}
    assert v["A"]["verdict"] == v["B"]["verdict"] == v["C"]["verdict"] == "NOT-CHECKED"
    assert v["B"]["why"] == "sink bins file not found" and v["C"]["why"] == "density type without sink bins"
    assert s["not_checked"] == 3 and s["stale"] == 0


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-SINKBIN-AGE not checked")
