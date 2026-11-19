"""CBC-RULES-1119 cbc_pass: plan key, shared thresholds, ft stations + K deltas, boundary banks, depth rows, token cost."""
import cbc_pass as C


def test_plan_key_default_on_off_and_overrides():
    assert C.cbc_settings({}) == (True, C.DEFAULTS)
    assert C.cbc_settings({"cbc": True})[0] is True
    assert C.cbc_settings({"cbc": False})[0] is False
    on, th = C.cbc_settings({"cbc": {"tap_sinks": 800}})
    assert on and th["tap_sinks"] == 800 and th["hop_um"] == 405.0
    assert C.cbc_settings({"cbc": {"enabled": False}})[0] is False


def test_thresholds_are_the_r713_amended_set():
    # amendment 11-19: keep 405 um per placed leg; r713: 13 levels, 1,000 sinks per tap, 32 per reset leaf
    assert (C.HOP_UM, C.DEPTH_LEVELS, C.TAP_SINKS, C.RESET_LEAF) == (405.0, 13, 1000, 32)


class FakeP:
    def __init__(self):
        self.types = {"t": dict(outline_um=[1000.0, 300.0], ft_slots=[
            dict(name="f", stations=1, in_face="W", out_face="E", width=64),      # 1000 um on 1 station -> 3
            dict(name="g", stations=1, in_face="N", out_face="S", width=8)])}     # 300 um: fine
        self.parts = {"p0": dict(type="t"), "p1": dict(type="t")}
        self.lanes = {"L0": {}, "L1": {}}

    def lane_crossings(self, lid):
        return [("p0", "f", 0, 1), ("p1", "f", 1, 2)] if lid == "L0" else [("p0", "g", 0, 1)]

    def lane_natural(self, lid):
        return dict(cycles=10)


def test_ft_stations_and_k_deltas():
    P = FakeP()
    P.types["t"]["hard_cores"] = [dict(inst="u_c", origin_um=[200.0, 100.0], outline_um=[400.0, 100.0])]  # a core-class leg
    rows = C.ft_station_rows(P, 405.0)
    assert list(rows) == [("t", "f")] and rows[("t", "f")]["set_stations"] == 3 and rows[("t", "f")]["delta"] == 2
    kd = C.k_deltas(P, rows)
    assert kd == [dict(lane="L0", before=10, after=14, delta=4, cause="p0.f+2,p1.f+2")]


def test_boundary_rows_from_bound_rtl(tmp_path):
    P = FakeP()
    P.types["t"]["buses"] = [dict(name="a", dir="in"), dict(name="b", dir="out")]
    (tmp_path / "x_t.sv").write_text("module t;\n ot_dp_st #(.W(1)) u_bin_a (.clk(clk));\nendmodule\n")
    rows = C.boundary_rows(P, str(tmp_path), ["t"])
    assert rows == [dict(type="t", bus="b", dir="out", width=None, rule="bus without its boundary bank")]


def test_depth_rows(tmp_path):
    p = tmp_path / "d.tsv"
    p.write_text("type\tendpoint\tlevels\nt\tu_a/D\t12\nt\tu_b/D\t30\n")
    assert C.depth_rows(str(p), 13) == [dict(type="t", endpoint="u_b/D", levels=30, add_stages=2)]


def test_token_cost_bounds():
    kd = [dict(delta=3), dict(delta=3)]
    c = C.token_cost(kd, 272641, 36, 1.2e9)
    assert c["low"]["add_cycles"] == 108 and c["high"]["add_cycles"] == 216
    assert c["base_tok_s"] > c["low"]["tok_s"] > c["high"]["tok_s"]
    assert C.token_cost([], 1, 1, 1.0) is None


def test_schema_accepts_the_cbc_key():
    import jsonschema
    import schema as S
    sub = S.SCHEMA["properties"]["cbc"]
    for ok in (True, False, {"enabled": True}, {"tap_sinks": 800, "hop_um": 300}):
        jsonschema.validate(ok, sub)
    for bad in ({"hop_um": 500}, {"x": 1}, "yes"):
        try:
            jsonschema.validate(bad, sub)
        except jsonschema.ValidationError:
            continue
        raise AssertionError(bad)


def test_stage_rtl_several_binders_and_name_forms(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.mkdir(); b.mkdir()
    (a / 'hub_part.sv').write_text('module hub_part; endmodule\n')
    (b / 'hub.sv').write_text('// later binder\n')
    (b / 's81p_tile.sv').write_text('module tile; endmodule\n')
    (b / 'pv_bound.sv').write_text('module pv; endmodule\n')
    d, n = C.stage_rtl(f'{a},{b}', ['hub', 'tile', 'pv', 'none'], tmp_path / 'out')
    assert n == 3
    assert (d / 'hub.sv').resolve() == (b / 'hub.sv').resolve()      # exact stem beats a _part form
    assert (d / 'tile.sv').read_text().startswith('module tile')
    assert (d / 'pv.sv').exists() and not (d / 'none.sv').exists()


def test_ft_priced_by_leg_class():
    # COORD 11-19: no +cycle from distance alone -- a pure ft chain over no core is a buffered leg (550 um per hop)
    P = FakeP()
    f = P.types['t']['ft_slots'][0]
    f.update(in_window_um=[140, 160], out_window_um=[140, 160])
    r = C.ft_station_rows(P, 405.0)[('t', 'f')]
    assert r['leg_class'] == 'buffered' and r['core_span_um'] == 0 and r['set_stations'] == 2 and r['delta'] == 1
    P.types['t']['hard_cores'] = [dict(inst='u_c', origin_um=[200.0, 100.0], outline_um=[400.0, 100.0])]
    r = C.ft_station_rows(P, 405.0)[('t', 'f')]
    assert r['leg_class'] == 'core' and r['core_span_um'] == 400 and r['set_stations'] == 3
    f['name'] = 'strap_ca_f'
    assert ('t', 'strap_ca_f') not in C.ft_station_rows(P, 405.0)


def test_ft_span_is_pin_to_pin():
    # FABLE-PD-QC-0407: a corner slot whose pins sit near the corner is a short leg, not (w + h) / 2
    P = FakeP()
    P.types['t']['ft_slots'] = [dict(name='c', stations=1, in_face='W', out_face='N', width=4,
                                     in_window_um=[280.0, 290.0], out_window_um=[5.0, 15.0])]
    assert C.ft_station_rows(P, 405.0) == {}
    (a, b), = C.ft_pin_legs(P.types['t'], dict(P.types['t']['ft_slots'][0], width=1))
    assert a == (0.0, 285.0) and b == (10.0, 300.0)
    # a W -> N slot with its pins far apart is priced on that pin distance (buffered: 550 um per hop)
    P.types['t']['ft_slots'][0].update(in_window_um=[0.0, 10.0], out_window_um=[990.0, 1000.0])
    r = C.ft_station_rows(P, 405.0)[('t', 'c')]
    assert r['leg_class'] == 'buffered' and r['span_um'] > 1200 and r['corner_span_um'] == 650.0 and r['set_stations'] == 3


def test_ft_pins_from_pin_table():
    # the bound pin sites: schema.pin_positions on the slot's layers (both ends, bit i -> bit i)
    t = dict(outline_um=[1000.0, 300.0])
    sl = dict(name='f', in_face='W', out_face='E', width=4, layers=['M5'], in_window_um=[0.0, 40.0], out_window_um=[200.0, 240.0])
    legs = C.ft_pin_legs(t, sl)
    assert len(legs) == 4 and all(a[0] == 0.0 and b[0] == 1000.0 for a, b in legs)
    assert all(0.0 <= a[1] <= 40.0 and 200.0 <= b[1] <= 240.0 for a, b in legs)
    assert legs[0][0][1] < legs[3][0][1] and legs[0][1][1] < legs[3][1][1]


def test_tap_rows_use_tap_resolve_span():
    # one tap, 1,000 um row of sinks: tap_resolve.solve (span 300) appends taps until every region is W + H <= 300
    class TP:
        raw = {}
    t = dict(outline_um=[1100.0, 100.0], clock={"tap_mode": "explicit"})
    sinks = [(float(x), 50.0, 4.0) for x in range(50, 1050, 10)]
    added, s0, s1, f = C.solve_taps(TP(), 't', t, [('clk_t0', 550.0, 50.0)], sinks, 1000)
    assert s0[0][4] > 300 and added and all(q[4] <= 300.0 for q in s1) and f == 1.0
    assert C.sink_tiles(sinks) == 7 and C.sink_tiles([(1.0, 1.0, 0.0)]) == 0
