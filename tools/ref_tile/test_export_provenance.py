"""Exercise actual subprocess transformation, preserving exporter evidence on failure."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import child_lint
import export_provenance as ep

LEF = '''VERSION 5.8 ;
MACRO demo
  ORIGIN 0 0 ;
  SIZE 10 BY 10 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 1 0.1 1.1 ;
    END
  END a
  OBS
    LAYER M4 ;
      RECT 0 1 0.2 1.1 ;
  END
END demo
END LIBRARY
'''

class ExportProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.lef = self.out / 'demo.lef'
        self.lef.write_text(LEF)
        self.manifest = {'ok': True, 'name': 'demo', 'files': {'demo.lef': ep.sha(self.lef)}}
        ep.write_json(self.out / 'abstract.json', self.manifest)
        self.raw_record = (self.out / 'abstract.json').read_bytes()
        self.lint = Mock(parse_lef=child_lint.parse_lef)
        self.lint.lint.return_value = {'verdict': 'PASS', 'fails': []}
        self.helper = Path(__file__).resolve().parents[1] / 'hier_contract/abstract_pin_stub.py'

    def run_export(self, helper=None):
        return ep.finalize(self.out, 'demo', helper or self.helper, self.lint)

    def assert_failed(self):
        self.assertFalse(json.loads((self.out / 'abstract.json').read_text())['ok'])
        self.assertEqual(self.lef.read_text(), LEF)
        self.assertEqual((self.out / 'provenance/view_export.abstract.json').read_bytes(), self.raw_record)

    def fake_helper(self, code):
        helper = self.out / 'helper.py'
        helper.write_text('import pathlib, sys\n' + code)
        return helper

    def test_normal_actual_helper_final_hash_and_raw_evidence(self):
        self.assertEqual(self.run_export()['verdict'], 'PASS')
        manifest = json.loads((self.out / 'abstract.json').read_text())
        self.assertTrue(manifest['ok'])
        self.assertEqual(manifest['files']['demo.lef'], ep.sha(self.lef))
        self.assertNotEqual(manifest['files']['demo.lef'], self.manifest['files']['demo.lef'])
        self.assertEqual((self.out / 'provenance/raw/demo.lef').read_text(), LEF)
        self.assertEqual((self.out / 'provenance/view_export.abstract.json').read_bytes(), self.raw_record)
        record = json.loads((self.out / manifest['export_provenance']['transformation']).read_text())
        self.assertEqual(record['helper']['sha256'], ep.sha(self.helper))
        self.assertEqual(record['status'], 'PASS')
        self.assertEqual(len(list(self.out.glob('*.lef'))), 1)

    def test_raw_hash_mismatch(self):
        self.lef.write_text(LEF + '\n')
        self.assertEqual(self.run_export()['verdict'], 'FAIL')
        self.assertFalse(json.loads((self.out / 'abstract.json').read_text())['ok'])
        self.lint.lint.assert_not_called()

    def test_helper_failure(self):
        self.assertEqual(self.run_export(self.fake_helper('sys.exit(7)\n'))['verdict'], 'FAIL')
        self.assert_failed()
        self.lint.lint.assert_not_called()

    def test_geometry_and_pin_mutants(self):
        mutations = [('SIZE 10 BY 10', 'SIZE 11 BY 10'), ('ORIGIN 0 0', 'ORIGIN 1 0'),
                     ('PIN a', 'PIN b'), ('DIRECTION INPUT', 'DIRECTION OUTPUT'),
                     ('USE SIGNAL', 'USE CLOCK'), ('0.1 1.1', '0.11 1.1')]
        for old, new in mutations:
            with self.subTest(new=new), tempfile.TemporaryDirectory() as d:
                out = Path(d)
                (out/'demo.lef').write_text(LEF)
                ep.write_json(out/'abstract.json', self.manifest)
                helper = self.fake_helper(f"pathlib.Path(sys.argv[2]).write_text(pathlib.Path(sys.argv[1]).read_text().replace({old!r}, {new!r}))\n")
                self.assertEqual(ep.finalize(out, 'demo', helper, self.lint)['verdict'], 'FAIL')
                self.assertEqual((out/'demo.lef').read_text(), LEF)
                self.assertFalse(json.loads((out/'abstract.json').read_text())['ok'])

    def test_transform_obs_over_pg_crossing_fails(self):
        # FABLE-CLOSURE-0910 lever 7: a finalize transform (via shadow, pocket closing) that covers the M5 PG stripes
        # with M6 OBS is refused even when child_lint passes
        pg = LEF.replace("  OBS\n", "  PIN VDD\n    DIRECTION INOUT ;\n    USE POWER ;\n    PORT\n      LAYER M5 ;\n"
                         "        RECT 5 0 5.12 10 ;\n    END\n  END VDD\n  OBS\n")
        self.lef.write_text(pg)
        ep.write_json(self.out / 'abstract.json', dict(self.manifest, files={'demo.lef': ep.sha(self.lef)}))
        helper = self.fake_helper("t = pathlib.Path(sys.argv[1]).read_text()\n"
                                  "pathlib.Path(sys.argv[2]).write_text(t.replace('  END\\nEND demo', "
                                  "'    LAYER M6 ;\\n      RECT 0 0 10 8 ;\\n  END\\nEND demo'))\n")
        result = self.run_export(helper)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('PG crossing preflight FAIL', result['fails'][0])
        self.assertEqual(self.lef.read_text(), pg)
        self.assertEqual(self.run_export_fresh(pg)['verdict'], 'PASS')

    def run_export_fresh(self, text):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / 'demo.lef').write_text(text)
            ep.write_json(out / 'abstract.json', dict(self.manifest, files={'demo.lef': ep.sha(out / 'demo.lef')}))
            return ep.finalize(out, 'demo', self.helper, self.lint)

    def test_lint_failure_no_final_publication(self):
        self.lint.lint.return_value = {'verdict': 'FAIL', 'fails': ['PG fixture']}
        result = self.run_export()
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('PG fixture', result['fails'][0])
        self.assert_failed()

    def test_exporter_nonzero_stops_before_helper_or_clock_measurement(self):
        import ref_tile
        kit = self.out / 'kit'
        kit.mkdir()
        (kit / 'floorplan.json').write_text(json.dumps({'top': 'demo'}))
        with patch.object(ref_tile, 'ROOT', self.out), patch('subprocess.run', return_value=Mock(returncode=9)) as run:
            self.assertEqual(ref_tile.export(str(self.out / 'orfs'), 'kit', str(self.out / 'views'), []), 1)
        self.assertEqual(run.call_count, 1)
        self.assertFalse((self.out / 'views/provenance').exists())

    def test_exporter_failed_manifest(self):
        self.manifest['ok'] = False
        ep.write_json(self.out/'abstract.json', self.manifest)
        self.assertEqual(self.run_export()['verdict'], 'FAIL')
        self.lint.lint.assert_not_called()

if __name__ == '__main__':
    unittest.main()
