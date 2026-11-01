import ast,re,subprocess,json,os
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-hbm-stations-1101/stage_miter');r.mkdir(exist_ok=True);src=Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-stations-1101/tools/die_plan/bind.py').read_text();cells=next(ast.literal_eval(x.value) for x in ast.parse(src).body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CELLS' for t in x.targets));primitive=re.search(r'module ot_dp_st\b.*?endmodule',cells,re.S).group();(r/'primitive.sv').write_text(primitive)
tb='''`timescale 1ps/1ps
module vehicle #(parameter W=178,K=5)(input clk,rst_n,input [W-1:0] d,input ea,output [W-1:0] a,b,output va,vb);
wire [W-1:0] oldq[0:K],newq[0:K+1];wire oldv[0:K],newv[0:K+1];assign oldq[0]=d;assign newq[0]=d;assign oldv[0]=ea;assign newv[0]=ea;
for(genvar i=0;i<K;i++) begin ot_dp_st #(W) u(clk,rst_n,oldq[i],oldv[i],oldq[i+1],oldv[i+1]);end
for(genvar i=0;i<K+1;i++) begin ot_dp_st #(W) u(clk,rst_n,newq[i],newv[i],newq[i+1],newv[i+1]);end
reg [W-1:0] delayed;reg vd;always @(posedge clk) begin delayed<=oldq[K];vd<=oldv[K];end
assign a=delayed;assign b=newq[K+1];assign va=vd;assign vb=newv[K+1];endmodule
module tb;reg clk=0,rst_n=0,ea=0;reg [177:0] d0=0;reg [2806:0] d1=0;wire [177:0] a0,b0;wire [2806:0] a1,b1;wire va0,vb0,va1,vb1;integer mutant=0,errors=0,checks=0;reg [31:0] rng=32'h53ad471b;
vehicle #(178,2) x0(clk,rst_n,d0,ea,a0,b0,va0,vb0);vehicle #(2807,4) x1(clk,rst_n,d1,ea,a1,b1,va1,vb1);
always begin #416;clk=1;#417;clk=0;end
initial begin void'($value$plusargs("MUTANT=%d",mutant));repeat(3) @(negedge clk);rst_n=1;
for(integer t=0;t<1040;t++) begin
for(integer i=0;i<2807;i++) begin rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};d1[i]=rng[0];if(i<178)d0[i]=rng[8];end
ea=(t%7!=0);@(posedge clk);#1;
if(t>=16) begin checks++;if(va0!==vb0 || va1!==vb1 || (vb0 && a0!==(b0 ^ {{177{1'b0}},(mutant!=0)})) || (vb1 && a1!==b1))errors++;end
@(negedge clk);end
$display("RESULT mutant=%0d checks=%0d errors=%0d period_ps=833",mutant,checks,errors);
if((mutant==0 && errors!=0)||(mutant!=0 && errors==0))$fatal(1,"miter gate");$finish;end endmodule
''';(r/'tb.sv').write_text(tb)
env=os.environ.copy();env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH']
with open(r/'build.log','w') as f:subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',str(r/'obj'),'-j','2',str(r/'primitive.sv'),str(r/'tb.sv')],stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
rows=[]
for mutant in [0,1]:
 out=subprocess.run([str(r/'obj/Vtb'),f'+MUTANT={mutant}'],capture_output=True,text=True,check=True);(r/f'run_{mutant}.log').write_text(out.stdout+out.stderr);rows.append(out.stdout.splitlines()[0])
(r/'result.json').write_text(json.dumps(dict(status='PASS',actual_primitive='bind.py CELLS ot_dp_st',period_ps=833,forms=[dict(width=178,old_k=2,new_k=3),dict(width=2807,old_k=4,new_k=5)],results=rows),indent=2));print('\n'.join(rows))
