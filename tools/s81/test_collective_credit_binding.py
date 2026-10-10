#!/usr/bin/env python3
"""Reject same-named legacy views and incomplete credit-link evidence without building a die."""
import copy
import hashlib
import json
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta as D
import assemble_views as A


class CreditBindingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        manifest = json.loads((D.ROOT / 'physical/s81_ph_views/collective/composition_split3cr.json').read_text())
        self.write('physical/s81_ph_views/collective/composition_split3cr.json', manifest)
        self.receipts = {}
        for m in D.COLL_CR_PARTS:
            source = manifest['source_commits']['lane' if m.endswith('lane_w') else 'core']
            directory = 'physical/credit_views/' + m
            route = 'route ' + ' '.join('--param ' + k + '=' + str(v) for k, v in manifest['required_parameters'][m].items())
            receipt = dict(block=m, source_commit=source, status='CLOSED', metrics=dict(ss_ps=12, ff_ps=3, drc=0),
                           benches=dict(exact=dict(ok=True, expect='pass'), mutant1=dict(ok=True, expect='fail'),
                                        mutant2=dict(ok=True, expect='fail')),
                           job_spec=dict(stages=dict(route=dict(cmd=route)), record=[dict(to=directory)]))
            vp = 'results/closure_loop/' + m + '/verdict.json'
            self.write(vp, receipt)
            self.receipts[m] = (vp, receipt)
            self.write(directory + '/check.json', dict(verdict='MATCH'))
            for c in ('ss', 'tt', 'ff'):
                p = self.root / directory / (m + '_' + c + '.lib')
                p.write_text('cell (' + m + ') {}\n')

        clock_dir = 'physical/s81_ph_views/closed/dsfd_coll_ck'
        self.write(clock_dir + '/verdict.json', dict(verdict='CLOSED', commit='752a48488384dbe9c95a72c084bc24e0ac800a17', ss_ps=9000, ff_ps=31, drc=0))
        for c in ('ss', 'tt', 'ff'):
            (self.root / clock_dir / ('dsfd_coll_ck_' + c + '.lib')).write_text('cell (dsfd_coll_ck) {}')

    def write(self, relative, obj):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj))

    def test_missing_or_legacy_lane_never_satisfies_binding(self):
        vp, receipt = self.receipts['dsfd_coll_lane_w']
        for change in ('source', 'parameter', 'bench', 'slack'):
            bad = copy.deepcopy(receipt)
            if change == 'source': bad['source_commit'] = 'legacy'
            if change == 'parameter': bad['job_spec']['stages']['route']['cmd'] = 'route --param LCR=0'
            if change == 'bench': bad['benches']['mutant1']['ok'] = False
            if change == 'slack': bad['metrics']['ff_ps'] = -0.01
            self.write(vp, bad)
            binding = D.collective_credit_binding(self.root)
            self.assertNotIn('dsfd_coll_lane_w', binding['tile_bindings'], change)
            self.assertFalse(binding['qualified'])
            self.assertTrue(binding['problems'])
        self.write(vp, receipt)
        (self.root / vp).unlink()
        self.assertTrue(D.collective_credit_binding(self.root)['problems'])

    def test_per_master_source_pin_rejects_previous_ce_and_accepts_only_successor(self):
        path = 'physical/s81_ph_views/collective/composition_split3cr.json'
        manifest = json.loads((self.root / path).read_text())
        manifest['per_master_source_commits'] = {'dsfd_coll_ce': 'f' * 40}
        self.write(path, manifest)
        binding = D.collective_credit_binding(self.root)
        self.assertNotIn('dsfd_coll_ce', binding['tile_bindings'])
        self.assertEqual(len(binding['tile_bindings']), 3)
        vp, receipt = self.receipts['dsfd_coll_ce']
        successor = copy.deepcopy(receipt)
        successor['source_commit'] = 'f' * 40
        self.write(vp, successor)
        self.assertFalse(D.collective_credit_binding(self.root)['problems'])
        for bad in ('', 'wrong-source', 1):
            manifest['per_master_source_commits']['dsfd_coll_ce'] = bad
            self.write(path, manifest)
            self.assertNotIn('dsfd_coll_ce', D.collective_credit_binding(self.root)['tile_bindings'])
        manifest['per_master_source_commits'] = {'unknown_master': 'f' * 40}
        self.write(path, manifest)
        self.assertFalse(D.collective_credit_binding(self.root)['tile_bindings'])

    def test_credit_recipe_preserves_full_width_lane_groups_and_mirrored_faces(self):
        shutil.copytree(D.ROOT / 'physical/s81_ph_views/ports/contract_split3',
                        self.root / 'physical/s81_ph_views/ports/contract_split3')
        spec, recipe = A.collective_credit_recipe(self.root)
        self.assertEqual(recipe['glue_bundles'], 87)
        self.assertEqual(recipe['glue_bits'], 16050)
        self.assertEqual(len(recipe['instances']), 11)
        self.assertTrue(all(n['length_um'] < 0.5 for n in recipe['nets']))
        for side, lanes in [('w', [1, 2]), ('e', [5, 6])]:
            for group, lane in enumerate(lanes):
                net = next(n for n in recipe['nets'] if n['launch'] == 'u_ce.' + side + 'lo_d'
                           and n['capture'] == f'g_lane[{lane}].g_{side}.u_l.lo_d')
                self.assertEqual(net['bits'], 553)
                self.assertEqual(net['launch_bits'][0], f'{side}lo_d[{group*553}]')
                self.assertEqual(net['capture_bits'][0], 'lo_d[0]')
        lane = self.root / 'physical/s81_ph_views/ports/contract_split3/dsfd_coll_lane_w/ports.json'
        bad = json.loads(lane.read_text())
        bad['ports']['lo_d']['direction'] = 'output'
        lane.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError, 'bad seam shape/direction'):
            A.collective_credit_recipe(self.root)

    def test_old_assembly_is_rejected_then_exact_credit_assembly_selected(self):
        binding = D.collective_credit_binding(self.root)
        self.assertFalse(binding['problems'])
        old_dir = self.root / 'physical/assembled_old'
        self.write('physical/assembled_old/assembled.json', dict(slab='dsfd_sp_collective', variant='legacy'))
        candidates = {c: {'dsfd_sp_collective': (old_dir / ('dsfd_sp_collective_' + c + '.lib'), 'assembled')}
                      for c in ('ss', 'tt', 'ff')}
        D.credit_assembled_views(self.root, binding, candidates)
        self.assertFalse(binding['qualified'])
        self.assertEqual(len(binding['problems']), 3)
        binding = D.collective_credit_binding(self.root)
        manifest = json.loads((self.root / 'physical/s81_ph_views/collective/composition_split3cr.json').read_text())
        q = dict(status='PASS', variant='split3cr', tile_bindings=binding['tile_bindings'], clock_binding=binding['clock_binding'], clock_period_ps=833.333, setup_uncertainty_ps=60, hold_uncertainty_ps=25, drc=0, tt_setup_ps=12, ff_hold_ps=3, clock_sinks=[r['inst'] + '/ck' for r in manifest['instances']], corner_sta='results/glue_corner.json')
        q.update(source_latency_policy='option1', clock_root=dict(instance='u_ck', x_um=0, y_um=1400), clock_taps={r['inst']: dict(tt_source_latency_ps=500, ff_source_latency_ps=400) for r in manifest['instances']})
        self.write('results/measured_glue.json', q)
        self.write('results/glue_corner.json', {k: dict(worst_slack_ps=v, errors=[], odb_sha256='a'*64, spef_sha256='b'*64, sdc_sha256='c'*64) for k,v in [('setup_tt',12), ('hold_ff',3)]})
        qhash = hashlib.sha256((self.root / 'results/measured_glue.json').read_bytes()).hexdigest()
        assembly = dict(slab='dsfd_sp_collective', variant='split3cr', tile_bindings=binding['tile_bindings'], clock_binding=binding['clock_binding'],
                        physical_qualification=dict(status='PASS', evidence='results/measured_glue.json', sha256=qhash),
                        glue_worst_ps=dict(tt_setup_bal=1, ff_hold_bal=2),
                        corners={c: dict(libs=dict({m: r['libs'][c] for m, r in binding['tile_bindings'].items()}, dsfd_coll_ck=binding['clock_binding']['libs'][c]))
                                 for c in ('ss', 'tt', 'ff')})
        self.write('physical/assembled_credit/assembled.json', assembly)
        for c in candidates:
            (self.root / 'physical/assembled_credit' / ('dsfd_sp_collective_' + c + '.lib')).write_text('cell (dsfd_sp_collective) {}')
        D.credit_assembled_views(self.root, binding, candidates)
        self.assertTrue(binding['qualified'])
        self.assertTrue(all('assembled_credit' in str(v['dsfd_sp_collective'][0]) for v in candidates.values()))
        self.assertEqual(D.PARTS['dsfd_sp_collective'], ('dsfd_coll_lane_w', 'dsfd_coll_core', 'dsfd_coll_ck'))
        assembly['glue_worst_ps']['ff_hold_bal'] = float('nan')
        self.write('physical/assembled_credit/assembled.json', assembly)
        binding = D.collective_credit_binding(self.root)
        D.credit_assembled_views(self.root, binding, candidates)
        self.assertFalse(binding['qualified'])


if __name__ == '__main__':
    unittest.main()
