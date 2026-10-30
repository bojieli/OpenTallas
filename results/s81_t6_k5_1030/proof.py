from pathlib import Path
import re,subprocess,json
r=Path(__file__).parent
b=Path('/home/ubuntu/OpenTallas/tools/die_plan/bind.py').read_text();cell=re.search(r'module ot_dp_st #.*?\nendmodule',b,re.S)[0]
mods=[cell]
for label,file in [('old','old_bound.sv'),('candidate','candidate_bound.sv')]:
 s=(r/file).read_text();lines=[x for x in s.splitlines() if re.search(r'wire \[1104:0\] ft[01]_o_s|u_ft_ft[01]_o_',x)]
 mods.append(f'module {label}(input clk,rst_n,input [1104:0] ft0_i,ft1_i,output [1104:0] ft0_o,ft1_o);\n'+'\n'.join(lines)+'\nendmodule')
tb='''module tb; reg clk=0,rst_n=0; always #5 clk=~clk; reg[1104:0] a,b; wire[1104:0] o0,o1,n0,n1,r0,r1; old O(clk,rst_n,a,b,o0,o1); candidate N(clk,rst_n,a,b,n0,n1); ot_dp_st #(.W(1104)) R0(clk,rst_n,o0[1103:0],o0[1104],r0[1103:0],r0[1104]); ot_dp_st #(.W(1104)) R1(clk,rst_n,o1[1103:0],o1[1104],r1[1103:0],r1[1104]); integer t,k,checks=0,mut=0; initial begin a=0;b=0; for(t=0;t<600;t=t+1)begin @(negedge clk); rst_n=(t%73>2); for(k=0;k<1105;k=k+1)begin a[k]=$random;b[k]=$random;end @(posedge clk);#1; if(t>6)begin if(n0!==r0||n1!==r1)$fatal(1,"MISMATCH %d",t);checks=checks+2; if(n0!==o0||n1!==o1)mut=mut+1;end end if(mut==0)$fatal(1,"MUTANT NOT DETECTED");$display("PASS checks=%0d mutant_cycles=%0d",checks,mut);$finish;end endmodule'''
(r/'miter.sv').write_text('\n'.join(mods)+'\n'+tb)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(r/'sim'),str(r/'miter.sv')],check=True)
p=subprocess.run(['vvp',str(r/'sim')],text=True,capture_output=True,check=True);(r/'proof.log').write_text(p.stdout);print(p.stdout)
