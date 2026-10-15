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
        self.capture = self.root.parent / (self.root.name + '-model.pickle')
        self.addCleanup(self.capture.unlink, missing_ok=True)
        self.addCleanup(self.capture.with_suffix('.json').unlink, missing_ok=True)
        provenance = dict(source_root=str(self.root), source_commit='fixed-source',
             generator_sha256=R.digest(self.generator), recipe_path='recipe.opts',
             recipe_sha256=R.digest(self.root / 'recipe.opts'), scope='test only')
        self.capture.write_bytes(cloudpickle.dumps(dict(model={'pdir': {'leaf': 7}},
                 state={'DIE': 'layer1'}, provenance=provenance)))
        (self.root / 'tools/geometry_helper.py').write_text('actual_height = 41\n')
        (self.root / 'macro.lef').write_text('SIZE 20 BY 30 ;\n')
        (self.root / 'contract.json').write_text('{"width":20}\n')
        files = []
        for path in (self.generator, self.root / 'recipe.opts', self.root / 'tools/geometry_helper.py', self.root / 'macro.lef', self.root / 'contract.json'):
            payload = path.read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(payload)).encode() + bytes([0]) + payload).hexdigest()
            files.append(dict(path=str(path.relative_to(self.root)), mode='100644', git_blob=blob, bytes=len(payload)))
        self.manifest = self.root.parent / (self.root.name + '-source_manifest.json')
        self.addCleanup(self.manifest.unlink, missing_ok=True)
        self.manifest.write_text(json.dumps(dict(source_commit='fixed-source',
              git_tree='fixed-tree', files=files, external_files=[])))
        self.meta = dict(provenance, capture_sha256=R.digest(self.capture),
              source_manifest_path=str(self.manifest),
              source_manifest_sha256=R.digest(self.manifest))
        self.capture.with_suffix('.json').write_text(json.dumps(self.meta))
        (self.root / 'tools/emitter.py').write_text("""import sys
import dsrom_s81_fulldie as G
G.apply_options(G.die_options(__import__('argparse').ArgumentParser()).parse_args(sys.argv[1:]))
assert G.finalize_r8(G.build()) == {'leaf': 7}
print('EXACT_MODEL_REUSED')
""")
        data = json.loads(self.manifest.read_text())
        path = self.root / 'tools/emitter.py'
        payload = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(payload)).encode() + bytes([0]) + payload).hexdigest()
        data['files'].append(dict(path='tools/emitter.py', mode='100644', git_blob=blob, bytes=len(payload)))
        self.manifest.write_text(json.dumps(data))
        self.meta['source_manifest_sha256'] = R.digest(self.manifest)
        self.capture.with_suffix('.json').write_text(json.dumps(self.meta))

    def test_valid_identity(self):
        R.validate(self.root, self.capture, self.meta)

    def test_each_source_mutation_refuses(self):
        for path in (self.generator, self.root / 'SOURCE_SHA', self.root / 'recipe.opts', self.capture, self.manifest, self.root / 'tools/geometry_helper.py', self.root / 'macro.lef', self.root / 'contract.json'):
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.assertRaises(ValueError, msg=str(path)):
                R.validate(self.root, self.capture, self.meta)
            path.write_bytes(original)
        with self.assertRaises(ValueError):
            R.validate(self.root.parent, self.capture, self.meta)

    def test_lfs_payload_and_untracked_geometry_refuse(self):
        path = self.root / 'macro.lef'
        payload = path.read_bytes()
        data = json.loads(self.manifest.read_text())
        entry = next(item for item in data['files'] if item['path'] == 'macro.lef')
        entry['lfs_sha256'] = hashlib.sha256(payload).hexdigest()
        self.manifest.write_text(json.dumps(data))
        self.meta['source_manifest_sha256'] = R.digest(self.manifest)
        R.validate(self.root, self.capture, self.meta)
        path.write_bytes(payload + b'changed')
        with self.assertRaises(ValueError):
            R.validate(self.root, self.capture, self.meta)
        path.write_bytes(payload)
        (self.root / 'tools/shadow_geometry.py').write_text('HEIGHT=3')
        with self.assertRaisesRegex(ValueError, 'untracked input'):
            R.validate(self.root, self.capture, self.meta)

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
