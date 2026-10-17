#!/usr/bin/env python3
"""opentallas.die_relay_stages.v1: schema module, per-die exporters, consumers, die_relay_check
(python3 tools/test_die_relay_stages.py)."""
import gzip
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'hbm_die_v15'))
import die_relay_stages as DRS  # noqa: E402
import die_relay_check as CHK  # noqa: E402
import importlib.util  # noqa: E402


def mod(rel, name):
    spec = importlib.util.spec_from_file_location(name, HERE / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def bus(si, sp, di, dp, stages, width=8, domain='core', **kw):
    return dict(id=DRS.bus_id(si, sp, di, dp), src=dict(inst=si, port=sp), dst=dict(inst=di, port=dp), width=width,
                stages=stages, domain=domain, **kw)


def plan(buses, design='hbm', pid='p1'):
    return DRS.make_doc(design, dict(id=pid), 833.333, 450.0, buses)


class Inst:
    def __init__(self, name, master, kind, domain='stream_1p2'):
        self.name, self.master, self.kind, self.domain = name, master, kind, domain


class Schema(unittest.TestCase):
    def test_roundtrip_gz_and_digest(self):
        d = plan([bus('a', 'x', 'b', 'y', 3), bus('a', 'x', 'c', 'y', 0)])
        self.assertEqual(DRS.validate(d), [])
        with tempfile.TemporaryDirectory() as t:
            for name in ('p.json', 'p.json.gz'):
                p = DRS.write(Path(t) / name, d)
                self.assertEqual(DRS.load(p)['digest'], d['digest'])
            raw = json.loads(gzip.open(Path(t) / 'p.json.gz').read())
            raw['buses'][0]['stages'] += 1                       # edited after export -> digest refuses
            (Path(t) / 'bad.json').write_text(json.dumps(raw))
            with self.assertRaises(DRS.RelayStagesError):
                DRS.load(Path(t) / 'bad.json')
            with self.assertRaises(DRS.RelayStagesError):
                DRS.load(Path(t) / 'missing.json')

    def test_digest_ignores_order_and_geometry(self):
        a = plan([bus('a', 'x', 'b', 'y', 3, stations=[dict(depth=1, x=1.0, y=2.0)]), bus('a', 'x', 'c', 'y', 1)])
        b = plan([bus('a', 'x', 'c', 'y', 1), bus('a', 'x', 'b', 'y', 3)])
        self.assertEqual(a['digest'], b['digest'])
        self.assertNotEqual(a['digest'], plan([bus('a', 'x', 'b', 'y', 4), bus('a', 'x', 'c', 'y', 1)])['digest'])

    def test_invalid(self):
        with self.assertRaises(DRS.RelayStagesError):
            plan([bus('a', 'x', 'b', 'y', 1), bus('a', 'x', 'b', 'y', 2)])     # duplicate id
        with self.assertRaises(DRS.RelayStagesError):
            plan([bus('a', 'x', 'b', 'y', -1)])
        with self.assertRaises(DRS.RelayStagesError):
            DRS.make_doc('nope', dict(id='p'), 833.0, 450.0, [])

    def test_table_fails_closed(self):
        t = DRS.Table(plan([bus('a', 'x+z', 'b', 'y', 3)]))
        self.assertEqual(t.stages('a.x+z -> b.y'), 3)
        self.assertEqual(len(t.match(src_inst='a', src_port='z')), 1)
        with self.assertRaises(DRS.MissingBus):
            t.stages('a.x -> c.y')

    def test_plan_path(self):
        with self.assertRaises(DRS.RelayStagesError):
            DRS.plan_path('hbm', None) if 'OT_DIE_RELAY_STAGES_HBM' not in os.environ else (_ for _ in ()).throw(
                DRS.RelayStagesError('env set'))
        os.environ['OT_DIE_RELAY_STAGES_S81'] = '/x/y.json'
        try:
            self.assertEqual(str(DRS.plan_path('s81')), '/x/y.json')
        finally:
            del os.environ['OT_DIE_RELAY_STAGES_S81']

    def test_json_schema_agrees(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema not installed')
        s = json.loads((ROOT / 'schemas/die/die_relay_stages_v1.schema.json').read_text())
        d = plan([bus('a', 'x', 'b', 'y', 3, eq_age_group='g')])
        jsonschema.validate(d, s)
        c = DRS.compiled(d, 'test')
        jsonschema.validate(c, s)
        bad = dict(c); bad.pop('compiled')
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, s)

    def test_trace_model(self):
        insts = {n: dict(master=m, kind=k, domain='d') for n, m, k in
                 [('s', 'SRC', 'blk'), ('r0', 'RLY', 'rly'), ('r1', 'RLY', 'rly'), ('t', 'SNK', 'blk'), ('u', 'SNK', 'blk')]}
        buses = [('b0', 'data', 8, [('s', 'o[0:7]'), ('r0', 'i')]), ('b0__r1', 'data', 8, [('r0', 'o'), ('r1', 'i'), ('u', 'd')]),
                 ('b0__r2', 'data', 8, [('r1', 'o'), ('t', 'd')]), ('ck', 'clock', 1, [('s', 'ck'), ('r0', 'ck')])]
        rec, prob = DRS.trace_model(insts, buses, lambda n: insts[n]['kind'] == 'rly', lambda _i, p: {'i': 'o'}.get(p),
                                    lambda p: p.split('[')[0])
        got = {r['id']: (r['stages'], r['width'], r['bid']) for r in rec}
        self.assertEqual(got, {'s.o -> t.d': (2, 8, 'b0'), 's.o -> u.d': (1, 8, 'b0')})
        self.assertEqual(prob, [])


class Check(unittest.TestCase):
    def setUp(self):
        self.p = plan([bus('a', 'x', 'b', 'y', 3), bus('a', 'x', 'c', 'y', 0)])

    def run_check(self, run, sched):
        with tempfile.TemporaryDirectory() as t:
            DRS.write(Path(t) / 'r.json', run); DRS.write(Path(t) / 's.json', sched)
            return CHK.main([str(Path(t) / 'r.json'), str(Path(t) / 's.json'), '--json', str(Path(t) / 'rep.json')])

    def test_pass(self):
        self.assertEqual(self.run_check(self.p, DRS.compiled(self.p, 'test')), 0)
        self.assertEqual(self.run_check(self.p, self.p), 0)

    def test_matching_partial_or_ambiguous_tables_do_not_qualify(self):
        import copy
        for changes in ({'coverage': 'relayed_only'}, {'problem_count': 1},
                        {'problems': ['unresolved endpoint']}):
            bad = dict(self.p, **changes)
            with self.subTest(changes=changes):
                self.assertEqual(CHK.check(bad, DRS.compiled(bad, 'test'))['verdict'], 'FAIL')
        bad = copy.deepcopy(self.p)
        bad['buses'][0]['domain'] = None
        bad = DRS.make_doc('hbm', {'id': 'unknown-domain'}, 833.333, 450, bad['buses'])
        self.assertEqual(CHK.check(bad, DRS.compiled(bad, 'test'))['verdict'], 'FAIL')

    def test_qwen_dump_cannot_claim_complete_compiler_coverage(self):
        exporter = mod('qwen_split/relay_stages_export.py', 'qwen_dump_test')
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'dump.json'
            path.write_text(json.dumps({'plans': [dict(bid='long', cl='data', bits=8,
                eps=[['a', 'o'], ['b', 'i']], n=2)]}))
            partial = exporter.export_dump(path, 'partial', reach=425)
        self.assertEqual(partial['coverage'], 'relayed_only')
        self.assertFalse(partial['compiler_qualified'])
        self.assertEqual(CHK.check(partial, DRS.compiled(partial, 'test'))['verdict'], 'FAIL')

    def test_stage_diff_fails(self):
        run = plan([bus('a', 'x', 'b', 'y', 4), bus('a', 'x', 'c', 'y', 0)])
        self.assertEqual(self.run_check(run, DRS.compiled(self.p, 'test')), 1)
        rep = CHK.check(run, DRS.compiled(self.p, 'test'))
        self.assertEqual(rep['stage_diffs'], [dict(bus='a.x -> b.y', die_run=4, schedule=3)])
        self.assertTrue(any('digest' in f for f in rep['fails']))

    def test_missing_bus_fails(self):
        run = plan([bus('a', 'x', 'b', 'y', 3)])
        rep = CHK.check(run, self.p)
        self.assertEqual(rep['verdict'], 'FAIL'); self.assertEqual(rep['only_in_schedule'], ['a.x -> c.y'])
        rep = CHK.check(self.p, run)
        self.assertEqual(rep['only_in_die_run'], ['a.x -> c.y'])

    def test_override_and_scheduled(self):
        c = DRS.compiled(self.p, 'test', overrides={'a.x -> b.y': 3})       # same value, still an override -> FAIL
        self.assertEqual(CHK.check(self.p, c)['verdict'], 'FAIL')
        c = DRS.compiled(self.p, 'rtl', scheduled={'a.x -> b.y': 3})
        self.assertEqual(CHK.check(self.p, c)['verdict'], 'PASS')
        c = DRS.compiled(self.p, 'rtl', scheduled={'a.x -> b.y': 2})
        self.assertEqual(CHK.check(self.p, c)['verdict'], 'FAIL')
        with self.assertRaises(DRS.MissingBus):
            DRS.compiled(self.p, 'rtl', scheduled={'nope': 1})

    def test_design_and_domain(self):
        self.assertEqual(CHK.check(self.p, plan(self.p['buses'], design='s81'))['verdict'], 'FAIL')
        other = plan([bus('a', 'x', 'b', 'y', 3, domain='serial'), bus('a', 'x', 'c', 'y', 0)])
        self.assertEqual(len(CHK.check(other, self.p)['domain_diffs']), 1)

    def test_bad_file_fails(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'x.json').write_text('{}')
            DRS.write(Path(t) / 'p.json', self.p)
            self.assertEqual(CHK.main([str(Path(t) / 'x.json'), str(Path(t) / 'p.json')]), 1)


# ---------------------------------------------------------------------------------------------------- HBM
LEF = """MACRO {m}
  SIZE 10 BY 10 ;
{pins}END {m}
"""
PIN = """  PIN {p}
    DIRECTION {d} ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 4 4 6 6 ;
    END
  END {p}
"""


def hbm_case(root, relays):
    """src u_src.o -> snk u_snk.d 1000 um apart (+ u_near.d 100 um); `relays` hbfd_rly_48 tiles in the chain to u_snk"""
    (root / 'views').mkdir(parents=True)
    lef = LEF.format(m='SRC', pins=PIN.format(p='o', d='OUTPUT')) + LEF.format(m='SNK', pins=PIN.format(p='d', d='INPUT')) + \
        LEF.format(m='hbfd_rly_48_WE', pins=PIN.format(p='i', d='INPUT') + PIN.format(p='o', d='OUTPUT'))
    (root / 'views' / 'm.lef').write_text(lef)
    pl = {'u_src': dict(m='SRC', x=0, y=0, o='R0'), 'u_snk': dict(m='SNK', x=1000, y=0, o='R0'),
          'u_near': dict(m='SNK', x=100, y=0, o='R0')}
    v = ['module die();']
    prev = 'n0'
    v.append(f'  SRC u_src (\n    .o({prev})\n  );')
    for k in range(relays):
        pl[f'r{k}'] = dict(m='hbfd_rly_48_WE', x=330 * (k + 1), y=0, o='R0')
        v.append(f'  hbfd_rly_48_WE r{k} (\n    .i({prev}),\n    .o(n{k + 1})\n  );')
        prev = f'n{k + 1}'
    v.append(f'  SNK u_snk (\n    .d({prev})\n  );')
    v.append('  SNK u_near (\n    .d(n0)\n  );')
    v.append('endmodule')
    (root / 'die.v').write_text('\n'.join(v) + '\n')
    man = dict(placement=pl, clock_entry_map={'stream': {'u_src': 1, 'u_snk': 1, 'u_near': 1}})
    (root / 'manifest.json').write_text(json.dumps(man))


class Hbm(unittest.TestCase):
    def export(self, relays, stations=None):
        X = mod('hbm_die_v15/relay_stages_export.py', 'hbm_relay_stages_export')
        with tempfile.TemporaryDirectory() as t:
            hbm_case(Path(t) / 'c', relays)
            return X.export(Path(t) / 'c', None, 'fixture', stations, reach=450.0)

    def test_plan_matches_relayed_run(self):
        st = dict(rows=[dict(driver='u_src.o', sinks=['u_near', 'u_snk'], sink_depths=[0, 2], depth=2, cls='p2p',
                             domain='stream')])
        p = self.export(0, st)
        self.assertEqual({b['id']: b['stages'] for b in p['buses']}, {'u_src.o -> u_snk.d': 2, 'u_src.o -> u_near.d': 0})
        self.assertEqual(p['problems'], [])
        # the relayed die run: the near sink now hangs off the driver net, the far one behind 2 netlist relays
        run = self.export(2)
        self.assertEqual(CHK.check(run, p)['verdict'], 'PASS')
        self.assertEqual(CHK.check(self.export(1), p)['verdict'], 'FAIL')

    def test_equal_age(self):
        st = dict(rows=[dict(driver='u_src.o', sinks=['u_near', 'u_snk'], sink_depths=[0, 2], depth=2,
                             cls='equal_age_pad', domain='stream')])
        p = self.export(0, st)
        self.assertEqual({b['stages'] for b in p['buses']}, {2})
        self.assertEqual(len({b['eq_age_group'] for b in p['buses']}), 1)

    def test_committed_d4b_plan(self):
        p = ROOT / 'results/arch/die_relay_stages_1016/hbm_d4b_450_plan.json.gz'
        s = ROOT / 'results/arch/die_relay_stages_1016/hbm_d4b_450_relay_class_price_sched.json.gz'
        import relay_class_price as RCP
        doc = DRS.load(p)
        vals, _ = RCP.class_stages(DRS.Table(doc))
        self.assertEqual(vals['SM_X'], 31)                       # vms.rr -> ctlw 3 + ctlw.xw -> smh 28 (equal-age max)
        # Historical scalar class projection survives, but its unresolved export problems cannot qualify a schedule.
        rep = CHK.check(doc, DRS.load(s))
        self.assertEqual(rep['verdict'], 'FAIL')
        self.assertIn('die run reports unresolved export problems', rep['fails'])

    def test_class_price_fails_closed_and_prices(self):
        import relay_class_price as RCP
        buses = []
        for cls, legs in RCP.CLASSES.items():
            for _how, alts in legs:
                for o, s in alts:
                    om, op = o.split('.', 1); sm, sp = s.split('.', 1)
                    buses.append(dict(bus(f'{om}_i', op, f'{sm}_i', sp, 2), src=dict(inst=f'{om}_i', port=op, master=om),
                                      dst=dict(inst=f'{sm}_i', port=sp, master=sm)))
        uniq = {b['id']: b for b in buses}
        t = DRS.Table(plan(list(uniq.values())))
        vals, used = RCP.class_stages(t)
        self.assertEqual(vals['SM_HBM'], 6); self.assertEqual(vals['SM_X'], 4); self.assertEqual(vals['LG_SU'], 2)
        drop = [b for b in uniq.values() if b['src']['master'] != 'ot_hbm_hc_q_static']
        with self.assertRaises(RCP.ClassPriceError):
            RCP.class_stages(DRS.Table(plan(drop)))


# ---------------------------------------------------------------------------------------------------- S81
class S81(unittest.TestCase):
    def model(self, n_relays=2):
        insts = [Inst('sp_capture', 'dsfd_hub', 'hub'), Inst('sp_mtp', 'dsfd_hub', 'hub')]
        buses, prev = [], ('sp_capture', 't_mtp')
        for k in range(n_relays):
            insts.append(Inst(f'g_{k}', 'dsfd_hstn', 'hstn'))
            buses.append((f'h{k}', 'hub', 32, [prev, (f'g_{k}', 'di')])); prev = (f'g_{k}', 'dq')
        buses.append(('hz', 'hub', 32, [prev, ('sp_mtp', 'f_capture')]))
        buses.append(('st', 'lane', 16, [('sp_mtp', 't_capture'), ('s0', 'di0')]))
        insts.append(Inst('s0', 'dsfd_stn', 'stn'))
        buses.append(('st1', 'lane', 16, [('s0', 'do0'), ('sp_capture', 'f_mtp')]))
        buses.append(('sv', 'hub', 8, [('sp_vm', 't_mtp'), ('sp_mtp', 'f_vm')]))
        buses.append(('mv', 'hub', 8, [('sp_mtp', 't_vm'), ('sp_vm', 'f_mtp')]))
        buses.append(('ck', 'col_clock', 1, [('ckr', 'ck'), ('g_0', 'ck')]))
        insts.append(Inst('sp_vm', 'dsfd_hub', 'hub'))
        return dict(insts=insts, buses=buses)

    def test_export_model(self):
        X81 = mod('s81/relay_stages_export.py', 's81_relay_stages_export')
        d = X81.export_model(self.model(), 't', reach=455.0)
        st = {b['id']: b['stages'] for b in d['buses']}
        self.assertEqual(st['sp_capture.t_mtp -> sp_mtp.f_capture'], 2)
        self.assertEqual(st['sp_mtp.t_capture -> sp_capture.f_mtp'], 1)
        self.assertEqual(d['buses'][0]['domain'], 'stream_1p2')
        self.assertFalse(any(b['dst']['port'] == 'ck' for b in d['buses']))
        self.assertEqual(d['problems'], [])

    def test_mtp_rtt_consumer(self):
        X81 = mod('s81/relay_stages_export.py', 's81_relay_stages_export')
        M = mod('s81/mtp_rtt_stages.py', 's81_mtp_rtt_stages')
        p = X81.export_model(self.model(), 't', reach=455.0)
        rtl = 'parameter integer FWD_R = 2, parameter integer RET_R = 1, parameter integer FWD_V = 0, parameter integer RET_V = 0,'
        rep, sched = M.run(p, rtl)
        self.assertEqual(rep['verdict'], 'PASS'); self.assertEqual(CHK.check(p, sched)['verdict'], 'PASS')
        rep, sched = M.run(p, rtl.replace('FWD_R = 2', 'FWD_R = 6'))
        self.assertEqual(rep['verdict'], 'FAIL'); self.assertEqual(CHK.check(p, sched)['verdict'], 'FAIL')
        q = DRS.make_doc('s81', dict(id='x'), 833.333, 455.0, [b for b in p['buses'] if 'sp_vm' not in b['id']])
        with self.assertRaises(DRS.MissingBus):
            M.run(q, rtl)

    def test_committed_plan_dump_agrees_with_hub_stage_count(self):
        d0 = ROOT / 'results/physical/die_iter_1012/s81/v18_screen_native_envelopes207'
        if not (d0 / 'plan.json.gz').exists():
            self.skipTest('committed S81 plan dump not checked out')
        import re
        X81 = mod('s81/relay_stages_export.py', 's81_relay_stages_export')
        d = X81.export_dump(d0 / 'plan.json.gz', 'v18', reach=455.0)
        t = DRS.Table(d)
        hub = json.loads((d0 / 'stage_counts.json').read_text())['hub_pin_to_pin_stages']
        n = 0
        for k, v in hub.items():
            a, b = (re.sub(r'\[[\d:]+\]', '', x) for x in k.split('->'))
            dst = b.split('.')[0]
            if '_t_' in dst or re.match(r'f_K\w+t_\d+$', dst):
                continue        # hub_stage_count stops at a trunk station; this table walks through it to the far end
            self.assertEqual(t.stages(f'{a} -> {b}'), v, k); n += 1
        self.assertGreater(n, 50)


# ---------------------------------------------------------------------------------------------------- Qwen
class Qwen(unittest.TestCase):
    def model(self):
        insts = [Inst('src', 'qfd_a', 'blk'), Inst('dst', 'qfd_b', 'blk'), Inst('rly_x_0', 'qfd_rly_8', 'relay'),
                 Inst('rly_x_1', 'qfd_rly_8', 'relay')]
        buses = [('x', 'corridor', 8, [('src', 'o'), ('rly_x_0', 'a')]), ('x__r1', 'corridor', 8, [('rly_x_0', 'b'), ('rly_x_1', 'a')]),
                 ('x__r2', 'corridor', 8, [('rly_x_1', 'b'), ('dst', 'i')]), ('y', 'corridor', 4, [('dst', 'q'), ('src', 'k')]),
                 ('ck', 'clock_trunk', 1, [('pll', 'c'), ('rly_x_0', 'ck')]), ('t', 'tap', 2, [('src', 't'), ('dst', 't')])]
        return dict(insts=insts, buses=buses, relay_stages={'x': 2, 'y': 1})

    def test_compute_export_and_b2_adapter(self):
        from qwen_split import relay_stages_export as QX
        d = QX.export_model(self.model(), 'q', reach=425.0)
        self.assertEqual({b['id']: (b['stages'], b['bid']) for b in d['buses']},
                         {'src.o -> dst.i': (2, 'x'), 'dst.q -> src.k': (0, 'y')})
        from qwen_static_schedule.b2_timing import _stage_of
        self.assertEqual(_stage_of(d), {'x': 3, 'y': 1})            # r21_stage_of convention: edges = stages + 1
        self.assertEqual(_stage_of({'x': 3}), {'x': 3})
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'dump.json').write_text(json.dumps(dict(plans=[
                dict(bid='x', cl='corridor', bits=8, eps=[['src', 'o'], ['dst', 'i']], n=2),
                dict(bid='y', cl='corridor', bits=4, eps=[['dst', 'q'], ['src', 'k']], n=0),
                dict(bid='t', cl='tap', bits=2, eps=[['src', 't'], ['dst', 't']], n=0)])))
            dd = QX.export_dump(Path(t) / 'dump.json', 'q', reach=425.0)
        self.assertEqual({b['id']: b['stages'] for b in dd['buses']}, {b['id']: b['stages'] for b in d['buses']})

    def test_kv_export_crosscheck(self):
        from qwen_kv_die import relay_stages_export as KX
        d = KX.export_model(self.model(), 'kv', reach=446.0)
        self.assertEqual(d['design'], 'qwen_kv')
        self.assertEqual(d['relay_stages_crosscheck']['mismatches'], 1)        # y recorded 1, netlist walk 0
        self.assertIn('kv_die relay_stages[y] = 1', d['problems'][0])


if __name__ == '__main__':
    unittest.main()
