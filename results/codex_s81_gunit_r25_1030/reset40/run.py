from pathlib import Path
import re,json,subprocess,sys
R=Path(__file__).parent;sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-s81-start-data-1030/tools/die_plan');import reset_consumers as E
text=(R/'source_before.sv').read_text();calls=E._calls(text);tree=json.load(open(R/'tree.json'));relays={x['q']:x for x in tree['relays']};needed={}
for target in ['rst_n_t19','rst_n_t40']:
 q=target
 while q!='rst_root_n':
  x=relays[q];needed[x['name']]=x;q=x['d']
assert all(calls[n]['ports']['clk'][0]=='clk'for n in needed)
bind=(R/'bind_cells.sv').read_text();prim=[]
for name in ['ot_dp_rrelay','ot_dp_st']:
 m=re.search(r'\bmodule\s+'+name+r'\s*(?:#|\()',bind);assert m
 prim.append(bind[m.start():bind.index('endmodule',m.start())+len('endmodule')])
mid='\n'.join('wire '+x['q']+';'for x in needed.values())+'\n'
for n,x in needed.items():mid+=f'ot_dp_rrelay {n} (.clk(clk), .d({x["d"]}), .q({x["q"]}));\n'
mut=relays['rst_n_t40']['d'];assert relays[mut]['depth']==6
bench='''`timescale 1ps/1ps
module tb;
reg clk=0; always #416.5 clk=~clk;
reg rst_root_n=0; reg[264:0] d=0;reg ea=0;
wire[264:0] qo,qn,qm,qp;wire eo,en,em,ep;
integer n=0,checks=0,depthbad=0,payloadbad=0;
'''+mid+f'''
ot_dp_st #(.W(265)) old_station(clk,rst_n_t19,d,ea,qo,eo);
ot_dp_st #(.W(265)) new_station(clk,rst_n_t40,d,ea,qn,en);
ot_dp_st #(.W(265)) bad_depth(clk,{mut},d,ea,qm,em);
ot_dp_st #(.W(265)) bad_payload(clk,rst_n_t40,d^265'd1,ea,qp,ep);
initial begin
 for(n=0;n<2400;n=n+1)begin
  @(negedge clk);
  if(n==64||n==832||n==1600)rst_root_n=1;
  if(n==768||n==1536)rst_root_n=0;
  d={{$random,$random,$random,$random,$random,$random,$random,$random,$random}};
  if(n%83==2)d[164:133]=32'hx;
  ea=((n%768)<96||(n%768)>740)?1:(n%2);
  @(posedge clk);#1;
  if(n>=64)begin
   checks=checks+1;
   if(qo!==qn||eo!==en)$fatal(1,"reset localization changed native fullW265 transport at %0d",n);
   if(qo!==qm||eo!==em)depthbad=depthbad+1;
   if(qo!==qp||eo!==ep)payloadbad=payloadbad+1;
  end
 end
 if(depthbad==0||payloadbad==0)$fatal(1,"mutant did not fire");
 $display("PASS833ps checks=%0d resetdepth_mutant=%0d payload_mutant=%0d cold64 warm64/64 addedcycles0",checks,depthbad,payloadbad);$finish;
end
endmodule
'''
(R/'coupon.sv').write_text('\n'.join(prim)+'\n'+bench)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(R/'coupon'),str(R/'coupon.sv')],check=True)
p=subprocess.run(['vvp',str(R/'coupon')],text=True,capture_output=True,check=True);(R/'run.log').write_text(p.stdout+p.stderr);print(p.stdout)
decl=[dict(instance='u_ist_unit_i0_0',pin='rst_n',old_reset='rst_n',new_reset=mut,clock_net='clk')]
try:E.localize(text,decl,tree)
except E.ResetConsumerError as e:(R/'depth_guard_control.txt').write_text('REFUSED '+str(e)+'\n')
else:raise AssertionError('unequal-depth reset accepted')
