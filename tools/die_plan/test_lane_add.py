"""lane_add.py (opt-in): S1 unplanned pairs -> plan lanes on the 4-partition tiny example."""
import json
from pathlib import Path

import lane_add
import schema as S

HERE = Path(__file__).resolve().parent


def _run(tmp_path, rows, split_mid=True):
    base = tmp_path / "base"
    base.mkdir()
    raw = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
    if split_mid:      # one type per partition (new buses on a shared type would leave the other instance unbound)
        raw["partition_types"]["mid2"] = json.loads(json.dumps(raw["partition_types"]["mid"]))
        next(p for p in raw["partitions"] if p["name"] == "pm2")["type"] = "mid2"
    (base / "die_plan.json").write_text(json.dumps(raw))
    pairs = tmp_path / "pairs.json"
    pairs.write_text(json.dumps(rows))
    rep = lane_add.run(base, pairs, tmp_path / "out")
    raw = json.loads((tmp_path / "out" / "die_plan.json").read_text())
    return rep, raw, S.Plan(raw)


def test_adjacent_near_far(tmp_path):
    rows = [dict(src="pa", dst="pm1", unplanned_bits=24),    # abutted: one boundary port
            dict(src="pa", dst="pm2", unplanned_bits=12),    # 864-um gap <= near: ft slot through pm1
            dict(src="pa", dst="pb", unplanned_bits=40)]     # 1728-um gap > near: report only
    rep, raw, P = _run(tmp_path, rows)
    t = rep["totals"]
    assert (t["built"], t["far"], t["failed"]) == (2, 1, 0)
    assert rep["far"][0]["src"] == "pa" and rep["far"][0]["dst"] == "pb"
    built = {(x["src"], x["dst"]): x for x in rep["built"]}
    adj, near = built[("pa", "pm1")], built[("pa", "pm2")]
    assert adj["kind"] == "adj" and adj["chain"] == ["pa", "pm1"] and adj["cycles"] == 2
    assert near["chain"] == ["pa", "pm1", "pm2"] and near["crossings"][0]["part"] == "pm1"
    assert near["cycles"] == 2 + near["stations"] and near["macro_hits"] == 0
    for x in (adj, near):
        lid = x["lane"]
        assert lid in P.lanes
        ent = raw["latency"]["lanes"][lid]
        assert ent["cycles"] == x["cycles"] and ent["pad"] == 0 and ent["param"] == "LAT_" + lid.upper()
        for q in P.lanes[lid]["ports"]:
            p = P.ports[q]
            assert p["width"] == x["bits"]
            for end in ("src", "dst"):         # every port end is a type bus or an ft slot (<slot>_i/_o)
                ty = P.ptype(p[end]["part"])
                tb = {b["name"]: b for b in ty["buses"]}
                slots = {f["name"]: f for f in ty.get("ft_slots", [])}
                bus = p[end]["bus"]
                if bus in tb:
                    assert tb[bus]["width"] == x["bits"]
                else:
                    assert bus[:-2] in slots and slots[bus[:-2]]["width"] == x["bits"]
    # original lanes untouched
    orig = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
    assert [l["id"] for l in raw["lanes"]][:len(orig["lanes"])] == [l["id"] for l in orig["lanes"]]


def test_windows_do_not_overlap(tmp_path):
    rows = [dict(src="pa", dst="pm1", unplanned_bits=16), dict(src="pm1", dst="pa", unplanned_bits=16)]
    rep, raw, P = _run(tmp_path, rows)
    assert rep["totals"]["built"] == 2
    w = sorted(tuple(x["windows"][0]["window_um"]) for x in rep["built"])
    assert w[0][1] <= w[1][0]


def test_shared_type_refused(tmp_path):
    rep, raw, P = _run(tmp_path, [dict(src="pa", dst="pm1", unplanned_bits=8)], split_mid=False)
    assert rep["totals"]["built"] == 0 and "shared" in rep["failed"][0]["why"]


def test_output_passes_g0(tmp_path):
    import check
    _run(tmp_path, [dict(src="pa", dst="pm1", unplanned_bits=24), dict(src="pa", dst="pm2", unplanned_bits=12)])
    assert check.main([str(tmp_path / "out" / "die_plan.json"), "--out", str(tmp_path / "g0")]) == 0


def test_capacity_failure_never_publishes_partial_pair(tmp_path):
    rep, raw, P = _run(tmp_path, [dict(src="pa", dst="pm1", unplanned_bits=8192)])
    assert rep["totals"]["built"] == 0
    assert rep["totals"]["failed"] == 1
    assert rep["failed"][0]["bits"] == 8192
    assert not any(x["id"].startswith("L16") for x in raw["lanes"])
    assert not any(b["name"].startswith("L16") for t in raw["partition_types"].values() for b in t["buses"])


def test_station_spacing_uses_existing_layer_margin(tmp_path):
    rep, raw, P = _run(tmp_path, [dict(src="pa", dst="pm2", unplanned_bits=12)])
    b = lane_add.Builder(raw)
    assert abs(b.reach - 364.5) < 1e-6
    x = rep["built"][0]
    for slot in x["crossings"]:
        assert slot["route_um"] / slot["stations"] <= b.reach
