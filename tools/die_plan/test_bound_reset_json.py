"""Bound reset identities must survive the actual JSON serialization boundary."""
import copy,hashlib,json,pathlib,tempfile,unittest
import bound_reset_contract as B

class JsonReceipt(unittest.TestCase):
 def tree(self):
  return {'root':[8.16,8.608],'tap_depth':{i:5 for i in range(12)},'tap_roles':{i:'leaf' for i in range(12)},'relays':[{'name':'u_rrl_0','d':'rst_root_n','q':'rst_rl_0','depth':1}]}
 def record(self):
  t=self.tree();return dict(schema=B.SCHEMA,plan_type='actual',bound_module='actual',tree=t,tree_sha256=B.digest(t))
 def test_numeric_maps_roundtrip(self):
  t=self.tree();self.assertEqual(B.digest(t),B.digest(json.loads(json.dumps(t))))
 def test_emission_identity_validates_after_disk(self):
  r=self.record();self.assertIsNotNone(B.validate(json.loads(json.dumps(r)),'actual'))
 def test_changed_reset_edge_rejected(self):
  r=json.loads(json.dumps(self.record()));r['tree']['relays'][0]['d']='different_reset'
  with self.assertRaisesRegex(ValueError,'content differs'):B.validate(r,'actual')
 def test_legacy_bad_serialization_still_rejected(self):
  r=self.record();r['tree_sha256']=hashlib.sha256(json.dumps(r['tree'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
  with self.assertRaisesRegex(ValueError,'content differs'):B.validate(json.loads(json.dumps(r)),'actual')
 def test_same_tree_cannot_authorize_changed_rtl(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'actual.sv';p.write_text('module actual; endmodule\n');r=self.record();r['bound_rtl_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();p.with_suffix('.reset_tree.json').write_text(json.dumps(r));B.source(p,'actual',d,d)
   p.write_text('module actual; wire changed; endmodule\n')
   with self.assertRaisesRegex(ValueError,'RTL identity differs'):B.source(p,'actual',d,d)
if __name__=='__main__':unittest.main()
