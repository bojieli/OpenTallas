"""Focused cache-provenance rejection tests; no exhaustive result is fabricated."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('hash_parallel_gate.py'))
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)


class CacheProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inputs = ['rtl/block.sv', gate.BENCH, gate.HARNESS, gate.GATE]
        for s in self.inputs:
            p = self.root / s; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s)
        self.log = self.root / 'exhaustive.log'; self.log.write_text(gate.SUMMARY + '\nPASS\n')
        self.proof = self.root / 'exhaustive.json'
        self.expected = self.snapshot()
        self.record = dict(schema=gate.SCHEMA, **copy.deepcopy(self.expected),
                           sources_unchanged=True, compile_returncode=0, simulation_returncode=0,
                           log_sha256=gate.sha(self.log))
        self.save()

    def snapshot(self):
        return dict(sources={s: gate.sha(self.root / s) for s in self.inputs},
                    compiler_inputs=[gate.BENCH, 'rtl/block.sv'],
                    recipe={'compiler_args': ['-g2012', '-s', gate.TOP]},
                    tools={'compiler': {'sha256': 'compiler-pin', 'version': 'version-pin'}})

    def save(self):
        self.proof.write_text(json.dumps(self.record))

    def test_matching_pins_and_log_accepted(self):
        self.assertEqual(gate.validate_cached(self.proof, self.log, self.expected), self.record)

    def test_stale_rtl_bench_and_gate_sources_rejected(self):
        for s in self.inputs:
            with self.subTest(source=s):
                p = self.root / s; old = p.read_text(); p.write_text(old + '\nstale change')
                with self.assertRaisesRegex(ValueError, 'sources'):
                    gate.validate_cached(self.proof, self.log, self.snapshot())
                p.write_text(old)

    def test_changed_log_with_pass_text_rejected(self):
        self.log.write_text(self.log.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'log digest'):
            gate.validate_cached(self.proof, self.log, self.expected)

    def test_incomplete_or_extra_source_set_rejected(self):
        for extra in (False, True):
            with self.subTest(extra=extra):
                self.record['sources'] = dict(self.expected['sources'])
                if extra:
                    self.record['sources']['untracked.sv'] = 'arbitrary'
                else:
                    self.record['sources'].pop('rtl/block.sv')
                self.save()
                with self.assertRaisesRegex(ValueError, 'sources'):
                    gate.validate_cached(self.proof, self.log, self.expected)

    def test_changed_compile_order_recipe_and_tools_rejected(self):
        for field in ('compiler_inputs', 'recipe', 'tools'):
            with self.subTest(field=field):
                expected = copy.deepcopy(self.expected); expected[field] = {'changed': True}
                with self.assertRaisesRegex(ValueError, field):
                    gate.validate_cached(self.proof, self.log, expected)

    def test_failed_or_unstable_execution_rejected(self):
        for key, val in [('compile_returncode', 1), ('simulation_returncode', 1), ('sources_unchanged', False)]:
            with self.subTest(key=key):
                old = self.record[key]; self.record[key] = val; self.save()
                with self.assertRaises(ValueError):
                    gate.validate_cached(self.proof, self.log, self.expected)
                self.record[key] = old

    def test_bare_log_cli_rejected_before_compilation(self):
        output = self.root / 'output.json'
        r = subprocess.run([sys.executable, str(Path(gate.__file__)), '--output', str(output),
                            '--baseline', str(self.root / 'nonexistent-baseline.json'),
                            '--exhaustive-log', str(self.log)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('source-pinned --exhaustive-record', r.stderr)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
