#!/usr/bin/env python3
"""LAYERBENCH-QWEN 10-18: tests of netlist_relay_stages.py + layer_compile.py (python3 tools/qwen_layerbench/test_layer_compile.py)."""
import json, sys, tempfile, unittest
from pathlib import Path

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
for p in (H, ROOT / 'tools', ROOT / 'tools' / 'qwen_split'):
    sys.path.insert(0, str(p))
import netlist_relay_stages as N   # noqa: E402
import layer_compile as C          # noqa: E402
import die_relay_stages as DRS     # noqa: E402
import die_relay_check as DRC      # noqa: E402
import d2d_link_calendar as L      # noqa: E402
import record_bundles as RB        # noqa: E402
import die_params as DP            # noqa: E402

RTL = """
module src (input wire ck, output wire [3:0] o, output wire v);
endmodule
module dst (input wire ck, input wire [3:0] i, input wire v);
endmodule
module qkd_rlys_1 (input wire ck, input wire [0:0] a, output wire [0:0] b); endmodule
module qkd_rlys_36 (input wire ck, input wire [35:0] a, output wire [35:0] b); endmodule
"""
DIE = """
module qfd_die ();
  wire [3:0] n_d; wire [3:0] n_d__r1; wire [3:0] n_d__r2; wire [0:0] n_v; wire [0:0] n_v__r1; wire [31:0] n_sp; wire [31:0] n_sp1;
  wire [0:0] n_clk_core_c;
  src u_s (.ck(n_clk_core_c), .o(n_d), .v(n_v));
  qkd_rlys_36 r0 (.ck(n_clk_core_c), .a({32'b0, n_d[3:0]}), .b({n_sp[31:0], n_d__r1[3:0]}));
  qkd_rlys_36 r1 (.ck(n_clk_core_c), .a({32'b0, n_d__r1[3:0]}), .b({n_sp1[31:0], n_d__r2[3:0]}));
  qkd_rlys_1 r2 (.ck(n_clk_core_c), .a(n_v), .b(n_v__r1));
  dst u_d (.ck(n_clk_core_c), .i(n_d__r2), .v(n_v__r1));
endmodule
"""


class NetlistWalk(unittest.TestCase):
    def test_stages_from_netlist(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'm.sv').write_text(RTL)
            (Path(t) / 'die.v').write_text(DIE)
            pb = dict(masters={m: dict(rtl=f'{t}/m.sv', kind='real') for m in ('src', 'dst', 'qkd_rlys_1', 'qkd_rlys_36')},
                      rtl_files=[], defines=[])
            doc = N.export(f'{t}/die.v', pb, 'qwen_kv', 'HEAD', [], [t], 'unit')
        b = {x['id']: x for x in doc['buses']}
        self.assertEqual(b['u_s.o -> u_d.i']['stages'], 2)
        self.assertEqual(b['u_s.o -> u_d.i']['width'], 4)
        self.assertEqual(b['u_s.v -> u_d.v']['stages'], 1)
        self.assertEqual(doc['relay_instances'], 3)
        self.assertEqual(doc['problem_count'], 0)

    def test_age_fields(self):
        r = dict(st={1}, lands={('rly_x_0',)})
        self.assertIsNone(N.age_fields(r, {'rly_x_0': 2})['age_edges'])  # K alone is not an age
        r = dict(st={5}, lands={('rly_x_4',)})
        self.assertIsNone(N.age_fields(r, {'rly_x_4': 3})['age_edges'])            # n > 1: needs the land plan
        self.assertEqual(N.age_fields(dict(st={3}, lands={()}), {})['age_edges'], 3)

    def test_shared_age_source_on_compute_seam(self):
        import record_bundles as RB
        f = ROOT / 'results/rtl/qwen_layer_tput_1018/fixtures/dv2f18dh2_seam'
        metadata = N.export_lanes(f / 'fwd_lanes.json')
        _, _, rows, problems = RB.rows_from_netlist(f / 'die.v', f / 'fwd_lanes.json')
        self.assertEqual(problems, [])
        self.assertTrue(any(row['n'] == 1 for row in rows.values()))
        self.assertTrue(any(row['n'] > 1 for row in rows.values()))
        lanes = {r['bid']: r for r in metadata.values()}
        for bid, row in rows.items():
            if row.get('E') is None:
                continue
            land = lanes[bid]['landing']
            record = dict(st={row['n']}, lands={(land,)})
            self.assertEqual(N.age_fields(record, {land: row['K']}, metadata)['age_edges'], RB.cycles(row), bid)
            self.assertIsNone(N.age_fields(record, {land: (row['K'] + 1) % 8}, metadata)['age_edges'])

    def test_kv_and_compute_landing_walk(self):
        for master, design in [('qfd_landh0_1', 'qwen_compute'), ('qkd_landsh0_1', 'qwen_kv')]:
            rtl = RTL + f"module {master} (input wire ck, input wire a, output wire b, input wire k0, k1, k2, tie_hi, tie_lo); endmodule"
            die = f"""module die();
wire n_clk_core_c, n_d, n_v, n_out, hi, lo;
src s (.ck(n_clk_core_c), .v(n_d));
{master} land (.ck(n_clk_core_c), .a(n_d), .b(n_out), .k0(lo), .k1(hi), .k2(lo), .tie_hi(hi), .tie_lo(lo));
dst d (.ck(n_clk_core_c), .v(n_out));
endmodule"""
            with tempfile.TemporaryDirectory() as t:
                Path(t, 'm.sv').write_text(rtl)
                Path(t, 'die.v').write_text(die)
                pb = dict(masters={m: dict(rtl=f'{t}/m.sv', kind='real') for m in ('src', 'dst', master)}, defines=[])
                doc = N.export(f'{t}/die.v', pb, design, 'HEAD', [], [t], 'unit',
                               land_e={'land': dict(E=1, K=2, cal=1, n=1)})
            self.assertEqual(doc['problem_count'], 0, doc['problems'])
            self.assertEqual(len(doc['buses']), 1)
            self.assertEqual(doc['buses'][0]['age_edges'], 2)

    def test_lane_calendar_required_and_checked(self):
        for row in [dict(bid='x', landing='land', E=3, K=1),
                    dict(bid='x', landing='land', E=3, K=1, cal=0)]:
            with tempfile.TemporaryDirectory() as t:
                path = Path(t, 'lanes.json')
                path.write_text(json.dumps(dict(lanes=[row])))
                with self.assertRaises(ValueError):
                    N.export_lanes(path)


def table(design, buses):
    return DRS.Table(DRS.make_doc(design, dict(id='t'), 833.333, 425.0, buses))


def bus(si, sp, di, dp, st, age=None, w=1):
    b = dict(id=DRS.bus_id(si, sp, di, dp), src=dict(inst=si, port=sp), dst=dict(inst=di, port=dp), width=w, stages=st,
             domain='stream_1p2', bid=f'lnk_{sp}')
    if age is not None:
        b.update(age_edges=age, age_basis='n=1 landed lane: E = K')
    return b


class Compile(unittest.TestCase):
    def test_txdp_bound_literal_and_image(self):
        lit = ("qfd_d2d_static_core #(.MUT(MUT), .TXDP(PR ? {8'd4, 8'd1, 8'd3, 8'd3} : 0)) u_core ();\n"
               "qkd_d2d_static_core #(.MUT(MUT), .TXDP(PR ? {8'd3, 8'd3, 8'd4, 8'd3} : 0)) u_core ();\n")
        self.assertEqual(C.txdp_bound(lit, None, 'C'), ([3, 3, 1, 4], 'rtl_literal'))
        self.assertEqual(C.txdp_bound(lit, None, 'K'), ([3, 4, 3, 3], 'rtl_literal'))
        par = ("module qfd_d2d_static #(parameter integer MUT = 0, parameter integer PR = 1, parameter [31:0] TXDP = 32'd0) ();\n"
               "module qkd_d2d_static #(parameter integer MUT = 0, parameter integer NL = 2, parameter integer NTX = 4, "
               "parameter integer PR = 1, parameter [31:0] TXDP = 32'd0) ();\n")
        img = "localparam [31:0] D2D_TXDP_C = 32'h09010306;\nlocalparam [31:0] D2D_TXDP_K = 32'h03030418;\n"
        self.assertEqual(C.txdp_bound(par, img, 'K'), ([24, 4, 3, 3], 'image_parameter'))
        self.assertEqual(C.txdp_bound(par, img, 'C'), ([6, 3, 1, 9], 'image_parameter'))
        with self.assertRaises(SystemExit):
            C.txdp_bound(par, None, 'K')                 # required parameter, no image: fail closed
        with self.assertRaises(SystemExit):
            C.txdp_bound('module other; endmodule', img, 'K')

    def test_landed_codec_source_and_calendar(self):
        def tile(params):
            return ('module qkd_kvs_attn (); qkd_native_attention_programme #(' + params + ') u_attn (); endmodule')
        self.assertEqual(C.kv_codec_edges(tile('.MUT(0)')), 1)
        self.assertEqual(C.kv_codec_edges(tile('.MUT(0), .LAND(1)')), 2)
        with self.assertRaises(SystemExit):
            C.kv_codec_edges(tile('.LAND(MISSING)'))
        with self.assertRaises(SystemExit):
            C.kv_codec_edges('module stub; endmodule')
        stages = dict(CS_TXS=2, SC_TX=2, CS_X3S=2, SC_X3=2, KS_TXS=9, SK_TXP=11)
        legacy = C.txd_of(stages, kv_codec=1)[1]
        landed = C.txd_of(stages, kv_codec=2)[1]
        self.assertEqual(landed['K'], [24, 4, 3, 3])
        self.assertEqual(landed['C'], legacy['C'])

    def test_xdie_plan_cross_check(self):
        # TOKEN-XDIE-QWEN plan stages (every seam bundle at its netlisted max) -> its record: TXD C [8,3,1,9] K [23,4,3,3], X 7
        S = dict(CS_TXS=2, CS_RXV=2, CS_RXP=2, CS_X3S=2, SC_TX=2, SC_X3=2, KS_RXV=11, KS_RXP=11, KS_TXS=9, KS_TXK=9,
                 KS_TXB=9, SK_TXV=11, SK_TXP=11)
        raw, txd = C.txd_of(S)
        self.assertEqual(txd, dict(C=[8, 3, 1, 9], K=[23, 4, 3, 3]))
        kvp = dict(RX_CMD=2, SERVICE_END=1777, TX_FIRST=1750)
        _, lay = L.program_profile(8, 7, str(ROOT / 'results/arch/token_path_20261009/qwen_rom.json'), host_stages=0, st_ofs=40,
                                   handoff=str(ROOT / 'results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json'))
        w = [lay['windows']['L1_35'][o] for o in ('rmsnorm1', 'qkv', 'qknorm_rope', 'attn_kv')]
        self.assertEqual(C.extension(w, txd, S, kvp, 6, 5)['X'], 7)

    def test_bundle_mismatch_and_compiled_check(self):
        c = [bus('d2d_rom', p, 'native59', p, 1, 2) for p in ('native_tx_slot', 'native_tx_slot_kind', 'native_tx_slot_beat',
                                                               'rx_payload', 'kv_x3_slot')]
        c += [bus('d2d_rom', p, 'native59', p, 0) for p in ('native_rx_v', 'native_rx_slot', 'native_rx_slot_kind', 'native_rx_slot_beat')]
        c += [bus('native59', p, 'd2d_rom', p, 0) for p in ('native_tx_v', 'native_tx_payload')]
        c += [bus('native59', p, 'd2d_rom', p, 1, 2) for p in ('x3', 'x3_identity', 'x3_generation')]
        k = [bus('d2d_kv', p, 'kvs_attn', p, 9) for p in ('att_rx_v', 'att_rx_kind', 'att_rx_beat', 'att_tx_slot', 'att_tx_kind', 'att_tx_beat')]
        k += [bus('d2d_kv', 'rx_payload', 'kvs_attn', 'rx_payload', 11)]
        k += [bus('kvs_attn', p, 'd2d_kv', p, 11) for p in ('attn__tx_valid', 'attn__tx_payload')]
        T = {'qwen_compute': table('qwen_compute', c), 'qwen_kv': table('qwen_kv', k)}
        with self.assertRaises(SystemExit):                               # compute ages never from hop counts
            C.bundle_ages(T)
        # the as-built seam (record_bundles lane cycles; F5: rx_v direct 0, payload landed 2)
        seam = {(b['src']['inst'], b['src']['port'], b['dst']['inst']): b.get('age_edges', b['stages']) for b in c}
        ba = C.bundle_ages(T, seam)
        self.assertFalse(ba['C.rx_record']['consistent'])                 # rx_v direct, payload landed E 2 (F5)
        self.assertEqual(ba['C.rx_record']['age'], 2)
        self.assertFalse(ba['K.rx_record']['consistent'])                 # 9 vs 11 (F6)
        self.assertTrue(ba['K.tx_slot']['consistent'])
        S = C.compile_stages(ba)
        self.assertEqual((S['CS_RXV'], S['KS_RXV'], S['SC_TX']), (2, 11, 0))
        # compiled schedule at bundle max -> die_relay_check fails exactly the short members
        doc = T['qwen_kv'].doc
        sched = {m['bus']: m['stages'] + ba['K.rx_record']['age'] - m['age'] for m in ba['K.rx_record']['members']}
        rep = DRC.check(doc, DRS.compiled(doc, 'unit', scheduled=sched))
        self.assertEqual(rep['verdict'], 'FAIL')
        self.assertEqual(sorted(d['bus'] for d in rep['stage_diffs']),
                         sorted(f'd2d_kv.{p} -> kvs_attn.{p}' for p in ('att_rx_v', 'att_rx_kind', 'att_rx_beat')))

    def test_extend_token_path(self):
        tp = json.loads((ROOT / 'results/arch/token_path_20261009/qwen_rom.json').read_text())
        d = C.extend_token_path(tp, {'L0': -10, 'L1': 5})
        g = {x['id']: x for x in d['groups']}
        self.assertEqual(g['L1']['start'], {x['id']: x for x in tp['groups']}['L1']['start'] - 10)
        self.assertEqual(d['totals']['cycles'], tp['totals']['cycles'] - 5)


LT = ROOT / 'results/rtl/qwen_layer_tput_1018'
# dv2f18dh2 (0d4c9808f): compute seam cut from the GEN die.v + fwd_lanes.json, the die's netlist relay table
# (netlist_relay_stages.py) and its die.v.params.json
FXS = LT / 'fixtures/dv2f18dh2_seam'


class SeamOneSource(unittest.TestCase):
    """QW-L1SEAM 10-19: layer_compile and the strict bind (DIE_PARAM_AUDIT (e) / RECORD_BUNDLE_AUDIT) read the compute
    D2D seam from ONE source, record_bundles.seam_stages(die.v, fwd_lanes.json).  dv2f18dh2: layer_compile counted relay
    HOPS (one-frame landings = 1) and asked TXDP C [6,3,1,10] + flagged C.rx_record ages [1,2], while the bind PASSED
    [8,3,1,10].  Any divergence of selectors, stage map, ages or TXD formula fails here."""

    def test_selectors_and_stage_map_are_record_bundles(self):
        for b in RB.COMPILER_BUNDLES:
            self.assertEqual(C.BUNDLES[b], ('qwen_compute', [(s, sp, d) for s, sp, d, _ in RB.BUNDLES[b]]), b)
        for b, mem in RB.SEAM_SINGLE.items():
            self.assertEqual(C.BUNDLES[b], ('qwen_compute', [(s, sp, d) for s, sp, d, _ in mem]), b)
        self.assertEqual(sorted(b for b, (d, _) in C.BUNDLES.items() if d == 'qwen_compute'),
                         sorted(list(RB.COMPILER_BUNDLES) + list(RB.SEAM_SINGLE)))
        self.assertEqual({k: v for k, v in C.STAGE_OF.items() if k[:2] in ('CS', 'SC')}, dict(RB.SEAM_STAGE_OF))
        self.assertEqual((C.N59_TX, C.N59_X3, C.PINREG_EXT), (L.N59_TX, L.N59_X3, L.PINREG_EXT))

    def tables(self):
        k = [bus('d2d_kv', p, 'kvs_attn', p, 9) for p in ('att_rx_v', 'att_rx_kind', 'att_rx_beat', 'att_tx_slot', 'att_tx_kind',
                                                          'att_tx_beat', 'rx_payload')]
        k += [bus('kvs_attn', p, 'd2d_kv', p, 11) for p in ('attn__tx_valid', 'attn__tx_payload')]
        return {'qwen_compute': DRS.Table(DRS.load(FXS / 'relay_stages.json')), 'qwen_kv': table('qwen_kv', k)}

    def test_dv2f18dh2_compiler_equals_strict_bind(self):
        st, per_key, _ = C.compute_seam(FXS / 'die.v')
        bind_st, _, probs = RB.seam_stages(FXS / 'die.v', FXS / 'fwd_lanes.json')     # the strict-bind call
        self.assertEqual(probs, [])
        self.assertEqual(st, bind_st)
        self.assertEqual(st, dict(CS_TXS=2, CS_RXV=2, CS_RXP=2, CS_X3S=3, SC_TX=2, SC_X3=2))
        T = self.tables()
        ba = C.bundle_ages(T, per_key)
        for b in C.COMPUTE_SEAM:
            self.assertTrue(ba[b]['consistent'], (b, ba[b]['ages']))
        self.assertEqual(ba['C.rx_record']['ages'], [2])
        S = C.compile_stages(ba)
        self.assertEqual({k: S[k] for k in st}, st)
        txd_c = C.txd_of(S)[1]['C']
        self.assertEqual(txd_c, DP.seam_txd_c(bind_st))                                # DIE_PARAM_AUDIT (e) formula
        self.assertEqual(txd_c, [8, 3, 1, 10])
        bound = json.loads((FXS / 'die.v.params.json').read_text())['masters']['qfd_d2d_static']['TXDP']
        self.assertEqual(L.txdp_word(txd_c), int(bound))                                # 0x0a010308, the GEN's TXDP
        # the hop counts layer_compile used before: one-frame landings read 1 -> [6,3,1,10] + a false torn rx_record
        hops = {(b['src']['inst'], b['src']['port'], b['dst']['inst']): b['stages'] for b in T['qwen_compute'].doc['buses']}
        self.assertEqual((hops[('d2d_rom', 'native_rx_v', 'native59')], hops[('d2d_rom', 'rx_payload', 'native59')],
                          hops[('d2d_rom', 'native_tx_slot', 'native59')]), (1, 2, 1))
        # the exporter's own ages are torn too (n > 1: E, n = 1: K) -> die_relay_check on the raw table FAILS ...
        raw = T['qwen_compute'].doc
        self.assertIn('C.rx_record', [n for n, _ in DRC.DRB.torn(raw)])
        # ... and on the seam-annotated table (record_bundles ages) the compiled schedule (whole bundles) PASSES
        doc, diff = C.annotate_seam_ages(raw, per_key)
        self.assertTrue(diff)
        sched = {m['bus']: m['stages'] + ba[b]['age'] - m['age'] for b in C.COMPUTE_SEAM for m in ba[b]['members']}
        self.assertEqual(DRC.check(doc, DRS.compiled(doc, 'unit', scheduled=sched))['verdict'], 'PASS')

    def test_torn_seam_fails_closed(self):
        txt = (FXS / 'die.v').read_text()
        ln = next(x for x in txt.splitlines() if ' rly_lnk_native_rx_v_0 ' in x)
        mut = ln.replace('.k1(n_ftk_lnk_native_rx_v_hi)', '.k1(n_ftk_lnk_native_rx_v_lo)')
        self.assertNotEqual(mut, ln)
        fl = json.loads((FXS / 'fwd_lanes.json').read_text())
        fl['lanes'] = [r for r in fl['lanes'] if r['bid'] != 'lnk_native_rx_v']       # E from the (mutated) K straps
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'die.v').write_text(txt.replace(ln, mut))
            (Path(t) / 'fwd_lanes.json').write_text(json.dumps(fl))
            with self.assertRaises(SystemExit):
                C.compute_seam(Path(t) / 'die.v')


if __name__ == '__main__':
    unittest.main()
