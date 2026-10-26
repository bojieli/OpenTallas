import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import view_identity as V


class ActualDieIdentity(unittest.TestCase):
    def test_actual_defaults_replace_candidate_parameters_and_defines(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'vm.sv'
            source.write_text('module vm; endmodule')
            (root / 'closed.json').write_text('{}')
            recipes = {'vm': dict(commit='a'*40, sources=['vm.sv'],
                                  params={'READ_PIPE':4,'CAP_PIPE':2}, defines=['CANDIDATE'])}
            def compare(actual, bound, **kwargs):
                self.assertEqual(actual['params'], {})
                self.assertEqual(actual['defines'], ['ACTUAL'])
                return dict(verdict='FAIL', errors=['actual0/0 differs from routed4/2'])
            with patch.object(V.VG,'source_bundle',return_value={'vm.sv':source.read_text()}), \
                 patch.object(V.VG,'compare_variants',side_effect=compare):
                r=V.attest(['vm'], recipes, {'vm':{'job':'closed'}}, {},
                           source_root=root, manifest_sources=[source], manifest_defines=['ACTUAL'], jobs_root=root)
            self.assertEqual(r['verdict'],'FAIL')
            self.assertIn('actual0/0',r['masters']['vm']['errors'][0])

    def test_unselected_or_modified_sources_cannot_attest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=root/'real.sv';source.write_text('actual')
            recipes={'tile':dict(commit='a'*40,sources=['other.sv'])}
            r=V.attest(['tile'],recipes,{}, {},source_root=root,manifest_sources=[source],
                       manifest_defines=[],jobs_root=root)
            self.assertEqual(r['verdict'],'FAIL')
            recipes['tile']['sources']=['real.sv']
            with patch.object(V.VG,'source_bundle',return_value={'real.sv':'stale'}):
                r=V.attest(['tile'],recipes,{}, {},source_root=root,manifest_sources=[source],
                           manifest_defines=[],jobs_root=root)
            self.assertIn('bytes differ',r['masters']['tile']['errors'][0])

    def test_duplicate_actual_top_cannot_select_a_convenient_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); a=root/'a.sv'; b=root/'b.sv'
            a.write_text('module tile; endmodule'); b.write_text('module tile; endmodule')
            recipes={'tile':dict(commit='a'*40,sources=['a.sv'])}
            with patch.object(V.VG,'source_bundle',return_value={'a.sv':a.read_text()}):
                r=V.attest(['tile'],recipes,{}, {},source_root=root,manifest_sources=[a,b],
                           manifest_defines=[],jobs_root=root)
            self.assertIn('ambiguous',r['masters']['tile']['errors'][0])

    def test_missing_generated_recipe_is_explicit_failure(self):
        r=V.attest(['generated'],{}, {},{},source_root='.',manifest_sources=[],manifest_defines=[],jobs_root='.')
        self.assertEqual(r['verdict'],'FAIL')
        self.assertIn('absent',r['masters']['generated']['errors'][0])

if __name__=='__main__': unittest.main()
