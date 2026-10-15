#!/usr/bin/env python3
"""Exact actual hard-wrapper oracle. Mutant exit1 requires observed payload/control FAIL."""
import pathlib,sys,subprocess
kind,g,mode,out=sys.argv[1],int(sys.argv[2]),sys.argv[3],pathlib.Path(sys.argv[4]);out.mkdir(parents=True,exist_ok=True)
root=pathlib.Path(__file__).resolve().parents[2];r=root/'rtl/dsrom_sys/s81_ph/vm'
np=9 if g==1 else 2 if g==4 else 4 if g>=6 else 8;no=8 if g==1 else np
variable=[j for j in range(np)if(g==0 and j in(0,1,4,5,6,7))or(g==1 and j in(0,5,6,7,8))or(g in(2,3,5)and j>=4)or g==4]
def fixed(j):return(j+3)%4 if g==1 else j%4
if kind=='q':
 ports=['.ck(ck)', '.rst_n(rst)', '.i_data(data)', '.i_valid(4\'hf)', '.i_expected(exp)', '.o_partial_valid(pv)', '.o_data(od)', '.fault(fault)']
 if variable:ports+=['.i_sel(sel)']
 if g in(0,1):ports+=['.i_su1_group(alt)']
 if g==0:ports+=['.i_peer_data(peer)', '.i_peer_valid(peerv)']
 if g==1:ports+=['.o_peer_data(peerd)', '.o_peer_valid(peero)']
 sv=f'''`timescale 1ns/1ps
module tb;
reg ck=0,rst=0;always #0.417 ck=~ck;
reg[255:0]data=0;reg[{np-1}:0]exp=0;reg[{max(1,len(variable)*2)-1}:0]sel=0;reg alt=0;
reg[63:0]peer=0;reg peerv=0;wire[63:0]peerd;wire peero;
wire[{np-1}:0]pv;wire[{64*no-1}:0]od;wire fault;
dsfd_vm_static_read_q{g} dut({','.join(ports)});
integer cy=0,bad=0,checks=0,j,p,s,prior_low=0,seed=1;reg prior_alt=0,prior_exp=0;
reg[{np-1}:0]ev[0:600];reg[{no-1}:0]ov[0:600];reg[{no*64-1}:0]ed[0:600];reg[63:0]ep[0:600];
function[63:0]value(input integer c,input integer slot);value=64'(c*1000003+slot*313+seed*7919+17);endfunction
initial for(integer k=0;k<=600;k=k+1)begin ev[k]=0;ov[k]=0;end
always @(posedge ck)if(rst)begin #0.01;
 if(pv!==ev[cy])bad=bad+1;
 for(integer q=0;q<{no};q=q+1)if(ov[cy][q])begin checks=checks+1;if(od[64*q+:64]!==ed[cy][64*q+:64])begin bad=bad+1;if(bad<5)$display("PAYLOAD cy%0d q%0d got%h exp%h",cy,q,od[64*q+:64],ed[cy][64*q+:64]);end end
'''
 if g==1:sv+=' if(peero!==ev[cy][0])bad=bad+1;if(ev[cy][0])begin checks=checks+1;if(peerd!==ep[cy])bad=bad+1;end\n'
 sv+=f'''end
initial begin
 if(!$value$plusargs("seed=%d",seed))seed=1;
 repeat(4)@(negedge ck);rst=1;repeat(5)@(negedge ck);
 for(j=0;j<400;j=j+1)begin
 @(negedge ck);cy=cy+1;
 peer=value(cy-1,4+prior_low);peerv=prior_alt&&prior_exp;
 alt=cy%2;
 for(p=0;p<4;p=p+1)data[64*p+:64]=value(cy,p);
 for(p=0;p<{np};p=p+1)exp[p]=((cy+p)%5!=0);
'''
 for z,p in enumerate(variable):sv+=f" sel[{2*z}+:2]=2'((cy+{p}+seed)%4);\n"
 for p in range(np):
  sl=f'(cy+{p}+seed)%4'if p in variable else str(fixed(p));want=f'exp[{p}]'+('&& !alt'if g==0 and p==1 else'&&alt'if g==1 and p==0 else'')
  sv+=f' ev[cy][{p}]={want};\n'
  if g==1 and p==0:sv+=f' ep[cy]=value(cy,{sl});\n';continue
  o=p-1 if g==1 else p
  sv+=f' ov[cy+1][{o}]=exp[{p}];ed[cy+1][64*{o}+:64]=value(cy,{sl});\n'
  if g==0 and p==1:sv+=f' if(alt)ed[cy+1][64*{o}+:64]=value(cy,4+{sl});\n'
 priorp=1 if g==0 else 0
 sv+=f''' prior_low=(cy+{priorp}+seed)%4;prior_alt=alt;prior_exp=exp[{priorp}];
 end
 @(negedge ck);cy=cy+1;exp=0;peer=value(cy-1,4+prior_low);peerv=prior_alt&&prior_exp;
 @(negedge ck);cy=cy+1;exp=0;peerv=0;repeat(2)@(negedge ck);
 if(fault)bad=bad+1;
 $display("NATIVE_LEAF %s q{g} checks %0d bad %0d",bad==0&&checks>500?"PASS":"FAIL",checks,bad);$finish;
end
endmodule
'''
 files=[r/'dsfd_vm_static_read_leaf.sv',r/'dsfd_vm_static_read_quartets.sv'];defines=['-DOT_VM_READ_MUT_SELECT']if mode=='mutant'else[]
elif kind=='v':
 nv=8 if g==1 else 5 if g==5 else np
 ports=['.ck(ck)','.rst_n(rst)','.i_expected(exp)','.i_slot(slot)','.i_partial_valid(pv)',".i_fault(8'd0)",'.o_valid(ov)','.fault(fault)']
 if g==0:ports+=['.i_peer_valid(peer)']
 sv=f'''`timescale 1ns/1ps
module tb;reg ck=0,rst=0;always #0.417 ck=~ck;
reg[{np-1}:0]exp=0;reg[{5*np-1}:0]slot=0;reg[{8*np-1}:0]pv=0;reg[7:0]peer=0;wire[{nv-1}:0]ov;wire fault;
dsfd_vm_static_read_v{g} dut({','.join(ports)});
integer cy=0,bad=0,checks=0,j,p,b,seed=1;reg[{np-1}:0]oldexp=0;reg oldalt=0;reg[{nv-1}:0]ev[0:600];
initial for(integer k=0;k<=600;k=k+1)ev[k]=0;
always @(posedge ck)if(rst)begin #0.01;if(ov!==ev[cy])begin bad=bad+1;if(bad<5)$display("VALID cy%0d got%h exp%h",cy,ov,ev[cy]);end checks=checks+{nv};end
initial begin
 if(!$value$plusargs("seed=%d",seed))seed=1;
 repeat(4)@(negedge ck);rst=1;repeat(5)@(negedge ck);
 for(j=0;j<400;j=j+1)begin
 @(negedge ck);cy=cy+1;
 for(b=0;b<8;b=b+1)begin pv[{np}*b+:{np}]=oldexp;
'''
 if g==0:sv+=f' pv[{np}*b+1]=oldexp[1]&&!oldalt;peer[b]=oldexp[1]&&oldalt;\n'
 if g==1:sv+=f' pv[{np}*b]=oldexp[0]&&oldalt;\n'
 sv+=f"end\n for(p=0;p<{np};p=p+1)begin exp[p]=(cy+p+seed)%5!=0;slot[5*p+:5]=5'({4*g}+(cy+p+seed)%4);end\n"
 if g==0:sv+=" slot[10+:5]=2;slot[15+:5]=3;slot[5+:5]=5'((cy%2)*4+(cy+seed)%4);\n"
 if g==1:sv+=" slot[0+:5]=5'((cy%2)*4+(cy+seed)%4);for(p=1;p<=4;p=p+1)slot[5*p+:5]=5'(3+p);\n"
 if g in(2,3,5):sv+=f" for(p=0;p<4;p=p+1)slot[5*p+:5]=5'({4*g}+p);\n"
 if g>=6:sv+=f" for(p=0;p<4;p=p+1)slot[5*p+:5]=5'({4*g}+p);\n"
 if g==1:sv+='ev[cy+1]=exp[8:1];\n'
 elif g==5:sv+='ev[cy+1]={exp[7:4],&exp[3:0]};\n'
 else:sv+='ev[cy+1]=exp;\n'
 sv+=f'''oldexp=exp;oldalt=cy%2;
 end
 @(negedge ck);cy=cy+1;exp=0;for(b=0;b<8;b=b+1)begin pv[{np}*b+:{np}]=oldexp;
'''
 if g==0:sv+=f' pv[{np}*b+1]=oldexp[1]&&!oldalt;peer[b]=oldexp[1]&&oldalt;\n'
 if g==1:sv+=f' pv[{np}*b]=oldexp[0]&&oldalt;\n'
 sv+=f'''end
 @(negedge ck);cy=cy+1;pv=0;peer=0;repeat(2)@(negedge ck);
 if(fault)bad=bad+1;$display("NATIVE_LEAF %s v{g} checks %0d bad %0d",bad==0&&checks>500?"PASS":"FAIL",checks,bad);$finish;
end endmodule
'''
 src=r/'dsfd_vm_static_read_valid.sv'
 if mode=='mutant':
  body=src.read_text();old='o_valid[0]<=&complete[3:0]'if g==5 else'o_valid[p]<=complete[p+(G==1?1:0)]';assert body.count(old)==1
  new='o_valid[0]<=~(&complete[3:0])'if g==5 else old+' ^ (p==0)'
  src=out/'mut_valid.sv';src.write_text(body.replace(old,new))
 files=[src,r/'dsfd_vm_static_read_valid_quartets.sv'];defines=[]
else:raise SystemExit('kind must q or v')
bench=out/'tb.sv';bench.write_text(sv)
subprocess.run(['iverilog','-g2012',*defines,'-s','tb','-o',str(out/'sim'),*map(str,files),str(bench)],check=True)
res=subprocess.run(['vvp',str(out/'sim'),'+seed=1'],text=True,capture_output=True,check=True);print(res.stdout,end='');(out/'run.log').write_text(res.stdout)
name=f'{kind}{g}'
if mode=='mutant':
 if f'NATIVE_LEAF FAIL {name} 'not in res.stdout:raise SystemExit('MUTANT NOT KILLED')
 raise SystemExit(1)
if f'NATIVE_LEAF PASS {name} 'not in res.stdout:raise SystemExit(2)
