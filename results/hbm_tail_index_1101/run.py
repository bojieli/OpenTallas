#!/usr/bin/env python3
"""Lockstep the exact production calendar/address slice; no arithmetic stubs."""
from pathlib import Path
import subprocess,json,hashlib
w=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent
src=w/'rtl/hbm_accel/cores_split/sk_en_q4/ot_hbm_hc_tail_rest_core_ce.sv';s=src.read_text()
# The address retime is the only functional change. Compare it for every edge
# of the original, unmodified control process, including invalid cycles.
constants=s[s.index('    localparam integer P1='):s.index('    reg active;')]
a=s.index('    wire p1=');z=s.index('    wire mv=',a);addresses=s[a:z]
a=s.index('    always @(posedge clk or negedge rst_n)begin',s.index('    reg sink_fault;'))
a=s.index('    always @(posedge clk or negedge rst_n)begin',a+1)
z=s.index('    always @(posedge clk)begin',a);control=s[a:z]
module='''module calendar #(parameter PREDECODE_INDEX=0)(input clk,rst_n,launch,sink_capture,output[4:0] idx,output[8:0] age_out,output active_out);
'''+constants+'''reg active;reg[8:0]age;reg fault,result_v;
wire mo=0,ao=0,eo=0,do_=0,ef=0,df=0,sink_fault=0,sv=1,sf=0;
wire[1:0]me=0,ae=0;
'''+addresses+control+'''assign idx=i;assign age_out=age;assign active_out=active;
endmodule
'''
(out/'calendar_slice.sv').write_text(module)
mut=module.replace('i_q<=address(age_next,active_next)','i_q<=address(age_next+9\'d1,active_next)')
assert mut!=module
(out/'calendar_slice_wrong.sv').write_text(mut)
tb='''module tb;
reg clk=0,rst=0,launch=0,cap=0;always #5 clk=~clk;
wire[4:0]a,b;wire[8:0]aa,ba;wire ax,bx;
calendar gold(clk,rst,launch,cap,a,aa,ax);
calendar #(.PREDECODE_INDEX(1)) dut(clk,rst,launch,cap,b,ba,bx);
integer checks=0,errors=0,seed=1234567,k,f;
reg[511:0]ages=0;
always @(negedge clk)if(rst)begin
checks=checks+1;ages[aa]=1;
if({a,aa,ax}!=={b,ba,bx})begin errors=errors+1;if(errors<3)$display("DIFF age%0d index%0d/%0d",aa,a,b);end
end
initial begin
repeat(4)@(negedge clk);#1;rst=1;
for(f=0;f<20;f=f+1)begin
 launch=1;@(negedge clk);#1;launch=0;
 repeat(205)@(negedge clk);#1;cap=1;@(negedge clk);#1;cap=0;
end
for(k=0;k<16000;k=k+1)begin
 @(negedge clk);#1;
 rst=($unsigned($random(seed))%67!=0);
 launch=($unsigned($random(seed))%43==0);
 cap=($unsigned($random(seed))%59==0);
end
@(negedge clk);#1;
$display("TAIL_INDEX checks=%0d errors=%0d visitedages=%0d",checks,errors,$countones(ages));
if(errors!=0||checks<18000||$countones(ages)<199)$fatal(1,"TAIL_INDEX FAIL");
$display("TAIL_INDEX PASS");$finish;
end
endmodule
'''
(out/'tb.sv').write_text(tb)
results={}
for kind,filename in [('positive','calendar_slice.sv'),('mutant','calendar_slice_wrong.sv')]:
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/kind),str(out/filename),str(out/'tb.sv')],check=True)
 r=subprocess.run(['vvp',str(out/kind)],capture_output=True,text=True);(out/(kind+'.log')).write_text(r.stdout+r.stderr)
 results[kind]={'rc':r.returncode,'log':r.stdout};print(kind,r.stdout.strip())
assert results['positive']['rc']==0 and results['mutant']['rc']!=0
(out/'receipt.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scope':'exact production control+address slice; no arithmetic retime','added_cycles':0,'added_flops_optin':5,'parent_activated':False,'physical_qualification':'NOT RUN','results':results},indent=2)+'\n')
