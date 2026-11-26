"""GRT-EST-OPTIMISTIC (QC-INT-R2-TOOLS 11-26): per-family multipliers from measured overflow, read by adv_route_demand in advisory mode."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_route_demand as RD  # noqa: E402
import grt_est_calibrate as GC  # noqa: E402

RAW = {"partition_types": {f"sle_fw_v{i}": {} for i in range(1, 5)} | {"coll_core": {}, "sle_st_a_v1": {}, "sle_fe_v1": {}, "glue": {}}}
PEAK = {"sle_fw_v1": 0.4, "sle_fw_v2": 0.5, "sle_fw_v3": 0.2, "sle_fw_v4": 0.3, "coll_core": 0.6, "sle_st_a_v1": 0.5, "sle_fe_v1": 0.1, "glue": 0.9}


def _peak(t):
    return None


def _build(rows):
    raw = {"partition_types": {n: {"name": n} for n in RAW["partition_types"]}}
    return GC.build(raw, rows, peak_fn=lambda t: PEAK[t["name"]])


def test_families():
    assert [GC.family_of(x) for x in ("sle_fw_v2__cl1", "slw_fe_v1", "slw_st_a_v1__clx", "coll_ft__cla4", "glue", "slw_fwx")] == ["fw", "fe", "st_a", "coll", None, None]


def test_multiplier_from_bad_types():
    cal = _build([("sle_fw_v1", 40000), ("sle_fw_v2", 30000), ("sle_fw_v3", 0), ("sle_fw_v4", 100), ("coll_core", 47000)])
    fw = cal["families"]["fw"]
    assert fw["status"] == "calibrated" and fw["n_bad"] == 2 and fw["median_bad_est_peak"] == 0.45
    assert fw["multiplier"] == round(0.8 / 0.45, 3) and fw["clean_false_alarms"] == 0 and fw["n_clean"] == 2
    assert cal["families"]["coll"]["status"] == "no-data" and cal["families"]["coll"]["multiplier"] == 1.0    # one bad type is under MIN_BAD
    assert cal["families"]["fe"]["n"] == 0 and cal["families"]["st_a"]["multiplier"] == 1.0


def test_clean_false_alarm_price_and_clamp():
    cal = _build([("sle_fw_v3", 20000), ("sle_fw_v1", 30000), ("sle_fw_v2", 50), ("sle_fw_v4", 10)])
    fw = cal["families"]["fw"]
    assert fw["multiplier"] == round(0.8 / 0.3, 3) and fw["clean_false_alarms"] == 2      # v2 (0.5) and v4 (0.3) x 2.667 reach 0.8
    cal2 = _build([("sle_fw_v3", 20000), ("sle_fw_v3", 30000)])
    assert cal2["families"]["fw"]["multiplier"] == GC.M_MAX


def test_triage_rows_and_resolve(tmp_path):
    t = tmp_path / "t.tsv"
    t.write_text("# c\ndie\ttype\thost\toverflow_latest\nQC\tcoll_core\th\t47612\nKV\tkit\th\t3621\nQC\tsle_ctl\th\t\n")
    assert GC.triage_rows(t) == [("coll_core", 47612.0)]
    assert GC.resolve({"partition_types": {"sle_ctl__clabc": {}}}, "sle_ctl") == "sle_ctl__clabc"
    assert GC.resolve({"partition_types": {}}, "zzz") is None


def test_route_demand_reads_the_calibration(tmp_path, monkeypatch):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"families": {"fw": {"multiplier": 2.5, "status": "calibrated"}, "coll": {"multiplier": 3.0, "status": "no-data"}}}))
    monkeypatch.setenv("OT_GRT_CALIB_JSON", str(f))
    RD._CALIB.clear()
    assert RD.type_multiplier("sle_fw_v2") == (2.5, "fw")
    assert RD.type_multiplier("coll_core") == (1.0, "coll")          # a no-data family is never scaled
    assert RD.type_multiplier("glue") == (1.0, None)
    monkeypatch.setenv("OT_GRT_CALIB_JSON", str(tmp_path / "missing.json"))
    assert RD.type_multiplier("sle_fw_v2") == (1.0, "fw")
    RD._CALIB.clear()
