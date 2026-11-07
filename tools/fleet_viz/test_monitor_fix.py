#!/usr/bin/env python3
"""Tests for fleet_discover.py and kit_verdicts.py (no ssh, no live files)."""
import json, os, pathlib, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fleet_discover as F, kit_verdicts as K


def el(item, verdict=None, gen='2026-11-06T10:00:00', tt=5.0, ff=1.0, **kw):
    m = dict(kind='kit', verdict=verdict, signoff_generated=gen, tt_wns=tt, ff_wns=ff, drc=0, reasons=['drv: FAIL']) if verdict else {}
    return dict(die='hbm', element=item, m=m, kw=dict(kit='epyc5:/x'), **kw)


def st(item, status, when='2026-11-06 12:00', cls='', stage='route', current='yes', kit='epyc6:/k'):
    return dict(die='s81', item=item, status=status, updated=when, plan_current=current, stage=stage, reason='why', event='e', kit=kit, evidence='', **{'class': cls})


class Hosts(unittest.TestCase):
    def test_parse_wrapper_output(self):
        self.assertEqual(F.parse_hosts_line('HOSTS = ["epyc2", "localhost"]   # note [x]\n'), ['epyc2', 'localhost'])
        self.assertIsNone(F.parse_hosts_line('nothing'))
        self.assertIsNone(F.parse_hosts_line('HOSTS = [os.x]'))

    def test_read_command_finds_released_script(self):
        with tempfile.TemporaryDirectory() as d:
            b = pathlib.Path(d, '.local/bin'); b.mkdir(parents=True); rel = pathlib.Path(d, 'rel-ot-run')
            rel.write_text('x = 1\nHOSTS = ["a", "localhost"]\nHOSTS = ["old"]\n')
            b.joinpath('ot-run').write_text('#!/bin/sh\nexport A=1\nexec /usr/bin/python3 %s "$@"\n' % rel)
            out = __import__('subprocess').run(['sh', '-c', F.READ_HOSTS], env=dict(os.environ, HOME=d), capture_output=True, text=True).stdout
            self.assertEqual(F.parse_hosts_line(out), ['a', 'localhost'])

    def test_missing_matches_id_or_alias(self):
        cfg = [dict(id='a', ssh='a'), dict(id='hub', ssh='ot-hub'), dict(id='localhost', ssh=None)]
        self.assertEqual(F.missing_hosts(cfg, ['a', 'ot-hub', 'new']), ['new'])

    def test_kind_text(self):
        self.assertEqual(F.kind_text('AMD EPYC 9554P 64-Core Processor\n1\n128\n791870488\n'), '1x EPYC 9554P (128T, 755 GB)')
        self.assertEqual(F.kind_text('Intel(R) Xeon(R) Gold 6330 CPU @ 2.00GHz\n2\n112\n1056406732\n'), '2x Xeon Gold 6330 (112T, 1007 GB)')
        self.assertEqual(F.kind_text(''), 'fleet host')

    def test_discover_adds_once_and_survives_read_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d, 'auto.json'); cfg = [dict(id='a', ssh='a')]
            self.assertEqual(F.discover(cfg, p, reader=lambda h: None), [])
            self.assertFalse(p.exists())
            new = F.discover(cfg, p, reader=lambda h: ['a', 'b'], prober=lambda h: '')
            self.assertEqual(new, ['b'])
            hosts = F.load_hosts(cfg, p); self.assertEqual([h['id'] for h in hosts], ['a', 'b'])
            self.assertEqual(F.discover(hosts, p, reader=lambda h: ['a', 'b']), [])
            self.assertEqual([h['id'] for h in F.load_hosts([dict(id='b', ssh='b')], p)], ['b'])


class Verdicts(unittest.TestCase):
    def test_signoff_kinds(self):
        r, _ = K.build([el('a', 'SIGNED'), el('b', 'LOCAL_PASS_NEEDS_PARENT'), el('c', 'NOT SIGNED', ff=-3.0), el('d', 'NOT SIGNED'), el('e')], [])
        got = {v['block']: (v['status'], v['kind']) for v in r}
        self.assertEqual(got, dict(a=('SIGNED OFF', 'closed'), b=('NEEDS PARENT', 'closed'), c=('NOT SIGNED', 'timing'), d=('NOT SIGNED', 'check')))
        self.assertEqual(next(v for v in r if v['block'] == 'a')['host'], 'epyc5')
        self.assertEqual(next(v for v in r if v['block'] == 'a')['cat'], 'HBM accelerator')

    def test_stage_rows(self):
        r, run = K.build([], [st('a', 'FAIL', cls='TIMING'), st('b', 'FAIL', cls='ROUTING'), st('c', 'FAIL', current='no'), st('d', 'SIGNED'),
                              st('e', 'RUNNING'), st('f', 'RUNNING', stage='place'), st('g', 'FAIL', kit='localhost:/k')])
        got = {v['block']: (v['status'], v['kind']) for v in r}
        self.assertEqual(got, dict(a=('FAIL TIMING', 'timing'), b=('FAIL ROUTE', 'flow'), d=('SIGNED OFF', 'closed'), g=('FAIL FLOW', 'flow')))
        self.assertEqual(run, {'DeepSeek ROM': 1})
        self.assertEqual(next(v for v in r if v['block'] == 'g')['host'], K.HUB)

    def merged(self, verdict, when):
        e = dict(el('x', verdict), die='s81')
        return K.build([e], [st('x', 'FAIL', when=when, cls='TIMING')])[0]

    def test_failure_before_signoff_is_history(self):
        self.assertEqual([v['status'] for v in self.merged('SIGNED', '2026-11-06 09:00')], ['SIGNED OFF'])

    def test_failure_after_signoff_is_shown(self):
        self.assertEqual(sorted(v['status'] for v in self.merged('SIGNED', '2026-11-06 12:00')), ['FAIL TIMING', 'SIGNED OFF'])

    def test_not_signed_and_failure_are_one_row(self):
        for when, want in (('2026-11-06 12:00', 'FAIL TIMING'), ('2026-11-06 09:00', 'NOT SIGNED')):
            r = self.merged('NOT SIGNED', when)
            self.assertEqual([v['status'] for v in r], [want]); self.assertEqual(r[0]['setup'], 5.0)

    def test_reader_flags_missing_file_and_keeps_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p, s = pathlib.Path(d, 'p.json'), pathlib.Path(d, 's.tsv')
            p.write_text(json.dumps(dict(generated=100.0, elements=[el('a', 'SIGNED')])))
            s.write_text('die\titem\tstatus\tplan_current\n')
            kv = K.KitVerdicts(p, s); self.assertEqual(len(kv.scan()), 1); self.assertIsNone(kv.err); self.assertEqual(kv.t, 100.0)
            s.unlink(); self.assertEqual(len(kv.scan()), 1); self.assertTrue(kv.err)


if __name__ == '__main__':
    unittest.main()
