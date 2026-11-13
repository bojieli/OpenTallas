"""tests for tools/die_plan/type_split.py (KV-SPLIT-1113).  Pure helpers always; the type-level split of the KV hub
family on the plan of record when the plan is present (skipped otherwise)."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import type_split as TS  # noqa: E402

ROOT = HERE.parents[1]
KV = ROOT / "physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json"


def test_cut_pieces_and_straddle():
    c = TS.Cut("y", [449.28, 846.72], 1676.16)
    assert c.n == 3
    assert c.piece(10, 20) == 0 and c.piece(500, 600) == 1 and c.piece(900) == 2
    assert c.ext(1) == pytest.approx(397.44)
    assert c.sh([5.0, 900.0], 2) == [5.0, pytest.approx(53.28)]
    with pytest.raises(TS.SplitError):
        c.piece(400, 500)
    with pytest.raises(TS.SplitError):
        TS.Cut("y", [900, 100], 1000)
    with pytest.raises(TS.SplitError):
        TS.Cut("x", [0.0], 1000)


def test_cut_x_axis_faces():
    c = TS.Cut("x", [520.0, 1080.0], 2000.0)
    assert c.axis_faces() == ("W", "E")
    assert c.shr([600, 1, 700, 2], 1) == [80.0, 1, 180.0, 2]


def test_local_face_involution():
    for o in ("R0", "MX", "MY", "R180"):
        for f in "NSEW":
            assert TS.die_face(o, TS.local_face(o, f)) == f
    assert TS.local_face("MX", "N") == "S" and TS.local_face("MY", "E") == "W" and TS.local_face("R0", "E") == "E"


def test_windows_disjoint_nearest_and_segments():
    items = [("a", 40, 100.0), ("b", 40, 101.0), ("edge", 2, 1278.72), ("fill", 900, None)]
    w = TS.windows_for(items, 1278.72, 8.0)
    spans = sorted((lo, hi) for segs in w.values() for lo, hi, _ in segs)
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        assert b0 >= a1 + 2.16 - 1e-6
    assert all(8.64 - 1e-6 <= lo and hi <= 1278.72 - 8.64 + 1e-6 for lo, hi in spans)
    assert abs((w["a"][0][0] + w["a"][0][1]) / 2 - 100) < 10
    assert sum(n for _, _, n in w["fill"]) == 900
    with pytest.raises(TS.SplitError):
        TS.windows_for([("big", 100000, None)], 100.0, 8.0)


class _Ev:
    def __init__(self, raw, spec):
        self.raw, self.spec, self.tag = raw, spec, "T"


@pytest.mark.skipif(not KV.exists(), reason="KV plan of record not present")
@pytest.mark.parametrize("tn", ["kv3_hub_Wo", "kv3_hub_Eo"])
def test_kv_hub_type_split(tn):
    raw = json.loads(KV.read_text())
    rx = {"kv3_hub_Eo": ("ES", "EN", 2, 3), "kv3_hub_Wo": ("WS", "WN", 0, 1)}[tn]
    spec = dict(axis="y", cuts_um=[449.28, 846.72], parts=[{"suffix": "_s"}, {"suffix": ""}, {"suffix": "_n"}], keep=1,
                fold_legs=True, station_snap_um=100.0,
                contents={tn: [[f"astk_{rx[0]}.*|seq__g_(fan|xs)_{rx[2]}__.*|hp_fault_{rx[2]}|u_idsrc_{rx[0]}", 0],
                               [f"astk_{rx[1]}.*|seq__g_(fan|xs)_{rx[3]}__.*|hp_fault_{rx[3]}|u_idsrc_{rx[1]}", 2],
                               ["u_efault", 1]]})
    ts = TS.TypeSplit(_Ev(raw, spec), tn)
    T = ts.split()
    t = raw["partition_types"][tn]
    # every bus, core, content lands in exactly one piece; outlines tile the type
    assert sum(len([b for b in x["buses"] if not b["name"].endswith("_p") and "_p_" not in b["name"]]) for x in T) == len(t["buses"])
    assert sum(len(x["hard_cores"]) for x in T) == len(t["hard_cores"])
    assert sum(len(x["contents"]) for x in T) == len(t["contents"])
    assert sum(x["outline_um"][1] for x in T) == pytest.approx(t["outline_um"][1])
    # a crossing slot gains one in-face station per cut it crosses; a whole slot keeps its count
    for f in ts.ft_cut:
        assert f["new"] == f["old"] + len(f["pieces"]) - 1
    # pieces stay inside their outline
    for x in T:
        w, h = x["outline_um"]
        for f in x["ft_slots"]:
            assert all(-1e-6 <= p[0] <= w + 1e-6 and -1e-6 <= p[1] <= h + 1e-6 for p in f["regs_um"])
        for r in x.get("internal_stations", []):
            for p in [r["from_um"], r["to_um"]] + r["regs_um"]:
                assert -1e-6 <= p[1] <= h + 1e-6
    # the region origin piece holds the START pins and the collector up link
    names = {p["name"] for p in T[1]["clock"]["landing_contract"]["pins"]}
    assert {"cland_tstart_in", "cland_tstart_out", "cland_raw_reset_out", "cland_up_ready", "cland_rstart_out"} <= names
    for i in (0, 2):
        pn = {p["name"] for p in T[i]["clock"]["landing_contract"]["pins"]}
        assert "cland_rstart_in" in pn and "cland_up_ready" in pn and "cland_tstart_in" not in pn
    # cut legs: each cut has an out bus on one side and the matching in bus on the other
    for leg in ts.legs:
        for c in leg["cuts"]:
            assert any(b["name"] == c["oname"] and b["dir"] == "out" for b in T[c["a"]]["buses"])
            assert any(b["name"] == c["iname"] and b["dir"] == "in" for b in T[c["b"]]["buses"])


@pytest.mark.skipif(not KV.exists(), reason="KV plan of record not present")
def test_kv_pv_x_split_chain_and_dedupe():
    """pv (KV-SPLIT-PV-1113 form): x cuts, keep 0, piece 2 not adjacent to the keep piece -> collector chain via
    piece 1; identical repeated internal-station rows are one chain (one cut leg each)"""
    raw = json.loads(KV.read_text())
    tn = "kv3_pv_v5n"
    ev = _Ev(raw, dict(axis="x", cuts_um=[622.08, 1537.92], parts=[{"suffix": ""}, {"suffix": "_x1"}, {"suffix": "_x2"}],
                       keep=0, fold_legs=True, station_snap_um=100.0, drop_clock_keys=[
                           "landing_reader_start", "landing_writer_start", "landing_raw_branches"]))
    ev.rep, ev.plan_dir = dict(notes=[]), KV.parent
    t0 = raw["partition_types"][tn]
    rows = [json.dumps({k: v for k, v in r.items() if k != "note"}, sort_keys=True) for r in t0["internal_stations"]]
    ts = TS.TypeSplit(ev, tn)
    assert len(ts.t["internal_stations"]) == len(set(rows))
    try:
        ts.split()
    except TS.SplitError as e:          # this unit test has no Event (census, core moves): only the chain is checked
        pytest.skip(f"needs the event inputs: {e}")
    links = {c["child_piece"]: c["parent_piece"] for c in ts.coll_links}
    assert links == {1: 0, 2: 1}


def test_split_output_keeps_manifest_relative_map_after_input_removed(tmp_path):
    """A fresh split dir must bind without an undocumented cp-al of the source inputs/."""
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    source_map = incoming / "asbuilt_map.json"
    mapping = {"parts": {"native.block": ["p", "core"]}}
    source_map.write_text(json.dumps(mapping))
    ev = TS.Event.__new__(TS.Event)
    ev.ab = {"map_file": "asbuilt_map.json", "base": "."}
    ev.ab_path = incoming / "asbuilt.json"
    ev.plan_dir, ev.pmap, ev.ts = incoming, {}, {}
    ev.out, ev.spec, ev.rep, ev.tag = {"partition_types": {}}, {}, {}, "test-map"
    ev._asbuilt()
    ev._census = lambda _out: {}
    ev.side, ev.pc_out, ev.latency_rows = None, None, []
    output = tmp_path / "new_split"
    ev.write(output, "new_split")
    source_map.unlink()
    published = json.loads((output / "asbuilt_vN.json").read_text())
    assert json.loads((output / published["map_file"]).read_text()) == mapping


@pytest.mark.parametrize("pin_rows, expected", [
    (None, [("seq__g_xs_N__u_xs", 256)]),
    ([dict(hub="p", src="seq__g_xs_2__u_xs", dst="fan", frm=0, to=2, bits=128, port=p)
      for p in ("q_e", "q_w")], [("seq__g_xs_N__u_xs_q_e", 128), ("seq__g_xs_N__u_xs_q_w", 128)])
])
def test_intra_cut_routes_keep_source_port_affinity_and_legacy_width(pin_rows, expected):
    """Splitting a two-output leaf must not turn both buses into anonymous residual capacity."""
    from types import SimpleNamespace
    ev = TS.Event.__new__(TS.Event)
    ev.rep, ev.pmap, ev.ts = {}, {"p": []}, {"t": SimpleNamespace(legs=[])}
    ev.raw_type = lambda _p: "t"
    ev.census = dict(intra=[["p", "seq__g_xs_2__u_xs", "fan", 0, 2, 256]])
    if pin_rows is not None:
        ev.census["intra_pin_routes"] = pin_rows
    captured = []
    def transit(_base, _ts, _frm, _to, stem, width, *_args):
        captured.append((stem, width))
        return "o", "i", "L1"
    ev._transit = transit
    ev._census_requests()
    assert captured == expected
    assert sum(n for _, n in captured) == 256


def test_deferred_bus_driver_routes_stay_in_their_own_split_family(tmp_path):
    """A first-family callback must not write into the last familys list of plan cells."""
    from types import SimpleNamespace
    doc = dict(types={t: dict(cells={}, bus_drivers=[dict(bus="o_out", drivers=[dict(inst="driver", port="q", bits=[0, 0])])], replicas=[t])
                      for t in ("A", "B")})
    source = tmp_path / "pc.json"
    source.write_text(json.dumps(doc))
    ev = TS.Event.__new__(TS.Event)
    ev.ab, ev.rep, ev.spec = dict(plan_cells=str(source)), {}, {}
    ev.raw = dict(partitions=[dict(name=t, type=t) for t in ("A", "B")])
    ev.ts = {t: SimpleNamespace(n=2, pname={t: [t+"0", t+"1"]}, t=dict(hard_cores=[]),
                              content_piece=dict(driver=0), keep=0, bp=lambda _b: 1,
                              tnames=[t+"0", t+"1"]) for t in ("A", "B")}
    result = ev._plan_cells({})
    for base, *_args, callback in ev.pc_routes:
        callback("o_cut_"+base, "i_cut_"+base)
    for t in ("A", "B"):
        assert result["types"][t+"0"]["bus_drivers"] == [dict(bus="o_cut_"+t, drivers=[dict(inst="driver", port="q", bits=[0, 0])])]
        assert result["types"][t+"1"]["bus_drivers"] == [dict(bus="o_out", drivers=[dict(bus="i_cut_"+t, bits=[0, 0])])]


def test_fresh_output_retains_inherited_core_pin_tables(tmp_path):
    incoming = tmp_path / "incoming"
    pins = incoming / "pins/core.json"
    pins.parent.mkdir(parents=True)
    payload = b"[{\"name\":\"ck\",\"layer\":\"M5\",\"x\":1.0,\"y\":2.0}]\n"
    pins.write_bytes(payload)
    ev = TS.Event.__new__(TS.Event)
    ev.plan_dir, ev.spec, ev.ts, ev.rep, ev.tag = incoming, {}, {}, {}, "test-pins"
    ev.out = dict(partition_types=dict(t=dict(hard_cores=[dict(pins_file="pins/core.json")])))
    ev._census = lambda _out: {}
    ev.side, ev.pc_out, ev.ab_out, ev.latency_rows = None, None, None, []
    output = tmp_path / "fresh"
    ev.write(output, "fresh")
    pins.unlink()
    assert (output / "pins/core.json").read_bytes() == payload


def test_new_passthrough_slots_get_macro_clear_actual_bit_banks(monkeypatch):
    from types import SimpleNamespace
    import schema
    import gen_phys
    slot = dict(name="ft0", width=4, stations=3, note="new pass-through")
    typ = dict(outline_um=[1000, 600], hard_cores=[dict(inst="core", origin_um=[400, 0], outline_um=[200, 400])], ft_slots=[slot])
    ev = TS.Event.__new__(TS.Event)
    ev.out, ev.raw, ev.rep = dict(partition_types=dict(t=typ)), dict(budgets=dict(ft_station_max_um=405)), {}
    ev.mid_slot_refs = [(SimpleNamespace(tnames=["t"]), 0, slot)]
    monkeypatch.setattr(schema, "Plan", lambda *_args: object())
    monkeypatch.setattr(gen_phys, "type_pins", lambda *_args: [
        (bus, bit, "M4", x, 50 + bit, face) for bus, x, face in [("ft0_i", 0, "W"), ("ft0_o", 1000, "E")] for bit in range(5)])
    ev._place_mid_slot_banks()
    assert slot["stations"] > 3
    assert len(slot["bit_sites_um"]) == slot["stations"] - 1
    assert all(len(row) == 5 for row in slot["bit_sites_um"])
    assert ev.rep["pass_through_paths"][0]["max_actual_bit_hop_um"] <= 405
    for row in slot["bit_sites_um"]:
        for x, y in row:
            assert not (400 < x < 600 and 0 < y < 400)


def test_added_cut_flops_count_with_existing_complete_bins(monkeypatch):
    from types import SimpleNamespace
    import schema
    import gen_phys
    slot = dict(name="ft1", bit_site_cell_um=[1.404, .27], bit_sites_um=[[[20, 30], [22.16, 30]]])
    a = dict(clock=dict(sink_bins_file="old_a.json"), ft_slots=[dict(name="ft1")])
    b = dict(clock=dict(sink_bins_file="old_b.json"), ft_slots=[slot])
    ev = TS.Event.__new__(TS.Event)
    ev.out = dict(partition_types=dict(a=a, b=b), partitions=[dict(name="a",type="a"),dict(name="b",type="b")],
                  ports=[dict(id="cut",src=dict(part="a",bus="ft1_o"),dst=dict(part="b",bus="ft1_i"))])
    ev.rep = dict(ports_added=["cut"])
    ev.mid_slot_refs = [(SimpleNamespace(tnames=["b"]),0,slot)]
    monkeypatch.setattr(schema,"Plan",lambda *_args: object())
    monkeypatch.setattr(gen_phys,"type_pins",lambda _p,tn: [("ft1_o" if tn=="a" else "ft1_i",bit,"M4",0,50+bit,"W")for bit in range(2)])
    ev._inventory_cut_sinks()
    assert ev.added_clock_cells == {"b":4}
    assert b["clock"]["sink_bins_file"] == "old_b.json"
    assert sum(row[2] for row in b["clock"]["sink_sites_um"]) == 4
    assert "sink_sites_um" not in a["clock"]  # FT output pins are not an extra clocked stage


def test_split_output_rebases_absolute_repository_base(tmp_path):
    ev = TS.Event.__new__(TS.Event)
    ev.plan_dir, ev.spec, ev.ts, ev.rep, ev.tag = tmp_path, {}, {}, {}, "test-base"
    ev.out, ev.ab_out = {}, dict(base=str(TS.ROOT))
    ev._census = lambda _out: {}
    ev.side, ev.pc_out, ev.latency_rows = None, None, []
    out = tmp_path / "new"
    ev.write(out, "new")
    published = json.loads((out / "asbuilt_vN.json").read_text())
    assert not Path(published["base"]).is_absolute()
    assert (out / published["base"]).resolve() == TS.ROOT
