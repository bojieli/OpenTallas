#!/usr/bin/env python3
"""Short proposal/guard checks only; no Verilator elaboration or C++ compile."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import full_sm_rf_verilator_gate as G
PROPOSAL=G.ROOT/'results/uarch/full_sm_rf_verilator_review_20261002/proposal_final.json'

class VerilatorProposal(unittest.TestCase):
    def test_actual_source_and_runner_pins(self):
        p=json.loads(PROPOSAL.read_text())
        self.assertEqual(p['runner_sha256'],G.sha(G.__file__))
        for path,h in p['source_sha256'].items():
            self.assertEqual(G.sha(G.ROOT/path),h)
            self.assertEqual(hashlib.sha256(subprocess.check_output(['git','show',G.BASE+':'+path],cwd=G.ROOT)).hexdigest(),h)
        self.assertEqual(p['unchanged_hardware']['lanes'],128)
        self.assertFalse(p['simulation_scope']['arithmetic_blackboxes'])
        self.assertFalse(p['simulation_scope']['behavioral_FP_substitution'])
    def test_no_GO_cannot_launch(self):
        with patch.object(G.subprocess,'Popen',side_effect=AssertionError('unauthorized launch')):
            with self.assertRaisesRegex(ValueError,'fresh committed parent GO'):
                G.execute(PROPOSAL,None,Path('/tmp/no-verilator-run-authorized'))
    def test_GO_exact_bindings(self):
        p=json.loads(PROPOSAL.read_text())
        go=dict(schema='opentallas.full-sm-service.verilator-GO.v1',admitted=True,
                proposal_sha256=G.sha(PROPOSAL),source_commit='reviewed-source',caps=p['caps'],unit='new-parent-unit.service')
        G.validate_go(go,p,PROPOSAL,'reviewed-source')
        with self.assertRaisesRegex(ValueError,'proposal/source pin mismatch'):
            G.validate_go(go,p,PROPOSAL,'other-source')
        go['caps']=dict(p['caps'],build_jobs=3)
        with self.assertRaisesRegex(ValueError,'exact caps'):
            G.validate_go(go,p,PROPOSAL,'reviewed-source')
    def test_separate_bounded_actual_phases(self):
        phases=G.commands('/tmp/reviewed-fresh-output')
        self.assertEqual([x[0] for x in phases],['verilate','cxx_build','actual_sim','storage_compile','storage_sim'])
        argv=phases[0][2]
        self.assertIn('--timing',argv);self.assertIn('--main',argv);self.assertIn('--exe',argv)
        self.assertNotIn('--build',argv);self.assertNotIn('--binary',argv)
        self.assertNotIn('--bbox-unsup',argv);self.assertNotIn('--bbox-sys',argv)
        self.assertEqual([v for v in argv if v.endswith('.sv')],[str(G.ROOT/p) for p in G.SOURCES])
        self.assertNotIn('arithmetic_blackboxes.sv',' '.join(argv))
        self.assertIn('-j2',phases[1][2]);self.assertIn('OPT_FAST=-O0',phases[1][2])
        self.assertLess(sum(x[1] for x in phases)+5*G.CAPS['kill_grace_s'],G.CAPS['whole_wall_s']-30)
    def test_sampled_output_size_and_toolchain_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'a').write_bytes(b'1234');(p/'sub').mkdir();(p/'sub/b').write_bytes(b'56')
            self.assertEqual(G.directory_bytes(p),6)
        p=json.loads(PROPOSAL.read_text())
        self.assertTrue(p['toolchain']['verilator_version'].startswith('Verilator 5.050 '))
        for path,h in p['toolchain']['files_sha256'].items():self.assertEqual(G.sha(path),h,path)
    def test_hardware_and_prior_model_unchanged(self):
        p=json.loads(PROPOSAL.read_text());pin=p['model_pin']
        self.assertEqual(G.sha(G.ROOT/pin['path']),pin['sha256'])
        self.assertFalse(p['build_GO']);self.assertFalse(p['unchanged_hardware']['area_changed'])
        self.assertFalse(p['unchanged_hardware']['token_model_changed'])
        self.assertEqual(p['elaboration_cost']['replicated_prefix_generate_bit_sites'],152320)
        self.assertEqual(p['prior_failure']['verdict'],'FAIL exit=124')

if __name__=='__main__':unittest.main()
