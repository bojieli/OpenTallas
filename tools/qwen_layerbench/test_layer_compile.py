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
        self.assertEqual(N.age_fields(r, {'rly_x_0': 2})['age_edges'], 2)          # n = 1 landed lane: E = K
        r = dict(st={5}, lands={('rly_x_4',)})
        self.assertIsNone(N.age_fields(r, {'rly_x_4': 3})['age_edges'])            # n > 1: needs the land plan
        self.assertEqual(N.age_fields(dict(st={3}, lands={()}), {})['age_edges'], 3)


def table(design, buses):
    return DRS.Table(DRS.make_doc(design, dict(id='t'), 833.333, 425.0, buses))


def bus(si, sp, di, dp, st, age=None, w=1):
    b = dict(id=DRS.bus_id(si, sp, di, dp), src=dict(inst=si, port=sp), dst=dict(inst=di, port=dp), width=w, stages=st, domain='stream_1p2')
    if age is not None:
        b.update(age_edges=age, age_basis='n=1 landed lane: E = K')
    return b


class Compile(unittest.TestCase):
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
        ba = C.bundle_ages(T)
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


if __name__ == '__main__':
    unittest.main()
