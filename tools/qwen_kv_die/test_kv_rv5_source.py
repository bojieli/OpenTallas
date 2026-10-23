import unittest
from pathlib import Path
import tempfile,shutil,json
import kv_rv5_source as R
ROOT=Path(__file__).resolve().parents[2]
class SelectedRv5Source(unittest.TestCase):
    def check(self,root=ROOT,**kw):
        p=dict(active=True,params={'RETIRE_STATIC':1,'STATUS_DELAY':213},kit='qkd_kvs_attn_rv5',master='qkd_kvs_attn',source_commit=R.COMMIT);p.update(kw)
        return R.selected_source_map(root,True,**p)
    def test_exact_archive_and_defaults(self):
        self.assertEqual(self.check(),{R.CANONICAL:R.SELECTED})
        text=(ROOT/R.SELECTED).read_text();self.assertIn('parameter integer KV_SIDE=1',text);self.assertIn('parameter integer MUT=0',text)
        self.assertNotIn('RX_FREE',text);self.assertNotIn('TX_FREE',text)
    def test_off_and_unrelated_view(self):
        self.assertEqual(R.selected_source_map(ROOT,False,active=False,params={}),{})
        self.assertEqual(self.check(kit='other'),{})
    def test_wrong_selection_parameter_and_commit(self):
        for kw in [dict(active=False),dict(params={'RETIRE_STATIC':0,'STATUS_DELAY':213}),dict(source_commit='foreign')]:
            with self.assertRaises(ValueError):self.check(**kw)
    def test_source_and_manifest_drift_refused(self):
        for change in ['source','manifest']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td)
                for rel in [R.IDENTITY,R.SELECTED]:
                    (root/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,root/rel)
                if change=='source':(root/R.SELECTED).write_text((root/R.SELECTED).read_text()+'\n')
                else:
                    p=root/R.IDENTITY;d=json.loads(p.read_text());d['parameter_defaults']['KV_SIDE']=0;p.write_text(json.dumps(d))
                with self.assertRaises(ValueError):self.check(root)
if __name__=='__main__':unittest.main()
