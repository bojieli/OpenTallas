"""PL-GATE 2026-10-18 (landed-regions standard): a multi-root (landed) cluster is judged PER ROOT at the child flops (hard
child clock pin + its views/<child>/insertion.json boundary min..max, with the root's soft landing / pad / reset-run
registers), per linked pair on the SAME root, TT and FF <= 80; a link between roots must go through a landing
(u_lpl_<n>_w -> u_lpl_<n>_r) or be a regional reset run, else FAIL "unlanded cross-region link".
Fixture: tools/landed_parent/lp.py selftest output (origin/claude/parents-landed-1018 77748fef6), regions ra = {u0, u3},
rb = {u1, u2}, 3 landings, 1 pad."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as G  # noqa: E402

LP_RTL = """`timescale 1ns/1ps
module lpt_top_lp #(
    parameter integer W = 8,
    parameter integer MUT = 0
) (
    input wire rst_n,
    input wire [W-1:0] x,
    output wire [W-1:0] z,
    output wire [W-1:0] z3,
    input wire ck_ra,
    input wire ck_rb
);
    wire [W-1:0] y0, y1, y2, y3;
    assign z = y2;
    assign z3 = y3;
    // ---- regional reset runs (1-bit plain hops: they define the landing epochs; region ra holds the root)
    wire lpr_root;  ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_ra), .d(rst_n), .q(lpr_root));
    wire lpr_ra;  ot_pl_pad #(.W(1), .N(3)) u_lpr_ra (.ck(ck_ra), .d(lpr_root), .q(lpr_ra));   // 0 hop(s) from ra
    wire lpr_rb;  ot_pl_pad #(.W(1), .N(3)) u_lpr_rb (.ck(ck_rb), .d(lpr_root), .q(lpr_rb));   // 3 hop(s) from ra
    // ---- LANDING 0: y0 ra -> rb, 8 b (u1.a, u2.b)
    wire [4*((W-1) - (0) + 1)-1:0] lpl_0_bank;  wire [11:0] lpl_0_epo;  wire [3:0] lpl_0_vld;  wire [W-1:0] y0__l_rb, lpl_0_o;
    ot_pl_land_w #(.W(((W-1) - (0) + 1)), .D(4)) u_lpl_0_w (.ck(ck_ra), .rsi(lpr_ra), .i(y0), .bank(lpl_0_bank), .epo(lpl_0_epo), .vld(lpl_0_vld));
    ot_pl_land_r #(.W(((W-1) - (0) + 1)), .D(4), .K((MUT == 2) ? 3 : 2)) u_lpl_0_r (.ck(ck_rb), .rsi(lpr_rb), .bank(lpl_0_bank), .epo(lpl_0_epo), .vld(lpl_0_vld), .o(lpl_0_o));
    assign y0__l_rb = (MUT == 1) ? y0 : lpl_0_o;
    // ---- LANDING 1: x ra -> rb, 8 b (u1.b)
    wire [4*((W-1) - (0) + 1)-1:0] lpl_1_bank;  wire [11:0] lpl_1_epo;  wire [3:0] lpl_1_vld;  wire [W-1:0] x__l_rb, lpl_1_o;
    ot_pl_land_w #(.W(((W-1) - (0) + 1)), .D(4)) u_lpl_1_w (.ck(ck_ra), .rsi(lpr_ra), .i(x), .bank(lpl_1_bank), .epo(lpl_1_epo), .vld(lpl_1_vld));
    ot_pl_land_r #(.W(((W-1) - (0) + 1)), .D(4), .K(2)) u_lpl_1_r (.ck(ck_rb), .rsi(lpr_rb), .bank(lpl_1_bank), .epo(lpl_1_epo), .vld(lpl_1_vld), .o(lpl_1_o));
    assign x__l_rb = lpl_1_o;
    // ---- LANDING 2: y1 rb -> ra, 8 b (u3.a)
    wire [4*((W-1) - (0) + 1)-1:0] lpl_2_bank;  wire [11:0] lpl_2_epo;  wire [3:0] lpl_2_vld;  wire [W-1:0] y1__l_ra, lpl_2_o;
    ot_pl_land_w #(.W(((W-1) - (0) + 1)), .D(4)) u_lpl_2_w (.ck(ck_rb), .rsi(lpr_rb), .i(y1), .bank(lpl_2_bank), .epo(lpl_2_epo), .vld(lpl_2_vld));
    ot_pl_land_r #(.W(((W-1) - (0) + 1)), .D(4), .K(2)) u_lpl_2_r (.ck(ck_ra), .rsi(lpr_ra), .bank(lpl_2_bank), .epo(lpl_2_epo), .vld(lpl_2_vld), .o(lpl_2_o));
    assign y1__l_ra = lpl_2_o;
    wire [W-1:0] x__p_u3;  ot_pl_pad #(.W(((W-1) - (0) + 1)), .N((MUT == 3) ? 5 : 6)) u_lpp_0 (.ck(ck_ra), .d(x), .q(x__p_u3));   // align u3: +6
    wire lpr_c_u0;  ot_pl_pad #(.W(1), .N((MUT == 4) ? 1 : 0)) u_lprc_u0 (.ck(ck_ra), .d(lpr_ra), .q(lpr_c_u0));   // t(u0) = 0
    wire lpr_c_u1;  ot_pl_pad #(.W(1), .N(3)) u_lprc_u1 (.ck(ck_rb), .d(lpr_rb), .q(lpr_c_u1));   // t(u1) = 3
    wire lpr_c_u2;  ot_pl_pad #(.W(1), .N(3)) u_lprc_u2 (.ck(ck_rb), .d(lpr_rb), .q(lpr_c_u2));   // t(u2) = 3
    wire lpr_c_u3;  ot_pl_pad #(.W(1), .N(6)) u_lprc_u3 (.ck(ck_ra), .d(lpr_ra), .q(lpr_c_u3));   // t(u3) = 6
    // ---- children (clock pins -> their region root; reset pins -> their reset run; landed / padded inputs)
    lpt_leaf #(.W(W)) u0 (.clk(ck_ra), .rst_n(lpr_c_u0), .a(x), .b(x), .y(y0));   // region ra, t = 0
    lpt_leaf #(.W(W)) u1 (.clk(ck_rb), .rst_n(lpr_c_u1), .a(y0__l_rb), .b(x__l_rb), .y(y1));   // region rb, t = 3
    lpt_leaf #(.W(W)) u2 (.clk(ck_rb), .rst_n(lpr_c_u2), .a(y1), .b(y0__l_rb), .y(y2));   // region rb, t = 3
    lpt_leaf #(.W(W)) u3 (.clk(ck_ra), .rst_n(lpr_c_u3), .a(y1__l_ra), .b(x__p_u3), .y(y3));   // region ra, t = 6
endmodule"""
INS = dict(u0=((200.0, 240.0), (160.0, 190.0)), u1=((150.0, 190.0), (120.0, 150.0)),
           u2=((210.0, 250.0), (170.0, 200.0)), u3=((200.0, 230.0), (160.0, 185.0)))
# per root and corner: child clock-pin arrivals and the soft-register span
ARR = {"ck_ra": dict(tt=(dict(u0=300.0, u3=310.0), (480.0, 530.0)), ff=(dict(u0=250.0, u3=255.0), (400.0, 440.0))),
       "ck_rb": dict(tt=(dict(u1=400.0, u2=330.0), (530.0, 575.0)), ff=(dict(u1=330.0, u2=270.0), (445.0, 470.0)))}


def domain(src, arr, soft=True):
    out = dict(source=src, clock=src)
    for c, (pins, (slo, shi)) in arr.items():
        raw = list(pins.values()) + [slo, shi]
        cf = dict(all=dict(n=22, min=slo, max=shi), boundary=dict(n=12, min=slo, max=shi))
        if soft:
            cf["soft"] = dict(all=dict(n=20, min=slo, max=shi), boundary=dict(n=10, min=slo, max=shi))
        out[c] = dict(all=dict(n=22, mean=sum(raw) / len(raw), min=min(raw), max=max(raw)),
                      boundary=dict(n=12, min=min(raw), max=max(raw)),
                      macros=dict(n=len(pins), pins=[dict(pin=f"{k}/clk", arr=v) for k, v in pins.items()]), child_flop=cf)
    return out


def gate_out(arr=ARR, soft=True):
    return ("textbook_lint: INFO clock_roots max_root_sinks=22 root=port:ck_ra\n" +
            "\n".join("GATE_CK_DOMAIN " + json.dumps(domain(s, a, soft)) for s, a in arr.items()) + "\n")


class LandedRoots(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "top.sv").write_text(LP_RTL)
        for n, (tt, ff) in INS.items():
            v = self.root / "v" / n
            v.mkdir(parents=True)
            (v / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"min": tt[0], "max": tt[1]}},
                                                          "ff": {"boundary": {"min": ff[0], "max": ff[1]}}}))
        self.old, G.ROOT = G.ROOT, self.root
        self.spec = dict(kind="cluster", top="lpt_top_lp", sources=["top.sv"], clock="multiple_cts_roots",
                         clock_port="ck_ra", clock_ports=["ck_ra", "ck_rb"],
                         children=[dict(view=f"v/{n}", inst=f"*{n}") for n in INS])

    def tearDown(self):
        G.ROOT = self.old
        self.td.cleanup()

    def roots(self, rec):
        return {r["source"]: r for r in rec["per_root"]}

    def test_graph_roots_and_landings(self):
        g = G.parent_link_graph(self.spec)
        self.assertEqual({i: x["root"] for i, x in g["insts"].items() if x["kid"]},
                         dict(u0="ck_ra", u1="ck_rb", u2="ck_rb", u3="ck_ra"))
        self.assertIsNone(g["insts"]["u_lprc_u0"]["kid"])            # "*u0" does not claim the reset run
        issues, landed = G.cross_region_links(g)
        self.assertEqual(issues, [])
        self.assertIn(("*u0", "*u1", "u_lpl_0"), landed)
        self.assertIn(("*u1", "*u3", "u_lpl_2"), landed)

    def test_per_root_child_pairs_pass(self):
        rec = G.clock_record(gate_out(), True, self.spec)
        r = self.roots(rec)
        # ra TT: u0 500..540, u3 510..540, soft 480..530 -> u0-soft 60, u3-soft 60 (u0-u3 not linked)
        self.assertEqual((r["ck_ra"]["tt_pin_spread_ps"], r["ck_ra"]["tt_pin_spread_basis"]), (60.0, "root_child_pair"))
        self.assertEqual(r["ck_ra"]["ff_pin_spread_ps"], 40.0)
        pairs = {(p["root"], p["corner"], *sorted((p["a"], p["b"]))): p["ps"] for p in r["ck_rb"]["pairs"]}
        self.assertEqual(pairs[("ck_rb", "tt", "u1", "u2")], 50.0)    # max(590-540, 580-550)
        self.assertEqual(pairs[("ck_rb", "tt", "soft", "u1")], 60.0)
        self.assertEqual(r["ck_rb"]["ff_pin_spread_ps"], 40.0)
        allp = [p for x in rec["per_root"] for p in x.get("pairs", [])]
        self.assertFalse([p for p in allp if {p["a"], p["b"]} & {"u0", "u3"} and {p["a"], p["b"]} & {"u1", "u2"}])
        self.assertEqual(rec["verdict"], "WARN", rec["text"])   # insertion > 300: guidance only
        self.assertEqual((rec["tt_pin_spread_ps"], rec["ff_pin_spread_ps"]), (60.0, 40.0))
        self.assertEqual(r["ck_ra"]["children"], ["u0", "u3"])

    def test_landed_offset_between_roots_is_not_skew(self):
        late = copy.deepcopy(ARR)                                     # rb 300 ps later than ra: landed, legal
        for c in ("tt", "ff"):
            pins, (lo, hi) = late["ck_rb"][c]
            late["ck_rb"][c] = ({k: v + 300.0 for k, v in pins.items()}, (lo + 300.0, hi + 300.0))
        rec = G.clock_record(gate_out(late), True, self.spec)
        self.assertEqual(rec["verdict"], "WARN", rec["text"])   # insertion > 300: guidance only

    def test_linked_pair_over_80_on_one_root_fails_at_ff(self):
        bad = copy.deepcopy(ARR)
        bad["ck_rb"]["ff"][0]["u2"] = 200.0                          # u2 FF 370..400 vs u1 450..480: 110
        rec = G.clock_record(gate_out(bad), True, self.spec)
        self.assertEqual(rec["verdict"], "REFUSE")
        self.assertEqual(self.roots(rec)["ck_rb"]["ff_pin_spread_ps"], 110.0)
        self.assertIn("ck_rb", rec["text"])
        self.assertEqual(self.roots(rec)["ck_ra"]["verdict"], "WARN")

    def test_unlanded_cross_region_link_fails(self):
        (self.root / "top.sv").write_text(LP_RTL.replace("assign y0__l_rb = (MUT == 1) ? y0 : lpl_0_o;",
                                                         "assign y0__l_rb = y0;"))
        rec = G.clock_record(gate_out(), True, self.spec)
        self.assertEqual(rec["verdict"], "REFUSE")
        self.assertIn("unlanded cross-region link y0", rec["text"])

    def test_old_ck_record_without_soft_split_takes_whole_root_span(self):
        rec = G.clock_record(gate_out(soft=False), True, self.spec)
        r = self.roots(rec)["ck_ra"]
        # TT children 500..540 + child_flop.all 480..530 -> 60, no pairs
        self.assertEqual((r["tt_pin_spread_ps"], r["tt_pin_spread_basis"]), (60.0, "root_child_flop"))
        self.assertNotIn("pairs", r)

    def test_unreadable_rtl_refuses(self):
        rec = G.clock_record(gate_out(), True, dict(self.spec, sources=["missing.sv"]))
        self.assertEqual(rec["verdict"], "REFUSE")
        self.assertIn("cannot be read", rec["text"])

    def test_gate_prints_per_root_lines(self):
        rec = G.clock_record(gate_out(), True, self.spec)
        msgs = []
        fake = type("F", (), {"add": lambda self, lvl, item, msg, fix=None: msgs.append((lvl, item, msg))})()
        G.clock_item(fake, rec)
        items = [m[1] for m in msgs]
        self.assertEqual(items.count("clock_root_child_flop"), 2)
        self.assertIn("clock_child_pair", items)
        self.assertIn("clock_landed_link", items)
        self.assertIn(("WARN", "clock_rule"), [(m[0], m[1]) for m in msgs])

    def test_tile_multi_root_unchanged(self):
        spec = dict(self.spec, kind="tile", children=[])
        rec = G.clock_record(gate_out(), True, spec)
        self.assertNotIn("landed_child_links", rec)
        self.assertFalse(any("root_child" in str(r.get("tt_pin_spread_basis")) for r in rec["per_root"]))


class Requirement(unittest.TestCase):
    """the commit's Gate-Rule trailer: tightening requires=landed_cluster_roots (source_binding judges old gates)"""
    def test_old_gates(self):
        import source_binding as SB
        with tempfile.TemporaryDirectory() as td:
            kd = Path(td) / "physical" / "ref_tile"
            for k, sp in dict(c=dict(kind="cluster", children=[dict(view="v", inst="u")]), t=dict(kind="tile")).items():
                (kd / k).mkdir(parents=True)
                (kd / k / "spec.json").write_text(json.dumps(sp))
            ok = lambda clock, kit: SB.relaxed_rule_requirement(["landed_cluster_roots"], clock, dict(kit=kit), root=td)[0]
            self.assertTrue(ok({"declared_clock": None}, "c"))                               # single root: unchanged
            self.assertTrue(ok({"declared_clock": "multiple_cts_roots"}, "t"))               # multi-root tile: unchanged
            self.assertFalse(ok({"declared_clock": "multiple_cts_roots"}, "c"))              # old multi-root cluster gate
            self.assertTrue(ok({"declared_clock": "multiple_cts_roots", "landed_child_links": []}, "c"))
            self.assertFalse(ok({"declared_clock": "multiple_cts_roots"}, "missing"))


if __name__ == "__main__":
    unittest.main()
