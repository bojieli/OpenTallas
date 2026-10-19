#!/usr/bin/env python3
"""QXF-SEAMK 2026-10-18 (TOKEN-XDIE-QWEN F6) unit tests: KV record-bundle equalisation, RELAY_CHECK against the compiler's
schedule with the record-bundle rule, and the OT_KV_ATTN_AT_D2D placement.

Fixture: the kvs14c die-run table results/rtl/qwen_layer_tput_1018/compiled_L1/die_run/kv_kvs14c_relay_stages.json.gz =
tools/qwen_layerbench/netlist_relay_stages.py on the kvs14c GEN netlist (kvs14c-place/port_bind_v2/die_bound.v, source
f05f9338f; digest sha256:957ba33f..., re-exported bit-identical by tools/qwen_kv_die/kv_relay_check.sh in
results/rtl/xdie_qwen_1018/qxf_seamk/relay_check_kvs14c_asbuilt.log).  OT_QXF_KVS14C_RUN=<dir with port_bind_v2/die_bound.v>
also re-walks the die.v itself (test_die_v_rewalk, ~30 s / 3 GB).
    python3 -m unittest tools/qwen_kv_die/test_kv_bundle_eq.py      (from the repository root)
"""
import math
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / 'tools'), str(ROOT / 'tools' / 'qwen_layerbench'), str(ROOT / 'tools' / 'qwen_split')]
import die_record_bundles as DRB   # noqa: E402
import die_relay_check as DRC      # noqa: E402
import die_relay_stages as DRS     # noqa: E402
import kv_bundle_eq as BEQ         # noqa: E402

L1 = ROOT / 'results/rtl/qwen_layer_tput_1018/compiled_L1'
ASBUILT = L1 / 'die_run/kv_kvs14c_relay_stages.json.gz'
SCHED_L1 = L1 / 'relay_schedule/kv_compiled.json.gz'


def compile_like_layer_compile(doc):
    """the compiler's relay-schedule rule (layer_compile.py main: every bundle member at its bundle's age), on one KV table"""
    import layer_compile as LC
    T = DRS.Table(doc)
    sched, used = {}, {}
    for name, (design, sel) in LC.BUNDLES.items():
        if design != 'qwen_kv':
            continue
        mem = [b for si, sp, di in sel for b in T.match(src_inst=si, src_port=sp, dst_inst=di)]
        age = max(LC.bus_age(b) for b in mem)
        for b in mem:
            sched[b['id']] = b['stages'] + (age - LC.bus_age(b))
            used.setdefault(b['id'], []).append(f'{name} (calendar age {age})')
    return DRS.compiled(doc, LC.CONSUMER, used_by=used, scheduled=sched)


class Kvs14cRelayCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asbuilt = DRS.load(ASBUILT)
        cls.fixed, cls.rows = BEQ.equalized_table(cls.asbuilt)

    def test_fixture_is_the_kvs14c_netlist(self):
        self.assertEqual(self.asbuilt['digest'],
                         'sha256:957ba33f9672035cd1f0bb734e38b6767dda79af334cd0b705217db9c02d10fa')
        self.assertEqual(self.asbuilt['plan']['commit'], 'f05f9338f')

    def test_asbuilt_bundles_torn(self):
        torn = dict(DRB.torn(self.asbuilt))
        self.assertEqual(sorted(torn), ['K.kvn_writer', 'K.rx_record', 'K.tx_record', 'K.tx_slot'])
        ages = {n: sorted({m['bus'].split(' -> ')[0]: m['age'] for m in r['members']}.items()) for n, r in torn.items()}
        self.assertEqual(dict(ages['K.tx_record']), {'kvs_attn.attn__tx_payload': 11, 'kvs_attn.attn__tx_valid': 6})
        self.assertEqual(dict(ages['K.tx_slot']), {'d2d_kv.att_tx_beat': 9, 'd2d_kv.att_tx_kind': 8, 'd2d_kv.att_tx_slot': 9})

    def test_asbuilt_fails_against_compiled_L1(self):
        rep = DRC.check(self.asbuilt, DRS.load(SCHED_L1))
        self.assertEqual(rep['verdict'], 'FAIL')
        self.assertEqual(sorted(d['bus'].split(' -> ')[0] for d in rep['stage_diffs']),
                         ['d2d_kv.att_rx_beat', 'd2d_kv.att_rx_kind', 'd2d_kv.att_rx_v', 'd2d_kv.att_tx_kind',
                          'kvs_attn.attn__tx_valid'])
        self.assertTrue(any(f.startswith('torn record bundle K.rx_record') for f in rep['fails']))

    def test_bundle_rule_independent_of_schedule(self):
        # a schedule copied from the torn die itself (what 'RELAY_CHECK SKIPPED' amounted to) still FAILS
        rep = DRC.check(self.asbuilt, DRS.compiled(self.asbuilt, 'self'))
        self.assertEqual(rep['verdict'], 'FAIL')
        self.assertEqual(rep['stage_diffs'], [])
        self.assertEqual(len(rep['torn_bundles']), 4)

    def test_equalised_plan(self):
        self.assertEqual(self.rows['K.rx_record'], {'d2d_kv.srx->kvs_attn': (9, 2), 'd2d_kv.rx_payload->kvs_attn': (11, 0)})
        self.assertEqual(self.rows['K.tx_slot']['d2d_kv.att_tx_kind->kvs_attn'], (8, 1))
        self.assertEqual(self.rows['K.tx_record']['kvs_attn.attn__tx_valid->d2d_kv'], (6, 5))
        self.assertEqual(self.rows['K.kvn_writer']['d2d_kv.skw->kvs_ctl'], (2, 2))
        self.assertEqual(DRB.torn(self.fixed), [])
        # nothing but the padded chains changed
        a = {b['id']: b['stages'] for b in self.asbuilt['buses']}
        changed = sorted(b['id'] for b in self.fixed['buses'] if b['stages'] != a[b['id']])
        self.assertEqual(len(changed), 4 + 1 + 1 + 2 + 1)  # srx->attn (4 slices), tx kind, tx_valid, skw (2), generation
        self.assertIn('d2d_kv.kvn_word_data -> kvs_attn.d2d__srx__521_10', changed)

    def test_fixed_passes_against_its_compiled_schedule(self):
        sched = compile_like_layer_compile(self.fixed)
        rep = DRC.check(self.fixed, sched)
        self.assertEqual(rep['verdict'], 'PASS', rep['fails'])

    def test_fixed_against_stale_L1_asks_for_recompile(self):
        rep = DRC.check(self.fixed, DRS.load(SCHED_L1))
        self.assertEqual(rep['verdict'], 'FAIL')
        self.assertTrue(any('re-compile against this die' in f for f in rep['fails']))
        self.assertEqual(rep['torn_bundles'], {})

    def test_identical_table_accepted_across_plan_ids(self):
        # the compiled table IS the die: pass although compiled from an earlier plan digest
        sched = compile_like_layer_compile(self.asbuilt)
        die = dict(sched, role='die_plan')
        die.pop('compiled')
        rep = DRC.check(DRS.make_doc(die['design'], die['plan'], die['clock_period_ps'], die['reach_um'], die['buses']),
                        sched, bundles=False)
        self.assertEqual(rep['verdict'], 'PASS', rep['fails'])

    @unittest.skipUnless(os.environ.get('OT_QXF_KVS14C_RUN'), 'set OT_QXF_KVS14C_RUN to re-walk the kvs14c die.v')
    def test_die_v_rewalk(self):
        import netlist_relay_stages as NRS
        import json
        run = Path(os.environ['OT_QXF_KVS14C_RUN'])
        pb = json.load(open(run / 'port_bind_v2/port_bind_v2.json'))
        doc = NRS.export(run / 'port_bind_v2/die_bound.v', pb, 'qwen_kv', 'f05f9338f',
                         ['/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14-f05f9338f/'],
                         [str(run / 'port_bind_v2'), str(run / 'case_kv')], 'kvs14c-netlist', None, None)
        self.assertEqual(doc['digest'], self.asbuilt['digest'])
        fixed, _ = BEQ.equalized_table(doc)          # the exporter's age_edges move with the pads
        self.assertEqual(DRB.torn(fixed), [])
        self.assertEqual(DRC.check(fixed, compile_like_layer_compile(fixed))['verdict'], 'PASS')


class BundleTables(unittest.TestCase):
    def test_compiler_bundles_are_checked(self):
        import layer_compile as LC
        for name, (design, sel) in LC.BUNDLES.items():
            self.assertEqual(DRB.BUNDLES[design][name], sel, name)

    def test_model_bundles_cover_check_bundles(self):
        for name, sel in DRB.BUNDLES['qwen_kv'].items():
            rtl = {(si, p, di) for si, port, di in BEQ.MODEL_BUNDLES[name] for p in BEQ.CHAIN_PORTS.get((si, port), (port,))}
            self.assertTrue(set(sel) <= rtl, name)

    def test_plan(self):
        self.assertEqual(BEQ.plan({'a': 9, 'b': 11}), {'a': 2, 'b': 0})
        self.assertEqual(BEQ.plan({}), {})


# ------------------------------------------------------------------------------------------------ generator plan pass
class _M:
    def __init__(self, ports):
        self.ports = ports


def _stub_K():
    import qwen_rom_fulldie as F
    K = SimpleNamespace(F=F, GX=F.GX, GY=F.GY, SHAVE=F.SHAVE, HOP=False, PIN_REACH=400.0, HOP_REACH=400.0,
                        width_reach=lambda bits: 340.0 if bits > 296 else 400.0,
                        up=lambda v, g: math.ceil(round(v / g, 6)) * g)
    pins = {'qkd_d2ds': {'srx': (0.0, 400.0), 'rx_payload': (0.0, 250.0)},
            'qkd_kvs_attn': {'d2d__srx': (230.0, 302.4), 'd2d__rx_payload': (80.0, 302.4)},
            'qkd_kvs_ctl': {'d2d__srx': (500.0, 172.8)}}
    K.masters = lambda m, k=1: {mst: _M(p) for mst, p in pins.items()}
    K.pin_xy = lambda it, mm, port: (it.x + mm.ports[port][0], it.y + mm.ports[port][1])
    return K, F


def _model(F):
    I = F.Inst
    insts = [I('d2d_kv', 'qkd_d2ds', 3000.0, 3000.0, 777.6, 518.4, kind='static'),
             I('kvs_attn', 'qkd_kvs_attn', 1000.0, 1000.0, 302.4, 302.4, kind='static'),
             I('kvs_ctl', 'qkd_kvs_ctl', 2600.0, 2400.0, 1123.2, 172.8, kind='static')]
    rl = lambda n, x, y: I(n, 'qkd_rly_522', x, y, 52.68, 30.24, kind='relay', region='relay')   # noqa: E731
    insts += [rl('rly_srx_0', 1250.0, 1450.0), rl('rly_rxp_0', 2400.0, 2000.0), rl('rly_rxp_1', 1600.0, 1600.0),
              rl('rly_rxp_2', 1200.0, 1400.0)]
    buses = [('seqst_rx', 'kv_oneway', 522, [('d2d_kv', 'srx'), ('rly_srx_0', 'a'), ('kvs_ctl', 'd2d__srx')]),   # fork net
             ('seqst_rx__r1', 'kv_oneway', 522, [('rly_srx_0', 'b'), ('kvs_attn', 'd2d__srx')]),
             ('ks_d2d_kv__rx_payload', 'kv_oneway', 548, [('d2d_kv', 'rx_payload'), ('rly_rxp_0', 'a')]),
             ('ks_d2d_kv__rx_payload__r1', 'kv_oneway', 548, [('rly_rxp_0', 'b'), ('rly_rxp_1', 'a')]),
             ('ks_d2d_kv__rx_payload__r2', 'kv_oneway', 548, [('rly_rxp_1', 'b'), ('rly_rxp_2', 'a')]),
             ('ks_d2d_kv__rx_payload__r3', 'kv_oneway', 548, [('rly_rxp_2', 'b'), ('kvs_attn', 'd2d__rx_payload')]),
             ('clk_core_c', 'clock_trunk', 1, [('ckb', 'ck'), ('d2d_kv', 'ck'), ('kvs_attn', 'ck')])]
    return dict(insts=insts, buses=buses, die=dict(w=6000.0, h=6000.0), relay_stages={'seqst_rx': 1,
                'ks_d2d_kv__rx_payload': 3})


class PlanPass(unittest.TestCase):
    def test_pads_shorter_member_at_sink(self):
        K, F = _stub_K()
        m = _model(F)
        n_before = len(m['insts'])
        BEQ.equalize(K, m, bundles={'K.rx_record': BEQ.MODEL_BUNDLES['K.rx_record']})
        by = {i.name: i for i in m['insts']}
        w = BEQ._walk(m, by, ('d2d_kv', 'srx'))
        self.assertEqual(w[('kvs_attn', 'd2d__srx')][0], 3)            # 1 + 2 pads = rx_payload's 3
        self.assertEqual(w[('kvs_ctl', 'd2d__srx')][0], 0)             # the fork's other branch untouched
        self.assertEqual(BEQ._walk(m, by, ('d2d_kv', 'rx_payload'))[('kvs_attn', 'd2d__rx_payload')][0], 3)
        pads = [i for i in m['insts'] if i.name.startswith(BEQ.PAD_PREFIX)]
        self.assertEqual(len(pads), 2)
        self.assertEqual(len(m['insts']), n_before + 2)
        self.assertEqual(m['relay_stages']['seqst_rx'], 3)
        sink = (1000.0 + 230.0, 1000.0 + 302.4)
        for p in pads:                                                  # beside the sink, legal, within reach
            self.assertLess(abs(p.x + p.w - sink[0]) + abs(p.y + p.h / 2 - sink[1]), 340.0)
            for q in m['insts']:
                if q is p:
                    continue
                ov = min(p.x + p.w, q.x + q.w) - max(p.x, q.x) > 0 and min(p.y + p.h, q.y + q.h) - max(p.y, q.y) > 0
                self.assertFalse(ov, (p.name, q.name))
        clk = next(b for b in m['buses'] if b[0] == 'clk_core_c')
        self.assertTrue(all((p.name, 'ck') in clk[3] for p in pads))
        self.assertEqual(m['bundle_eq']['bundles']['K.rx_record']['stages'], 3)

    def test_no_spot_fails_closed(self):
        K, F = _stub_K()
        m = _model(F)
        m['insts'].append(F.Inst('wall', 'blk', 700.0, 1150.0, 900.0, 900.0, kind='static'))   # covers the sink side
        with self.assertRaises(ValueError):
            BEQ.equalize(K, m, bundles={'K.rx_record': BEQ.MODEL_BUNDLES['K.rx_record']})


# ------------------------------------------------------------------------------------------------ placement knob
# kvs14c pin offsets (case_kv/elements.lef.prestd, R0, um from the frame origin; centre of each pin group)
D2D = dict(x=6241.536, y=27155.52, w=777.6, h=518.4,
           pins={'att_tx_slot': ('W', 4.5), 'att_tx_kind': ('W', 3.8), 'att_tx_beat': ('W', 2.6), 'att_tx_v': ('W', 4.7),
                 'rx_payload': ('W', 261.8), 'srx': ('W', 403.6), 'att_tx_payload': ('S', 128.6)})
ATTN = {'d2d__att_tx_slot': (4.6, 302.2), 'd2d__att_tx_kind': (3.9, 302.2), 'd2d__att_tx_beat': (2.7, 302.2),
        'd2d__rx_payload': (80.5, 302.2), 'd2d__srx': (228.3, 302.2), 'attn__tx_valid': (302.2, 263.4),
        'attn__tx_payload': (302.2, 132.6)}
REACH = {1: 400.0, 4: 400.0, 5: 400.0, 522: 340.0, 548: 340.0}       # kvs14c OT_KV_REACH_W 36:400,296:370,100000:340
SEAM = [('K.rx_record', 'srx', 'd2d__srx', 522, 'in'), ('K.rx_record', 'rx_payload', 'd2d__rx_payload', 548, 'in'),
        ('K.tx_slot', 'att_tx_slot', 'd2d__att_tx_slot', 1, 'in'), ('K.tx_slot', 'att_tx_kind', 'd2d__att_tx_kind', 4, 'in'),
        ('K.tx_slot', 'att_tx_beat', 'd2d__att_tx_beat', 5, 'in'), ('K.tx_record', 'att_tx_v', 'attn__tx_valid', 1, 'out'),
        ('K.tx_record', 'att_tx_payload', 'attn__tx_payload', 548, 'out')]


def seam_stages(ax, ay):
    """minimum relay stages of every seam member for kvs_attn at (ax, ay) (pin-to-pin Manhattan / reach - 1)"""
    out = {}
    for b, dp, ap, bits, _ in SEAM:
        f, c = D2D['pins'][dp]
        p = (D2D['x'], D2D['y'] + c) if f == 'W' else (D2D['x'] + c, D2D['y'])
        q = (ax + ATTN[ap][0], ay + ATTN[ap][1])
        out[(b, dp)] = max(0, math.ceil((abs(p[0] - q[0]) + abs(p[1] - q[1])) / REACH[bits]) - 1)
    return out


class AttnAtD2D(unittest.TestCase):
    def test_attn_at_d2d_rx_row(self):
        # OT_KV_ATTN_D2D_TOP=0.48 (N face on the end's rx_payload row): seam rx 0 / tx slot 1 / tx 0
        import kv_static_die as S
        d2d = SimpleNamespace(**{k: D2D[k] for k in 'xywh'})
        an = S.d2d_side_anchors(d2d, S.FRAME['attn'], S.FRAME['emb'], top=0.48)
        w, h = S.FRAME['attn']
        st = seam_stages(an['kvs_attn'][0] - w / 2, an['kvs_attn'][1] - h / 2)
        self.assertEqual((st[('K.rx_record', 'rx_payload')], st[('K.tx_slot', 'att_tx_kind')], st[('K.tx_record', 'att_tx_payload')]),
                         (0, 1, 0))

    def test_attn_at_d2d_pin_hops(self):
        import kv_static_die as S
        d2d = SimpleNamespace(**{k: D2D[k] for k in 'xywh'})
        an = S.d2d_side_anchors(d2d, S.FRAME['attn'], S.FRAME['emb'])
        w, h = S.FRAME['attn']
        ax, ay = an['kvs_attn'][0] - w / 2, an['kvs_attn'][1] - h / 2
        self.assertGreaterEqual(d2d.x - (ax + w), 21.6 - 1e-6)                  # one halo W of the end
        st = seam_stages(ax, ay)
        self.assertEqual(sorted(st.items()), sorted({('K.rx_record', 'srx'): 1, ('K.rx_record', 'rx_payload'): 1,
                                                     ('K.tx_slot', 'att_tx_slot'): 0, ('K.tx_slot', 'att_tx_kind'): 0,
                                                     ('K.tx_slot', 'att_tx_beat'): 0, ('K.tx_record', 'att_tx_v'): 0,
                                                     ('K.tx_record', 'att_tx_payload'): 0}.items()))
        ew, eh = S.FRAME['emb']
        ex = an['kvs_emb'][0] - ew / 2
        self.assertLessEqual(ex + ew, ax - 21.6 + 1e-6)                         # kvs_emb W of kvs_attn, no overlap

    def test_kvs14c_position_is_far(self):
        st = seam_stages(5201.712, 24850.8)                                     # kvs14c kvs_attn origin
        self.assertGreaterEqual(min(st.values()), 5)


if __name__ == '__main__':
    unittest.main()
