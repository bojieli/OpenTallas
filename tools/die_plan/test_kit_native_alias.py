import hashlib,json,subprocess,tempfile,unittest,shutil
from pathlib import Path
import kit_assembly as A

class NativeAliasTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which("yosys"), "requires the actual small hierarchy frontend")
 def test_two_fixed_masters_and_soft_sibling(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); src=p/'top.sv'
   original='''module bank #(parameter B0=0, NG=5)(input [7:0] d, output [7:0] q); assign q=d+B0+NG; endmodule
  module top(input [7:0] d, output [7:0] a,b,c);
  bank #(.B0(0),.NG(5)) u_ga (.d(d),.q(a));
  bank #(.B0(5),.NG(3)) u_gb (.d(d),.q(b));
  bank #(.B0(8),.NG(1)) u_gc (.d(d),.q(c)); endmodule
  '''
   src.write_text(original)
   for name in ('bank','bank_b3'):
    (p/(name+'_bb.v')).write_text('(* blackbox *) module '+name+'(input [7:0] d,output [7:0] q); endmodule\n')
   children=[dict(master='bank',inst='u_ga'),dict(master='bank_b3',native_master='bank',inst='u_gb')]
   contracts=[dict(master=c['master'],instance=c['inst'],child_params=dict(B0=b,NG=n),binding_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),**({'native_master':c['native_master']} if 'native_master' in c else {})) for c,b,n in zip(children,(0,5),(5,3))]
   wrong=[dict(c) for c in contracts];wrong[1]['native_master']='OTHER'
   try:A.assemble_fixed_children(p,children,wrong)
   except ValueError:pass
   else:raise AssertionError('wrong native seal accepted')
   assert src.read_text()==original
   r=A.assemble_fixed_children(p,children,contracts)
   t=src.read_text(); assert 'bank_b3 u_gb (' in t and 'bank u_ga (' in t and 'bank__soft #(.B0(8),.NG(1)) u_gc' in t
   subprocess.run(['yosys','-Q','-q','-p',f'read_verilog {p}/bank_bb.v {p}/bank_b3_bb.v {src}; hierarchy -check -top top; write_json {p}/design.json'],check=True)
   inv=A.hierarchy_inventory(json.loads((p/'design.json').read_text()),'top',children)
   assert not inv['problems'],inv
   cells=json.loads((p/'design.json').read_text())['modules']['top']['cells']
   assert cells['u_gc']['type'].startswith('$paramod')
