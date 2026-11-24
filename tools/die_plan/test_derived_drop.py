"""derived_drop.py (PRE RSTREACH / DERIVEDNAME, PRECHECK-DERIVED-DROP 11-23).
python3 -m pytest -q tools/die_plan/test_derived_drop.py

Positives are the three 11-23 drops in miniature: KV pv FSTART raw branches stripped (one co-sited chain 2 mm from the face
flops), KV A3g grow (raw branch stage no longer a D-chain of the re-solved tree), S81 c7a svc_tap_inv (START raw pointers
aimed at the old taps)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derived_drop as D  # noqa: E402
import plan_gate_pre as G  # noqa: E402


class Fake:
    def __init__(self, relays=None, taps=None, hops=None):
        self.r, self.k, self.h = relays or {}, taps or {}, hops or {}

    def relays(self, tn):
        return self.r[tn]

    def tree(self, tn):
        return {"relays": [{"q": q, "d": d, "xy": list(xy), "kind": "tap" if q.startswith("rst_n_t") else "pad"}
                           for q, (d, xy) in self.r[tn].items()]}

    def taps(self, tn):
        return self.k.get(tn, set())

    def raw_hops(self, tn):
        return self.h.get(tn, [])


def _pins(*xy):
    return {"pins": [{"name": f"cland_fstart_out_b{i}", "xy_um": list(p)} for i, p in enumerate(xy)],
            "bands": {"bi": {"rect_um": [0, 0, 10, 10]}}}


def _pv(branches=None):
    ck = {"landing_contract": _pins((36.0, 2.6), (500.0, 500.0), (3.1, 259.4))}
    if branches is not None:
        ck["landing_raw_branches"] = branches
    return {"clock": ck}


TREE = {"rst_rl_5": (None, (100.0, 100.0)), "rst_rl_13": ("rst_rl_5", (100.0, 300.0)), "rst_n_t1": ("rst_rl_13", (100.0, 600.0))}


def test_stripped_raw_branches_fail_plan_only():
    out = D.findings({"partition_types": {"kv3_pv_v3": _pv()}}, "/x/p.json", solver=Fake({"kv3_pv_v3": TREE}))
    assert len(out) == 1 and out[0].startswith("WARN RSTREACH kv3_pv_v3: 3 FSTART") and "no clock.landing_raw_branches" in out[0]


def test_bound_type_without_face_flops_is_skipped(tmp_path):
    (tmp_path / "kv3_pv_v3e_part.sv").write_text("    assign cland_fstart_out_b0 = cland_start;\n")
    assert D.findings({"partition_types": {"kv3_pv_v3e": _pv()}}, "/x/p.json", solver=Fake({"kv3_pv_v3e": TREE}),
                      bind_rtl=tmp_path) == []


def test_bound_raw_relay_cosited_chain_named(tmp_path):
    chain = "\n".join(f"    ot_dp_rrelay u_rrl_{i} (.clk(clk), .d({'rst_root_n' if i == 0 else f'rst_rl_{i - 1}'}), "
                      f".q({'rst_n_t111' if i == 10 else f'rst_rl_{i}'}));  // tap 111 depth {i + 1} @ (37.8, 1458.5)"
                      for i in range(11))
    (tmp_path / "kv3_pv_v3_part.sv").write_text(chain + "\n    assign cland_start_raw = rst_n_t111;\n"
                                                "    ot_dp_landing_relay u_cland_fstart_b0 (.clk(clk), .rst_raw_n(cland_start_raw));\n")
    out = D.findings({"partition_types": {"kv3_pv_v3": _pv()}}, "/x/p.json", solver=Fake({"kv3_pv_v3": TREE}),
                     bind_rtl=tmp_path)
    assert len(out) == 1 and "rst_n_t111 at (37.8, 1458.5)" in out[0] and "11 of 11 chain stages on that site" in out[0]


def _branches(last_xy=(450.0, 400.0)):
    return [{"name": f"fs_b{i}", "base": "rst_rl_5", "stages": [{"original": "rst_rl_13", "xy_um": list(a)},
                                                                {"original": "rst_n_t1", "xy_um": list(b)}],
             "consumers": [f"fstart:b{i}"]}
            for i, (a, b) in enumerate([((60.0, 80.0), (40.0, 10.0)), ((300.0, 200.0), last_xy), ((60.0, 200.0), (10.0, 250.0))])]


def test_fixed_raw_branches_pass_and_far_copy_fails():
    S = Fake({"kv3_pv_v3": TREE})
    assert D.findings({"partition_types": {"kv3_pv_v3": _pv(_branches())}}, "/x/p.json", solver=S) == []
    out = D.findings({"partition_types": {"kv3_pv_v3": _pv(_branches((300.0, 200.0)))}}, "/x/p.json", solver=S)
    assert len(out) == 1 and out[0].startswith("FAIL RSTREACH kv3_pv_v3: 1 landing_raw_branches hop") and "fstart:b1" in out[0]


def test_raw_branch_dchain_after_grow_fails():
    t = _pv(_branches())
    grown = dict(TREE, rst_n_t1=("rst_rl_58", (100.0, 600.0)), rst_rl_58=("rst_rl_13", (0.0, 0.0)))
    out = D.findings({"partition_types": {"kv3_io_ft_v1": t}}, "/x/p.json", solver=Fake({"kv3_io_ft_v1": grown}))
    assert any(x.startswith("FAIL DERIVEDNAME kv3_io_ft_v1: stale landing_raw_branches") and "rebuild 3 chain(s)" in x
               and "rst_rl_13" in x and "--resets rstnode" in x for x in out)


def test_rstnode_rule1_renumbered_final_vs_base():
    """KV A3 +112.32 um grow: kv3_hroot finals name rst_n_t11 whose site moved; the base's node now is rst_n_t12"""
    t = _pv(_branches())
    old = {"rst_rl_5": (None, (100.0, 100.0)), "rst_rl_13": ("rst_rl_5", (100.0, 300.0)), "rst_n_t1": ("rst_rl_13", (100.0, 600.0))}
    new = {"rst_rl_5": (None, (100.0, 100.0)), "rst_rl_13": ("rst_rl_5", (100.0, 300.0)), "rst_n_t1": ("rst_rl_5", (900.0, 900.0)),
           "rst_n_t2": ("rst_rl_13", (100.0, 600.0))}
    base = {"partition_types": {"kv3_hroot": t}}
    out = D.findings({"partition_types": {"kv3_hroot": t}}, "/x/p.json", solver=Fake({"kv3_hroot": new}), base=base,
                     base_solver=Fake({"kv3_hroot": old}), classes=["DERIVEDNAME"])
    assert len(out) == 1 and "rename 3 final(s) (rst_n_t1 -> rst_n_t2)" in out[0]
    assert D.findings({"partition_types": {"kv3_hroot": t}}, "/x/p.json", solver=Fake({"kv3_hroot": old}), base=base,
                      base_solver=Fake({"kv3_hroot": old}), classes=["DERIVEDNAME"]) == []


def test_start_raw_pointers_at_old_taps_fail():
    hops = {"svc_lo_t1": [("reader:b0:3", "rst_n_t7", "same", 2233.0, 405.0), ("writer:b1:0", "rst_n_t2", "same", 120.0, 405.0),
                          ("reader:b0:4", "rst_n_t99", "missing", None, 0.0)]}
    t = {"clock": {"landing_reader_start": {"branches": {"bi": {"stages": [{"xy_um": [0, 0], "raw_reset": "rst_n_t7"}]}}}}}
    out = D.findings({"partition_types": {"svc_lo_t1": t}}, "/x/p.json",
                     solver=Fake({"svc_lo_t1": {"rst_n_t7": (None, (0, 0))}}, hops=hops))
    assert any("1 START / local reset raw hop(s) over" in x and "2233 um" in x for x in out)
    assert any("1 START / local reset raw net(s) not in" in x and "rst_n_t99" in x for x in out)


def test_stale_names_consumers_and_station_instances():
    t = _pv(_branches())
    t["clock"]["landing_raw_branches"][0]["consumers"].append("fstart:gone")
    t["clock"]["landing_local_resets"] = [{"raw": "rst_rl_77"}, {"raw": "rr_t1"}]
    t["clock"]["collector_tree"] = {"q": "rst_rl_999"}
    t["hard_cores"] = [{"inst": "pvg0_p0"}]
    t["internal_stations"] = [{"conn": "bus:x", "launch": "core:pvg0_p0"}, {"conn": "bus:y", "launch": "leaf u_gone"}]
    out = D.findings({"partition_types": {"kv3_pv_v3": t}}, "/x/p.json", solver=Fake({"kv3_pv_v3": TREE}),
                     classes=["DERIVEDNAME"])
    j = "\n".join(out)
    assert "rst_rl_77" in j and "rr_t1" not in j and "rst_rl_999" not in j
    assert "fstart:gone" in j and "leaf u_gone" in j and "core:pvg0_p0" not in j
    assert [x.split()[0] for x in out] == ["FAIL", "FAIL", "WARN"]


def test_hard_and_clean_types_silent_errors_warn():
    raw = {"partition_types": {"phy": dict(_pv(), hard=True), "none": {"clock": {"tap_mode": "density"}},
                               "kv3_x": _pv(_branches())}}

    class Boom(Fake):
        def relays(self, tn):
            raise ValueError("no tree")
    out = D.findings(raw, "/x/p.json", solver=Boom())
    assert out and all(x.startswith("WARN ") and "kv3_x: not checked" in x for x in out)


def test_l1_radius():
    assert D.l1_radius([(0, 0)]) == 0.0
    assert D.l1_radius([(0, 0), (810, 0)]) == 405.0


def test_classes_registered_in_pre():
    assert "RSTREACH" in G.CLASSES and "DERIVEDNAME" in G.CLASSES


def test_solver_tree_method_not_shadowed():
    S = D.Solver({"partition_types": {}}, "/x/p.json", "/some/tree")
    assert callable(S.tree) and S.root == "/some/tree"


def test_references_the_bind_repicks_are_warn():
    """LOCAL-RESET-RAW-1: the bind re-picks a gone / far landing_local_resets raw (S81 leaf, bk_sel): WARN, not FAIL"""
    t = {"clock": {"landing_local_resets": [{"name": "fstart_2", "raw": "rst_rl_27", "xy_um": [0, 0]}]}}

    class Rp(Fake):
        def repaired(self, tn):
            return {"clock/landing_local_resets/0/raw"}
    S = Rp({"bk_sel": {"rst_rl_1": (None, (0, 0))}}, hops={"bk_sel": [("local_reset:fstart_2", "rst_rl_27", "missing", None, 0.0)]})
    out = D.findings({"partition_types": {"bk_sel": t}}, "/x/p.json", solver=S)
    assert out and all(x.startswith("WARN") for x in out)
    out = D.findings({"partition_types": {"bk_sel": t}}, "/x/p.json",
                     solver=Fake({"bk_sel": {"rst_rl_1": (None, (0, 0))}}, hops=S.h))
    assert sum(x.startswith("FAIL") for x in out) == 2
    assert D.hop_path("reader_start:ft0_i:3", {}) == "clock/landing_reader_start/branches/ft0_i/stages/3/raw_reset"


def test_stale_die_relay_parent_fails():
    """S81 c8 24_tgr5: reset.die_relays fW0_p1_b0 parent svc_1_rs/18, solve svc_9_att/5"""
    class W(Fake):
        def wf_parent(self):
            return {"fW0_p1_b0": ("svc_9_att", 5), "fE0": ("svc_1_rs", 2)}
    raw = {"reset": {"die_relays": {"fW0_p1_b0": {"parent": "svc_1_rs", "site": 18}, "fE0": {"parent": "svc_1_rs", "site": 2}}},
           "partition_types": {}}
    out = D.findings(raw, "/x/p.json", solver=W())
    assert len(out) == 1 and out[0].startswith("FAIL DERIVEDNAME die: 1 of 2") and "solve svc_9_att/5" in out[0]
    raw["reset"]["die_relays"]["fW0_p1_b0"] = {"parent": "svc_9_att", "site": 5}
    assert D.findings(raw, "/x/p.json", solver=W()) == []


def test_rr_t_and_collector_nodes_are_warn():
    """QC C1b slw_su_c: rr_t names absent from start_relays and collector_children nodes, strict bind clean"""
    t = {"clock": {"landing_contract": {"collector_children": [{"node": "rst_n_t88"}]},
                   "landing_reader_start": {"branches": {"x_i": {"stages": [{"xy_um": [0, 0], "raw_reset": "rr_t137"}]}}}}}
    S = Fake({"su": {"rst_rl_1": (None, (0, 0))}},
             hops={"su": [("reader_start:x_i:0", "rr_t137", "missing", None, 0.0)]})
    out = D.findings({"partition_types": {"su": t}}, "/x/p.json", solver=S)
    assert out and all(x.startswith("WARN") for x in out)


# ENTRYFOOT (PRE-QC-GENCHECK 11-23): QC C1-noSU 12b66c0e4829 cbn_q00__cl622f65d2 -- u_t00/u_t01 + footprints moved 43.2 um,
# early taps clk_c0/clk_c2 not; kit GEN died in validate_access.
def _ef_type(tap_x=332.704, core_x=60.48):
    return {"clock": {"core_taps": "early", "taps": [{"kind": "core", "name": "u_t00.ck", "xy": [tap_x, 648.012]}]},
            "hard_cores": [{"inst": "u_t00", "origin_um": [core_x, 69.12], "outline_um": [457.92, 1157.76], "orient": "R0",
                            "clock_entry_access": {"pin": "ck", "footprints_um": {"M7": [[289.488, 647.628, 289.52, 648.396]]}}}]}


class EF(Fake):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def entry_rows(self, tn):
        return self.rows[tn]


def _row(x, foot=(289.488, 647.628, 289.52, 648.396), on_track=True):
    return {"port": "clk_c0", "inst": "u_t00", "pin": "ck", "xy": (x, 648.012), "top": 7, "on_track": on_track,
            "box": [x - 0.016, 647.628, x + 0.016, 648.396], "foot": [list(foot)] if foot else []}


def test_entryfoot_tap_left_behind_fails():
    raw = {"partition_types": {"cbn": _ef_type()}}
    out = D.findings(raw, "/x/p.json", solver=EF({"cbn": [_row(332.704)]}), classes=["ENTRYFOOT"])
    assert len(out) == 1 and out[0].startswith("WARN ENTRYFOOT cbn: clk_c0 (u_t00.ck)") and "d +43.2,+0" in out[0]
    assert "[289.504,648.012]" in out[0]


def test_entryfoot_matching_tap_passes_and_off_track_fails():
    raw = {"partition_types": {"cbn": _ef_type(289.504)}}
    assert D.findings(raw, "/x/p.json", solver=EF({"cbn": [_row(289.504)]}), classes=["ENTRYFOOT"]) == []
    out = D.findings(raw, "/x/p.json", solver=EF({"cbn": [_row(289.504, on_track=False)]}), classes=["ENTRYFOOT"])
    assert len(out) == 1 and "off the preferred M7 routing track" in out[0]
    out = D.findings(raw, "/x/p.json", solver=EF({"cbn": [_row(289.504, foot=None)]}), classes=["ENTRYFOOT"])
    assert len(out) == 1 and "0 M7 footprint boxes" in out[0]


def test_entryfoot_types_without_access_not_solved():
    t = _ef_type()
    del t["hard_cores"][0]["clock_entry_access"]
    assert D.entry_types({"partition_types": {"cbn": t, "x": {"hard_cores": []}}}) == []
    assert D.entry_types({"partition_types": {"cbn": _ef_type()}}) == ["cbn"]


def test_entryfoot_tap_follows_moved_core():
    base = {"partition_types": {"cbn": _ef_type(332.704, 103.68)}}
    left = {"partition_types": {"cbn": _ef_type(332.704, 60.48)}}
    out = D.tapfollow_findings(left, base)
    assert len(out) == 1 and out[0].startswith("FAIL ENTRYFOOT cbn: 1 early core tap(s)") and "core moved (-43.2,+0)" in out[0]
    assert D.tapfollow_findings({"partition_types": {"cbn": _ef_type(289.504, 60.48)}}, base) == []
    assert D.tapfollow_findings({"partition_types": {"cbn": _ef_type(289.504, 103.68)}}, base) == []   # tap-only fix row
    assert D.tapfollow_findings(left, None) == []


def test_gen_rtl_landings_get_plan_path(monkeypatch, tmp_path):
    """GENDRY on QC (cwd = tree root): write_rtl built clock_landings.Landings without plan_path, so the plan-relative count
    frame (plan_of_record/feed_*.json) resolved against the cwd: 'count frame files not found' on all 14 cb types"""
    import clock_landings as CL
    import gen_rtl as GR
    seen = {}

    def fake(raw, landing, **kw):
        seen.update(kw)
        raise CL.LandingError("stop")
    monkeypatch.setattr(GR.S, "validate", lambda raw: [])
    monkeypatch.setattr(GR.S, "scope_errors", lambda errs, scope: [])
    monkeypatch.setattr(GR.S, "Plan", lambda raw, pp=None: object())
    monkeypatch.setattr(GR, "bus_epochs", lambda P: {})
    monkeypatch.setattr(CL, "Landings", fake)
    plan = tmp_path / "plan_of_record" / "p.json"
    try:
        GR.write_rtl({"clock": {"landing_network": {"root_observer": "o"}}}, tmp_path / "o", plan_path=plan,
                     landing={"collector": {"observer": "o"}})
    except GR.GenError as e:
        assert "stop" in str(e)
    assert seen.get("plan_path") == plan


# STALE-EXPORT-TAP (ENTRYFOOT c., KV A5: export buffer left at the landing-compose tap 320-1942 um from the port)
def _fx(src, xy=(10.0, 10.0)):
    return {"clock": {"landing_contract": {"pins": [
        {"name": "fclk_out_a", "kind": "clock", "dir": "out", "xy_um": list(xy), "source_clock_port": src},
        {"name": "d_a", "kind": "data", "dir": "out", "xy_um": [0, 0]}]}}}


class GF(Fake):
    def __init__(self, grid):
        super().__init__()
        self.g = grid

    def grid(self, tn):
        return self.g


def test_stale_export_tap_fails_and_nearest_passes():
    g = {"clk": (500.0, 500.0), "clk_t1": (20.0, 20.0), "clk_t9": (900.0, 10.0)}
    raw = {"partition_types": {"pv": _fx("clk_t9")}, "partitions": [{"name": "a", "type": "pv"}, {"name": "b", "type": "pv"}]}
    out = D.findings(raw, "/x/p.json", solver=GF(g), classes=["ENTRYFOOT"])
    assert out[0].startswith("WARN ENTRYFOOT pv: STALE-EXPORT-TAP 1 of 1") and "clk_t9 890 um (nearest clk_t1 20 um)" in out[0]
    assert out[-1].startswith("LIST ENTRYFOOT STALE-EXPORT-TAP die: 1 of 1") and "2 of 2 placed" in out[-1]
    raw["partition_types"]["pv"] = _fx("clk")         # far root: stale too
    assert D.findings(raw, "/x/p.json", solver=GF(g), classes=["ENTRYFOOT"])[0].startswith("WARN ENTRYFOOT")
    raw["partition_types"]["pv"] = _fx("clk_t1")
    out = D.findings(raw, "/x/p.json", solver=GF(g), classes=["ENTRYFOOT"])
    assert [x for x in out if not x.startswith("LIST")] == []


def test_stale_export_tap_gone_and_no_nearer_tap_fail():
    g = {"clk_t1": (20.0, 20.0)}
    out, n, m = D.exporttap_type("pv", _fx("clk_t7"), g)
    assert n == 1 and out[0].startswith("FAIL") and "1 a tap that no longer exists" in out[0]
    out, n, m = D.exporttap_type("pv", _fx("clk_t1", (400.0, 20.0)), g)
    assert n == 1 and len(out) == 1 and out[0].startswith("FAIL ENTRYFOOT pv: STALE-EXPORT-TAP 1 forwarded")
    g = {"clk_t1": (20.0, 20.0), "clk_t2": (60.0, 20.0)}      # nearer tap exists but is itself over 300 um: stale, not "no nearer"
    out, n, m = D.exporttap_type("pv", _fx("clk_t1", (400.0, 20.0)), g)
    assert n == 1 and "take a source tap more than 300" in out[0] and "nearest clk_t2 340 um" in out[0]


def test_stale_export_tap_budget_never_silent():
    raw = {"partition_types": {"pv": _fx("clk_t9")}}
    out = D.exporttap_findings(raw, GF({"clk_t9": (900.0, 10.0)}), budget=-1)
    assert len(out) == 1 and out[0].startswith("WARN ENTRYFOOT STALE-EXPORT-TAP: 1 type(s) not checked") and "pv" in out[0]


# ENTRYFOOT-WARN-1124 (COORD r703): ENTRYFOOT / STALE-EXPORT-TAP are report-only on every die; other classes keep FAIL
def test_entryfoot_is_warn_only_and_other_classes_keep_fail(monkeypatch):
    assert D.ENTRYFOOT_LEVEL == "WARN"
    monkeypatch.setattr(D, "entryfoot_findings", lambda *a, **k: ["FAIL ENTRYFOOT t: tap off footprint"])
    monkeypatch.setattr(D, "exporttap_findings", lambda *a, **k: ["FAIL ENTRYFOOT t: STALE-EXPORT-TAP 1 of 1", "LIST ENTRYFOOT x"])
    monkeypatch.setattr(D, "die_relay_findings", lambda *a, **k: ["FAIL DERIVEDNAME die: 1 of 1 reset.die_relays"])

    class S:
        grid = None
    raw = {"partition_types": {}}
    out = D.findings(raw, "/x/p.json", solver=S(), classes=["ENTRYFOOT", "DERIVEDNAME"])
    assert out == ["FAIL DERIVEDNAME die: 1 of 1 reset.die_relays", "WARN ENTRYFOOT t: tap off footprint",
                   "WARN ENTRYFOOT t: STALE-EXPORT-TAP 1 of 1", "LIST ENTRYFOOT x"]
    assert not any(l.startswith("FAIL ENTRYFOOT") for l in out)
