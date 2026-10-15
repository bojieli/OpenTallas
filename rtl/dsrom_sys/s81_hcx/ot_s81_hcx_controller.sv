`timescale 1ns/1ps
`default_nettype none
// Named physical owner of ALL HCX command/prefetch/join/CDC state.
// Related PLL clocks: cck 1.2 GHz, sk 0.9 GHz, fixed phase relation from reset.
// Fast commands use phase2/4; cmd_box payload stays stable through the job.
// Two-flop toggles transfer events; no acknowledgement/credit/ready exists.
// Both native raw output and fast public completion have COMPILED deadlines.
// Observed leaf-valid and CDC returns only verify those deadlines, never move
// them. FAST_CYC and RETURN_CYC must be bound from the real physical calendar.
module ot_s81_hcx_controller #(
 parameter integer RL=4,FAST_CYC=0,
 parameter [95:0] RETURN_CYC={6{16'd264}}
)(
 input wire cck,crst_n,sk,srst_n,
 input wire [84:0] c_cmd,
 output reg [8:0] c_done,
 output reg [1:0] c_st,
 output wire [7:0] rq_v,
 output wire [111:0] rq_row,
 input wire [7:0] rs_v,
 output wire stage_begin,stage_v,
 output wire [6:0] stage_word,
 output wire leaf_cmd_v,
 output reg leaf_ffn,
 output reg [5:0]leaf_layer,
 input wire [5:0] leaf_v,leaf_fault,
 input wire [191:0] leaf_d,
 output reg t_raw_v,
 output reg [191:0] t_raw_d
);
 function automatic integer max_return(input[95:0]x);
  max_return=0;for(integer l=0;l<6;l=l+1)if(x[16*l+:16]>max_return)max_return=x[16*l+:16];
 endfunction
 localparam integer JOIN=max_return(RETURN_CYC)+1;
 reg[1:0]phase;
 reg[83:0]cmd_box;
 reg req_toggle;
 reg[15:0]ctick;
 reg c_busy,cfault,have_return;
 reg[7:0]ctag;
 reg esync1,esync2,eseen;
 reg ssync1,ssync2;
 reg sreq1,sreq2,sseen;
 reg native_busy,run;
 reg[15:0]age;
 reg[7:0]stag,done_tag;
 reg done_toggle,sfault;
 reg[191:0]raw_buf;
 wire event_s=sreq2!=sseen;
 wire pfault;
 wire[5:0]expected;
 generate for(genvar l=0;l<6;l=l+1)begin:g_due
  assign expected[l]=run && age+1'b1==RETURN_CYC[16*l+:16];
 end endgenerate
 // Only metadata lives in this controller. The 4096-bit VM payload is a
 // real staged die multicast directly to projection-leaf pin registers.
 ot_s81_hcx_prefetch #(.RL(RL))prefetch(
  .clk(sk),.rst_n(srst_n),.start(event_s),.h_base_row(cmd_box[21:8]),
  .rq_v(rq_v),.rq_row(rq_row),.rs_v(rs_v),
  .stage_begin(stage_begin),.stage_v(stage_v),.stage_word(stage_word),.cmd_v(leaf_cmd_v),.fault(pfault));
 always @(posedge sk or negedge srst_n)begin
  if(!srst_n)begin sreq1<=0;sreq2<=0;sseen<=0;native_busy<=0;run<=0;age<=0;done_toggle<=0;sfault<=0;t_raw_v<=0;end
  else begin
   sreq1<=req_toggle;sreq2<=sreq1;t_raw_v<=0;
   if(event_s)begin
    sseen<=sreq2;
    if(native_busy || cmd_box[30:28]!=0 || cmd_box[27:22]>42)sfault<=1;
    stag<={cmd_box[83],cmd_box[6:0]};leaf_ffn<=cmd_box[7];leaf_layer<=cmd_box[27:22];native_busy<=1;
   end
   if(leaf_cmd_v)begin run<=1;age<=0;end
   if(leaf_v!=expected)sfault<=1;
   if(run)begin
    age<=age+1'b1;
    for(integer l=0;l<6;l=l+1)if(expected[l])raw_buf[32*l+:32]<=leaf_d[32*l+:32];
    if(age+1'b1==JOIN)begin
     t_raw_v<=1;t_raw_d<=raw_buf;done_tag<=stag;done_toggle<=!done_toggle;
     native_busy<=0;run<=0;age<=0;
    end
   end
   if(pfault || |leaf_fault)sfault<=1;
  end
 end
 always @(posedge cck or negedge crst_n)begin
  if(!crst_n)begin phase<=0;req_toggle<=0;ctick<=0;c_busy<=0;cfault<=0;c_done<=0;c_st<=0;esync1<=0;esync2<=0;eseen<=0;ssync1<=0;ssync2<=0;have_return<=0;end
  else begin
   phase<=phase+1'b1;c_done[8]<=0;c_st<={1'b1,cfault|ssync2};
   esync1<=done_toggle;esync2<=esync1;ssync1<=sfault;ssync2<=ssync1;
   if(c_cmd[84])begin
    if(c_busy || phase!=2 || FAST_CYC<1)cfault<=1;
    cmd_box<=c_cmd[83:0];ctag<={c_cmd[83],c_cmd[6:0]};req_toggle<=!req_toggle;
    c_busy<=1;ctick<=0;have_return<=0;
   end
   if(esync2!=eseen)begin
    eseen<=esync2;have_return<=1;
    if(!c_busy || done_tag!=ctag || ctick+1'b1!=FAST_CYC-1)cfault<=1;
   end
   if(c_busy)begin
    ctick<=ctick+1'b1;
    if(ctick+1'b1==FAST_CYC)begin
     c_done<={1'b1,ctag};c_busy<=0;have_return<=0;
     if(!have_return)cfault<=1;
    end
   end
  end
 end
endmodule
`default_nettype wire
