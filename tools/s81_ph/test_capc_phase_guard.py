"""Adoption checks reject stale routed evidence and actual phase failures."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/s81_ph'), str(ROOT / 'tools/ref_tile')]
import capc_phase_guard as guard

class PhaseGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.view = base / 'dsfd_capt_x8_dual'; self.view.mkdir()
        self.state = base / 'state'; (self.state / 'jobs').mkdir(parents=True)
        commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'bc2c93f92'], text=True).strip()
        binding = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':physical/ref_tile/dsfd_capt_x8_dual/gate_result.json'], text=True))['source_binding']
        self.job = dict(status='CLOSED', commit_full=commit, host='ot-epyc1tb', run='/fixture/route-job')
        self.job_path = self.state / 'jobs/fixture.json'; self.job_path.write_text(json.dumps(self.job))
        ins = dict(parasitics='spef', base='/fixture/route-job/routes/run/base', db='6_final.odb', clock_measurements={p: {c: {'boundary': {'mean': r}} for c in ('tt', 'ff')} for p, r in [('ck', 174.3), ('ckv', 204.6)]})
        (self.view / 'insertion.json').write_text(json.dumps(ins))
        for name in ['abstract.json', 'dsfd_capt_x8_dual.lef'] + ['dsfd_capt_x8_dual_'+c+'.lib' for c in ('tt', 'ff', 'ss')]:
            (self.view / name).write_text('isolated validation fixture\n')
        for name in ('audit.tcl', 'audit.log'): (self.view / name).write_text('isolated validation fixture\n')
        self.receipt = dict(schema='opentallas.capture.routed_phase_audit.v1', job='fixture', source_commit=commit, source_binding=binding,
            view_sha256={p.name: guard.sha(p) for p in self.view.iterdir() if p.name not in ('audit.tcl','audit.log')},
            routed_db=dict(path=ins['base']+'/6_final.odb', sha256='db-fixture-hash'), phase='pin_source_latency_minus_boundary_R', parasitics='spef',
            period_ps=dict(core=833.333, serial=1111.110667), setup_uncertainty_ps=60, hold_uncertainty_ps=25, cross_domain_exceptions=[],
            clock_R_ps={c: dict(ck=174.3, ckv=204.6) for c in ('tt','ff')},
            paths=[dict(corner=c, launch=a, capture=b, sense=s, startpoint='actual/Q', endpoint='actual/D', slack_ps=1.0) for c in ('tt','ff') for a,b in [('core','serial'),('serial','core')] for s in ('max','min')],
            audit_sha256={n: guard.sha(self.view/n) for n in ('audit.tcl','audit.log')})

    def check(self, receipt=None, digest='db-fixture-hash'):
        (self.view / 'routed_phase_audit.json').write_text(json.dumps(receipt or self.receipt))
        return guard.validate(self.view, self.state, db_hash=lambda _: digest)

    def test_valid(self): self.check()

    def test_rejects_failed_crossing(self):
        r=copy.deepcopy(self.receipt); r['paths'][7]['slack_ps']=-1.738
        with self.assertRaisesRegex(ValueError,'timing fails'): self.check(r)

    def test_rejects_incomplete_crossings(self):
        r=copy.deepcopy(self.receipt); r['paths'].pop()
        with self.assertRaisesRegex(ValueError,'both directions'): self.check(r)

    def test_rejects_changed_db(self):
        with self.assertRaisesRegex(ValueError,'DB changed'): self.check(digest='different')

    def test_rejects_stale_R(self):
        r=copy.deepcopy(self.receipt); r['clock_R_ps']['ff']['ckv']+=1
        with self.assertRaisesRegex(ValueError,'R mismatch'): self.check(r)

    def test_rejects_nonclosed_producer(self):
        self.job['status']='RUNNING'; self.job_path.write_text(json.dumps(self.job))
        with self.assertRaisesRegex(ValueError,'not CLOSED'): self.check()

    def test_rejects_changed_view(self):
        (self.view/'dsfd_capt_x8_dual_tt.lib').write_text('changed')
        with self.assertRaisesRegex(ValueError,'view changed'): self.check()

    def test_rejects_route_periods(self):
        r=copy.deepcopy(self.receipt); r['period_ps']=dict(core=770,serial=1026.666667)
        with self.assertRaisesRegex(ValueError,'nominal'): self.check(r)

if __name__ == '__main__': unittest.main()
