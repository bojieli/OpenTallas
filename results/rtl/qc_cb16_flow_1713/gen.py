import re,json
from pathlib import Path
r=Path(__file__).resolve().parent;c=json.load(open(r/'dag_candidate.json'));classes=sorted({(sum(b-a+1 for a,b in m['sink_bits']),m['tree_align']) for m in c['members']})
src=(r.parents[2]/'tools/die_plan/bind.py').read_text();module=re.search(r'module ot_dp_dly\b[\s\S]*?endmodule',src)[0];(r/'ot_dp_dly.sv').write_text('`timescale 1ns/1ps\n'+module+'\n')
body=['`timescale 1ns/1ps','module tb;','reg clk=0;always #0.4165 clk=~clk;','integer cycle=0,mut=0,checks=0;','initial begin if($value$plusargs("MUT=%d",mut))begin end end']
for k,(w,d) in enumerate(classes):
 v=0 if w==516 else 512
 body += [f'reg [{w-1}:0] din{k}=0; wire [{w-1}:0] q{k};reg [{w-1}:0] h{k}[0:{d-1}];reg [63:0] rng{k}=64\'h{0x123456789abcdef0+k:016x};',f'genvar g{k}; generate for(g{k}=0;g{k}<{w};g{k}=g{k}+1)begin : field{k}',f'ot_dp_dly #(.W(1),.D({d})) u(.clk(clk),.d(din{k}[g{k}]),.q(q{k}[g{k}]));end endgenerate']
 body += [f'wire [{w-1}:0] check{k};']
 if (w,d)==(516,1):body += [f'assign check{k}=(mut==1)?din{k}:q{k};']
 elif (w,d)==(514,16):body += [f'wire early{k};ot_dp_dly #(.W(1),.D(15)) early(.clk(clk),.d(din{k}[512]),.q(early{k}));',f'assign check{k}={{q{k}[513],(mut==2?early{k}:q{k}[512]),q{k}[511:0]}};']
 else:body += [f'assign check{k}=q{k};']
 body += [f'always @(posedge clk) begin : replay{k}',f'integer j,b;if(cycle>64)begin',f'if(check{k}!==h{k}[{d-1}])begin $display("CB16_FLOW_MISMATCH class={k} W={w} D={d} cycle=%0d mut=%0d",cycle,mut);$fatal(1,"packet/timing mismatch");end',f'end for(j={d-1};j>0;j=j-1)h{k}[j]=h{k}[j-1];h{k}[0]=din{k};',f'for(b=0;b<{w};b=b+1)begin rng{k}=rng{k}^(rng{k}<<13);rng{k}=rng{k}^(rng{k}>>7);rng{k}=rng{k}^(rng{k}<<17);din{k}[b]<=rng{k}[0];end',f'din{k}[{v}]<=((cycle%11)<7);din{k}[513]<=((cycle%251)==0);end']
body += ['always @(posedge clk) begin cycle<=cycle+1;if(cycle==4096)begin $display("CB16_PAD_FLOW_PASS cycles=%0d classes='+str(len(classes))+'",cycle);$finish;end end','endmodule']
(r/'tb.sv').write_text('\n'.join(body)+'\n');(r/'classes.json').write_text(json.dumps(classes));print('CLASSES',classes)
