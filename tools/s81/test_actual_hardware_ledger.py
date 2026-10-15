"""Negative controls for whole-die evidence, partial aliases, and source interfaces."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import actual_hardware_ledger as ledger

class LedgerGate(unittest.TestCase):
 def test_partial_alias_or_stale_gate_cannot_pass(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'rtl').mkdir()
   (root/'rtl/r.sv').write_text('module leaf(input wire ck,input wire [7:0] x,output reg [7:0] y);always @(posedge ck)y<=x;endmodule')
   req=root/'req.json';req.write_text(json.dumps({'scope':'whole canonical die','canonical':{'field_pairs':2417,'bf_pairs':519,'phase_width':10},'operations':[{'operation':'first','module':'leaf','source':'rtl/r.sv'},{'operation':'missing_second','module':'absent','source':None}]}))
   manifest=root/'list.f';manifest.write_text(str(root/'rtl/r.sv')+'\n')
   die=root/'die.v';die.write_text('module die(ck);input ck;wire [7:0] n;leaf u(.ck(ck),.x(n),.y(n));endmodule')
   shape=root/'shape.json';shape.write_text(json.dumps({'field_pairs':2417,'bf_pairs':519,'phase_width':10}))
   gate=root/'gate.json';gate.write_text(json.dumps({'verdict':'PASS','die_sha256':hashlib.sha256(die.read_bytes()).hexdigest()}))
   with patch.object(ledger,'ROOT',root):r=ledger.audit(req,manifest,die,gate,shape)
   self.assertEqual(r['verdict'],'FAIL')
   self.assertIn('operation:missing_second',r['failures'])
   self.assertEqual(r['operations'][0]['ports']['x']['bits'],8)
   gate.write_text(json.dumps({'verdict':'PASS','die_sha256':'old'}))
   with patch.object(ledger,'ROOT',root):r=ledger.audit(req,manifest,die,gate,shape)
   self.assertIn('whole_die_port_gate_missing_or_not_pinned_pass',r['failures'])
 def test_manifest_omission_and_unknown_phase_fail(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'r.sv').write_text('module a(input wire ck);always @(posedge ck)begin end endmodule')
   req=root/'req.json';req.write_text(json.dumps({'scope':'whole','canonical':{'phase_width':10},'operations':[{'operation':'a','module':'a','source':'r.sv','required_defines':['STATIC']}]}))
   fl=root/'list.f';fl.write_text('')
   with patch.object(ledger,'ROOT',root):r=ledger.audit(req,fl)
   self.assertIn('canonical_phase_width_unproven',r['failures'])
   self.assertIn('missing_build_define:STATIC',r['operations'][0]['binding_findings'])
   self.assertIn('source_not_selected_in_manifest',r['operations'][0]['binding_findings'])
if __name__=='__main__':unittest.main()
