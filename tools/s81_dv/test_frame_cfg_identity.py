import copy
import json
from pathlib import Path
import tempfile
import unittest
import frame_cfg_identity as F

PINS='.ce_in(ce), .clk(ck), .addr_in(addr), .rd_out(rd)'
PARENT='ot_rom_4096x72_m8 #(.INSTANCE({INSTANCE,"_c0_0"})) u_c0_0 ('+PINS+');'
BAND='ot_rom_4096x72_m8 u_c0_0 ('+PINS+');'
INST='u_f_A.u_r0.u_c0_0'
REPORT={'instance_path_params':[{'inst':INST,'module':'ot_rom_4096x72_m8','param':'INSTANCE','value':json.dumps(INST)}]}
DATA=('1'.zfill(144)+'\n')*512

class BoundAliases(unittest.TestCase):
    def test_exact_bound_alias_and_idempotence(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'u_f_A_c0_0.viamap.hex').write_text(DATA)
            rows=F.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',REPORT,p)
            self.assertEqual((p/(INST+'.viamap.hex')).read_text(),DATA)
            self.assertEqual(rows,F.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',REPORT,p))
            self.assertEqual(rows[0]['image'],'u_f_A_c0_0.viamap.hex')

    def test_wrong_bound_selector_control(self):
        with tempfile.TemporaryDirectory() as t:
            r=copy.deepcopy(REPORT);r['instance_path_params'][0]['value']='"u_f_B.u_r0.u_c0_0"'
            with self.assertRaisesRegex(ValueError,'differs from its proven original leaf'):
                F.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',r,t)

    def test_changed_electrical_pin_control(self):
        with self.assertRaisesRegex(ValueError,'electrical pins changed'):
            F.emit_bound_aliases(PARENT,BAND.replace('addr_in(addr)','addr_in(other)'),'u_f_A','u_r0',REPORT,'.')

    def test_conflicting_alias_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'u_f_A_c0_0.viamap.hex').write_text(DATA)
            alias=p/(INST+'.viamap.hex');alias.write_text('wrong')
            with self.assertRaisesRegex(ValueError,'preserve conflicting'):
                F.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',REPORT,p)
            self.assertEqual(alias.read_text(),'wrong')

    def test_duplicate_selector_control(self):
        r=copy.deepcopy(REPORT);r['instance_path_params']*=2
        with self.assertRaisesRegex(ValueError,'duplicate bound'):
            F.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',r,'.')

    def test_missing_audit_control(self):
        with self.assertRaisesRegex(ValueError,'missing actual bound'):
            F.emit_bound_aliases(PARENT,BAND,'u_f_A','u_r0',{},'.')

if __name__=='__main__':unittest.main()
