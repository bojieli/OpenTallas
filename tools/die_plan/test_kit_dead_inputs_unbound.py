"""Whole spare input declarations need native mapping, ABI, and unread-source proofs."""
import ast,copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kit_dead_inputs as K

class UnboundInputTest(unittest.TestCase):
 def fixture(self,p):
  report=p/'bind_report.json';report.write_text(json.dumps({'n_errors':0,'errors':[],'unmapped':0,'proof':dict(unbound=0,tied=0,undriven=0,multiply_bound=0)}))
  native=p/'bound.sv';native.write_text('module bound(input wire a,output wire z);assign z=a;endmodule\n')
  wrapper=p/'top.sv';wrapper.write_text('module top(input wire [2:0] L1213_i,input wire a,output wire z); bound u_bound(.a(a),.z(z)); endmodule\n')
  rows=[dict(port='L1213_i',width=3)];missing=['L1213_i']
  rc=dict(wrapper=str(wrapper),sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),narrow_buses=[],
          unbound_input_buses=rows,unbound_source_proof=K.unbound_receipt(rows,missing,report,native,'bound'))
  m=dict(plan_buses_unbound=missing,unbound_input_buses=rows,narrow_buses=[],dead_inputs=dict(schema='opentallas.kit_dead_inputs.v1',bits=[f'L1213_i[{i}]'for i in range(3)],proof=dict(verdict='PASS',method='strict source mapping and literal unread input audit',receipt=rc)))
  return m,wrapper,native,report
 def gen(self,m,p):
  (p/'kit_rtl.json').write_text(json.dumps(m));tree=ast.parse(Path(__file__).with_name('gen_phys.py').read_text())
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='kit_dead_inputs')
  ns=dict(Path=Path,json=json,_hashlib=hashlib);exec(compile(ast.Module(body=[node],type_ignores=[]),'gen_phys.py','exec'),ns)
  return ns['kit_dead_inputs'](p/'kit_rtl.f')
 def test_source_and_gen_reprove_exact_unused_input(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);m,w,_,_=self.fixture(p);K.refresh(m,w)
   self.assertEqual(set(self.gen(m,p)['bits']),{'L1213_i[0]','L1213_i[1]','L1213_i[2]'})
 def test_added_literal_read_rejected_even_with_fresh_wrapper_hash(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);m,w,_,_=self.fixture(p);w.write_text(w.read_text().replace('endmodule','wire use=L1213_i[1];endmodule'))
   m['dead_inputs']['proof']['receipt']['sha256']=hashlib.sha256(w.read_bytes()).hexdigest()
   with self.assertRaises(ValueError):K.refresh(m,w)
   with self.assertRaises(Exception):self.gen(m,p)
 def test_added_bound_abi_port_rejected_even_with_fresh_source_hash(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);m,w,n,_=self.fixture(p);n.write_text(n.read_text().replace('input wire a','input wire [2:0] L1213_i,input wire a'))
   m['dead_inputs']['proof']['receipt']['unbound_source_proof']['bound_source']=K._hash_file(n)
   with self.assertRaises(ValueError):K.refresh(m,w)
 def test_wrong_bus_record_rejected(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);m,w,_,_=self.fixture(p);m['plan_buses_unbound']=['OTHER_i']
   with self.assertRaises(ValueError):K.refresh(m,w)
 def test_source_mapping_failure_rejected_even_with_fresh_hash(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);m,w,_,r=self.fixture(p);d=json.loads(r.read_text());d['proof']['unbound']=1;r.write_text(json.dumps(d))
   m['dead_inputs']['proof']['receipt']['unbound_source_proof']['bind_report']=K._hash_file(r)
   with self.assertRaises(ValueError):K.refresh(m,w)
 def test_stale_native_source_hash_rejected(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);m,w,n,_=self.fixture(p);n.write_text(n.read_text()+'// changed\n')
   with self.assertRaises(ValueError):K.refresh(m,w)
 def test_legacy_narrow_payload_behavior_unchanged(self):
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);w=p/'top.sv';w.write_text('module top(input wire [3:0] L_i); bound u(.p({L_i[3],L_i[0]}));endmodule\n')
   rows=[dict(port='L_i',bound=1,plan=3)];m=dict(narrow_buses=rows,dead_inputs=dict(bits=['L_i[1]','L_i[2]'],proof=dict(verdict='PASS',receipt=dict(wrapper=str(w),sha256=hashlib.sha256(w.read_bytes()).hexdigest(),narrow_buses=rows))))
   K.refresh(m,w)

if __name__=='__main__':unittest.main()
