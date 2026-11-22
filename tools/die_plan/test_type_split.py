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


def test_relay_tx_sites_one_centre_pin_unless_relays_on_both_sides():
    """FABLE-FIX-KV-PV-CUT: the 2-way form (and a chain away from an end keep piece) keeps its ONE centre pin; a keep
    piece with a relay piece on each side gets one tx pin per side, each next to its neighbour's rx pin"""
    mid = 760.32
    two = TS.Cut("x", [622.08], 2160.0)
    assert TS.relay_tx_sites(two, 0, [1], mid) == [("cland_rstart_out", [311.04, 756.0], [1])]
    assert TS.relay_tx_sites(two, 1, [0], mid) == [("cland_rstart_out", [768.96, 756.0], [0])]
    three = TS.Cut("x", [622.08, 1537.92], 2160.0)
    assert TS.relay_tx_sites(three, 0, [1, 2], mid) == [("cland_rstart_out", [311.04, 756.0], [1, 2])]
    both = TS.relay_tx_sites(three, 1, [0, 2], mid)
    assert both == [("cland_rstart_out", [2.656, 756.0], [0]), ("cland_rstart_out_1", [913.184, 756.0], [2])]
    # the neighbour's rx pin sits 2.656 um inside its own cut face at the same offset: both hops are 5.312 um (<= 405)
    for (_name, tx, (child,)), rx_local in zip(both, (three.ext(0) - 2.656, 2.656)):
        tx_die, rx_die = three.lo(1) + tx[0], three.lo(child) + rx_local
        assert abs(tx_die - rx_die) == pytest.approx(5.312)
    ycut = TS.Cut("y", [449.28, 846.72], 1676.16)
    assert TS.relay_tx_sites(ycut, 1, [0, 2], 501.12) == [("cland_rstart_out", [496.8, 2.656], [0]),
                                                           ("cland_rstart_out_1", [496.8, 394.784], [2])]
    four = TS.Cut("x", [500.0, 1000.0, 1500.0], 2000.0)
    with pytest.raises(TS.SplitError, match="one adjacent relay piece per side"):
        TS.relay_tx_sites(four, 1, [0, 2, 3], mid)


def test_landing_network_relay_edges_name_the_tx_pin_of_their_side():
    """each relay piece's cland_relay__ edge leaves the tx pin its coll_link names (default: the one legacy pin)"""
    class _Ts:
        keep, croot, cut = 1, 1, None
        coll_links = [dict(child_piece=0, parent_piece=1, index=0), dict(child_piece=2, parent_piece=1, index=1)]
        relay_links = [dict(child_piece=0), dict(child_piece=2, tx="cland_rstart_out_1")]
    ev = TS.Event.__new__(TS.Event)
    ev.out = dict(clock=dict(landing_network=dict(edges=[])))
    ev.pmap, ev.ts, ev.rep = {"p": ["p_s", "p", "p_n"]}, {"T": _Ts()}, {}
    ev.raw_type = lambda base: "T"
    ev._landing_network()
    relay = {e["id"]: (e["src"], e["dst"]) for e in ev.out["clock"]["landing_network"]["edges"]
             if e["id"].startswith("cland_relay__")}
    assert relay == {"cland_relay__p_s": (dict(part="p", bus="cland_rstart_out"), dict(part="p_s", bus="cland_rstart_in")),
                     "cland_relay__p_n": (dict(part="p", bus="cland_rstart_out_1"), dict(part="p_n", bus="cland_rstart_in"))}
    # collector root in an end piece (it holds the up pins), keep / count origin in the middle: the collector chain
    # runs 2 -> 1 -> 0 while both relay edges still leave the keep piece, one tx pin per side
    _Ts.croot = 0
    _Ts.coll_links = [dict(child_piece=1, parent_piece=0, index=0), dict(child_piece=2, parent_piece=1, index=0)]
    ev.out = dict(clock=dict(landing_network=dict(edges=[dict(id="cland_mon_ready__p", src=dict(part="p", bus="cland_up_ready"),
                                                              dst=dict(part="par", bus="cland_dn_ready_3"))])))
    ev._landing_network()
    edges = ev.out["clock"]["landing_network"]["edges"]
    assert len({e["id"] for e in edges}) == len(edges)             # the old up edge is renamed to its new child
    got = {e["id"]: (e["src"]["part"], e["src"]["bus"], e["dst"]["part"]) for e in edges}
    assert got["cland_mon_ready__p_s"] == ("p_s", "cland_up_ready", "par")
    assert got["cland_mon_ready__p"] == ("p", "cland_up_ready", "p_s") and got["cland_mon_ready__p_n"][2] == "p"
    assert got["cland_relay__p_s"] == ("p", "cland_rstart_out", "p_s")
    assert got["cland_relay__p_n"] == ("p", "cland_rstart_out_1", "p_n")
    assert ev._piece_of_pin("p", "cland_up_ready") == (0, "cland_up_ready")
    assert ev._piece_of_pin("p", "cland_tstart_in") == (1, "cland_tstart_in")
    _Ts.croot = 1
    _Ts.coll_links = [dict(child_piece=0, parent_piece=1, index=0)]     # 2-way: unchanged edge
    _Ts.relay_links = [dict(child_piece=0)]
    ev.out = dict(clock=dict(landing_network=dict(edges=[])))
    ev.pmap = {"p": ["p_s", "p"]}
    ev._landing_network()
    assert [e["src"] for e in ev.out["clock"]["landing_network"]["edges"] if e["id"] == "cland_relay__p_s"] == [
        dict(part="p", bus="cland_rstart_out")]


@pytest.mark.parametrize("foreign_pin", [False, True])
def test_landing_collector_status_pins_use_the_owner_piece_frame(foreign_pin):
    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn, ts.tnames, ts.n, ts.keep = "PV", ("PV", "PVe"), 2, 0
    ts.cut, ts.W, ts.H = TS.Cut("x", [1080.0], 2160.0), 2160.0, 1520.64
    ts.T, ts.rep = [{"clock": {}} for _ in range(2)], {}
    ts.bp = lambda _bus: 1
    pin_x = 1079.0 if foreign_pin else 2151.36
    source = dict(name="ft10_i", xy_um=[2151.36, 12.96],
                  pin_xy_um=[2130.6764, 0], status_pins_xy_um=[[pin_x, 12.96], [2149.2, 16.0]])
    child = dict(part="PV_child", index=7, xy_um=[1520, 22],
                 status_pins_xy_um=[[1518, 20], [1522, 22]])
    contract = dict(collector_local_sources=[source], collector_children=[child])
    if foreign_pin:
        with pytest.raises(TS.SplitError, match="collector ft10_i status pin .* outside piece 1"):
            ts._landing_contract(contract)
        return
    ts._landing_contract(contract)
    east = ts.T[1]["clock"]["landing_contract"]
    assert east["collector_local_sources"][0]["status_pins_xy_um"] == [[1071.36, 12.96], [1069.2, 16.0]]
    assert east["collector_children"][0]["status_pins_xy_um"] == [[438.0, 20.0], [442.0, 22.0]]
    assert source["status_pins_xy_um"][0] == [2151.36, 12.96]
    assert child["status_pins_xy_um"][0] == [1518, 20]
    TS.Event._attach(None, "PVe", east, {"relays": [
        {"q": "rst_n_t3", "xy": [1073.0, 20.0]}, {"q": "rst_n_t4", "xy": [440.0, 22.0]},
    ]}, 405)
    assert east["collector_local_sources"][0]["node"] == "rst_n_t3"
    assert east["collector_children"][0]["node"] == "rst_n_t4"


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
                drop_clock_keys=["landing_reader_start", "landing_writer_start", "landing_raw_branches"],
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
    # relay pieces on both sides of the keep piece: one tx pin per side, each within the hop limit of its rx pin
    assert "cland_rstart_out_1" in names
    assert {c["child_piece"]: c.get("tx", "cland_rstart_out") for c in ts.relay_links} == {0: "cland_rstart_out",
                                                                                          2: "cland_rstart_out_1"}
    pins = {i: {p["name"]: p["xy_um"] for p in T[i]["clock"]["landing_contract"]["pins"]} for i in range(3)}
    for child, tx in ((0, "cland_rstart_out"), (2, "cland_rstart_out_1")):
        a, b = pins[1][tx], pins[child]["cland_rstart_in"]
        hop = abs(a[0] - b[0]) + abs((ts.cut.lo(1) + a[1]) - (ts.cut.lo(child) + b[1]))
        assert hop <= 405
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
    ev.rep, ev.pmap, ev.ts = {}, {"p": []}, {"t": SimpleNamespace(legs=[], parts=[{}])}
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
    ev.ts = {t: SimpleNamespace(n=2, parts=[dict(name=t)], pname={t: [t+"0", t+"1"]}, t=dict(hard_cores=[]),
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


def test_replicated_transit_reuses_type_buses_and_interior_banks():
    from types import SimpleNamespace
    ev=TS.Event.__new__(TS.Event);ev.tag="TEST";ev.ab={"map":{"parts":{"hsl_EN_5":["A","hsl0"],"hsl_ES_5":["B","hsl0"]}}};ev.lmax=20;ev.req=[]
    typ=[{"buses":[],"ft_slots":[]}for _ in range(3)]
    ts=SimpleNamespace(tn="cohort",parts=[{"name":"A"},{"name":"B"}],T=typ,bus_piece={})
    def new_bus(i,stem):
        used={b["name"]for b in typ[i]["buses"]};candidate=stem;n=1
        while candidate in used:n+=1;candidate=stem+str(n)
        return candidate
    ts._new_bus_name=new_bus
    ev._mid_slot=lambda ts,i,a,z,w:typ[i]["ft_slots"].append({"name":"ft0"})or typ[i]["ft_slots"][-1]
    a=ev._transit("A",ts,0,2,"hsl0_ao",32,"data","leaf hsl_EN_5 -> slg")
    b=ev._transit("B",ts,0,2,"hsl0_ao",32,"data","leaf hsl_ES_5 -> slg")
    assert a[:2]==b[:2] and a[2]!=b[2]
    assert len(typ[0]["buses"])==len(typ[2]["buses"])==len(typ[1]["ft_slots"])==1
    assert len(ev.req)==4
    assert {r["base"]for r in ev.req}=={"A","B"}
    # A distinct occurrence in the same instance remains distinct, never silently merged by name/width.
    c=ev._transit("A",ts,0,2,"hsl0_ao",32,"data","leaf hsl_EN_5 -> slg")
    assert c[0]!=a[0]


def test_plancell_replica_callback_runs_once_with_shared_type_endpoints():
    from types import SimpleNamespace
    ev=TS.Event.__new__(TS.Event);ev.tag="TEST";ev.ab={};ev.lmax=0;ev.req=[]
    typ=[{"buses":[],"ft_slots":[]}for _ in range(2)]
    ts=SimpleNamespace(tn="cohort",parts=[{"name":"A"},{"name":"B"}],T=typ,bus_piece={})
    ts._new_bus_name=lambda i,stem:stem
    calls=[];ev.pc_routes=[(("A","B"),ts,0,1,"id",2,"data","shared id",lambda a,b:calls.append((a,b)))]
    ev._plancell_requests()
    assert calls==[("o_id","i_id")]
    assert len(ev.req)==2 and len(typ[0]["buses"])==1


def test_lane_reference_is_published_with_the_piece_groups(tmp_path):
    """FABLE-FIX-KV-PV-CUT (bind: 'native stations ...: expected one outgoing lane'): an old lane whose forward sources
    land in another piece must keep its as-built bits, so the split names the base bind's frozen lane payloads in the
    manifest with each split partition's group = its pieces"""
    ref = dict(schema="opentallas.split_lane_reference.v1", payload_sha256="x", cells={},
               part_groups={"p": ["p"], "q": ["q"]},
               lanes=[dict(id="L1", src="p", dst="q", drivers=[["p.a", "q", 0], ["p.a", "q", 1]])])
    (tmp_path / "ref.json").write_text(json.dumps(ref))

    def event(spec, lanes=("L1", "L9")):
        ev = TS.Event.__new__(TS.Event)
        ev.plan_dir, ev.ts, ev.rep, ev.tag = tmp_path, {}, {}, "test-ref"
        ev.spec, ev.pmap = spec, {"p": ["p", "p_x1", "p_x2"]}
        ev.out = dict(partition_types={}, lanes=[dict(id=i) for i in lanes])
        ev._census = lambda _out: {}
        ev.side, ev.pc_out, ev.latency_rows = None, None, []
        ev.ab_out = {}
        return ev
    ev = event(dict(lane_reference=str(tmp_path / "ref.json")))
    out = tmp_path / "split"
    ev.write(out, "rel/split")
    ab = json.loads((out / "asbuilt_vN.json").read_text())
    assert ab["split_lane_reference"] == "rel/split/split_lane_reference.json"
    got = json.loads((out / "split_lane_reference.json").read_text())
    assert got["part_groups"] == {"p": ["p", "p_x1", "p_x2"], "q": ["q"]}
    assert got["lanes"] == ref["lanes"] and got["payload_sha256"] == "x"      # payload untouched
    assert ev.rep["lane_reference"]["bits"] == 2
    # no spec key: the manifest is unchanged (existing splits bind as before)
    ev = event({})
    ev.write(tmp_path / "plain", "rel/plain")
    assert "split_lane_reference" not in json.loads((tmp_path / "plain" / "asbuilt_vN.json").read_text())
    assert not (tmp_path / "plain" / "split_lane_reference.json").exists()
    # fail closed: a base lane the split dropped, a reference that is not from the unsplit base
    with pytest.raises(TS.SplitError, match="base lanes are not in the split plan"):
        event(dict(lane_reference=str(tmp_path / "ref.json")), lanes=("L9",)).write(tmp_path / "gone", "rel/gone")
    ref["part_groups"]["p"] = ["p", "p_old"]
    (tmp_path / "ref.json").write_text(json.dumps(ref))
    with pytest.raises(TS.SplitError, match="exported from the bind of the unsplit base plan"):
        event(dict(lane_reference=str(tmp_path / "ref.json"))).write(tmp_path / "bad", "rel/bad")


def test_density_piece_forwarded_clock_sources_follow_the_piece_taps():
    """bind EMIT '<piece>: forwarded clock source clk_t139 is not a planned physical tap input': the base type's density
    tap names do not exist in a piece (its taps are re-derived); each forwarded clock pin takes the nearest piece tap"""
    from types import SimpleNamespace
    cut = TS.Cut("x", [600.0], 1400.0)
    pin = lambda name, tap, x: dict(name=name, dir="out", kind="clock", xy_um=[x, 5.0], source_clock_port=tap,
                                    source_clock_tap=tap)
    base = dict(clock=dict(tap_mode="density", landing_contract=dict(pins=[
        pin("fclk_out_a", "clk_t139", 20.0), pin("fclk_out_b", "clk_t3", 900.0), dict(name="cland_up_ready")])))
    ts = SimpleNamespace(t=base, cut=cut, tnames=["T", "T_x1"])
    ev = TS.Event.__new__(TS.Event)
    # the pieces as _clock leaves them: the port keeps the base name, the tap went through the R4 grid map (wrong in
    # density mode)
    ev.out = dict(partition_types={
        "T": dict(clock=dict(landing_contract=dict(pins=[pin("fclk_out_a", "clk_t139", 20.0)]))),
        "T_x1": dict(clock=dict(landing_contract=dict(pins=[dict(pin("fclk_out_b", "clk_t3", 300.0),
                                                                 source_clock_tap="clk_t2")])))})
    old = {"T": [("clk", 10.0, 10.0), ("clk_t3", 950.0, 40.0), ("clk_t139", 30.0, 900.0)]}
    new = {"T": [("clk", 300.0, 300.0), ("clk_t1", 40.0, 880.0)], "T_x1": [("clk", 345.0, 50.0), ("clk_t1", 100.0, 700.0)]}
    rep = ev._remap_clock_sources([("T", ts)], old.__getitem__, new.__getitem__)
    a = ev.out["partition_types"]["T"]["clock"]["landing_contract"]["pins"][0]
    b = ev.out["partition_types"]["T_x1"]["clock"]["landing_contract"]["pins"][0]
    assert (a["source_clock_port"], a["source_clock_tap"]) == ("clk_t1", "clk_t1")
    assert (b["source_clock_port"], b["source_clock_tap"]) == ("clk", "clk")       # old tap 950 -> 350 in piece 1
    assert rep == {"T": 2, "T_x1": 2}
    for nm in new:        # every source is now a planned tap of its piece
        names = {n for n, _x, _y in new[nm]}
        assert all(q["source_clock_port"] in names for q in ev.out["partition_types"][nm]["clock"]["landing_contract"]["pins"])
    base["clock"]["landing_contract"]["pins"][0]["source_clock_port"] = "clk_t999"
    with pytest.raises(TS.SplitError, match="not a tap of the base type"):
        ev._remap_clock_sources([("T", ts)], old.__getitem__, new.__getitem__)
    # other tap modes: untouched (the pass selects density types only)
    ev.ts = {"G": SimpleNamespace(t=dict(clock=dict(tap_mode="grid+explicit")))}
    ev.rep = {}
    ev._forwarded_clock_sources()
    assert "forwarded_clock_sources" not in ev.rep


def test_split_inline_memory_and_typed_proof_follow_pieces():
    """Service SRAM rows carry their physical extent in the content itself."""
    raw = {
        "die": {"name": "fixture", "outline_um": [100.0, 100.0], "reach_um": 405.0},
        "partitions": [{"name": "p", "type": "T", "origin_um": [0.0, 0.0]}],
        "lanes": [],
        "ports": [],
        "partition_types": {
            "T": {
                "outline_um": [100.0, 100.0],
                "verilog_defines": ["V0"],
                "port_buf_at_pin": True,
                "ft_track_frac": 0.35,
                "dead_inputs": [{"module": "sx", "ports": {"a": [[0, 2]]}}],
                "contents": [{"inst": "u_mem", "origin_um": [5.0, 75.0],
                              "outline_um": [10.0, 10.0]}],
            },
        },
    }
    spec = dict(axis="y", cuts_um=[50.0], parts=[{"suffix": ""}, {"suffix": "_r"}],
                contents={"T": [["u_mem", 1]]}, dead_input_pieces={"T": {"sx": 1}})
    low, high = TS.TypeSplit(_Ev(raw, spec), "T").split()
    assert high["contents"][0]["origin_um"] == [5.0, 25.0]
    assert high["dead_inputs"] == raw["partition_types"]["T"]["dead_inputs"]
    assert "dead_inputs" not in low
    assert low["port_buf_at_pin"] and high["port_buf_at_pin"]
    assert low["ft_track_frac"] == high["ft_track_frac"] == 0.35
    assert low["verilog_defines"] == high["verilog_defines"] == ["V0"]
    with pytest.raises(TS.SplitError, match="dead-input proof for sx needs a piece"):
        TS.TypeSplit(_Ev(raw, {**spec, "dead_input_pieces": {}}), "T").split()


def test_split_census_keeps_generated_instance_indices(tmp_path):
    """PC page-cache leaves keep their full path while finding the owner."""
    raw = {
        "die": {"name": "fixture", "outline_um": [100.0, 100.0], "reach_um": 405.0},
        "partitions": [{"name": "p", "type": "T", "origin_um": [0.0, 0.0]}],
        "partition_types": {"T": {"outline_um": [100.0, 100.0],
                                  "contents": [{"inst": "p_cache"}, {"inst": "p_rest"}]}},
        "ports": [],
        "lanes": [],
    }
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(raw))
    manifest = tmp_path / "asbuilt.json"
    manifest.write_text(json.dumps({"map": {"parts": {
        "u": ["p", "p_rest"],
        "u.g_pc[0].u_pc": ["p", "p_cache"],
    }}}))
    (tmp_path / "bind_latency.json").write_text('{"buses":[]}')
    (tmp_path / "bind_sinks.json").write_text(json.dumps({
        "u.g_drain[3].d[3]": ["pin", "u.g_pc[0].u_pc.rq[5]"],
        "u.g_drain[3].v[0]": ["const", "0"],
    }))
    spec = dict(plan=str(plan), asbuilt=str(manifest), family=["T"], axis="y", cuts_um=[43.2],
                parts=[{"suffix": ""}, {"suffix": "_r"}], contents={"T": [["p_cache", 0], ["p_rest", 1]]})
    result = TS.census(spec, tmp_path)
    assert result["unplaced"] == []
    assert result["intra_pin_routes"] == [
        {"hub": "p", "src": "u", "dst": "u", "frm": 0, "to": 1, "port": "rq", "bits": 1},
    ]



def test_named_h8_lanes_allow_numeric_split_lane_allocation():
    names = ["attn__svc_9__svc_8", "rsv__svc_8__svc_9", "attn__svc_8__svc_9"]
    raw = {"lanes": [{"id": lane} for lane in names]}
    assert TS._lane_num(raw) == 0

    mixed = names + ["L11", "L2"]
    raw = {"lanes": [{"id": lane} for lane in mixed]}
    assert TS._lane_num(raw) == 11
    assert sorted(mixed, key=TS._lane_sort_key) == ["L2", "L11", *sorted(names)]


def _sidecar_event(tmp_path, side):
    ev = TS.Event.__new__(TS.Event)
    ev.plan_dir, ev.spec, ev.rep, ev.tag = tmp_path, {}, {}, "test-side"
    ev.ts = {"a": type("TS", (), {"tnames": ["a", "a_att"]})()}
    ev.out, ev.ab_out = {"partition_types": {"a": {}, "a_att": {}}}, None
    ev._census = lambda _out: {}
    ev.side, ev.pc_out, ev.latency_rows = side, None, []
    return ev


def test_sidecar_tree_less_base_rows_are_carried(tmp_path):
    """base sidecar rows without a tree (hard / tree-less types outside the split) do not fail the split"""
    tree = {"root": [0, 0], "depth": 1, "relays": []}
    side = {"collector": {"types": {"a": {"tree": tree}, "a_att": {"tree": tree}, "hard_x": {"tree": None}}}}
    _sidecar_event(tmp_path, side).write(tmp_path / "o", "o")
    out = json.loads((tmp_path / "o" / "eW_sidecar.json").read_text())
    assert out["collector"]["types"]["hard_x"]["tree"] is None


def test_sidecar_piece_row_without_tree_fails(tmp_path):
    tree = {"root": [0, 0], "depth": 1, "relays": []}
    side = {"collector": {"types": {"a": {"tree": tree}, "a_att": {"tree": None}}}}
    with pytest.raises(TS.SplitError, match="a_att"):
        _sidecar_event(tmp_path, side).write(tmp_path / "o", "o")


def test_sidecar_part_region_declares_every_piece():
    ev = TS.Event.__new__(TS.Event)
    ev.side = {"regions": [{"tag": "svc_9", "parts": ["svc_9"]}], "part_region": {"svc_9": "svc_9", "x": "r"},
               "ports": []}
    ev.pmap = {"svc_9": ["svc_9", "svc_9_att"]}
    ev.ts = {"t": type("TS", (), {"keep": 0, "tnames": ["t", "t_att"]})()}
    ev.raw_type = lambda base: "t"
    ev.ports, ev.rep = {}, {}
    try:
        ev._sidecar()
    except Exception:
        pass  # later sidecar steps need a full plan; the declaration is written first
    assert ev.side["part_region"]["svc_9_att"] == "svc_9"
    assert ev.side["regions"][0]["parts"] == ["svc_9", "svc_9_att"]


def _core_tap_split(taps):
    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn = "t"
    ts.cut = TS.Cut("x", [570.24], 1442.88)
    ts.t = {"hard_cores": [{"inst": "u_a.u_c", "origin_um": [578.88, 86.4], "outline_um": [157.68, 259.2]}]}
    return [ts._core_tap_piece(tp) for tp in taps]


def test_core_tap_follows_its_core_not_its_xy():
    # OPUS-FIX-S81-SVC-R7 11-21: a core tap goes to its core's piece; a plain tap (no core) keeps the xy rule (None)
    assert _core_tap_split([{"kind": "core", "name": "u_a.u_c.clk", "xy": [657.708, 86.64]},
                            {"name": "u_other.clk", "xy": [10.0, 10.0]}]) == [1, None]


def test_core_tap_off_its_core_fails_closed():
    # the hi4 x_epoch repack moved the core to x 578.88 but left its tap at x 113.388 (rest piece)
    with pytest.raises(TS.SplitError, match="not on its core"):
        _core_tap_split([{"kind": "core", "name": "u_a.u_c.clk", "xy": [113.388, 34.8]}])


def test_core_tap_requires_known_owner():
    with pytest.raises(TS.SplitError, match="names no hard core"):
        _core_tap_split([{"kind": "core", "name": "u_missing.clk", "xy": [10.0, 10.0]}])


def test_x_split_windows_use_the_piece_frame_and_share_cut_geometry():
    import schema

    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn = "S"
    ts.cut = TS.Cut("x", [50], 100)
    north = dict(name="north", face="N", window_um=[70, 90], layers=["M5", "M7"])
    ts._shift_piece_window(north, "face", "window_um", 1)
    assert north["window_um"] == [20, 40]

    ts.T = [
        dict(outline_um=[50, 100], ft_slots=[dict(name="ft", out_face="E", out_window_um=[40, 50],
                                                in_window_um=[10, 20], layers=["M6", "M4"])]),
        dict(outline_um=[50, 100], buses=[north],
             ft_slots=[dict(name="ft", in_face="W", in_window_um=[10, 20], layers=["M6", "M4"])]),
    ]
    ev = TS.Event.__new__(TS.Event)
    ev._set_ft_cut_geometry(ts, dict(slot="ft", a=0, b=1), [(21.6, 30.24, 16)], ["M4", "M6"])
    plan = schema.Plan({
        "die": {"name": "test", "outline_um": [120, 120], "reach_um": 405},
        "partition_types": {"lo": ts.T[0], "hi": ts.T[1]},
        "partitions": [{"name": "l", "type": "lo", "origin_um": [50, 0], "orient": "MY"},
                       {"name": "h", "type": "hi", "origin_um": [0, 0], "orient": "MY"}],
        "ports": [], "lanes": [],
    })
    seam = dict(src=dict(part="l", bus="ft_o"), dst=dict(part="h", bus="ft_i"))
    expected = ("W", [21.6, 30.24], ["M4", "M6"], "lsb_low")
    assert plan.port_geom_from(seam, "src") == plan.port_geom_from(seam, "dst") == expected
    assert plan.geom_to_die("h", plan._type_geom("h", "north"))[1] == [10, 30]
    assert ts.T[0]["ft_slots"][0]["in_window_um"] == [10, 20]


def test_forwarded_clock_sources_read_the_unmoved_base_taps(monkeypatch):
    """OPUS-FIX-KV-PV-R5 11-21 (split 11): core_moves rewrite self.raw before the split, and a moved core changes the
    density tap grid, so the base pin's clk_t171 was looked up in the MOVED grid ('is not a tap of the base type').
    The old tap names come from the plan as written (raw_premove); the new taps from the split output."""
    from types import SimpleNamespace
    import schema as S
    import taps as TP
    monkeypatch.setattr(S, "Plan", lambda raw, path: SimpleNamespace(raw=raw))
    monkeypatch.setattr(S, "tap_grid", lambda P, tn: list(P.raw["grid"][tn]))
    monkeypatch.setattr(TP, "_clear_density_cache", lambda: None)
    ev = TS.Event.__new__(TS.Event)
    ev.plan_path, ev.rep = None, {}
    ev.raw_premove = {"grid": {"T": [("clk_t171", 30.0, 900.0)]}}
    ev.raw = {"grid": {"T": [("clk_t170", 30.0, 900.0)]}}          # after the core move: the name is gone
    ev.out = {"grid": {"T": [("clk_t1", 40.0, 880.0)]},
              "partition_types": {"T": {"clock": {"landing_contract": {"pins": [
                  dict(name="fclk_out_ft0_o", source_clock_port="clk_t171")]}}}}}
    cut = TS.Cut("x", [600.0], 1400.0)
    base = dict(clock=dict(tap_mode="density", landing_contract=dict(pins=[dict(name="fclk_out_ft0_o",
                                                                                source_clock_port="clk_t171")])))
    ev.ts = {"T": SimpleNamespace(t=base, cut=cut, tnames=["T"])}
    ev._forwarded_clock_sources()
    assert ev.out["partition_types"]["T"]["clock"]["landing_contract"]["pins"][0]["source_clock_port"] == "clk_t1"
    del ev.raw_premove                     # the old behaviour (moved grid) fails closed, as split 11 did
    ev.out["partition_types"]["T"]["clock"]["landing_contract"]["pins"][0]["source_clock_port"] = "clk_t171"
    with pytest.raises(TS.SplitError, match="clk_t171 is not a tap of the base type"):
        ev._forwarded_clock_sources()


class _RK:
    """the slice of TypeSplit that _relay_keys reads (OPUS-FIX-KV-PV-R4 11-21)"""
    def __init__(self):
        self.tn, self.n = "t", 2
        self.cut = TS.Cut("x", [1080.0], 2160.0)
        self.T = [dict(hard_cores=[{}]), dict(hard_cores=[{}])]
        self.rep = {}
        self.bus_piece = {"i_a": 1}
        self.t = dict(
            relay_depth=[dict(inst="pv_u_g0_j", port="sf", side="sink", D=1), dict(inst="pv_u_g3_j", port="sf", side="sink", D=2)],
            relay_polylines=[dict(group_re="u_y_xd_T1Q0_y_[0-9]+$", polyline_um=[[2066.0, 794.0], [1667.0, 794.0]]),
                             dict(group_re="u_y_xd_T0Q0_y_[0-9]+$", polyline_um=[[1426.0, 794.0], [580.0, 794.0]])],
            relay_sites={"u_bin_i_a.q[0]": [1100.0, 10.0], "u_bin_i_a.q[1]": [20.0, 10.0], "u_x.q": [30.0, 5.0], "u_y.q": [2000.0, 5.0]},
            reset_replicate=[dict(form="rsync", driver="u_rs_ri_pv_u_g0_j_rst_n", copy_depth=4)])

    def _local_piece_of(self, inst):
        return 0 if ("_g0_" in inst or "T0Q" in inst) else 1


def test_relay_keys_follow_core_bus_and_position():
    s = _RK()
    TS.TypeSplit._relay_keys(s)
    T = s.T
    assert [r["inst"] for r in T[0]["relay_depth"]] == ["pv_u_g0_j"] and [r["D"] for r in T[1]["relay_depth"]] == [2]
    # a polyline inside its piece is shifted; one that leaves its piece is dropped and reported
    assert T[1]["relay_polylines"][0]["polyline_um"] == [[986.0, 794.0], [587.0, 794.0]] and "relay_polylines" not in T[0]
    assert s.rep["relay_keys"]["polylines_dropped"] == ["u_y_xd_T0Q0_y_[0-9]+$"]
    # u_bin_<bus> sites follow the bus piece (off-piece ones dropped); others go by position
    assert T[1]["relay_sites"] == {"u_bin_i_a.q[0]": [20.0, 10.0], "u_y.q": [920.0, 5.0]}
    assert T[0]["relay_sites"] == {"u_x.q": [30.0, 5.0]} and s.rep["relay_keys"]["sites_dropped"] == 1
    # reset_replicate: every piece with cores, driver generalised to a regex, optional
    rr = [x["reset_replicate"][0] for x in T]
    assert all(r["optional"] and r["driver_re"] == r"u_rs_ri_pv_u_g\d+_j_rst_n" and "driver" not in r for r in rr)
    import re
    assert re.fullmatch(rr[1]["driver_re"], "u_rs_ri_pv_u_g1_j_rst_n")


@pytest.mark.parametrize("move_blocker_later", [False, True])
def test_core_move_carries_its_internal_station_rows(monkeypatch, move_blocker_later):
    """OPUS-FIX-KV-PV-R5 11-21 (kv3_pv_v3 split 14, bind 8c: 'native stations pv_S_3.o_pvw__u_sN_j_y_valid_p: expected one
    outgoing lane'): the g1<->g2 column swap moved core pv__u_g1_j east but its 'core pv__u_g1_j.fault' rows kept the old
    west from_um, so the split cut an empty leg.  A row launched / captured at a moved core moves that end with the core and
    keeps its reg count (cycles), re-spaced on a polyline outside every core box."""
    from types import SimpleNamespace
    import schema as S
    import check as C
    monkeypatch.setattr(S, "Plan", lambda raw, path: SimpleNamespace(grid=0.54, layers={}))
    monkeypatch.setattr(C, "core_pins", lambda h, d=None: [])
    blocker_final = [1600.02, 700.38]
    blocker_origin = [1600.02, 300.24] if move_blocker_later else blocker_final
    t = dict(outline_um=[2160.0, 1520.64],
             hard_cores=[dict(inst="j1", origin_um=[708.48, 604.8], outline_um=[172.8, 172.8]),
                         dict(inst="blk", origin_um=blocker_origin, outline_um=[200.88, 200.88])],
             internal_stations=[dict(conn="bus:o_y", launch="core j1.fault", capture="face bus o_y", from_um=[881.28, 773.28],
                                     to_um=[2132.0, 1520.64], regs_um=[[1100.0, 773.28]] * 6, bits=1),
                                dict(conn="bus:o_z", launch="leaf u_x", capture="face bus o_z", from_um=[10.0, 10.0],
                                     to_um=[20.0, 0.0], regs_um=[[15.0, 10.0]], bits=1)])
    ev = TS.Event.__new__(TS.Event)
    moves = {"j1": [1244.16, 604.8]}
    if move_blocker_later:
        moves["blk"] = blocker_final
    ev.spec = {"core_moves": {"T": moves}}
    ev.raw = {"partition_types": {"T": t}, "budgets": {}}
    ev.tag, ev.plan_dir, ev.rep = "t", None, {}
    ev._core_moves()
    r, z = t["internal_stations"]
    assert r["from_um"] == [pytest.approx(1416.96), pytest.approx(773.28)] and r["to_um"] == [2132.0, 1520.64]
    assert len(r["regs_um"]) == 6
    x, y = blocker_final
    blk = (x, y, x + 200.88, y + 200.88)
    assert not any(blk[0] < q[0] < blk[2] and blk[1] < q[1] < blk[3] for q in r["regs_um"])
    assert z["from_um"] == [10.0, 10.0] and z["regs_um"] == [[15.0, 10.0]]     # not core-bound: untouched
    assert ev.rep["core_moves"][0]["istation_rows_moved"] == 1


def test_x_split_resolves_mirrored_type_native_port_window():
    from types import SimpleNamespace

    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn = "S"
    ts.cut = TS.Cut("x", [40], 100)
    source = dict(name="s", type="S", origin_um=[100, 0], orient="MY")
    dest = dict(name="r", type="R", origin_um=[100, 100], orient="MY")
    port = dict(id="native", width=4, kind="data", face="N",
                src=dict(part="s", bus="out"), dst=dict(part="r", bus="in"))
    types = {
        "S": dict(outline_um=[100, 100], buses=[
            dict(name="out", dir="out", width=4, face="N", window_um=[65, 85], layers=["M7", "M5", "M3"])]),
        "R": dict(outline_um=[100, 100], buses=[
            dict(name="in", dir="in", width=4, face="S", window_um=[65, 85], layers=["M7", "M5", "M3"])]),
    }
    raw = {"die": {"name": "test", "outline_um": [200, 200], "reach_um": 405},
           "partition_types": types, "partitions": [source, dest], "ports": [port], "lanes": []}
    ts.ev = SimpleNamespace(raw=raw, plan_path=None)
    assert ts._end_piece(port, source, "N") == 1
    assert ts.ev._native_port_geometry.ports["native"]["window_um"] == [115, 135]
    assert "window_um" not in port



def test_port_geometry_check_fails_split_ports_only(monkeypatch):
    """COORD 11-21: the plan validator runs after the split; only errors of ports with an end on a split piece fail it"""
    import schema
    from types import SimpleNamespace
    ev = SimpleNamespace(spec={}, rep={}, ppart={"p_b": ("p", 1, None)},
                         out={"ports": [{"id": "a", "src": {"part": "p_b"}, "dst": {"part": "q"}},
                                        {"id": "b", "src": {"part": "q"}, "dst": {"part": "r"}}]})
    monkeypatch.setattr(schema, "validate", lambda raw: ["port b: window lo >= hi", "type x: something"])
    assert TS.Event.port_geometry_check(ev) == []
    monkeypatch.setattr(schema, "validate", lambda raw: ["port a: port geometry (..) != src type geometry (..)"])
    with pytest.raises(TS.SplitError, match="PORT-GEOMETRY 1"):
        TS.Event.port_geometry_check(ev)
    ev.spec["skip_port_check"] = True
    assert TS.Event.port_geometry_check(ev) == []


def test_cut_window_pref_centres_a_cut_route_between_its_endpoints():
    """OPUS-FIX-S81-SVC-R9 (FABLE-PD-S81-2000 rank 1): spec cut_window_pref sets the window preference of a cut route,
    so the window sits near the given along-cut position instead of in the left-to-right fill order."""
    from types import SimpleNamespace
    ev = TS.Event.__new__(TS.Event)
    ev.rep, ev.req, ev.lmax, ev.tag = {}, [], 0, "T"
    ev.spec = {"cut_window_pref": {"t": [[r"0>1:far_.*", 830.0]]}}
    ev._req = lambda **k: ev.req.append(k)
    new_bus = {0: [], 1: []}
    T = [{"buses": []}, {"buses": []}]
    ts = SimpleNamespace(tn="t", parts=[{}], T=T, bus_piece={}, _new_bus_name=lambda piece, base: base)
    ev._transit("p", ts, 0, 1, "far_p", 100, "data", "leaf far")
    ev._transit("p", ts, 0, 1, "near_p", 100, "data", "leaf near")
    assert [r["xpref"] for r in ev.req] == [830.0, None]
    assert ev.rep["cut_window_pref"] == [dict(type="t", route="0>1:far_p", bus="o_far_p", along_um=830.0)]
    # a preferred window is placed at its preference; an unpreferred one fills from the low end
    items = [(r["key"], 101, r["xpref"]) for r in ev.req]
    w = TS.windows_for(items, 2747.52, 7.2)
    lo, hi, _ = w[ev.req[0]["key"]][0]
    assert abs((lo + hi) / 2 - 830.0) < 2.2
    assert w[ev.req[1]["key"]][0][0] < 20


def test_core_move_rows_are_respaced_against_the_final_column_swap(monkeypatch):
    """OPUS-FIX-KV-PV-R5 11-21 (D28 all-16 pv split, kv3_pv_v1n: 'plan points newly inside a core box: istation
    o_pvw__u_sN_j_y_valid reg 1'): in a column swap the row's regs were re-spaced while the partner core still sat at its
    old place, so a reg landed where that core arrives.  Re-spacing now runs after every core of the type has moved."""
    from types import SimpleNamespace
    import schema as S
    import check as C
    monkeypatch.setattr(S, "Plan", lambda raw, path: SimpleNamespace(grid=0.54, layers={}))
    monkeypatch.setattr(C, "core_pins", lambda h, d=None: [])
    # a (west) and b (east) swap; a's row runs east to the face; b's FINAL box sits where a starts (old a place)
    t = dict(outline_um=[2160.0, 1520.64],
             hard_cores=[dict(inst="a", origin_um=[648.0, 604.8], outline_um=[172.8, 172.8]),
                         dict(inst="b", origin_um=[1244.16, 604.8], outline_um=[172.8, 172.8])],
             internal_stations=[dict(conn="bus:o_y", launch="core a.fault", capture="face bus o_y", from_um=[820.8, 700.0],
                                     to_um=[400.0, 1520.64], regs_um=[[700.0, 700.0]] * 3, bits=1)])
    ev = TS.Event.__new__(TS.Event)
    ev.spec = {"core_moves": {"T": {"a": [1244.16, 604.8], "b": [648.0, 604.8]}}}
    ev.raw = {"partition_types": {"T": t}, "budgets": {}}
    ev.tag, ev.plan_dir, ev.rep = "t", None, {}
    ev._core_moves()
    r = t["internal_stations"][0]
    assert r["from_um"] == [pytest.approx(1416.96), pytest.approx(700.0)] and len(r["regs_um"]) == 3
    b_final = (648.0, 604.8, 820.8, 777.6)
    assert not any(b_final[0] < q[0] < b_final[2] and b_final[1] < q[1] < b_final[3] for q in r["regs_um"])


def test_reset_consumer_sites_are_dropped_per_piece():
    """OPUS-FIX-KV-PV-R5 11-21: reset.consumer_sites_um names the base clock taps, which the split re-derives; each piece
    drops it (reported) instead of failing 'unhandled reset keys'."""
    from types import SimpleNamespace
    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn, ts.n, ts.tnames, ts.rep = "T", 2, ["T", "Te"], {}
    ts.cut = TS.Cut("x", [1080.0], 2160.0)
    ts.t = dict(reset=dict(tap_um=[100.0, 100.0], local_taps_um=[[50.0, 50.0], [1500.0, 50.0]],
                           consumer_sites_um=[["clk_t1", 17.76, 17.312], ["clk_t2", 1500.0, 17.3]]))
    ts.T = [dict(outline_um=[1080.0, 1520.64]), dict(outline_um=[1080.0, 1520.64])]
    ts._reset()
    assert all("consumer_sites_um" not in ts.T[i]["reset"] for i in range(2))
    assert ts.rep["reset_consumer_sites_dropped"] == ["T", "Te"]
    assert ts.T[1]["reset"]["local_taps_um"] == [[420.0, 50.0]]

def _local_reset_split(rows):
    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn, ts.n, ts.keep = "t", 3, 1
    ts.tnames = ["t__strip_S", "t", "t__strip_N"]
    ts.cut = TS.Cut("y", [43.2, 1183.68], 1226.88)
    ts.bus_piece = {"ft0_o": 0, "leafdn_o3": 0, "xring_o0": 1, "leafup_o1": 2}
    ts.T = [{"clock": {}} for _ in range(3)]
    ts.rep = {}
    ts._local_resets(rows)
    return ts


def test_landing_local_resets_follow_their_site_and_consumers():
    # FLOW-STRIPBODY-R2 11-21 (S81 J7 lepe_mu_C t1): a local reset copy goes to the piece of its site, in the piece frame
    ts = _local_reset_split([
        {"name": "fstart_0", "raw": "rst_rl_32", "xy_um": [1440.72, 453.792], "consumers": ["u_cland_fstart_xring_o0", "u_cland_origin"]},
        {"name": "fstart_1", "raw": "rst_rl_135", "xy_um": [75.392, 2.656], "consumers": ["u_cland_fstart_ft0_o"]},
        {"name": "fstart_9", "raw": "rst_rl_9", "xy_um": [75.392, 1220.0], "consumers": ["u_cland_fstart_leafup_o1"]}])
    # a copy sited in a cut-off piece is dropped (that piece builds its own shallow reset tree) and reported
    assert "landing_local_resets" not in ts.T[0]["clock"] and "landing_local_resets" not in ts.T[2]["clock"]
    assert ts.T[1]["clock"]["landing_local_resets"][0]["xy_um"] == [1440.72, 410.592]
    assert ts.rep["local_resets"] == {"t": ["fstart_0"]}
    assert ts.rep["local_resets_dropped"] == {"t__strip_S": ["fstart_1"], "t__strip_N": ["fstart_9"]}


def test_landing_local_reset_consumer_across_a_cut_fails_closed():
    # a keep-piece copy whose consumer landing went to a strip piece
    with pytest.raises(TS.SplitError, match="consumer u_cland_fstart_leafdn_o3 in piece 0"):
        _local_reset_split([{"name": "f", "raw": "r", "xy_um": [400.0, 300.0], "consumers": ["u_cland_fstart_leafdn_o3"]}])


# ---- gen-mode types (HEAD): type nets, content params, native stage groups (FABLE-FIX-HEAD-LEP0N-R5 11-21)
def _gen_mode_split(spec=None, nets=None, contents=None):
    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn, ts.n, ts.keep = "hd", 2, 1
    ts.tnames = ["hd_w", "hd"]
    ts.cut = TS.Cut("x", [907.2], 1892.16)
    ts.ev = _Ev({}, dict(spec or {}))
    ts.rep = {}
    rows = contents or [
        dict(inst="u_core", module="hub", params={"TXI": "16'h2442", "PIN": 6},
             bind={"ck": "clk", "h2r1": "net:h2r1", "r2h1": "net:r2h1", "pin": "net:pin"}),
        dict(inst="u_io", module="io", bind={"ck": "clk", "pin": "net:pin"}),
        dict(inst="u_rg1", module="rgn", params={"K": 1}, bind={"ck": "clk", "h2r": "net:h2r1", "r2h": "net:r2h1"})]
    ts.content_piece = {"u_core": 1, "u_io": 1, "u_rg1": 0}
    ts.T = [dict(contents=[]) for _ in range(2)]
    for c in rows:
        ts.T[ts.content_piece[c["inst"]]]["contents"].append(json.loads(json.dumps(c)))
    ts.t = dict(contents=rows)
    if nets is not False:
        ts.t["nets"] = nets or [dict(name="h2r1", width=574), dict(name="r2h1", width=558), dict(name="pin", width=1150)]
    return ts


def test_type_net_inside_one_piece_stays_and_a_cut_net_is_queued_with_its_driver():
    ts = _gen_mode_split(dict(net_drivers={"hd": {"h2r1": "u_core.h2r1", "r2h1": "u_rg1"}}, net_kinds={"hd": {"r2h1": "ctl"}}))
    ts._type_nets()
    assert "nets" not in ts.T[0] and ts.T[1]["nets"] == [dict(name="pin", width=1150)]
    got = {c["net"]: (c["drv"][0], c["drv"][1]["inst"], c["drv"][2], c["load"][0], c["load"][1]["inst"], c["load"][2],
                      c["width"], c["kind"]) for c in ts.net_cuts}
    assert got == {"h2r1": (1, "u_core", "h2r1", 0, "u_rg1", "h2r", 574, "data"),
                   "r2h1": (0, "u_rg1", "r2h", 1, "u_core", "r2h1", 558, "ctl")}
    assert ts.rep["nets"]["kept"] == [0, 1]


@pytest.mark.parametrize("spec,nets,match", [
    ({}, None, "net_drivers must name its driving leaf port"),
    (dict(net_drivers={"hd": {"h2r1": "u_io"}}), None, "net_drivers must name its driving leaf port"),
    (dict(net_drivers={"hd": {"nope": "u_core"}}), None, "name no net"),
    ({}, [dict(name="h2r1", width=574), dict(name="pin", width=1150)], "does not declare"),
    (dict(net_drivers={"hd": {"h2r1": "u_core", "r2h1": "u_rg1"}}),
     [dict(name="h2r1", width=574), dict(name="r2h1", width=558), dict(name="pin", width=1150),
      dict(name="idle", width=1)], "net idle has no leaf port")])
def test_type_net_cut_fails_closed(spec, nets, match):
    with pytest.raises(TS.SplitError, match=match):
        _gen_mode_split(spec, nets)._type_nets()


def test_three_leaf_net_across_a_cut_fails_closed():
    rows = [dict(inst="u_core", module="hub", bind={"rs": "net:rs"}), dict(inst="u_io", module="io", bind={"rs": "net:rs"}),
            dict(inst="u_rg1", module="rgn", bind={"rs": "net:rs"})]
    with pytest.raises(TS.SplitError, match="with 3 leaf ports"):
        _gen_mode_split({}, [dict(name="rs", width=123)], rows)._type_nets()


def test_type_without_nets_is_untouched_and_a_stray_net_bind_fails():
    rows = [dict(inst="u_core", module="hub", bind={"ck": "clk"}), dict(inst="u_io", module="io", bind={}),
            dict(inst="u_rg1", module="rgn", bind={})]
    ts = _gen_mode_split({}, False, rows)
    ts._type_nets()
    assert ts.net_cuts == [] and all("nets" not in x for x in ts.T) and "nets" not in ts.rep


def test_net_requests_point_both_binds_at_the_cut_buses():
    ts = _gen_mode_split(dict(net_drivers={"hd": {"h2r1": "u_core", "r2h1": "u_rg1.r2h"}}))
    ts._type_nets()
    ev = TS.Event.__new__(TS.Event)
    ev.ts, ev.rep, ev.pmap = {"hd": ts}, {}, {"lep0N": ["lep0N_w", "lep0N"]}
    ev.raw = dict(partitions=[dict(name="lep0N", type="hd")])
    calls = []

    def transit(part, ts_, a, b, stem, width, kind, how, pc=None):
        calls.append((part, a, b, stem, width, kind, how))
        return f"o_{stem}", f"i_{stem}", f"L{len(calls)}"
    ev._transit = transit
    ev._net_requests()
    assert calls == [("lep0N", 1, 0, "h2r1", 574, "data", "type net h2r1"), ("lep0N", 0, 1, "r2h1", 558, "data", "type net r2h1")]
    core = ts.T[1]["contents"][0]["bind"]
    rg = ts.T[0]["contents"][0]["bind"]
    assert core["h2r1"] == "bus:o_h2r1" and rg["h2r"] == "bus:i_h2r1"
    assert rg["r2h"] == "bus:o_r2h1" and core["r2h1"] == "bus:i_r2h1" and core["pin"] == "net:pin"
    assert [r["lanes"] for r in ev.rep["net_routes"]] == [["L1"], ["L2"]]


def test_content_params_delta_is_applied_with_the_split():
    ts = _gen_mode_split(dict(content_params={"hd": {"u_core": {"TXI": "16'h2222", "PIN": None}}}))
    ts._content_params()
    assert ts.T[1]["contents"][0]["params"] == {"TXI": "16'h2222"}
    assert ts.rep["content_params"] == {"u_core": {"TXI": ["16'h2442", "16'h2222"], "PIN": [6, None]}}
    for bad, match in (({"u_x": {"A": 1}}, "names no content"), ({"u_core": {"PIN": 6}}, "changes nothing")):
        with pytest.raises(TS.SplitError, match=match):
            _gen_mode_split(dict(content_params={"hd": bad}))._content_params()


def _nsg(groups, v2=False):
    if v2:
        return dict(schema="opentallas.native_stage_groups.v2", groups=groups, contents=[
            dict(content="u_core", module="hub", params={"TXI": "16'h2442", "PIN": 6}),
            dict(content="u_io", module="io", params={}), dict(content="u_rg1", module="rgn", params={"K": 1})])
    return dict(schema="opentallas.native_stage_groups.v1", content="u_core", module="hub",
                params={"TXI": "16'h2442", "PIN": 6}, groups=groups)


def test_native_stage_groups_follow_their_content_into_the_piece_frame():
    rows = [dict(prefix=r"u_core\.u\.g_plw", rect_um=[1000.0, 10.0, 1100.0, 20.0], tag="stage:plw"),
            dict(prefix=r"u_io\.u\.g_pin", rect_um=[1800.0, 10.0, 1850.0, 20.0], tag="stage:pin"),
            dict(prefix=r"u_rg1\.g_rxf\.g_s\[0\]", rect_um=[100.0, 600.0, 200.0, 620.0], tag="stage:rx0", match="cell"),
            dict(prefix=r"u_rg1\.g_txi\.g_s\[3\]", rect_um=[900.0, 600.0, 1000.0, 620.0], tag="stage:txi3")]
    ts = _gen_mode_split(dict(content_params={"hd": {"u_core": {"TXI": "16'h2222"}}},
                              native_stage_drop={"hd": [r"u_rg1\\\.g_txi\\\.g_s\\\[[23]\\\]"]}))
    ts._content_params()
    L = [dict(), dict()]
    ts._native_stage_groups(_nsg(rows, v2=True), L)
    assert L[0]["native_stage_groups"] == dict(schema="opentallas.native_stage_groups.v1", content="u_rg1", module="rgn",
                                               params={"K": 1}, groups=[rows[2]])
    e = L[1]["native_stage_groups"]
    assert e["schema"] == "opentallas.native_stage_groups.v2"
    assert e["contents"] == [dict(content="u_core", module="hub", params={"TXI": "16'h2222", "PIN": 6}),
                             dict(content="u_io", module="io", params={})]
    assert [g["rect_um"] for g in e["groups"]] == [[pytest.approx(92.8), 10.0, pytest.approx(192.8), 20.0],
                                                   [pytest.approx(892.8), 10.0, pytest.approx(942.8), 20.0]]
    assert ts.rep["native_stage_groups"] == dict(pieces=[1, 2], dropped=[rows[3]["prefix"]])


def test_native_stage_groups_one_content_base_and_fail_closed_forms():
    row = dict(prefix=r"u_core\.u\.g_plw", rect_um=[1000.0, 10.0, 1100.0, 20.0], tag="stage:plw")
    L = [dict(), dict()]
    _gen_mode_split()._native_stage_groups(_nsg([row]), L)
    assert "native_stage_groups" not in L[0] and L[1]["native_stage_groups"]["content"] == "u_core"
    for groups, spec, match in (
            ([row | {"rect_um": [100.0, 10.0, 200.0, 20.0]}], {}, "lies outside piece 1"),
            ([row | {"rect_um": [900.0, 10.0, 1000.0, 20.0]}], {}, "native stage group"),
            ([row | {"prefix": "u_other"}], {}, "starts with no listed content"),
            ([row], dict(native_stage_drop={"hd": ["u_none"]}), "matches no native stage group")):
        with pytest.raises(TS.SplitError, match=match):
            _gen_mode_split(spec)._native_stage_groups(_nsg(groups), [dict(), dict()])
    with pytest.raises(TS.SplitError, match="schema/fields"):
        _gen_mode_split()._native_stage_groups(dict(_nsg([row]), schema="v0"), [dict(), dict()])


# ---- HEAD type / clock keys of a gen-mode type (FABLE-FIX-HEAD-LEP0N-R6 11-21)
def _head_keys_split(t, spec=None):
    ts = TS.TypeSplit.__new__(TS.TypeSplit)
    ts.tn, ts.n, ts.keep = "hd", 2, 1
    ts.tnames = ["hd_w", "hd"]
    ts.cut = TS.Cut("x", [907.2], 1892.16)
    ts.ev = _Ev({}, dict(spec or {}))
    ts.rep = {}
    ts.t = t
    ts.T = [dict() for _ in range(2)]
    return ts


def test_id_strap_goes_to_every_piece_and_an_outside_site_is_reseated():
    ts = _head_keys_split(dict(id_straps=[dict(name="strap_rst_ph", width=1, layer="M7", sites_um=[[10.016, 4.32]]),
                                          dict(name="strap_e", width=1, layer="M7", sites_um=[[1880.0, 4.32]])]))
    ts._id_straps()
    assert [r["name"] for r in ts.T[0]["id_straps"]] == [r["name"] for r in ts.T[1]["id_straps"]] == ["strap_rst_ph", "strap_e"]
    assert ts.T[0]["id_straps"][0]["sites_um"] == [[10.016, 4.32]]        # inside the W piece: unchanged
    assert ts.T[1]["id_straps"][0]["sites_um"] == [[10.016, 4.32]]        # re-seated 10.016 from the E piece's low edge
    assert ts.T[1]["id_straps"][1]["sites_um"] == [[972.8, 4.32]]         # inside the E piece: piece frame
    assert ts.T[0]["id_straps"][1]["sites_um"] == [[895.04, 4.32]]        # re-seated 12.16 from the W piece's high edge
    assert [(r["piece"], r["strap"]) for r in ts.rep["id_strap_sites_reseated"]] == [("hd_w", "strap_e"), ("hd", "strap_rst_ph")]
    assert ts.t["id_straps"][0]["sites_um"] == [[10.016, 4.32]]           # the base rows are not edited


def test_reset_start_raw_exports_are_only_dropped_for_rederivation():
    t = dict(private_reset_start_exports=True,
             reset_start_raw_exports=[dict(port="rst_start_raw_0", instance="u_rrl_698", net="rst_rl_698", xy_um=[972.1, 595.1])])
    with pytest.raises(TS.SplitError, match="reset_start_raw_exports names the whole-type reset relay tree"):
        _head_keys_split(t)._reset_start_exports()
    with pytest.raises(TS.SplitError, match="only reset_start_raw_exports can be dropped"):
        _head_keys_split(t, dict(drop_type_keys=["buses"]))._reset_start_exports()
    ts = _head_keys_split(t, dict(drop_type_keys=["reset_start_raw_exports"]))
    ts._reset_start_exports()
    assert all(q == {"private_reset_start_exports": True} for q in ts.T)
    assert ts.rep["type_keys_dropped"] == ["reset_start_raw_exports"]


def test_clock_start_capture_follows_the_piece_tap_and_reserved_sites_their_rect():
    ck = dict(tap_um=[1131.84, 596.16], start_capture_um=[1140.48, 596.16],
              reserved_sites_um=[dict(rect_um=[17.496, 443.34, 20.196, 445.23], kind="die_clock_tree", route_layers="M1-M7"),
                                 dict(rect_um=[961.3, 642.1, 966.2, 645.6], kind="die_clock_tree", route_layers="M1-M7")])
    ts = _head_keys_split(dict(clock=ck))
    w, e = dict(tap_um=[449.28, 708.48]), dict(tap_um=[224.64, 596.16])
    ts._clock_sites(ck, w, 0)
    ts._clock_sites(ck, e, 1)
    assert w["start_capture_um"] == [457.92, 708.48] and e["start_capture_um"] == [233.28, 596.16]
    assert [r["rect_um"] for r in w["reserved_sites_um"]] == [[17.496, 443.34, 20.196, 445.23]]
    assert e["reserved_sites_um"] == [dict(rect_um=[54.1, 642.1, 59.0, 645.6], kind="die_clock_tree", route_layers="M1-M7")]
    ck["reserved_sites_um"].append(dict(rect_um=[905.0, 10.0, 909.0, 12.0], kind="die_clock_tree"))
    with pytest.raises(TS.SplitError, match="clock.reserved_sites_um die_clock_tree .* straddles a cut"):
        ts._clock_sites(ck, {"tap_um": [0.0, 0.0]}, 0)


def test_head_clock_scalars_are_known_and_start_keys_need_drop_clock_keys():
    assert {"insertion_ff_ps", "tap_model", "tap_group", "landing_export_form"} <= TS.CLOCK_COPY_KEYS
    ck = dict(tap_model="frozen_anchor", insertion_ff_ps=380.0, tap_passthrough=True, landing_reader_start={"depth": 4},
              reset_tree_anchor={})
    with pytest.raises(TS.SplitError, match=r"unhandled clock keys \['landing_reader_start', 'reset_tree_anchor'\]"):
        _head_keys_split(dict(clock=ck))._clock()


# ---- HEAD gen-mode ports, pair core taps and per-bus landing pins (FABLE-FIX-HEAD-LEP0N-R7 11-21)
class _Geo:
    def __init__(self, ports):
        self.ports = ports


def test_port_face_of_a_port_without_face_comes_from_the_plan_geometry():
    ev = _Ev({}, {})
    assert TS.port_face(ev, dict(id="a", face="N")) == "N"
    ev._native_port_geometry = _Geo({"kd__0": dict(face="W", window_um=[10.0, 20.0]), "x": dict()})
    assert TS.port_face(ev, dict(id="kd__0", src=dict(part="ctl", bus="o"), dst=dict(part="lep", bus="i"))) == "W"
    with pytest.raises(TS.SplitError, match="port x has no face"):
        TS.port_face(ev, dict(id="x"))


def test_pair_core_tap_in_the_band_is_legal_inside_its_cores_piece():
    # hd_lep0N: u_rg<i>.u_pair.clk is declared at its band-side source, 250 um off the pair
    def piece(xy):
        ts = TS.TypeSplit.__new__(TS.TypeSplit)
        ts.tn = "hd"
        ts.cut = TS.Cut("x", [820.8], 1892.16)
        ts.t = {"hard_cores": [{"inst": "u_rg0.u_pair", "origin_um": [967.68, 846.72], "outline_um": [777.6, 492.48]}]}
        return ts._core_tap_piece({"kind": "core", "name": "u_rg0.u_pair.clk", "xy": xy})
    assert piece([1328.88, 596.16]) == 1
    with pytest.raises(TS.SplitError, match="not on its core .* and not in its piece"):
        piece([467.04, 643.68])


def test_head_per_bus_landing_pin_names():
    m = TS.HEAD_BUS_PIN.match("cland_dn_ready_coll_i0")
    assert m and m.group(2) == "coll_i0"
    assert TS.HEAD_BUS_PIN.match("cland_up_fault_lepk_o0").group(2) == "lepk_o0"
    assert TS.HEAD_BUS_PIN.match("rst_start_raw_3").group(2) == "3"
    assert not TS.HEAD_BUS_PIN.match("cland_tstart_in") and not TS.HEAD_BUS_PIN.match("fclk_in_coll_i0")


# ---- HEAD region-monitor landing contract: derived data, re-composed after the split (FABLE-FIX-HEAD-LEP0N-R7 11-21)
def _head_region_split(spec=None):
    ts = _head_keys_split(dict(buses=[dict(name="coll_i1"), dict(name="lepk_o0")]), spec)
    ts.cut = TS.Cut("x", [820.8], 1892.16)
    ts.W, ts.H = 1892.16, 1408.32
    ts.T = [dict(clock={}) for _ in range(2)]
    ts.bus_piece = {"coll_i1": 0, "lepk_o0": 1}
    return ts


def test_region_monitor_contract_splits_by_bus_and_leaves_the_cut_rows_to_the_compose():
    lc = dict(monitor="region", base_type="hd",
              pins=[dict(name="cland_dn_ready_coll_i1", xy_um=[2.144, 924.44], layer="M7"),
                    dict(name="cland_up_ready_lepk_o0", xy_um=[1890.0, 100.0], layer="M7"),
                    dict(name="rst_start_raw_0", xy_um=[900.0, 600.0], layer="M7")],
              bands={"coll_i1": dict(rect_um=[17.28, 634.24, 58.32, 840.24])},
              collector_children=[dict(bus="coll_i1", ready="cland_dn_ready_coll_i1", fault="cland_dn_fault_coll_i1",
                                       xy_um=[0, 924.44], seam=True)],
              collector_local_sources=[dict(name="coll_i1", xy_um=[0, 924.44])],
              collector_root_node="cland_up_ready_lepk_o0", collector_tree=None)
    with pytest.raises(TS.SplitError, match="set spec landing_recompose"):
        _head_region_split()._landing_contract(lc)
    ts = _head_region_split(dict(landing_recompose=True))
    ts._landing_contract(lc)
    w, e = (t["clock"]["landing_contract"] for t in ts.T)
    assert [p["name"] for p in w["pins"]] == ["cland_dn_ready_coll_i1"] and [p["name"] for p in e["pins"]] == ["cland_up_ready_lepk_o0"]
    assert e["pins"][0]["xy_um"] == [1069.2, 100.0]                       # E piece frame; the raw START pin is dropped
    assert list(w["bands"]) == ["coll_i1"] and e["bands"] == {}
    assert [c["bus"] for c in w["collector_children"]] == ["coll_i1"] and e["collector_children"] == []
    assert w["collector_root_node"] == "RAW_RECOMPOSE_REQUIRED" and e["collector_root_node"] == "cland_up_ready_lepk_o0"
    assert w["status"] == e["status"] == "RAW_RECOMPOSE_REQUIRED" and w["base_type"] == "hd_w"
    assert ts.head_recompose and ts.coll_links == [] and ts.relay_links == [] and ts.croot == ts.keep


def test_head_landing_network_pin_follows_its_bus():
    ev = TS.Event.__new__(TS.Event)
    ts = _head_region_split(dict(landing_recompose=True))
    ts.head_recompose = True
    ev.ts = {"hd": ts}
    ev.raw_type = lambda base: "hd"
    assert ev._piece_of_pin("lep", "cland_dn_ready_coll_i1") == (0, "cland_dn_ready_coll_i1")
    assert ev._piece_of_pin("lep", "fclk_out_lepk_o0") == (1, "fclk_out_lepk_o0")
    assert ev._piece_of_pin("lep", "cland_up_fault_lepk_o0") == (1, "cland_up_fault_lepk_o0")
    assert ev._piece_of_pin("lep", "cland_tstart_in") == (1, "cland_tstart_in")
    with pytest.raises(TS.SplitError, match="has no piece"):
        ev._piece_of_pin("lep", "cland_dn_ready_7")


def test_census_none_plan_has_no_census_to_split(tmp_path):
    ev = TS.Event.__new__(TS.Event)
    ev.out = dict(census={"none": "top-down plan of a new die"})
    assert ev._census(tmp_path) == {}


def test_gen_mode_cut_leg_gets_its_leaf_or_a_feed_through():
    # hd_lep0N coll_i0: the band is in piece W, the leaf u_core in piece E
    class _T:
        tnames = ["hd_w", "hd"]
    note = "T: piece 0 of the crossing leg bus:coll_i0"
    w = dict(buses=[dict(name="coll_i0", dir="in", width=514, leaf="u_core.coll_i0"), dict(name="o_coll_i0_p", dir="out", width=514)],
             contents=[dict(inst="u_rg1", bind={})], sources=[],
             internal_stations=[dict(conn="bus:o_coll_i0_p", regs_um=[], launch="bus coll_i0", capture="face bus o_coll_i0_p", note=note)])
    e = dict(buses=[dict(name="i_coll_i0_p", dir="in", width=514)], contents=[dict(inst="u_core", bind={})],
             internal_stations=[dict(conn="bus:i_coll_i0_p", regs_um=[], launch="face:W", capture="u_core.coll_i0", note=note)])
    ev = TS.Event.__new__(TS.Event)
    ev.ts, ev.tag, ev.rep, ev.out = {"hd": _T()}, "T", {}, dict(partition_types={"hd_w": w, "hd": e})
    ev._gen_leg_leaves()
    assert e["buses"][0]["leaf"] == "u_core.coll_i0"
    feed = w["contents"][-1]
    assert (feed["inst"], feed["module"], feed["params"], feed["bind"]) == (
        "u_feed_o_coll_i0_p", "ot_dp_feed", {"W": 514}, {"d": "bus:coll_i0", "q": "bus:o_coll_i0_p"})
    assert "leaf" not in w["buses"][0] and w["sources"] == ["rtl/common/ot_dp_feed.sv"]
    assert (ROOT / "rtl/common/ot_dp_feed.sv").is_file()


def test_carried_short_fixed_never_falls_below_the_new_station_rows():
    # lepe_mu_C t1 up_s_7N_L0: base fixed 3 with 4 station rows (short, carried); the cut leaves 1 row -> 1, not 0
    assert TS.carried_fixed(3, 4, 1) == 1
    assert TS.carried_fixed(4, 4, 2) == 2
    assert TS.carried_fixed(2, 2, 1) == 1
    assert TS.carried_fixed(3, 4, 2) == 2


def test_cut_face_reserve_keeps_its_span_free_of_windows():
    """FABLE-FIX-KV-PV-SINKSPREAD (KV pv D29): spec cut_face_reserve_um spans take no cut window; a pinned window
    whose preference lies in a reserve slides beside it, and the reach-bounded left packing steps over one."""
    per_um, L = 7.695, 1520.64
    routes = [("tr:a", 1025, None), ("tr:b", 271, None), ("leg:c", 400, 700.0), ("leg:top", 900, 1460.0)]
    free = TS.windows_for(list(routes), L, per_um)
    assert free["tr:a"][0][0] < 60 and free["leg:top"][0][1] > 1400     # unreserved: bottom fill, top pinned leg
    res = TS.reserve_spans([[1397.52, 1512.0], [8.64, 149.04], [300, 350]], L, "t")
    assert res == [(8.64, 149.04), (300.0, 350.0), (1397.52, 1512.0)]
    w = TS.windows_for(list(routes), L, per_um, reserved=res)
    assert set(w) == {r[0] for r in routes}
    assert sum(n for segs in w.values() for _, _, n in segs) == 1025 + 271 + 400 + 900
    spans = sorted((lo, hi) for segs in w.values() for lo, hi, _ in segs)
    for lo, hi in spans:
        assert all(hi <= r0 + 1e-6 or lo >= r1 - 1e-6 for r0, r1 in res), (lo, hi)
    assert all(a[1] <= b[0] + 1e-6 for a, b in zip(spans, spans[1:]))
    assert w["leg:top"][0][1] <= 1397.52 + 1e-6                          # the pinned leg moved below the top reserve
    # reach-bounded (ft) windows: the earliest-deadline left packing also leaves the reserve free
    ranged = [(f"ft:{i}", 600, 120.0 + i, (60.0, 420.0)) for i in range(3)]
    w2 = TS.windows_for(ranged, L, per_um, reserved=[(150.0, 200.0)])
    for segs in w2.values():
        for lo, hi, _ in segs:
            assert hi <= 150 + 1e-6 or lo >= 200 - 1e-6
    with pytest.raises(TS.SplitError, match="cut_face_reserve_um"):
        TS.reserve_spans([[100, 2000]], L, "t")
    assert TS.windows_for(list(routes), L, per_um, reserved=()) == free


def test_cut_face_bank_inset_moves_the_inventory_and_writes_the_kit_key(monkeypatch):
    """FABLE-FIX-KV-PV-SINKSPREAD (KV pv D29): spec cut_face_bank_inset_um sites the new cut-face banks inside the
    piece in the sink inventory and gives each piece its budgets.face_flop_ew_types inset on its cut face."""
    from types import SimpleNamespace
    import schema
    import gen_phys
    a = dict(clock={}, ft_slots=[])
    b = dict(clock={}, ft_slots=[])
    ev = TS.Event.__new__(TS.Event)
    ev.spec = dict(axis="x", cut_face_bank_inset_um=25.92)
    ev.ts = {"t": SimpleNamespace(tnames=["a", "b"])}
    ev.out = dict(partition_types=dict(a=a, b=b), partitions=[dict(name="a", type="a"), dict(name="b", type="b")],
                  budgets=dict(face_flop_ew_types=dict(b=dict(row_stride=2))),
                  ports=[dict(id="cut", src=dict(part="a", bus="o_x_p"), dst=dict(part="b", bus="i_x_p"))])
    ev.rep = dict(ports_added=["cut"])
    monkeypatch.setattr(schema, "Plan", lambda *_args: object())
    monkeypatch.setattr(gen_phys, "type_pins", lambda _p, tn: [("o_x_p", bit, "M4", 1080.0, 50 + bit, "E") if tn == "a" else
                                                               ("i_x_p", bit, "M4", 0.0, 50 + bit, "W") for bit in range(2)])
    ev._inventory_cut_sinks()
    assert sorted(r[0] for r in a["clock"]["sink_sites_um"]) == [pytest.approx(1080 - 25.92)] * 2
    assert sorted(r[0] for r in b["clock"]["sink_sites_um"]) == [pytest.approx(25.92)] * 2
    assert ev.out["budgets"]["face_flop_ew_types"] == dict(a=dict(inset_um=dict(E=25.92)), b=dict(row_stride=2, inset_um=dict(W=25.92)))
    assert ev.rep["cut_face_bank_inset_um"] == dict(a=dict(E=25.92), b=dict(W=25.92))
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(ev.out["budgets"]["face_flop_ew_types"], schema.SCHEMA["properties"]["budgets"]["properties"]["face_flop_ew_types"])
    # without the key: the legacy 1-um face site and no budgets row
    ev2 = TS.Event.__new__(TS.Event)
    a2, b2 = dict(clock={}, ft_slots=[]), dict(clock={}, ft_slots=[])
    ev2.out = dict(ev.out, partition_types=dict(a=a2, b=b2), budgets={})
    ev2.rep = dict(ports_added=["cut"])
    ev2._inventory_cut_sinks()
    assert sorted(r[0] for r in b2["clock"]["sink_sites_um"]) == [pytest.approx(1.0)] * 2 and ev2.out["budgets"] == {}


def test_drop_clock_keys_drops_reserved_sites_that_straddle_the_cut():
    """FABLE-FIX-KV-PV-SINKSPREAD (KV pv D29): the die clock spine of a pv type runs on the x 1080 cut; with
    drop_clock_keys the reserved sites are dropped for re-derivation instead of failing the split."""
    ck = dict(tap_um=[1131.84, 596.16], reserved_sites_um=[dict(rect_um=[905.0, 10.0, 909.0, 12.0], kind="die_clock_tree"),
                                                          dict(rect_um=[17.496, 443.34, 20.196, 445.23], kind="die_clock_tree")])
    ts = _head_keys_split(dict(clock=ck))
    with pytest.raises(TS.SplitError, match="straddles a cut"):
        ts._clock_sites(ck, {"tap_um": [0.0, 0.0]}, 0)
    ts.ev.spec = dict(ts.ev.spec, drop_clock_keys=["reserved_sites_um"])
    c = {"tap_um": [0.0, 0.0]}
    ts._clock_sites(ck, c, 0)
    assert "reserved_sites_um" not in c and len(ck["reserved_sites_um"]) == 2
