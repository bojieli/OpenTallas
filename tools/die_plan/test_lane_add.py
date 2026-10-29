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


def _builder_raw():
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["partition_types"]["mid2"] = json.loads(json.dumps(raw["partition_types"]["mid"]))
    next(p for p in raw["partitions"] if p["name"] == "pm2")["type"] = "mid2"
    return raw


def test_final_natural_landing_latency_rejects_and_restores(monkeypatch):
    raw = _builder_raw()
    before = json.loads(json.dumps(raw))
    natural = S.Plan.lane_natural

    def with_new_landing(plan, lid):
        d = natural(plan, lid)
        if lid.startswith("L16"):
            d["clock_landing"] = 3
            d["cycles"] += 3
        return d

    monkeypatch.setattr(S.Plan, "lane_natural", with_new_landing)
    b = lane_add.Builder(raw)
    b.build([dict(src="pa", dst="pm1", unplanned_bits=24)])
    assert not b.report["built"] and len(b.report["failed"]) == 1
    assert "including clock landings" in b.report["failed"][0]["why"]
    assert raw == before and b.next_id == 160 and not b.ids
    assert not any(b.taken.values())


def test_parallel_word_parts_must_have_identical_actual_cycles(monkeypatch):
    raw = _builder_raw()
    before = json.loads(json.dumps(raw))
    b = lane_add.Builder(raw)
    alloc, stations = b.alloc, b.stations_for
    monkeypatch.setattr(b, "alloc", lambda a, z, width, prefer=None:
                        None if width > 70 else alloc(a, z, width, prefer))
    count = [0]

    def varied(*args):
        k, seg, length = stations(*args)
        count[0] += 1
        return k + (count[0] % 2), seg, length

    monkeypatch.setattr(b, "stations_for", varied)
    b.build([dict(src="pa", dst="pm2", unplanned_bits=128)])
    assert not b.report["built"] and len(b.report["failed"]) == 1
    assert "split cycles" in b.report["failed"][0]["why"]
    assert raw == before and b.next_id == 160 and not any(b.taken.values())


def test_near_mirror_keeps_the_split_index():
    base = _builder_raw()
    raw = json.loads(json.dumps(base))
    raw["partition_types"], raw["partitions"], raw["ports"], raw["lanes"] = {}, [], [], []
    raw["latency"]["lanes"] = {}
    for prefix, dy in (("NW_", 0), ("NE_", 1728)):
        for tn, t in base["partition_types"].items():
            raw["partition_types"][prefix + tn] = json.loads(json.dumps(t))
        for src in base["partitions"]:
            p = json.loads(json.dumps(src))
            p["name"], p["type"] = prefix + p["name"], prefix + p["type"]
            p["origin_um"][1] += dy
            raw["partitions"].append(p)
        for src in base["ports"]:
            p = json.loads(json.dumps(src)); p["id"] = prefix + p["id"]
            for end in ("src", "dst"):
                if p[end]["part"] != S.DIE_PART:
                    p[end]["part"] = prefix + p[end]["part"]
            if p.get("face") in ("E", "W"):
                p["window_um"] = [x + dy for x in p["window_um"]]
            raw["ports"].append(p)
        for src in base["lanes"]:
            q = json.loads(json.dumps(src)); q["id"] = prefix + q["id"]
            q["ports"] = [prefix + x for x in q["ports"]]
            raw["lanes"].append(q)
        for lid, ent in base["latency"]["lanes"].items():
            raw["latency"]["lanes"][prefix + lid] = json.loads(json.dumps(ent))
    b = lane_add.Builder(raw)
    b.build([dict(src="NW_pa", dst="NW_pm2", unplanned_bits=12),
             dict(src="NE_pa", dst="NE_pm2", unplanned_bits=12)])
    assert not b.report["failed"]
    assert [r["lane"] for r in b.report["built"]] == ["L160", "L160m"]


def test_macro_station_halo_is_the_existing_resite_halo():
    raw = _builder_raw()
    raw["partition_types"]["mid"]["hard_cores"] = [dict(
        inst="core", origin_um=[100, 100], outline_um=[100, 100], module="core")]
    b = lane_add.Builder(raw)
    # Type x98 lies outside the core body but inside its existing 4.32-um station halo.
    assert b.macro_hits("pm1", [b.P.to_die("pm1", (98, 150))]) == 1
    assert b.macro_hits("pm1", [b.P.to_die("pm1", (94, 150))]) == 0
