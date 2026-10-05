import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('W',ROOT/'tools/W1_euclid_provider_hygiene_gate.py');W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
class IdentityTests(unittest.TestCase):
 def test_actual_enabled_identity(self):self.assertTrue(W.identity()['enabled_branch_byte_identical'])
 def fixture(self,p):
  for path in (W.OLD,W.NEW,'tools/uarch_model.py'):
   q=p/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((ROOT/path).read_bytes())
  record=p/'record';record.mkdir();(record/'pre-edit-model-identity-r1.json').write_bytes((W.RECORD/'pre-edit-model-identity-r1.json').read_bytes());return record
 def mutant(self,path,old,new):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);rec=self.fixture(p);f=p/path;f.write_bytes(f.read_bytes().replace(old,new));oldroot,oldrec=W.ROOT,W.RECORD
   try:
    W.ROOT=p;W.RECORD=rec
    with self.assertRaises(ValueError):W.identity()
   finally:W.ROOT=oldroot;W.RECORD=oldrec
 def test_wrong_default_ack_fails(self):self.mutant(W.NEW,b'assign commit_r=0;',b"assign commit_r=32'hffffffff;")
 def test_enabled_branch_mutation_fails(self):self.mutant(W.NEW,b'assign commit_r=commit_ready;',b'assign commit_r=0;')
 def test_original_edit_fails(self):self.mutant(W.OLD,b'assign commit_ready=0;',b'assign commit_r=0;')
 def test_model_root_mutation_fails(self):self.mutant('tools/uarch_model.py',b'\n',b'\n#unexpected model edit\n')
if __name__=='__main__':unittest.main()
