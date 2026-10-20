`default_nettype none
// L2H-IDXSEL s3 (LEAD3-HBM route B): the CTL child tile of the landed IDX selector cluster ot_hbm_idx_selector_s3.
// Holds the die-port pin flops of the control word (op/pass/addr/k), the reset landing (2 sync + region stage), the
// choose-bin pipeline (4-way histogram sums, rank recurrence, threshold, pass-2 tie split) and the sticky fault.
// Every crossing to the four quadrant tiles is a LANDED net in the generated parent (+3 edges each, fixed latency):
//   ctl -> q: cw (control word, one output pin flop stage after the input pin flop), thr (= the threshold register),
//             ties_<q> (tie budget registers);
//   q -> ctl: ret_<q> = {op1, op3, op5, pass, addr[5:0], hrd[13:0]} (the quadrant's histogram read WITH the op tags of
//             the edge that issued it), qf_<q> (sticky hazard flags).
// The choose pipeline runs on the RETURNED stream: stage A = the input pin flops of ret_<q> (quadrant 0's tags drive
// the pipe; all four quadrants' tags must agree, else fault), B = sums, then threshold / found / rank_left exactly as
// the flat core's B -> C -> D (same arithmetic).  The op1 frame clear (threshold 0, rank_left <= k, found 0, k range
// check) and the op 8 fault (selected-only face) act on the ctl's own pin-flop copy of the control word.
// Schedule: the threshold reaches a quadrant's compare 12 edges after that quadrant read the deciding histogram bin and
// the ties 13 edges after (flat core 3 / 4): the IDX compiler idles sel_choose_rt = 8 more edges after every op5 run
// before the next op3/op4/op6 (tools/hbm_idx_static_calendar.py, registered_s3).  Hazard checks (diagnostic, sticky):
// op1 while any op5 is still in the choose loop (outstanding counter), op5 within 2 edges after an op3 on the returned
// stream (the flat core's check, same relative window), op 8, k out of range, quadrant tags disagree, any qf.
// DMUT (bench only): 6 = the B stage takes the tags straight from the ret pins (one edge early vs the sums).
module ot_hidx_s3_ctl #(parameter integer DMUT=0)(
 input wire clk,
 input wire rst_n,
 input wire [3:0] op,input wire [1:0] pass,input wire [7:0] addr,input wire [9:0] k,
 output reg [13:0] cw,
 output reg [15:0] thr,
 output reg [13:0] ties_0,ties_1,ties_2,ties_3,
 input wire [24:0] ret_0,ret_1,ret_2,ret_3,
 input wire qf_0,qf_1,qf_2,qf_3,
 output reg fault
);
 function automatic [15:0] pmask(input [1:0] p);
  pmask=(p==0)?16'd0:((p==1)?16'hf800:16'hffc0);
 endfunction
 function automatic [3:0] pshift(input [1:0] p);
  pshift=(p==0)?4'd11:((p==1)?4'd6:4'd0);
 endfunction
 wire [0:0] rr_n;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr_n));
 wire rc_n=rr_n[0];
 // ---------------- input pin flops ----------------
 (* keep *) reg [13:0] cw_r;(* keep *) reg [9:0] k_r;
 reg [24:0] a_ret[0:3];reg [3:0] a_qf;
 always @(posedge clk)begin
  cw_r<={addr,pass,op};k_r<=k;
  cw<=cw_r;                                      // output pin flop of the control word (-> 4 landings)
  a_ret[0]<=ret_0;a_ret[1]<=ret_1;a_ret[2]<=ret_2;a_ret[3]<=ret_3;
  a_qf<={qf_3,qf_2,qf_1,qf_0};
 end
 wire [3:0] c_op=cw_r[3:0];
 // stage A (returned stream): tags of quadrant 0, histogram reads of all four
 wire [10:0] a_tag=(DMUT==6)?ret_0[24:14]:a_ret[0][24:14];
 wire a_op1=a_tag[10],a_clr=a_tag[9],a_v=a_tag[8];wire [1:0] a_pass=a_tag[7:6];wire [5:0] a_addr=a_tag[5:0];
 wire a_tagbad=(a_ret[1][24:14]!=a_ret[0][24:14])||(a_ret[2][24:14]!=a_ret[0][24:14])||(a_ret[3][24:14]!=a_ret[0][24:14]);
 wire [13:0] hrd[0:3];
 for(genvar q=0;q<4;q=q+1)begin:gh
  assign hrd[q]=a_ret[q][13:0];
 end
 reg [15:0] threshold;
 reg [13:0] rank_left;
 reg found;
 reg b_v,b_clr,z_v,z_clr,b_op1;reg [1:0] b_pass;reg [5:0] b_addr;reg [15:0] b_all;reg [15:0] b_s[0:3];reg [13:0] b_h[0:3];
 reg d_go;reg [13:0] d_r;reg [15:0] d_s[0:3];reg [13:0] d_h[0:3];
 reg [13:0] ties[0:3];
 reg [6:0] out5;                                 // op5 issued at the ctl pin and not yet through stage B
 reg [15:0] thr_n;
 always @*begin
  thr_n=threshold;
  if(c_op==1)thr_n=16'd0;
  if(b_v&&!found&&!({2'b0,rank_left}>b_all))thr_n=(threshold&pmask(b_pass))|(16'(b_addr)<<pshift(b_pass));
  if(!rc_n)thr_n=16'd0;
 end
 always @(posedge clk or negedge rc_n)begin
  if(!rc_n)begin
   threshold<=0;rank_left<=0;found<=0;fault<=0;b_v<=0;b_clr<=0;z_v<=0;z_clr<=0;b_op1<=0;d_go<=0;out5<=0;
   for(integer q=0;q<4;q=q+1)ties[q]<=0;
  end else begin
   if(|a_qf)fault<=1;
   b_v<=a_v;b_clr<=a_clr;b_op1<=a_op1;
   z_v<=b_v;z_clr<=b_clr;
   out5<=out5+7'(c_op==5)-7'(b_v);
   d_go<=0;
   threshold<=thr_n;
   if(c_op==1)begin rank_left<={4'b0,k_r};found<=0;if(k_r>512||k_r==0)fault<=1;end
   if(c_op==8)fault<=1;                          // selected-only face: no emit readback (as ot_hbm_idx_selector_static_sel)
   if(b_clr)found<=0;
   if(b_v&&!found)begin
    if({2'b0,rank_left}>b_all)rank_left<=rank_left-b_all[13:0];
    else begin
     found<=1;
     if(b_pass==2)d_go<=1;
    end
   end
   if(d_go)for(integer q=0;q<4;q=q+1)begin
    if({2'b0,d_r}<=d_s[q])ties[q]<=0;
    else if({2'b0,d_r}-d_s[q]>={2'b0,d_h[q]})ties[q]<=d_h[q];
    else ties[q]<=14'({2'b0,d_r}-d_s[q]);
   end
   if((c_op==1&&(out5!=0||b_v))||(a_v&&(b_clr||z_clr))||a_tagbad)fault<=1;
  end
 end
 always @(posedge clk)begin
  b_pass<=a_pass;b_addr<=a_addr;
  for(integer q=0;q<4;q=q+1)b_h[q]<=hrd[q];
  b_s[0]<=16'd0;b_s[1]<=16'(hrd[0]);b_s[2]<=16'(hrd[0])+16'(hrd[1]);
  b_s[3]<=(16'(hrd[0])+16'(hrd[1]))+16'(hrd[2]);
  b_all<=(16'(hrd[0])+16'(hrd[1]))+(16'(hrd[2])+16'(hrd[3]));
  d_r<=rank_left;
  for(integer q=0;q<4;q=q+1)begin d_s[q]<=b_s[q];d_h[q]<=b_h[q];end
 end
 // ---------------- output pin flops (registers driving the landings) ----------------
 always @*begin
  thr=threshold;
  ties_0=ties[0];ties_1=ties[1];ties_2=ties[2];ties_3=ties[3];
 end
endmodule
`default_nettype wire
