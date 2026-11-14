from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--patched',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
old=(a.source/'ot_s81ph_hq_slice.sv').read_text();new=(a.patched/'ot_s81ph_hq_slice.sv').read_text()
def extract(s,name):
 inp=s[s.index('    reg            i0_v,'):s.index('`ifndef OT_BKQ_SPLIT',s.index('    reg            i0_v,'))]
 # The old/new input, H8 nibble compare, key and ingest state are actual source.
 r1=s[s.index('    wire rpd ='):s.index('    // tsw:',s.index('    wire rpd ='))]
 sign=s[s.index('    wire [W*2-1:0] r1sg;'):s.index('    wire [W-1:0]    c1_gt_d',s.index('    wire [W*2-1:0] r1sg;'))]
 kp=s[s.index('    function automatic [15:0] kp'):s.index('    endfunction',s.index('    function automatic [15:0] kp'))+len('    endfunction')]
 body=f'''module {name}(input clk,rst_n,acc,rp_acc,in_last,t2_fl,input [15:0] in_lv,input [255:0] in_val,input [319:0] in_idx,input [63:0] in_sg,input [127:0] c_Tc,input [31:0] c_Btc,input [591:0] mem_rdata,output [591:0] lane_view,replay,output [255:0] key_view,output [31:0] sign_view,output [31:0] mask_view,output [143:0] cmp_view,output [4:0] controls);
 localparam integer W=16,IW=20,EW=37,MW=592,NG=22,GB=27,HLAT=1,MUT=0;
 genvar gl,gg;
 wire in_last_l=in_last;wire [15:0]in_lv_l=in_lv;wire [255:0]in_val_l=in_val;wire[319:0]in_idx_l=in_idx;
 wire [MW-1:0]r1_d;
'''+kp+'\n'+inp+'\n'+r1+'\n'+sign+'''
 reg[15:0]s_hcr;always @(posedge clk)s_hcr<=i1_s_d;
 assign lane_view=i0_lane;assign replay=r1_d;assign key_view=i1_k;assign sign_view=r1sg;assign mask_view={i1_fm,s_hcr};assign controls={i0_v,i0_rp,i0_last,i1_v,i1_fl};
 for(genvar cg=0;cg<16;cg=cg+1)begin:obs
 assign cmp_view[9*cg+:9]={g_i1[cg].cmp_gt,g_i1[cg].cmp_eq,g_i1[cg].hi_match};end
endmodule
'''
 if name=='i0_new':body=body.replace('ot_s81ph_hlk #(.W(W*(17+IW)), .EN(HLAT)) u_fl_i0out','i0_probe_hlk #(.W(W*(17+IW)), .EN(HLAT)) u_fl_i0out')
 return body
h=old[old.index('module ot_s81ph_hlk #'):];h=h[:h.index('endmodule')+9]
hm=h.replace('module ot_s81ph_hlk #','module i0_probe_hlk #').replace('always_latch if (!clk) l <= d;','''`ifdef I0_OUT_STALE_MUT
        always @(posedge clk) l <= d; // extra-cycle mutant ONLY on new forwarding hop
`else
        always_latch if (!clk) l <= d;
`endif''')
tb=r'''
module tb;
 reg clk=0,rst_n=0,acc=0,rp_acc=0,in_last=0,t2_fl=0;always #5 clk=~clk;
 reg[15:0]lv=0;reg[255:0]val=0;reg[319:0]idx=0;reg[63:0]sg=0;reg[127:0]th=0;reg[31:0]bt=0;reg[591:0]mem=0;
 wire[591:0]lane_a,lane_b,r_a,r_b;wire[255:0]key_a,key_b;wire[31:0]sign_a,sign_b,mask_a,mask_b;wire[143:0]cmp_a,cmp_b;wire[4:0]ctl_a,ctl_b;
 i0_ref a(clk,rst_n,acc,rp_acc,in_last,t2_fl,lv,val,idx,sg,th,bt,mem,lane_a,r_a,key_a,sign_a,mask_a,cmp_a,ctl_a);
 i0_new b(clk,rst_n,acc,rp_acc,in_last,t2_fl,lv,val,idx,sg,th,bt,mem,lane_b,r_b,key_b,sign_b,mask_b,cmp_b,ctl_b);
 reg[31:0]seed=32'h9110fa5d;integer i,j,g,checks=0,lane_errors=0,receive_errors=0,compare_errors=0,control_errors=0,resets=0,replays=0,negzero=0;
 function automatic[31:0]rng(input[31:0]x);reg[31:0]t;begin t=x^(x<<13);t=t^(t>>17);rng=t^(t<<5);end endfunction
 always @(posedge clk)begin
  if(i>6 && rst_n)begin
   checks=checks+1;
   // Actual receiving edge, before source NBA updates.
   if(lane_a!==lane_b)lane_errors=lane_errors+1;
   #1;
   if({r_a,key_a,sign_a,mask_a}!=={r_b,key_b,sign_b,mask_b})receive_errors=receive_errors+1;
   if(cmp_a!==cmp_b)compare_errors=compare_errors+1;
   if(ctl_a!==ctl_b)control_errors=control_errors+1;
  end
 end
 initial begin
  for(i=0;i<4096;i=i+1)begin
   @(negedge clk);#1;rst_n=(i>3 && i%251!=0);if(!rst_n)resets=resets+1;
   seed=rng(seed);{acc,rp_acc,in_last,t2_fl}=seed[3:0];if(acc&&rp_acc)replays=replays+1;lv=seed[31:16];
   for(g=0;g<16;g=g+1)begin
    seed=rng(seed);val[16*g+:16]=seed[15:0];
    if(i%32==0)begin val[16*g+:16]=16'h8000;negzero=negzero+1;end
    if(i%32==1)val[16*g+:16]=16'hff80;
    sg[4*g+:4]={4{val[16*g+15]}};
    seed=rng(seed);idx[20*g+:20]=seed[19:0];
   end
   for(j=0;j<128;j=j+1)begin seed=rng(seed);th[j]=seed[0];end
   for(j=0;j<32;j=j+1)begin seed=rng(seed);bt[j]=seed[0];end
   for(j=0;j<592;j=j+1)begin seed=rng(seed);mem[j]=seed[0];end
   @(posedge clk);#2;
  end
  if(checks<4000 || replays==0 || negzero==0 || resets<2)$fatal(1,"missing coverage");
  if(compare_errors!=0 || control_errors!=0)$fatal(1,"untouched H8/control path changed");
`ifdef I0_OUT_STALE_MUT
  if(lane_errors==0 || receive_errors==0)$fatal(1,"new-hop stale mutant survived");
  $display("I0_OUT_HLAT_MUTANT_KILLED checks=%0d lane_errors=%0d receive_errors=%0d H8_errors=%0d control_errors=%0d",checks,lane_errors,receive_errors,compare_errors,control_errors);
`else
  if(lane_errors!=0 || receive_errors!=0)$fatal(1,"forwarding exactness failed");
  $display("I0_OUT_HLAT_EXACT_PASS checks=%0d payload_bits=592 replays=%0d negative_zero_lanes=%0d resets=%0d H8_errors=0 control_errors=0 cycle_delta=0",checks,replays,negzero,resets);
`endif
  $finish;
 end
endmodule
'''
a.out.write_text('`timescale 1ns/1ps\n`define OT_BKQ_FO8\n`define OT_BKQ_R1C8\n`define OT_BKQ_I0_OUT_HLAT\n'+h+'\n'+hm+'\n'+extract(old,'i0_ref')+'\n'+extract(new,'i0_new')+'\n'+tb)
