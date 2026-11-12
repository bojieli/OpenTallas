import importlib.util, json, os, pathlib, sys, tempfile, types, unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import design_export_hook as H


def autoclean():
    spec = importlib.util.spec_from_file_location('ot_autoclean', HERE.parent / 'fleet' / 'ot-autoclean.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class HookTest(unittest.TestCase):
    def test_norm_matches_autoclean(self):
        ac = autoclean()
        for n in ('kl_dsfd_su_t_rxsf_r1t', 'dp_kv3_hgi', 'slw_hc0__cl1bc59e1c', 'hd_serdes__t2', 'coll_n'):
            self.assertEqual(H.norm(n), ac.dx_norm(n))
        self.assertEqual(H.norm('kl_dsfd_su_t_rxsf_r1t'), 'dsfd_su_t_rxsf')

    def test_ledger_reads_cuts_and_manifests(self):
        with tempfile.TemporaryDirectory() as d:
            st = pathlib.Path(d)
            (st / 'cuts.json').write_text(json.dumps({'epyc2:/a/6_final.odb': {'verdict': 'IDENTICAL'}, 'epyc2:/b.odb': {'verdict': 'DIFFERENT'}}))
            (st / 'elements/x').mkdir(parents=True)
            (st / 'elements/x/j.json').write_text(json.dumps({'element': 'x', 'design': {'db': 'epyc4:/c/6_final.odb'}, 'verify': {'verdict': 'IDENTICAL'}}))
            self.assertEqual(sorted(H.ledger(st)), ['epyc2:/a/6_final.odb', 'epyc4:/c/6_final.odb'])

    def test_autoclean_holds_until_cut(self):
        ac = autoclean()
        with tempfile.TemporaryDirectory() as d:
            b = pathlib.Path(d) / 'attempt_3/gen/kv3_hgi/run/results/asap7/dp_kv3_hgi/base'; b.mkdir(parents=True)
            for f in ('3_place.odb', '4_1_cts.odb', '5_1_grt.odb'): (b / f).write_text('x')
            J = types.SimpleNamespace(host='epyc9', dx_sent=set(),
                                      dx=dict(ledger=set(), paths=set(), names={'kv3_hgi'}, stages=H.STAGES))
            hold = lambda: ac.Job.dx_hold(J, d)
            self.assertIn('5_1_grt.odb', hold() or '')                 # best routed stage, not 4_1_cts
            J.dx['ledger'].add('epyc9:%s/5_1_grt.odb' % b)
            self.assertIsNone(hold())                                  # cut -> released
            J.dx['names'] = set(); J.dx['ledger'] = set()
            self.assertIsNone(hold())                                  # not a current design -> no hold
            J.dx = None
            self.assertIsNone(hold())                                  # no snapshot file -> gate off


    def test_drain_order_starved_hosts_first(self):
        q = lambda h, t: ['%s:/x/%s/6_final.odb' % (h, t), 'd', '6_final', t, 'newest']
        pend = [q('epyc9', '01'), q('epyc2', '03'), q('epyc4', '05'), q('epyc4', '02'), q('epyc7', '00'), q('gone', '00')]
        todo, starved = H.order_queue(pend, {'epyc9': 3000, 'epyc2': 61, 'epyc4': 58, 'epyc7': 275, 'gone': None}, 150, 2, 60)
        self.assertEqual(starved, {'epyc2', 'epyc4'})
        self.assertEqual([r[0].split(':')[0] + r[3] for r in todo], ['epyc402', 'epyc405', 'epyc203', 'epyc700', 'gone00'])
        todo, _ = H.order_queue(pend, {'epyc2': 61, 'epyc4': 58}, 150, 0, 1)   # caps apply per class
        self.assertEqual([r[0].split(':')[0] for r in todo], ['epyc4'])


if __name__ == '__main__':
    unittest.main()
