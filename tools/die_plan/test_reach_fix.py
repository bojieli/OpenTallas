"""reach_fix.py (REACH-FIX-1, OWNER 11-12): one failing fixture per class that the tool fixes, plus idempotency."""
import copy
import json
import sys
import types as _t
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import reach_fix as RF  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _write(tmp_path, plan, name="plan.json"):
    p = tmp_path / name
    p.write_text(json.dumps(plan))
    return p


def _rows(tmp_path, plan_path):
    out = tmp_path / ("chk_%s.json" % plan_path.stem)
    assert RF.main(["check", str(plan_path), "--json", str(out)]) == 0
    return {r["type"]: r for r in json.loads(out.read_text())["rows"]}


def _fix(tmp_path, plan_path, tag, *extra):
    out, ev = tmp_path / ("%s.json" % tag), tmp_path / ("%s_event.json" % tag)
    assert RF.main(["fix", str(plan_path), "--out-plan", str(out), "--event", str(ev)] + list(extra)) == 0
    return out, json.loads(ev.read_text())


def test_class1_tap_radius_fixed(tmp_path):
    # tiny_plan: 864-um types on the 400-um R4 grid: face registers 261.5 um from their tap (plan_geom fixture)
    base = _write(tmp_path, EX)
    before = _rows(tmp_path, base)
    assert before["mid"]["c1"] > 0 and before["mid"]["c1_max_um"] > RF.RADIUS_UM
    out, ev = _fix(tmp_path, base, "f1")
    after = _rows(tmp_path, out)
    assert all(r["c1"] == 0 for r in after.values()), {k: (r["c1"], r.get("error")) for k, r in after.items()}
    ck = json.loads(out.read_text())["partition_types"]["mid"]["clock"]
    assert ck["tap_mode"] == "grid+explicit" and ck["added_taps"]            # the R4 grid kept, taps added
    assert ev["summary_after"]["c1_types"] == 0 < ev["summary_before"]["c1_types"]


def test_class2_tap_load_split(tmp_path):
    p = copy.deepcopy(EX)
    ck = p["partition_types"]["mid"]["clock"]
    # 6,000 sinks in one 60 x 60 um block: more than the grid taps in reach can take at the cap
    ck["sink_sites_um"] = [[300.0 + 6.0 * i, 300.0 + 6.0 * j, 20.0] for i in range(10) for j in range(10)]
    ck["sink_sites_um"] = [r[:2] + [60.0] for r in ck["sink_sites_um"]]
    base = _write(tmp_path, p)
    b = _rows(tmp_path, base)["mid"]
    assert b["c2"] >= 1 and b["c2_max"] > RF.CAP_SINKS
    out, _ev = _fix(tmp_path, base, "f2")
    a = _rows(tmp_path, out)["mid"]
    assert a["c2"] == 0 and a["c2_max"] <= RF.CAP_SINKS and a["c1"] == 0, a
    import schema as S
    fixed = json.loads(out.read_text())
    assert S.validate_structure(fixed) == []                         # only schema keys (no stray clock keys)


def test_class4_signal_hop_gets_registers(tmp_path):
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["ft_slots"][0]["stations"] = 1       # one 864-um hop W -> E
    base = _write(tmp_path, p)
    b = _rows(tmp_path, base)["mid"]
    assert b["c4"] == 1 and b["c4_max_um"] > RF.REACH_UM
    out, ev = _fix(tmp_path, base, "f4", "--classes", "4")
    a = _rows(tmp_path, out)["mid"]
    assert a["c4"] == 0 and a["c4_max_um"] <= RF.REACH_UM
    slot = json.loads(out.read_text())["partition_types"]["mid"]["ft_slots"][0]
    assert slot["stations"] == 3                                     # ceil(864 / 405)
    assert ev["cycles_added"]["mid"] == 2                            # owner-approved cycles reported per type


def test_idempotent(tmp_path):
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["ft_slots"][0]["stations"] = 1
    out1, _ = _fix(tmp_path, _write(tmp_path, p), "i1")
    out2, ev2 = _fix(tmp_path, out1, "i2")
    assert ev2["applied"] == 0 and ev2["summary_before"]["types_viol"] == 0
    assert out1.read_bytes() == out2.read_bytes()


def test_class3_forwarded_clock_split(monkeypatch):
    t = {"outline_um": [2400.0, 400.0], "hard_cores": [],
         "clock": {"edge_clocks": [{"port": "fclk_in_x", "tap_um": [10.0, 200.0]}],
                   "landing_contract": {"pins": [{"name": "fclk_in_x", "dir": "in", "kind": "clock",
                                                  "xy_um": [2.16, 200.0]}],
                                        "bands": {"x": {"rect_um": [2100.0, 150.0, 2200.0, 250.0],
                                                        "instance": "u_cland_x"}}}}}
    P = _t.SimpleNamespace(types={"T": t}, path=None)
    rows = RF.fwd_metrics(P, "T")
    assert rows and not rows[0]["ok"] and rows[0]["far_um"] > RF.REPEATER_UM
    Q = {"partition_types": {"T": copy.deepcopy(t)}}
    assert [r["port"] for r in RF.fix_fwd(P, Q, "T")] == ["fclk_in_x"]
    P2 = _t.SimpleNamespace(types=Q["partition_types"], path=None)
    assert RF.fwd_metrics(P2, "T")[0]["ok"]
    assert RF.fix_fwd(P2, copy.deepcopy(Q), "T") == []                   # idempotent
    # the kit consumer: gen_phys.edge_split_ports names the forwarded port on a die outside EDGE_SPLIT_DIES
    import gen_phys as GP
    P3 = _t.SimpleNamespace(types=Q["partition_types"], die={"name": "s81"}, grid=None, layers=None)
    monkeypatch.setattr(GP, "edge_clock_pins", lambda PP, tn: [("fclk_in_x", 10.0, 200.0, 1)])
    assert GP.edge_split_ports(P3, "T") == ["fclk_in_x"]


def test_class5_raw_tap_reference_reselected(monkeypatch):
    import reset_tree
    trees = {
        "base": dict(relays=[dict(name="u_rrl_3", q="rst_n_t3", d="rst_root_n", depth=2, xy=[100.0, 50.0]),
                             dict(name="u_rrl_5", q="rst_n_t5", d="rst_root_n", depth=2, xy=[900.0, 50.0])]),
        "new": dict(relays=[dict(name="u_rrl_3", q="rst_n_t3", d="rst_root_n", depth=2, xy=[900.0, 50.0]),
                            dict(name="u_rrl_5", q="rst_n_t5", d="rst_root_n", depth=2, xy=[110.0, 50.0]),
                            dict(name="u_rrl_6", q="rst_n_t6", d="rst_root_n", depth=3, xy=[100.0, 50.0])]),
    }
    monkeypatch.setattr(RF, "plan_obj", lambda raw, path: _t.SimpleNamespace(tag=raw["tag"]))
    monkeypatch.setattr(RF, "_reset_caches", lambda PQ: None)
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: trees[PP.tag])
    st = dict(raw_reset="rr_t3", xy_um=[100.0, 50.0])
    t = {"clock": {"landing_reader_start": {"branches": {"b": {"stages": [st]}}}}}
    P = _t.SimpleNamespace(tag="base")
    Q = {"tag": "new", "partition_types": {"x": t}}
    rec = RF.fix_raw_tap_refs(P, Q, "x", None)
    assert rec == [["landing_reader_start.b.0", "rr_t3", "rr_t5"]]          # same depth, nearest
    assert st["raw_reset"] == "rr_t5"
    assert RF.fix_raw_tap_refs(P, Q, "x", None) == []                        # idempotent


# ---------------------------------------------------------------------------------------------- REACH-FIX-2 (11-12)
def test_die_cap_per_die():
    # COORD 05:19: S81 800 plan sinks, QC / KV 1200; HEAD / HBM 1200 (METHODOLOGY 3.3); --cap overrides
    assert RF.die_cap("s81") == 800 and RF.die_cap("qwen_compute") == 1200 and RF.die_cap("qwen_kvsys") == 1200
    assert RF.die_cap("s81_head") == 1200 and RF.die_cap("hbm") == 1200
    assert RF.die_cap("qwen_kvsys", 900) == 900 and RF.die_cap("tiny") == RF.CAP_SINKS


def test_wkmedians_density_weighted():
    # two weighted clusters: the heavy one pulls its centre, k = 2 separates them, deterministic
    pts = [(10.0, 10.0, 50.0), (12.0, 10.0, 1.0), (500.0, 500.0, 5.0), (502.0, 500.0, 5.0)]
    cen, groups = RF._wkmedians(pts, 2)
    assert sorted(len(g) for g in groups) == [2, 2]
    assert (10.0, 10.0) in cen
    assert RF._wkmedians(pts, 2) == (cen, groups)


def test_measured_sinks_split_and_refused(tmp_path):
    # placed sinks (tap_sinks_dump.tcl) replace the plan sinks; 3,000 registers in one block overload a tap; the fix
    # splits it by weighted k-medians; a dump with a sink outside the outline (another form) is refused
    good = [[300.0 + 1.0 * (i % 60), 300.0 + 1.0 * (i // 60)] for i in range(3000)]
    (tmp_path / "sinks").mkdir()
    (tmp_path / "sinks" / "mid.json").write_text(json.dumps(good))
    (tmp_path / "sinks" / "src.json").write_text(json.dumps([[5000.0, 5.0]]))
    base = _write(tmp_path, copy.deepcopy(EX))
    chk = tmp_path / "chk.json"
    assert RF.main(["check", str(base), "--sinks-dir", str(tmp_path / "sinks"), "--json", str(chk)]) == 0
    rec = json.loads(chk.read_text())
    assert rec["inputs"]["measured"] == ["mid"] and "src" in rec["inputs"]["measured_refused"]
    b = {r["type"]: r for r in rec["rows"]}["mid"]
    # the kit split caps a tap at 800 and pushes the rest beyond the radius: the debt shows as class 1
    assert b["sink_source"] == "measured" and b["c1"] > 0 and b["c2_max"] >= RF.CAP_SINKS
    out, ev = _fix(tmp_path, base, "fm", "--sinks-dir", str(tmp_path / "sinks"))
    assert RF.main(["check", str(out), "--sinks-dir", str(tmp_path / "sinks"), "--json", str(chk)]) == 0
    a = {r["type"]: r for r in json.loads(chk.read_text())["rows"]}["mid"]
    assert a["c2"] == 0 and a["c1"] == 0 and a["taps"] >= b["taps"] + 3, a      # 3000 / 800 -> >= 4 taps there


def test_min_taps_input(tmp_path):
    # die-owner minimum tap count (KV hgi_v8 16 -> 39 class): a type short of taps gets split to the count
    base = _write(tmp_path, copy.deepcopy(EX))
    b = _rows(tmp_path, base)["mid"]
    n = b["taps"] + 3
    chk = tmp_path / "c.json"
    assert RF.main(["check", str(base), "--min-taps", "mid=%d" % n, "--json", str(chk)]) == 0
    assert {r["type"]: r for r in json.loads(chk.read_text())["rows"]}["mid"]["taps_short"] == 3
    out, _ev = _fix(tmp_path, base, "mt", "--min-taps", "mid=%d" % n)
    assert RF.main(["check", str(out), "--min-taps", "mid=%d" % n, "--json", str(chk)]) == 0
    a = {r["type"]: r for r in json.loads(chk.read_text())["rows"]}["mid"]
    assert a["taps"] >= n and not a.get("taps_short"), a


def test_tap_table(tmp_path):
    # QC HF-1c condition (b): one row per tap with sinks and max tap-to-sink distance
    base = _write(tmp_path, copy.deepcopy(EX))
    tt = tmp_path / "taps.tsv"
    assert RF.main(["check", str(base), "--tap-table", str(tt), "--json", str(tmp_path / "c.json")]) == 0
    lines = tt.read_text().splitlines()
    assert lines[0].startswith("type\ttap\tx_um\ty_um\tsinks\tmax_tap_to_sink_um")
    mids = [ln.split("\t") for ln in lines[1:] if ln.startswith("mid\t")]
    assert mids and max(float(r[5]) for r in mids) > RF.RADIUS_UM                # the 261.5-um class-1 fixture
    assert "tap_rows" not in json.loads((tmp_path / "c.json").read_text())["rows"][0]


def test_reset_relay_reselect_keeps_role(monkeypatch):
    # HEAD-94 hd_st_n3_transit.u2_i: a raw rst_rl_* reference > 405 um from its stage must take the nearest RAW relay
    # of the same depth (rst_rl_26), never the closer GATED consumer leaf rst_n_t1
    import reset_tree
    import street_rule as SR
    rel = [dict(name="u_rl25", q="rst_rl_25", d="rst_root_n", depth=2, xy=[900.0, 50.0]),
           dict(name="u_rl26", q="rst_rl_26", d="rst_root_n", depth=2, xy=[300.0, 50.0]),
           dict(name="u_t1", q="rst_n_t1", d="rst_root_n", depth=2, xy=[110.0, 50.0])]
    tree = dict(relays=rel, start=True)
    monkeypatch.setattr(RF, "plan_obj", lambda raw, path: _t.SimpleNamespace(tag="x"))
    monkeypatch.setattr(RF, "_reset_caches", lambda PQ: None)
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: tree)
    monkeypatch.setattr(SR, "_q_roles", lambda tr: {"rst_rl_25": dict(role="raw"), "rst_rl_26": dict(role="raw"),
                                                    "rst_n_t1": dict(role="gated"), "rr_t1": dict(role="raw")})
    st = dict(raw_reset="rst_rl_25", xy_um=[100.0, 50.0])
    Q = {"partition_types": {"x": {"clock": {"landing_reader_start": {"branches": {"b": {"stages": [st]}}}}}}}
    rec = RF.fix_raw_tap_refs(_t.SimpleNamespace(), Q, "x", None)
    assert rec == [["landing_reader_start.b.0", "rst_rl_25", "rst_rl_26"]] and st["raw_reset"] == "rst_rl_26"
    # the only same-role relay at its depth is itself: unchanged, the closer gated leaf is never taken
    st2 = dict(raw_reset="rst_rl_25", xy_um=[100.0, 50.0])
    rel[1]["depth"] = 3
    Q2 = {"partition_types": {"x": {"clock": {"landing_reader_start": {"branches": {"b": {"stages": [st2]}}}}}}}
    rec2 = RF.fix_raw_tap_refs(_t.SimpleNamespace(), Q2, "x", None)
    assert st2["raw_reset"] == "rst_rl_25" and rec2 == []


def test_class6_landed_window(tmp_path):
    # S81 ready12b: a landed hop over the 416.5-ps window by 500 ps -> k = 2 cycles on every lane of that part pair;
    # idempotent (target from latency.lanes); unmapped pairs reported
    raw = {"ports": [{"id": "p0", "src": {"part": "a"}, "dst": {"part": "b"}},
                     {"id": "p1", "src": {"part": "b"}, "dst": {"part": "a"}}],
           "lanes": [{"id": "ab", "ports": ["p0"], "fixed_cycles": None}, {"id": "ba", "ports": ["p1"]}],
           "latency": {"lanes": {"ab": {"cycles": 3}, "ba": {"cycles": 2}}}}
    tsv = tmp_path / "hops.tsv"
    tsv.write_text("# header\nover_ps\tcorner\tlane_tag\tlaunch_part\tcapture_part\n"
                   "500.0\tTT\ta->b\ta\tb\n10.0\tTT\tx->y\tx\ty\n")
    rows = RF.landed_rows(raw, str(tsv))
    by = {r["lane"]: r for r in rows}
    assert by["ab"]["k"] == 2 and by["ab"]["target"] == 5 and not by["ab"]["ok"]
    assert by[None]["reason"].startswith("no plan lane") and "ba" not in by
    Q = copy.deepcopy(raw)
    assert RF.fix_landed(Q, rows) == {"ab": [None, 5]}
    assert Q["lanes"][0]["fixed_cycles"] == 5 and "fixed_cycles" not in Q["lanes"][1]
    rows2 = RF.landed_rows(Q, str(tsv))
    assert {r["lane"]: r for r in rows2}["ab"]["ok"] and RF.fix_landed(Q, rows2) == {}


def test_reset_resolve_empty_tap_dropped(monkeypatch):
    # RESET-WAVEFRONT-TAPS (HEAD-95 srx3 hd_st_turn clk_t4 load 0): an explicit tap emptied by the reset re-solve is
    # dropped (any non-core tap), the canonical names re-pack, core taps stay
    ck = {"tap_mode": "explicit", "taps": [dict(name="clk", xy=[1, 1]), dict(name="clk_t1", xy=[2, 2]),
                                           dict(name="cA", xy=[3, 3], kind="core"), dict(name="clk_t2", xy=[4, 4])]}
    errs = iter(["ValueError: T: explicit tap clk_t1 load=0/1500, radius=0/250.0, empty=True", None])
    monkeypatch.setattr(RF, "_export_ok", lambda Q, path, tn: next(errs))
    rec = dict(changes=[])
    assert RF._drop_one_empty({}, None, "T", ck, "explicit", rec, None) == "clk_t1"
    assert [(r["name"], r["xy"]) for r in ck["taps"]] == [("clk", [1, 1]), ("cA", [3, 3]), ("clk_t1", [4, 4])]
    assert rec["changes"] == [["dropped_empty_tap", "reset-resolve", "clk_t1"]]
    assert RF._drop_one_empty({}, None, "T", ck, "explicit", rec, None) is None


def test_group_override_rekeyed_by_role(monkeypatch):
    # QC sle_ctl__cl372cea1c: group_rects_um names u_cland_collect_rst_n_t19, gone after the re-solve -> the nearest
    # live collector of the same ROLE (gated rst_n_t*) within reach; a raw rst_rl_* override with no raw node in reach
    # is dropped
    import landing_place as LP
    tree = dict(start=True, root=[0.0, 0.0], relays=[dict(q="rst_n_t20", d="rst_root_n", xy=[100.0, 100.0]),
                                                     dict(q="rst_rl_3", d="rst_root_n", xy=[105.0, 100.0])])
    monkeypatch.setattr(LP, "collector_event", lambda c: dict(tree=tree, collector_root_node="rst_root_n"))
    monkeypatch.setattr(LP, "collector_nodes", lambda ev: ({"rst_root_n", "rst_n_t20", "rst_rl_3"},
                                                           {"rst_root_n": [0.0, 0.0], "rst_n_t20": [100.0, 100.0],
                                                            "rst_rl_3": [105.0, 100.0]}))
    ov = {"u_cland_collect_rst_n_t19": [90.0, 90.0, 110.0, 110.0], "u_cland_collect_rst_rl_9": [900, 900, 910, 910]}
    Q = {"partition_types": {"T": {"outline_um": [1000, 1000],
                                   "clock": {"landing_contract": {"group_rects_um": dict(ov)}}}}}
    out = RF.fix_group_overrides(Q, "T", None)
    assert out == [["u_cland_collect_rst_n_t19", "u_cland_collect_rst_n_t20"], ["u_cland_collect_rst_rl_9", None]]
    assert Q["partition_types"]["T"]["clock"]["landing_contract"]["group_rects_um"] == {
        "u_cland_collect_rst_n_t20": [90.0, 90.0, 110.0, 110.0]}
    assert RF.fix_group_overrides(Q, "T", None) == []                         # idempotent


def test_balance_residue_tsv_feeds_class6(tmp_path):
    # INSERTION-BALANCE: the part-pair residue of a balanced die clock (balance_score rows) is written in the
    # reach_hops TSV form and class 6 maps it to the lanes of each pair (+k registers)
    res = {"TT": dict(over=[dict(launch_part="a", capture_part="b", damage_ps=534.0, bits=12, lane_tag="",
                                 launch_tap="t_a__clk", capture_tap="t_b__clk", lca="n0_0")]),
           "FF": dict(over=[])}
    tsv = tmp_path / "res.tsv"
    RF.write_hops_tsv(tsv, res, 416.5, "test")
    raw = {"ports": [{"id": "p0", "src": {"part": "a"}, "dst": {"part": "b"}}],
           "lanes": [{"id": "ab", "ports": ["p0"]}], "latency": {"lanes": {"ab": {"cycles": 2}}}}
    rows = RF.landed_rows(raw, str(tsv))
    assert rows == [dict(lane="ab", k=1, over_ps=117.5, hops=["a->b"], cycles_before=2, fixed_before=None,
                         target=3, ok=False)]


def test_reset_depth_drift_reselected_from_ref_plan(monkeypatch):
    # HEAD srx3 hd_tile tile_geo_3: the die wavefront re-solve moved rst_rl_95 from depth 4 to 3, so the local copy
    # (depth raw + 1) no longer matches its consumer. With --ref-plan the raw takes the nearest same-role relay at
    # the REF depth (4), even though rst_rl_95 is within reach
    import reset_tree
    import street_rule as SR
    rel = [dict(name="u95", q="rst_rl_95", d="rst_root_n", depth=3, xy=[100.0, 50.0]),
           dict(name="u96", q="rst_rl_96", d="rst_root_n", depth=4, xy=[200.0, 50.0]),
           dict(name="ut", q="rst_n_t2", d="rst_root_n", depth=4, xy=[101.0, 50.0])]
    tree = dict(relays=rel, start=True)
    monkeypatch.setattr(RF, "plan_obj", lambda raw, path: _t.SimpleNamespace(tag="x"))
    monkeypatch.setattr(RF, "_reset_caches", lambda PQ: None)
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: tree)
    monkeypatch.setattr(SR, "_q_roles", lambda tr: {"rst_rl_95": dict(role="raw"), "rst_rl_96": dict(role="raw"),
                                                    "rst_n_t2": dict(role="gated")})
    monkeypatch.setitem(RF.REF, "P", _t.SimpleNamespace(types={"x": {}}))
    monkeypatch.setitem(RF.REF, ("depths", "x"), {"rst_rl_95": 4, "rst_rl_96": 5})
    lr = dict(name="tile_geo_3", raw="rst_rl_95", xy_um=[100.0, 50.0], consumers=["u_cland_up_o"])
    Q = {"partition_types": {"x": {"clock": {"landing_local_resets": [lr]}}}}
    rec = RF.fix_raw_tap_refs(_t.SimpleNamespace(), Q, "x", None)
    assert rec == [["landing_local_resets.0", "rst_rl_95", "rst_rl_96"]] and lr["raw"] == "rst_rl_96"


def test_depth_drift_from_reselect_is_caught(monkeypatch):
    # HEAD srx3 hd_host_e k2: the re-select moved a local reset raw from rst_rl_23 (depth 2) to rst_rl_17 (depth 1);
    # the base depth is the contract (consumer depth = raw depth + 1), so the drift is reported and the raw re-picked
    import reset_tree
    import street_rule as SR
    base = dict(relays=[dict(name="u23", q="rst_rl_23", d="x", depth=2, xy=[100.0, 0.0])], start=True)
    new = dict(relays=[dict(name="u17", q="rst_rl_17", d="x", depth=1, xy=[90.0, 0.0]),
                       dict(name="u24", q="rst_rl_24", d="x", depth=2, xy=[150.0, 0.0])], start=True)
    lr0 = dict(name="k2", raw="rst_rl_23", xy_um=[100.0, 0.0], consumers=["u_cland_agg_3"])
    P = _t.SimpleNamespace(types={"x": {"clock": {"landing_local_resets": [lr0]}}})
    monkeypatch.setattr(RF, "plan_obj", lambda raw, path: _t.SimpleNamespace(tag="q"))
    monkeypatch.setattr(RF, "_reset_caches", lambda PQ: None)
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: base if PP is P else new)
    monkeypatch.setattr(SR, "_q_roles", lambda tr: {r["q"]: dict(role="raw") for r in tr["relays"]})
    RF.REF.clear()
    lr = dict(lr0, raw="rst_rl_17")
    Q = {"partition_types": {"x": {"clock": {"landing_local_resets": [lr]}}}}
    assert RF.depth_drift(P, Q, "x", None) == [["landing_local_resets.0", "rst_rl_17", 1, 2]]
    rec = RF.fix_raw_tap_refs(P, Q, "x", None)
    assert rec == [["landing_local_resets.0", "rst_rl_17", "rst_rl_24"]] and RF.depth_drift(P, Q, "x", None) == []


def test_tap_cap_priced_on_nearest_split(tmp_path):
    # TAP-CAP (b) (COORD 11-12, VL3 hd_spn_end SP3: cap 1000 on paper, 1225 at place): a placed register bank the
    # planner inventory does not list sits on one tap.  Class 2 is priced on the NEAREST split (what AUTO-GEOM measures
    # at place), not on the pre-CTS capacity moves; the fix re-sites taps until the nearest split meets the cap, and the
    # new taps survive the planner's empty-tap check (anchor sinks).
    import taps as TP
    bank = [[300.0 + 1.0 * (i % 80), 300.0 + 0.4 * (i // 80)] for i in range(2400)]
    (tmp_path / "sinks").mkdir()
    (tmp_path / "sinks" / "mid.json").write_text(json.dumps(bank))
    base = _write(tmp_path, copy.deepcopy(EX))
    sd = ["--sinks-dir", str(tmp_path / "sinks"), "--cap", "1000"]
    chk = tmp_path / "chk.json"
    for mode in ("kit", "nearest"):
        assert RF.main(["check", str(base), "--json", str(chk), "--assign", mode] + sd) == 0
        r = {x["type"]: x for x in json.loads(chk.read_text())["rows"]}["mid"]
        if mode == "kit":
            kit_max = r["c2_max"]
        else:
            assert r["c2"] >= 1 and r["c2_max"] > kit_max and r["c2_max"] > 1000, (kit_max, r)
    out, _ev = _fix(tmp_path, base, "fcap", *sd)
    assert RF.main(["check", str(out), "--json", str(chk)] + sd) == 0
    a = {x["type"]: x for x in json.loads(chk.read_text())["rows"]}["mid"]
    assert a["c2"] == 0 and a["c2_max"] <= 1000, a
    # independent of the tool's pricing: the plain nearest split on the fixed plan's taps
    import plan_geom as PG
    import geom_rules as GR
    PQ = RF.plan_obj(json.loads(out.read_text()), out)
    grid = [(n, x, y) for n, x, y in PG.type_sites(PQ, "mid")["entries"] if GR.GRID_TAP_RE.match(n)]
    load, _f, _o = TP.assign(grid, [(x, y, 1.0) for x, y in bank], float("inf"), 0.0)
    assert max(load) <= 1000, max(load)


def test_added_station_counted_in_fixed_cycles(tmp_path):
    # FIXED-CYCLES (COORD 11-12, DIE-S81-88 12:29): a station register reach_fix adds on an internal_stations bus row
    # is a lane cycle: fixed_cycles += added on every lane through that (part, bus), bind's native rule (fixed ==
    # source + destination stations) kept where it held, latency table refreshed; ft stations reprice the table too
    import gen as GEN
    import schema as S
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["internal_stations"] = [
        {"conn": "bus:cfg_o", "from_um": [10.0, 10.0], "to_um": [854.0, 854.0], "regs_um": [[432.0, 432.0]],
         "launch": "core", "capture": "face flop"}]
    p["partition_types"]["mid"]["ft_slots"][0]["stations"] = 1          # x lane: 864-um ft hop -> 3 stations
    ln = {x["id"]: x for x in p["lanes"]}
    ln["cfg12"]["fixed_cycles"] = 1                                   # meets the rule: 1 source + 0 destination
    p["latency"] = {"lanes": GEN.latency_table(S.Plan(copy.deepcopy(p)))}
    base = _write(tmp_path, p)
    out, ev = _fix(tmp_path, base, "fc", "--classes", "4")
    q = json.loads(out.read_text())
    regs = len(q["partition_types"]["mid"]["internal_stations"][0]["regs_um"])
    added = regs - 1
    assert added >= 1 and all(h <= RF.REACH_UM + 0.01 for h in [
        RF._d(a, b) for a, b in zip([(10.0, 10.0)] + [tuple(r[:2]) for r in q["partition_types"]["mid"][
            "internal_stations"][0]["regs_um"]], [tuple(r[:2]) for r in q["partition_types"]["mid"][
            "internal_stations"][0]["regs_um"]] + [(854.0, 854.0)])])
    qln = {x["id"]: x for x in q["lanes"]}
    # both mid parts launch cfg_o: cfg12 (pm1 -> pm2) and cfg23 (pm2 -> pb); cfg01 (pa -> pm1.cfg_i) is untouched
    assert qln["cfg12"]["fixed_cycles"] == 1 + added and qln["cfg23"]["fixed_cycles"] == added
    assert qln["cfg01"].get("fixed_cycles") is None
    fc = ev["fixed_cycles"]
    assert fc["bus_deltas"] == {"mid.cfg_o": added} and fc["rule_broken"] == []
    assert fc["lanes"]["cfg12"]["rule_before"]["ok"] and fc["lanes"]["cfg12"]["rule_after"]["ok"]
    # the latency table equals the plan's own pricing again (check.py latency), incl. the ft stations of lane x
    want = GEN.latency_table(S.Plan(q))
    assert {k: v["cycles"] for k, v in q["latency"]["lanes"].items()} == {k: v["cycles"] for k, v in want.items()}
    assert fc["latency"]["x"] == [4, 8]                                # 2 mid crossings x 1 -> 3 stations and fc["latency"]["cfg12"] == [3, 3 + added]
    # idempotent: a second pass adds nothing
    out2, ev2 = _fix(tmp_path, out, "fc2", "--classes", "4")
    assert out2.read_bytes() == out.read_bytes()


def test_per_type_error_is_a_nonzero_exit_with_the_type_list(tmp_path, monkeypatch, capsys):
    # FAIL-LOUD (COORD 11-12, DIE-KV-99): an unresolved pin table (pins/<x>.json missing) left 8 KV hg types unfixed
    # with exit 0.  Any per-type error now exits 3 and lists the types on stderr, in check and in fix; outputs are
    # still written so the event can be read
    real = RF.type_row

    def row(P, tn, *a, **k):
        if tn == "mid":
            raise FileNotFoundError("pins/qkd_astk_ex_s_hg1101.json")
        return real(P, tn, *a, **k)
    monkeypatch.setattr(RF, "type_row", row)
    base = _write(tmp_path, EX)
    chk = tmp_path / "c.json"
    assert RF.main(["check", str(base), "--json", str(chk)]) == 3
    err = capsys.readouterr().err
    assert "REACH-FIX-FAIL check: 1 type(s)" in err and "mid: FileNotFoundError" in err and "hg1101" in err
    out, ev = tmp_path / "o.json", tmp_path / "e.json"
    assert RF.main(["fix", str(base), "--out-plan", str(out), "--event", str(ev)]) == 3
    err = capsys.readouterr().err
    assert "REACH-FIX-FAIL fix" in err and "mid:" in err and out.exists() and ev.exists()
    monkeypatch.setattr(RF, "type_row", real)
    assert RF.main(["check", str(base), "--json", str(chk)]) == 0
