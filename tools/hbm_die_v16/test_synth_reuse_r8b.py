"""A matching previous wrapper must never hide a changed implementation source."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class SourceReuseTest(unittest.TestCase):
    def test_previous_wrapper_still_requires_source_inventory(self):
        tool = Path(__file__).with_name('synth_reuse_r8b.py')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for d in ('views/wrap', 'prev/wrap', 'meta/c', 'source/rtl'):
                (root / d).mkdir(parents=True)
            (root / 'source/rtl/c.sv').write_text('module c; endmodule\n')
            for d in ('views', 'prev'):
                (root / d / 'wrap/w.sv').write_text('module w; c u(); endmodule\n')
                (root / d / 'views.json').write_text(json.dumps({'c': {'kind': 'SYNTH', 'wrapper': 'w'}}))
            src = {'rtl/c.sv': 'source/rtl/c.sv', 'v16w/w.sv': 'views/wrap/w.sv'}
            inventory = {k: hashlib.sha256((root / v).read_bytes()).hexdigest() for k, v in src.items()}
            meta = root / 'meta/c/meta.json'
            meta.write_text(json.dumps({'source_file_sha256': inventory}))

            def run():
                subprocess.run(['python3', str(tool), '--views', str(root / 'views'), '--prev', str(root / 'prev'),
                                '--metas', str(root / 'meta'), '--root', str(root / 'source'), '--out', str(root / 'out')],
                               check=True, capture_output=True)
                return json.loads((root / 'out').read_text())

            self.assertEqual(run()['reuse'], ['c'])
            (root / 'source/rtl/c.sv').write_text('module c; wire new_pipeline_stage; endmodule\n')
            self.assertEqual(run()['synth'], {'c': 'source changed: rtl/c.sv'})
            meta.write_text('{}')
            self.assertEqual(run()['synth'], {'c': 'prior synthesis has no immutable source inventory'})


if __name__ == '__main__':
    unittest.main()
