"""ADV-STN-CONFLICT on the VIS-S81-MISC gate 10 positive (iqf idx_o0: qr 149 bits + qr_v 1 bit, own geometry each)."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_stn_conflict as A  # noqa: E402


def _iqf():
    t = {"outline_um": [1442.88, 2980.8], "buses": [{"name": "idx_o0", "dir": "out", "width": 150}],
         "internal_stations": [
             {"conn": "bus:idx_o0", "regs_um": [[700.0, 1200.0]], "bits": 149, "note": "J8 qr"},
             {"conn": "bus:idx_o0", "regs_um": [[690.0, 1210.0]], "bits": 1, "note": "J8 qr_v"}]}
    return {"partition_types": {"iqf__t1": t}, "partitions": [{"name": "iqf0", "type": "iqf__t1"}]}


AB = {"internal_stations_types": ["iqf"]}


def test_iqf_positive_out_conflict():
    out = A.findings(_iqf(), "p.json", asbuilt=AB)
    assert any("iqf__t1: CONFLICT bus idx_o0 (out)" in x and "conflicting OUT station geometry idx_o0" in x for x in out), out


def test_one_row_clean_and_note_only_difference_clean():
    raw = _iqf()
    t = raw["partition_types"]["iqf__t1"]
    t["internal_stations"][1] = dict(t["internal_stations"][0], note="other")
    assert A.findings(raw, "p.json", asbuilt=AB) == []
    del t["internal_stations"][1]
    assert A.findings(raw, "p.json", asbuilt=AB) == []


def test_kit_type_out_rows_counted_not_listed():
    out = A.findings(_iqf(), "p.json", asbuilt={"internal_stations_types": ["other"]})
    assert not any("iqf__t1:" in x for x in out)


def test_in_bus_per_core_rows_are_merged_not_flagged():
    raw = _iqf()
    t = raw["partition_types"]["iqf__t1"]
    t["buses"][0]["dir"] = "in"
    for r in t["internal_stations"]:
        r["bits"] = 64
    assert A.findings(raw, "p.json") == []
    t["internal_stations"][0]["bit_sites_um"] = [[1.0, 1.0]]
    t["internal_stations"][0]["regs_um"].append([700.0, 800.0])
    assert any("conflicting destination station counts" in x for x in A.findings(raw, "p.json"))


def test_valid_bus_stationed_apart():
    t = {"buses": [{"name": "rq", "dir": "out"}, {"name": "rq_v", "dir": "out"}],
         "internal_stations": [{"conn": "bus:rq", "regs_um": [[1, 1], [2, 2]]}, {"conn": "bus:rq_v", "regs_um": [[1, 1]]}]}
    raw = {"partition_types": {"x": t}}
    assert any("VALID-SPLIT bus rq_v" in x for x in A.findings(raw, "p.json"))
    t["internal_stations"][1]["regs_um"] = [[1, 1], [2, 2]]
    assert A.findings(raw, "p.json") == []
