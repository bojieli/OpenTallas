#!/usr/bin/env python3
import hashlib,json,pathlib,sys,tempfile,unittest,shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import qrom_issue_lockstep_terminal_review as r
class Review(unittest.TestCase):
 def test_archive(self):self.assertEqual(r.review()['status'],'PASS_ARCHIVE_INTEGRITY_ONLY')
 def corrupt(self,name,change,expected):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp);p=root/r.PACKET;shutil.copytree(r.ROOT/r.PACKET,p)
   for pinned_name in json.loads((p/"artifact-pins.json").read_text()):
    if pinned_name.startswith("tools/"):
     dst=root/pinned_name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r.ROOT/pinned_name,dst)
   f=p/name;change(f)
   pins=json.loads((p/'artifact-pins.json').read_text());pins[str(r.PACKET/name)]=hashlib.sha256(f.read_bytes()).hexdigest();(p/'artifact-pins.json').write_text(json.dumps(pins))
   with self.assertRaisesRegex(ValueError,expected):r.review(root)
 def test_no_proof_promotion(self):
  def change(p):v=json.loads(p.read_text());v['unbounded_induction_PASS']=True;p.write_text(json.dumps(v))
  self.corrupt('classification.json',change,'unsupported proof claim')
 def test_original_fail_immutable(self):
  def change(p):v=json.loads(p.read_text());v['status']='PASS_LITERAL_ISSUE_LOCKSTEP';p.write_text(json.dumps(v))
  self.corrupt('raw/terminal.json',change,'original terminal changed')
 def test_no_invented_kernel_cause(self):self.corrupt('kernel-journal-PID1998275.log',lambda p:p.write_text('dmesg denied; cause UNKNOWN'), 'kernel cause not substantiated')
 def test_bounded_not_induction(self):
  def change(p):v=json.loads(p.read_text());v['unbounded_transition_induction']=True;p.write_text(json.dumps(v))
  self.corrupt('prior-base12-PASS-unchanged.json',change,'bounded scope changed')
 def test_byte_corruption(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp);p=root/r.PACKET;shutil.copytree(r.ROOT/r.PACKET,p);(p/'raw/literal.sv').write_text('changed')
   with self.assertRaisesRegex(ValueError,'artifact hash mismatch'):r.review(root)
if __name__=='__main__':unittest.main()
