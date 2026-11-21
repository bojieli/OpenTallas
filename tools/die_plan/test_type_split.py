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
