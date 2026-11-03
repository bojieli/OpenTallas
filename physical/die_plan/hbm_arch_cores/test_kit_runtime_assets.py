import hashlib
import tempfile
import unittest
import json
import sys
from pathlib import Path
from kit_runtime_assets import stage
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import lec


class RuntimeAssets(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=self.root/'source';self.kit=self.root/'kit'
        self.repo.mkdir();self.kit.mkdir();(self.repo/'rows.tcl').write_text('puts ACTUAL_PLAN\n')
        self.hash=hashlib.sha256((self.repo/'rows.tcl').read_bytes()).hexdigest()
    def row(self,**kw):return dict(source='rows.tcl',sha256=self.hash,destination='runtime/rows.tcl',**kw)
    def test_default_empty_retains_bytes(self):
        self.assertEqual(stage(self.kit,self.repo),[]);self.assertEqual(stage(self.kit,self.repo,[]),[])
        self.assertEqual(list(self.kit.iterdir()),[])
    def test_exact_bytes_manifest_and_no_overwrite(self):
        row=self.row();out=stage(self.kit,self.repo,[row]);self.assertEqual(out[0]['sha256'],self.hash)
        self.assertEqual((self.kit/'runtime/rows.tcl').read_bytes(),(self.repo/'rows.tcl').read_bytes())
        with self.assertRaises(ValueError):stage(self.kit,self.repo,[row])
    def test_wrong_hash_refuses_before_any_write(self):
        wrong=self.row();wrong['sha256']='0'*64
        with self.assertRaises(ValueError):stage(self.kit,self.repo,[self.row(),wrong])
        self.assertFalse((self.kit/'runtime').exists())
    def test_source_traversal_and_absolute_refused(self):
        for src in ('../rows.tcl','/tmp/rows.tcl','./rows.tcl'):
            row=self.row();row['source']=src
            with self.assertRaises(ValueError):stage(self.kit,self.repo,[row])
    def test_runtime_only_destinations(self):
        for dst in ('config.mk','rtl/a.sv','runtime/../config.mk','/runtime/a','runtime/run_hook.tcl','runtime/freeze.json'):
            row=self.row();row['destination']=dst
            with self.assertRaises(ValueError):stage(self.kit,self.repo,[row])
    def test_source_symlink_escape(self):
        (self.root/'outside').write_text('not selected');(self.repo/'escape').symlink_to(self.root/'outside')
        row=self.row();row['source']='escape'
        with self.assertRaises(ValueError):stage(self.kit,self.repo,[row])
    def test_destination_symlink_escape(self):
        (self.kit/'runtime').symlink_to(self.repo,target_is_directory=True)
        with self.assertRaises(ValueError):stage(self.kit,self.repo,[self.row()])
    def test_nested_file_collision_validated_before_write(self):
        one=self.row();one['destination']='runtime/a';two=self.row();two['destination']='runtime/a/b'
        with self.assertRaises(ValueError):stage(self.kit,self.repo,[one,two])
        self.assertFalse((self.kit/'runtime').exists())
    def test_preexisting_file_ancestor_before_any_copy(self):
        (self.kit/'runtime').mkdir();(self.kit/'runtime/file').write_text('preserved')
        row=self.row();row['destination']='runtime/file/child'
        with self.assertRaises(ValueError):stage(self.kit,self.repo,[self.row(),row])
        self.assertFalse((self.kit/'runtime/rows.tcl').exists())
        self.assertEqual((self.kit/'runtime/file').read_text(),'preserved')
    def identity_fixture(self,entries=None):
        for name in ('config.mk','lec.py'):(self.kit/name).write_text('actual '+name)
        (self.kit/'freeze.json').write_text(json.dumps({}if entries is None else dict(runtime_files=entries)))
        (self.kit/'rtl').mkdir();(self.kit/'rtl/source.sv').write_text('module actual; endmodule')
    def test_default_identity_byte_set_unchanged(self):
        self.identity_fixture();self.assertEqual(set(lec._kit_input_identity(self.kit)),{'config.mk','freeze.json','lec.py','rtl/source.sv'})
    def test_runtime_identity_and_mutant(self):
        assets=stage(self.kit,self.repo,[self.row()]);self.identity_fixture(assets)
        out=lec._kit_input_identity(self.kit);self.assertEqual(out['runtime/rows.tcl'],self.hash)
        (self.kit/'runtime/rows.tcl').write_text('puts WRONG_PLAN')
        with self.assertRaises(ValueError):lec._kit_input_identity(self.kit)
    def test_identity_missing_and_duplicate_assets(self):
        self.identity_fixture([self.row()])
        with self.assertRaises(FileNotFoundError):lec._kit_input_identity(self.kit)
        assets=stage(self.kit,self.repo,[self.row()]);(self.kit/'freeze.json').write_text(json.dumps(dict(runtime_files=assets*2)))
        with self.assertRaises(ValueError):lec._kit_input_identity(self.kit)


if __name__=='__main__':unittest.main()
