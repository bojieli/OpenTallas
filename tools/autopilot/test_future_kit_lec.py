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

class RunnerAdapter(unittest.TestCase):
    @staticmethod
    def template():
        import ast
        tree=ast.parse((Path(__file__).resolve().parents[1]/'die_plan/gen_phys.py').read_text())
        return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RUN_KIT' for t in n.targets))
    def test_exact_normalized_old_recipe_and_gates_preserved(self):
        import kit_resume as R
        old="#!/bin/bash\nNAME=dpkit-example-$$\n  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0;\n  $M synth; existing_gate --unchanged; $M place\n"
        new,reason=R.adapt_type_runner(old,self.template())
        self.assertIn(R.MARKER,new)
        self.assertEqual(R.runner_norm(new),old)
        self.assertIn('identical',reason)
    def test_core_unknown_runner_is_unchanged(self):
        import kit_resume as R
        old='#!/bin/bash\nmake core_route\n'
        new,reason=R.adapt_type_runner(old,self.template())
        self.assertEqual(new,old)
        self.assertIn('fallback',reason)
    def test_non_harness_change_refused(self):
        import kit_resume as R
        old="NAME=dpkit-x\n  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0;\n"
        bad=self.template().replace('RS=0; KWRS_M=  # KWRS','bad_physical_change')
        with self.assertRaisesRegex(ValueError,'normalized'): R.adapt_type_runner(old,bad)
