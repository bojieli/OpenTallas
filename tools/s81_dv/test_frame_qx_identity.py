import copy,json,tempfile,unittest
from pathlib import Path
import frame_qx_identity as Q

PINS='.clk(ck),.rst_n(rst),.go(go),.xs_sv(sv),.r(ret)'
PARENT='ot_v41_rom_elem_q_qxpq_w10 #(.INSTANCE({INSTANCE,"_e0"})) u_e0 ('+PINS+');'
BAND='ot_v41_rom_elem_q_qxpq_w10 u_e0 ('+PINS+');'
INST='u_f_A.u_r0.u_e0'
REPORT={'instance_path_params':[{'inst':INST,'module':Q.OLD,'param':'INSTANCE','value':json.dumps(INST)}]}
class QxIdentity(unittest.TestCase):
 def test_four_bank_aliases(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t)
   for i,b in enumerate(Q.SUFFIXES):(p/('u_f_A_e0'+b+'.viamap.hex')).write_text((f'{i+1:0548x}\n')*512)
   rows=Q.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',REPORT,p)
   self.assertEqual(len(rows),4)
   for r in rows:self.assertEqual((p/r['image']).read_bytes(),(p/r['alias']).read_bytes())
 def test_empty_selector_control(self):
  r=copy.deepcopy(REPORT);r['instance_path_params'][0]['value']='""'
  with self.assertRaisesRegex(ValueError,'empty or wrong'):Q.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',r,'.')
 def test_wrong_leaf_control(self):
  r=copy.deepcopy(REPORT);r['instance_path_params'][0]['value']='"u_f_B.u_r0.u_e0"'
  with self.assertRaisesRegex(ValueError,'empty or wrong'):Q.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',r,'.')
 def test_changed_ports_control(self):
  with self.assertRaisesRegex(ValueError,'electrical pins changed'):Q.prove(PARENT,BAND.replace('.go(go)','.go(other)'))
 def test_missing_audit_control(self):
  with self.assertRaisesRegex(ValueError,'missing actual bound'):Q.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',{},'.')
 def test_duplicate_audit_control(self):
  r=copy.deepcopy(REPORT);r['instance_path_params']*=2
  with self.assertRaisesRegex(ValueError,'duplicate bound'):Q.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',r,'.')
if __name__=='__main__':unittest.main()
