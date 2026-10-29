"""Apply only qualified output-load delta to an existing one-hot physical leaf."""
from pathlib import Path
import sys
leaf,wrapper=map(Path,sys.argv[1:])
s=leaf.read_text();key='module ot_qwen_tp8_pv_join_t__leaf #';a=s.index(key);b=s.index('endmodule',a)+len('endmodule');m=s[a:b]
assert 'reg[6:1] sa' in m and 'reg[5:1] sb' in m, 'current one-hot operand source required'
assert m.count('RESET_PIN=0)(')==1 and 'OUTPUT_LOAD_LOCAL' not in m
m=m.replace('RESET_PIN=0)(', 'RESET_PIN=0, OUTPUT_LOAD_LOCAL=0)(',1)
old='''  if(jrun&&jage==J_OUT)y_hold<=jy;
  y<=(jrun&&jage==J_OUT)?jy:y_hold;                // port copy: same value/edge as the held result, drives only its pin
 end
'''
new=''' end
 generate if(OUTPUT_LOAD_LOCAL != 0)begin:g_output_load_local
  for(genvar q=0;q<32;q=q+1)begin:g_word
   (* keep = "true", dont_touch = "true" *) reg load_q;
   always @(posedge clk or negedge local_rst_n)
    if(!local_rst_n)load_q<=1'b0;
    else load_q<=nrun&&(nage==5'(J_OUT));
   always @(posedge clk)begin
    if(load_q)y_hold[16*q+:16]<=jy[16*q+:16];
    y[16*q+:16]<=load_q?jy[16*q+:16]:y_hold[16*q+:16];
   end
  end
 end else begin:g_output_load_legacy
  always @(posedge clk)begin
   if(jrun&&jage==J_OUT)y_hold<=jy;
   y<=(jrun&&jage==J_OUT)?jy:y_hold;
  end
 end endgenerate
'''
assert m.count(old)==1;m=m.replace(old,new,1)
w=wrapper.read_text();oldinst='ot_qwen_tp8_pv_join_t__leaf #(.J_LAT(7), .MUT(0), .RESET_PIN(1)) u_leaf'
assert w.count(oldinst)==1
w=w.replace(oldinst,oldinst.replace('.RESET_PIN(1)', '.RESET_PIN(1), .OUTPUT_LOAD_LOCAL(1)'))
leaf.write_text(s[:a]+m+s[b:]);wrapper.write_text(w)
