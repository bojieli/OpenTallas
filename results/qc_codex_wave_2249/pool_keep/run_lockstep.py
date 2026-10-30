from pathlib import Path
import re,subprocess,json
D=Path(__file__).resolve().parent;repo=D.parents[2]
src=repo/'rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv';candidate=src.read_text()
baseline=subprocess.run(['git','show','HEAD:rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv'],cwd=repo,text=True,capture_output=True,check=True).stdout
# Extract the real three coupled epoch writes and the real forwarded pool consumer.
def mech(s,attr,mut=False):
 stm=[]
 for pat in (r'^\s*if \(b_vk\[0\]\) e_pool\[b_epk\[0\]\] <= b_poolm;',r'^\s*if \(b_vk\[0\] && !b_epk\[0\]\) e_poolc0 <= \{4\{b_poolm\}\};',r'^\s*if \(b_vk\[0\] && b_epk\[0\]\) e_poolc1 <= \{4\{b_poolm\}\};'):
  m=re.search(pat,s,re.M);assert m,pat;stm.append(m[0])
 px=re.search(r'wire\s+pool_x\s*=.*?;',s)[0];pc=re.search(r'POOLc <=.*?;',s)[0]
 if mut:stm[0]=stm[0].replace('e_pool[b_epk[0]]','e_pool[!b_epk[0]]')
 return f'''module MNAME(input ck,input [2:0] b_vk,input [2:0] b_epk,input b_poolm,input b_v,input b_ep,input REP_k,output reg [8:0] POOLc,output reg[3:0] e_poolc0,e_poolc1);
{attr} reg e_pool[0:1];
wire fwd=b_v && (b_ep==REP_k);
{px}
always @(posedge ck) begin {''.join(stm)} {pc} end
endmodule\n'''
g=mech(baseline,'').replace('MNAME','gold');c=mech(candidate,'(* keep="true" *)').replace('MNAME','cand');m=mech(candidate,'(* keep="true" *)',True).replace('MNAME','mut')
assert mech(baseline,'')==mech(candidate,'')
tb='''module tb;
reg ck=0;always begin #416;ck=1;#417;ck=0;end
reg[2:0] b_vk=0,b_epk=0;reg b_poolm=0,b_v=0,b_ep=0,REP_k=0;wire[8:0] a,b,m;wire[3:0] ac0,ac1,bc0,bc1,mc0,mc1;
gold A(ck,b_vk,b_epk,b_poolm,b_v,b_ep,REP_k,a,ac0,ac1);cand B(ck,b_vk,b_epk,b_poolm,b_v,b_ep,REP_k,b,bc0,bc1);mut M(ck,b_vk,b_epk,b_poolm,b_v,b_ep,REP_k,m,mc0,mc1);
integer n,checks=0,mutant_first=-1;reg[31:0] state=32'h3a987154;
initial begin
for(n=0;n<4096;n=n+1)begin
 @(negedge ck);state=state^(state<<13);state=state^(state>>17);state=state^(state<<5);
 b_vk=state[2:0];b_epk=state[5:3];b_poolm=state[6];b_v=state[7];b_ep=state[8];REP_k=state[9];
 if(n<4)begin b_vk=1;b_epk=n%2;b_poolm=n%2;b_v=0;REP_k=0;end
 @(posedge ck);#1;
 if(a!==b || ac0!==bc0 || ac1!==bc1)begin $display("LOCKSTEP_FAIL edge=%0d",n);$fatal(1);end
 checks=checks+3;if(n>=3 && a!==m && mutant_first<0)mutant_first=n;
end
if(mutant_first<0)$fatal(1,"mutant not caught");$display("LOCKSTEP_PASS edges=4096 checks=%0d added_cycles=0 MUTANT_CAUGHT edge=%0d",checks,mutant_first);$finish;
end
endmodule
'''
(D/'vehicle.sv').write_text('`timescale 1ps/1ps\n'+g+c+m+tb)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(D/'vehicle.vvp'),str(D/'vehicle.sv')],check=True)
r=subprocess.run(['vvp',str(D/'vehicle.vvp')],text=True,capture_output=True,check=True);print(r.stdout);(D/'lockstep.log').write_text(r.stdout)
