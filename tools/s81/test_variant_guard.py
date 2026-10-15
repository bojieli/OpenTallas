#!/usr/bin/env python3
"""Actual elaboration positives and source/parameter/hierarchy negative proofs."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import variant_guard as V


class VariantGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Variant guard test')
        (self.repo / 'top.sv').write_text('''module child #(parameter N=1)(input [N-1:0] a, output [N-1:0] y);
assign y=~a; endmodule
module top #(parameter N=1)(input [N-1:0] a, output [N-1:0] y);
child #(.N(N)) u_child(a,y); endmodule
''')
        self.git('add', 'top.sv')
        self.git('commit', '-qm', 'source')
        self.commit = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def actual(self, params=None):
        return dict(commit=self.commit, top='top', sources=['top.sv'], params=params or {})

    def job(self, params=None, commit=None, top='top', sources=None):
        commit = commit or self.commit
        cmd = 'tools/route_mtp.sh label ' + top
        for source in sources or ['top.sv']:
            cmd += ' --source ' + source
        for key, value in (params or {}).items():
            cmd += f' --param {key}={value}'
        return dict(commit_full=commit, spec=dict(block=top, source=dict(commit=commit), stages=dict(route=dict(cmd=cmd))))

    def test_identical_source_parameters_and_hierarchy_pass(self):
        result = V.compare_variants(self.actual(), self.job(), repo=self.repo)
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertEqual(result['actual']['reachable_modules'], 2)
        self.assertFalse(result['native_qualified'])

    def test_default_and_explicit_equal_parameter_pass(self):
        result = V.compare_variants(self.actual(), self.job({'N': 1}), repo=self.repo)
        self.assertEqual(result['verdict'], 'PASS', result)

    def test_changed_child_is_rejected_with_same_top_ports(self):
        text = (self.repo / 'top.sv').read_text().replace('assign y=~a', 'assign y=a')
        (self.repo / 'top.sv').write_text(text)
        self.git('commit', '-qam', 'child changed')
        actual = dict(self.actual(), commit=self.git('rev-parse', 'HEAD'))
        result = V.compare_variants(actual, self.job(), repo=self.repo)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('hierarchy_sha256 mismatch', result['errors'])
        self.assertIn('transitive source contents mismatch', result['errors'])

    def test_parameter_changes_derived_child_hierarchy(self):
        one = V.elaborate(self.actual({'N': 1}), self.repo)
        two = V.elaborate(self.actual({'N': 2}), self.repo)
        self.assertNotEqual(one['hierarchy_sha256'], two['hierarchy_sha256'])
        self.assertNotEqual(one['effective_parameters'], two['effective_parameters'])

    def test_missing_job_or_source_fails_closed(self):
        for actual, job in ((self.actual(), {}), (dict(self.actual(), sources=['absent.sv']), self.job())):
            result = V.compare_variants(actual, job, repo=self.repo)
            self.assertEqual(result['verdict'], 'FAIL', result)
            self.assertTrue(result['errors'])

    def test_analysis_override_cannot_replace_synthesis_recipe(self):
        job = self.job({'N': 1})
        job['spec']['rtl_boundary'] = dict(top='top', sources=['top.sv'], params={'N': 2})
        result = V.compare_variants(self.actual({'N': 2}), job, repo=self.repo)
        self.assertEqual(result['verdict'], 'FAIL', result)
        self.assertEqual(result['bound_parameters']['N'], 1)

    def test_unresolved_child_cannot_pass(self):
        (self.repo / 'top.sv').write_text('module top(input a,output y); absent u(a,y); endmodule')
        self.git('commit', '-qam', 'unresolved child')
        self.commit = self.git('rev-parse', 'HEAD')
        result = V.compare_variants(self.actual(), self.job(), repo=self.repo)
        self.assertEqual(result['verdict'], 'FAIL', result)
        self.assertIn('elaboration failed', ' '.join(result['errors']))

    def test_preprocessor_variant_changes_actual_hierarchy(self):
        (self.repo / 'top.sv').write_text('''module top(input a,output y);
`ifdef INVERT
assign y=~a;
`else
assign y=a;
`endif
endmodule
''')
        self.git('commit', '-qam', 'conditional implementation')
        self.commit = self.git('rev-parse', 'HEAD')
        result = V.compare_variants(dict(self.actual(), defines=['INVERT']), self.job(), repo=self.repo)
        self.assertEqual(result['verdict'], 'FAIL', result)
        self.assertIn('hierarchy_sha256 mismatch', result['errors'])

    def test_archived_kit_parameters_and_defines_are_used(self):
        kit = self.repo / 'kit'
        kit.mkdir()
        (kit / 'kit.env').write_text("TOP=top\nSRCS='top.sv'\nPARAMS=(--param N=2)\nEXTRA=(--orfs-var 'VERILOG_DEFINES=-DSYNTHESIS -DGUARDED')\n")
        self.git('add', 'kit/kit.env')
        self.git('commit', '-qm', 'archived kit')
        self.commit = self.git('rev-parse', 'HEAD')
        job = self.job()
        job['spec']['stages']['route']['cmd'] = 'bash tools/ref_tile/ref_route.sh kit/kit.env LABEL RUN'
        recipe = V.job_recipe(job, self.repo)
        self.assertEqual(recipe['params'], {'N': '2'})
        self.assertEqual(recipe['defines'], ['GUARDED'])
        result = V.compare_variants(dict(self.actual({'N': 2}), defines=['GUARDED']), job, repo=self.repo)
        self.assertEqual(result['verdict'], 'PASS', result)

    def test_actual_dsfd_sp_vm_defaults_do_not_match_4_2_view(self):
        # Use the actual Git-pinned production wrapper, not a substitute module.
        repo = Path(__file__).resolve().parents[2]
        commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        source = 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv'
        actual = dict(commit=commit, top='dsfd_sp_vm', sources=[source], params={})
        job = self.job({'READ_PIPE': 4, 'CAP_PIPE': 2}, commit=commit, top='dsfd_sp_vm', sources=[source])
        result = V.compare_variants(actual, job, repo=repo)
        self.assertEqual(result['verdict'], 'FAIL', result)
        # main's wrapper now also carries WSCATTER_PIPE (default 0); the guard reports every actual parameter
        self.assertEqual({k: v for k, v in result['actual_parameters'].items() if k in ('READ_PIPE', 'CAP_PIPE')},
                         {'READ_PIPE': 0, 'CAP_PIPE': 0})
        self.assertEqual(result['actual_parameters'].get('WSCATTER_PIPE', 0), 0)
        self.assertEqual(result['bound_parameters'], {'READ_PIPE': 4, 'CAP_PIPE': 2})
        self.assertIn('effective_parameters mismatch', ' '.join(result['errors']))


if __name__ == '__main__':
    unittest.main()
