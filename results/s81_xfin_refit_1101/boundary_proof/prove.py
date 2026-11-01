#!/usr/bin/env python3
"""Prove only 8f0's boundary rewrite, with unconstrained unchanged datapath results.
The arithmetic/datapath body is unchanged; its input-valid signals are compared
cycle-for-cycle and every possible wr_v/wr_n/wr_d/f_add/dup stream is admitted.
Root data is observed only when r_v, exactly as ot_s81dv_xfin consumes it.
"""
from pathlib import Path
import hashlib,json,subprocess,os
R=Path(__file__).resolve().parent
D=R/f"attempt_{len(list(R.glob('attempt_*'))):02d}";D.mkdir()
rev='8f0bf2371d540ee4daa6d5b627f446395002abb1'
f='rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv'
models=[];sections={}
for label,ref in [('old',rev+'^'),('new',rev)]:
 text=subprocess.check_output(['git','show',ref+':'+f],text=True)
 text=text[text.index('module ot_s81dv_eng_finish'):];text=text[:text.index('endmodule')]
 prefix=text[text.index('reg go_t;'):text.index('    wire        wr_v;')]
 tail=text[text.index('    // roots: node 1 of each tree'):]
 held='{r_dd,r_kk,r_hh}' if label=='old' else '{dd_s,kk_s,hh_s}'
 sections[label]=dict(revision=ref,prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),tail_sha256=hashlib.sha256(tail.encode()).hexdigest())
 models.append(f'''module {label}_boundary(input clk,rstn,go,input [2:0] f_v,input [5:0] f_t,input [23:0] f_base,input [479:0] f_d,
 input wr_v,input [9:0] wr_n,input [31:0] wr_d,input f_add,input [2:0] dup,
 output reg r_v,output reg [31:0] r_hh,r_kk,r_dd,output fault,
 output [2:0] iv_out,dn_out,output [95:0] held_out);
 localparam P=3,T=3,NVP=128,K=5;
 {prefix}
 {tail}
 assign iv_out=iv;assign dn_out=dn;assign held_out={held};
endmodule
''')
ports='clk,rstn,go,f_v,f_t,f_base,f_d,wr_v,wr_n,wr_d,f_add,dup'
top='''module top #(parameter MUT=0)(input clk,rstn,go,input [2:0] f_v,input [5:0] f_t,input [23:0] f_base,input [479:0] f_d,
 input wr_v,input [9:0] wr_n,input [31:0] wr_d,input f_add,input [2:0] dup);
 wire ov,nv,ofault,nfault;wire [31:0] oh,ok,od,nh,nk,nd;wire [2:0] oi,ni,odn,ndn;wire [95:0] oheld,nheld;
 old_boundary o(PORTS,ov,oh,ok,od,ofault,oi,odn,oheld);
 new_boundary n(PORTS,nv,nh,nk,nd,nfault,ni,ndn,nheld);
 wire [95:0] observed_new={nd,nk,nh} ^ ((MUT && nv) ? 96'd1 : 96'd0);
 reg initialized=0;
 always @(posedge clk) begin
  if (!rstn) initialized<=1;
  if (initialized) begin
   assert(oi==ni);assert(odn==ndn);assert(ov==nv);assert(ofault==nfault);
   assert(!ov || {od,ok,oh}==observed_new);
   assert(!odn[0] || oheld[31:0]==nheld[31:0]);
   assert(!odn[1] || oheld[63:32]==nheld[63:32]);
   assert(!odn[2] || oheld[95:64]==nheld[95:64]);
  end
 end
endmodule
'''.replace('PORTS',ports)
(D/'boundary_miter.sv').write_text('\n'.join(models)+top)
results={}
for mutant in (0,1):
 script=f'''read_verilog -formal -sv {D}/boundary_miter.sv
chparam -set MUT {mutant} top
prep -top top
async2sync
dffunmap
flatten
opt_clean
sat -set-def-inputs -seq 8 -tempinduct -set-at 1 rstn 0 -prove-asserts -verify -dump_vcd {D}/mut{mutant}.vcd
'''
 (D/f'mut{mutant}.ys').write_text(script)
 with (D/f'mut{mutant}.log').open('w') as log:r=subprocess.run([os.environ.get('YOSYS','yosys'),'-Q','-s',str(D/f'mut{mutant}.ys')],stdout=log,stderr=subprocess.STDOUT)
 logtext=(D/f'mut{mutant}.log').read_text();observed=('proved' if r.returncode==0 and 'SUCCESS' in logtext else 'counterexample' if 'proof did fail' in logtext or 'model found: FAIL' in logtext else 'ERROR')
 results[str(mutant)]=dict(returncode=r.returncode,expected='proved' if mutant==0 else 'counterexample',observed=observed)
print(json.dumps(results))
(D/'result.json').write_text(json.dumps(dict(scope=__doc__,source_sections=sections,results=results,cycles_added=0),indent=1)+'\n')
if results['0']['observed']!='proved' or results['1']['observed']!='counterexample':raise SystemExit(1)
