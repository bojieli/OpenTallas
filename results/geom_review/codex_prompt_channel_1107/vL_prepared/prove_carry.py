from pathlib import Path
import re,subprocess,json
p=Path(__file__).parent
q='\\u_control.u_control.u_host.u_core.c_reqs '
def extract(filename,name):
 s=p.joinpath(filename).read_text()
 assigns=[]
 for n in ['_0856_','_1610_','_1611_','_0674_','_1612_']:
  a=re.search(r'^  assign '+n+r' = [^;]*;',s,re.M).group(0)
  assigns.append(a)
 a=re.search(r'  always @\(posedge ck, negedge rr_c_l28\)\n    if \(!rr_c_l28\) '+re.escape(q)+r'<= 32.d0;\n    else[^;]*;',s,re.S).group(0)
 extra=''
 if name!='gold':
  extra=s[s.index('  reg ot_creq_c8'):s.index('  assign _0856_ =')]
 body='\n'.join(assigns)+'\n'+a+'\n'+extra
 body=body.replace(q,'count ').replace('\\u_control.u_control.u_host.u_core.m_bvalid ','mb ').replace('\\u_control.u_control.u_host.u_core.d_st ','state ')
 body=re.sub(r'\(\*.*?\*\)','',body)
 return 'module '+name+'(input ck,rr_c_l28,_1021_,mb,input [3:0]state,output reg[31:0]count);\nwire[31:0]_0856_,_1610_,_1611_,_0674_;wire _1612_;\n'+body+'\nendmodule\n'
gold=extract('gold.v','gold');new=extract('new.v','cand')
mut=new.replace('module cand(','module mutant(').replace('[15:8] + ot_creq_c8','[15:8] + ot_creq_c16')
p.joinpath('exact_blocks.v').write_text(gold+new+mut)
# Use actual patch RHS in one-step combinational induction: state flags are exact reductions.
s=p.joinpath('carry_patch.txt').read_text();rhs=re.search(r'assign _0856_ = (.*?);',s,re.S).group(1).replace(q,'count ')
checks=[]
for n in [8,16,24]:
 flag_expr=re.search(r'ot_creq_c'+str(n)+r' <= \((.*)\);',s).group(1).replace(q,'count ')
 checks.append(f'wire next_c{n}=inc ? ({flag_expr}) : ot_creq_c{n};')
step='''module step(input [31:0] count,input inc,output bad);
wire ot_creq_c8=&count[7:0],ot_creq_c16=&count[15:0],ot_creq_c24=&count[23:0];
wire[31:0] chunk='''+rhs+''';
wire[31:0] next=inc?chunk:count;
'''+ '\n'.join(checks)+'''
assign bad=(next != count+inc) | (next_c8 != (&next[7:0])) | (next_c16 != (&next[15:0])) | (next_c24 != (&next[23:0]));
endmodule
'''
p.joinpath('induction.v').write_text(step)
r=subprocess.run(['yosys','-Q','-p',f'read_verilog {p}/induction.v; prep -top step -flatten; sat -verify -prove bad 0 -show-inputs'],text=True,capture_output=True)
p.joinpath('induction.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
# Actual extracted flop blocks exercise reset, all enable conditions and boundaries.
tb='''module tb;reg ck=0,rst=0,e=0,mb=0;reg[3:0]st=0;wire[31:0] g,n,m;
gold G(ck,rst,e,mb,st,g);cand N(ck,rst,e,mb,st,n);mutant M(ck,rst,e,mb,st,m);
integer i,j,diffs=0;reg[31:0]seeds[0:11];
always #5 ck=~ck;
task check;begin @(posedge ck);#1;if(g!==n)$fatal(1,"mismatch %h %h",g,n);if(g!==m)diffs=diffs+1;end endtask
initial begin
seeds[0]=0;seeds[1]='hfd;seeds[2]='hfe;seeds[3]='hff;seeds[4]='hfffd;seeds[5]='hfffe;seeds[6]='hffff;seeds[7]='hfffffd;seeds[8]='hfffffe;seeds[9]='hffffff;seeds[10]='hfffffffe;seeds[11]='hffffffff;
#1;rst=1;#1;rst=0;check();@(negedge ck);rst=1;
for(j=0;j<12;j=j+1)begin
@(negedge ck);G.count=seeds[j];N.count=seeds[j];M.count=seeds[j];
N.ot_creq_c8=&seeds[j][7:0];N.ot_creq_c16=&seeds[j][15:0];N.ot_creq_c24=&seeds[j][23:0];
M.ot_creq_c8=&seeds[j][7:0];M.ot_creq_c16=&seeds[j][15:0];M.ot_creq_c24=&seeds[j][23:0];
for(i=0;i<40;i=i+1)begin e=1;mb=1;st=11;check();@(negedge ck);end
end
for(i=0;i<10000;i=i+1)begin e=$random;mb=$random;st=$random;check();@(negedge ck);end
rst=0;#1;if(g!==0 || n!==0)$fatal(1,"async reset");check();@(negedge ck);rst=1;
for(i=0;i<100;i=i+1)begin e=1;mb=1;st=11;check();@(negedge ck);end
if(diffs==0)$fatal(1,"mutant not distinguished");$display("PASS exact extracted sequential blocks; mutant %0d differences",diffs);$finish;
end endmodule
'''
p.joinpath('tb.v').write_text(tb)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(p/'exact_blocks.v'),str(p/'tb.v')],check=True)
r=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True);p.joinpath('sequential.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
print(r.stdout.strip());print('PASS arbitrary 32-bit one-step SAT and carry-state invariant induction, reset base zero')
