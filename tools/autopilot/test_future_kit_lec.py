import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import future_kit_lec as F

class Staging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.k = self.root/'kit'; self.k.mkdir()
        (self.k/'lec.py').write_text('old')
        (self.k/'config.mk').write_text('unchanged config')
        self.tool=self.root/'lec.py'; self.tool.write_text('new')
        self.meta=dict(commit='a'*40, sha256=F.sha(self.tool))
    def tearDown(self): self.tmp.cleanup()
    def test_without_source_receipt_is_honest(self):
        r=F.stage(self.k,self.tool,self.meta)
        self.assertFalse(r['source_receipt_present'])
        self.assertFalse((self.k/'PROVENANCE.json').exists())
        self.assertEqual((self.k/'config.mk').read_text(),'unchanged config')
        self.assertEqual((self.k/'lec.py').read_text(),'new')
    def test_existing_source_receipt_preserved(self):
        rec=dict(schema='opentallas.kit_provenance.v1',provenance=dict(commit='b'*40,dirty=False),files={n:F.sha(self.k/n) for n in ('lec.py','config.mk')})
        (self.k/'PROVENANCE.json').write_text(json.dumps(rec))
        F.stage(self.k,self.tool,self.meta)
        self.assertEqual(json.loads((self.k/'PROVENANCE.generated.json').read_text()),rec)
        new=json.loads((self.k/'PROVENANCE.json').read_text())
        self.assertEqual(new['provenance'],rec['provenance'])
        self.assertEqual(new['tool_update']['source_commit'],'a'*40)
        self.assertEqual(new['files']['config.mk'],rec['files']['config.mk'])
    def test_live_or_resumed_attempt_refused(self):
        (self.k/'run').mkdir()
        with self.assertRaisesRegex(ValueError,'never modified'): F.stage(self.k,self.tool,self.meta)
        self.assertEqual((self.k/'lec.py').read_text(),'old')
    def test_snapshot_corruption_refused(self):
        self.tool.write_text('corrupt')
        with self.assertRaisesRegex(ValueError,'snapshot'): F.stage(self.k,self.tool,self.meta)
    def test_source_corruption_refused(self):
        rec=dict(schema='opentallas.kit_provenance.v1',files={'lec.py':'wrong'})
        (self.k/'PROVENANCE.json').write_text(json.dumps(rec))
        with self.assertRaisesRegex(ValueError,'differs'): F.stage(self.k,self.tool,self.meta)
if __name__=='__main__': unittest.main()
