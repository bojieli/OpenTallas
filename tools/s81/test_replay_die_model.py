#!/usr/bin/env python3
"""Source, recipe and actual emitter option mutations must refuse model reuse."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import cloudpickle
import replay_die_model as R


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'tools').mkdir()
        self.generator = self.root / 'tools/dsrom_s81_fulldie.py'
        self.generator.write_text("""import argparse
DIE='layer1'
def die_options(parser):
 parser.add_argument('--die', default='layer1'); return parser
def apply_options(options): pass
def build(): raise AssertionError('construction was repeated')
def finalize_r8(model): raise AssertionError('finalization was repeated')
""")
        (self.root / 'SOURCE_SHA').write_text('fixed-source\n')
        (self.root / 'recipe.opts').write_text('--die layer1\n')
        self.capture = self.root / 'model.pickle'
        provenance = dict(source_root=str(self.root), source_commit='fixed-source',
             generator_sha256=R.digest(self.generator), recipe_path='recipe.opts',
             recipe_sha256=R.digest(self.root / 'recipe.opts'), scope='test only')
        self.capture.write_bytes(cloudpickle.dumps(dict(model={'pdir': {'leaf': 7}},
                 state={'DIE': 'layer1'}, provenance=provenance)))
        self.meta = dict(provenance, capture_sha256=R.digest(self.capture))
        self.capture.with_suffix('.json').write_text(json.dumps(self.meta))
        (self.root / 'tools/emitter.py').write_text("""import sys
import dsrom_s81_fulldie as G
G.apply_options(G.die_options(__import__('argparse').ArgumentParser()).parse_args(sys.argv[1:]))
assert G.finalize_r8(G.build()) == {'leaf': 7}
print('EXACT_MODEL_REUSED')
""")

    def test_valid_identity(self):
        R.validate(self.root, self.capture, self.meta)

    def test_each_source_mutation_refuses(self):
        for path in (self.generator, self.root / 'SOURCE_SHA', self.root / 'recipe.opts', self.capture):
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.assertRaises(ValueError, msg=str(path)):
                R.validate(self.root, self.capture, self.meta)
            path.write_bytes(original)
        with self.assertRaises(ValueError):
            R.validate(self.root.parent, self.capture, self.meta)

    def test_emitter_reuses_and_wrong_options_refuse(self):
        cmd = [sys.executable, str(Path(R.__file__)), '--source', str(self.root),
               '--capture', str(self.capture), '--script', 'tools/emitter.py', '--', '--die']
        good = subprocess.run(cmd + ['layer1'], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn('EXACT_MODEL_REUSED', good.stdout)
        bad = subprocess.run(cmd + ['head'], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn('captured die options differ', bad.stderr)
        self.assertNotIn('EXACT_MODEL_REUSED', bad.stdout)


if __name__ == '__main__':
    unittest.main()
