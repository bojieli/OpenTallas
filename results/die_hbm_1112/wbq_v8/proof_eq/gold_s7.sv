`timescale 1ns/1ps
`default_nettype none
// ROOT S7: private source, shared ot_wbq_split.sv/SW untouched.
// Defaults CBREG=0/SSTOPREG=0 match vS6. Kit opt-in adds exactly +1 fifo_clk
// input cycle on copy_bank and s_stop; parent fault/inflight qualification is
// required before adoption. No payload/valid/output cycle added. No fences.
module ot_wbq_root_s7_grp #(parameter integer G=0, parameter integer CRED=4, parameter integer MUT=0, parameter integer CBREG=0, parameter integer SSTOPREG=CBREG, parameter integer RSTCP=1, parameter integer O8=0)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,input wire [3:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire g_credit,
 output wire root_ready,
 output wire g_v,output wire [285:0] g_d
);
 // CBREG=1 adds one fifo-clock bank input cycle; SSTOPREG independently adds one stop cycle.
 // SSTOPREG=0 preserves dynamic fault-stop timing; +1 bank pin cycle remains schedulable.
 // SSTOPREG=1 needs parent qualification for the extra stop-response edge.
 wire core_s_stop;
 if(SSTOPREG) begin : g_stopreg
  (* keep *) reg q;
  always @(posedge fifo_clk) q <= s_stop;
  assign core_s_stop=q;
 end else begin : g_stopwire
  assign core_s_stop=s_stop;
 end
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 // V8 (HBM-CORES-C 11-12): srst loads (copy_row/pending_row/read_pending/fifo wclk side) spread over kept first-stage + output copies (<= OT_RST_COPIES_MAX each);
 // same release edge as the single flop (ot_reset_sync TREE form), drv RESETN slew class of g0 clk52.
 ot_reset_sync #(.OUTPUT_COPIES(RSTCP),.TREE(RSTCP>1?1:0)) u_root_reset(.clk(fifo_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 assign root_ready=srst;
 wire [255:0] wd[0:3];
 assign wd[0]=wd0;assign wd[1]=wd1;assign wd[2]=wd2;assign wd[3]=wd3;
 reg [31:0] base[0:1];reg [11:0] total[0:1];reg [11:0] committed[0:1];
 reg filling,fill_bank;reg [11:0] ordinal;
 // O8=1: ordinal8 == ordinal+8 (13 bit, unwrapped) kept as a register; the fill compare and the committed value read it instead of re-adding.
 reg [12:0] ordinal8;
 (* keep *) wire [12:0] inv_chk = {1'b0,ordinal}+13'd8;
 reg copy_q;reg [6:0] copy_row[0:3];reg [5:0] pending_row[0:3];reg [3:0] read_pending;
 wire [3:0] fifo_full,fifo_empty,fifo_we,fifo_re,mem_read;
 wire [287:0] fifo_head[0:3];wire [255:0] mem_data[0:3];
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:g_lane
  localparam integer GL=4*G+g;
  wire [4:0] lane={root_id,3'(GL)};
  wire [6:0] row=copy_row[g];
  // CODEX bank-face +1 PIN CYCLE: independent kept copy per macro lane.
  // Removes the measured face-bank broadcast from committed select and macro CE.
  wire local_copy_bank, local_s_stop;
  if (CBREG) begin : g_cbreg
   (* keep *) reg q;
   always @(posedge fifo_clk) q <= copy_bank;
   assign local_copy_bank = q;
  end else begin : g_cbwire
   assign local_copy_bank = copy_bank;
  end
  if(SSTOPREG) begin : g_stopreg
   (* keep *) reg q;
   always @(posedge fifo_clk) q <= s_stop;
   assign local_s_stop=q;
  end else begin : g_stopwire
   assign local_s_stop=s_stop;
  end
  wire [31:0] sector=base[local_copy_bank]+{pending_row[g],5'b0}+lane;
  assign fifo_we[g]=copy_q&&read_pending[g]&&!fifo_full[g]&&!local_s_stop;
  assign mem_read[g]=copy_q&&(!read_pending[g]||fifo_we[g])&&row*32+int'(lane)<committed[local_copy_bank]&&!local_s_stop;
`ifdef OT_WBQ_ROOT_S7_RPIPE
  ot_wbq_root_s7_rr_fifo #(.W(288),.AW(2),.RSEL(0)) u_fifo(
`else
  ot_hbm_accel_cdc_fifo #(.W(288),.AW(2)) u_fifo(
`endif
   .wclk(fifo_clk),.wrst_n(srst),.we(fifo_we[g]),.wdata({sector,mem_data[g]}),.full(fifo_full[g]),.rd_freed(),
   .rclk(hbm_clk),.rrst_n(hrst),.re(fifo_re[g]),.rdata(fifo_head[g]),.empty(fifo_empty[g]));
  ot_sram_1r1w_128x256_m1_r0c0_g256 u_payload(
   .clk(fifo_clk),.r_ce_in(mem_read[g]),.r_addr_in({local_copy_bank,row[5:0]}),.rd_out(mem_data[g]),
   .w_ce_in(filling&&!local_s_stop&&ordinal+GL<total[fill_bank]&&ordinal[4:3]==root_id&&wd_v[g]),
   .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd[g]),.w_mask_in(1'b1));
 end endgenerate
 integer s;
 always @(posedge fifo_clk or negedge srst)begin
  if(!srst)begin
   filling<=0;fill_bank<=0;ordinal<=0;ordinal8<=13'd8;copy_q<=0;read_pending<=0;
   for(s=0;s<2;s=s+1)begin base[s]<=0;total[s]<=0;committed[s]<=0;end
   for(s=0;s<4;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end
  end else begin
   if(reserve_v)begin base[reserve_bank]<={2'b00,reserve_base};total[reserve_bank]<=reserve_total;committed[reserve_bank]<=0;end
   if(fill_start)begin filling<=1;fill_bank<=fill_start_bank;ordinal<=0;ordinal8<=13'd8;end
   if(filling&&!core_s_stop)begin
    if(O8!=0)begin
     if(ordinal8>=total[fill_bank])begin filling<=0;committed[fill_bank]<=total[fill_bank];end
     else begin ordinal<=ordinal8[11:0];ordinal8<=ordinal8+13'd8;committed[fill_bank]<={ordinal8[11:5],5'b0};end
    end else begin
    if(ordinal+8>=total[fill_bank])begin filling<=0;committed[fill_bank]<=total[fill_bank];end
    else begin ordinal<=ordinal+8;committed[fill_bank]<=((ordinal+12'd8)>>5)<<5;end
    end
   end
   copy_q<=copy_on;
   if(copy_on&&!copy_q)begin
    read_pending<=0;
    for(s=0;s<4;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end
   end else begin
    for(s=0;s<4;s=s+1)begin
     if(fifo_we[s])read_pending[s]<=0;
     if(mem_read[s])begin read_pending[s]<=1;pending_row[s]<=copy_row[s][5:0];copy_row[s]<=copy_row[s]+1'b1;end
    end
   end
  end
 end
 reg [2:0] credit;integer mc;
 wire [3:0] ne=~fifo_empty;
 wire [1:0] sel=ne[0]?2'd0:ne[1]?2'd1:ne[2]?2'd2:2'd3;
 wire send=(|ne)&&credit!=0&&!h_stop&&hrst;
 assign g_v=send;
 assign g_d=fifo_head[sel][285:0];
 assign fifo_re=send?(4'b1<<sel):4'b0;
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)credit<=(MUT==2)?3'(CRED+1):3'(CRED);
  else credit<=credit-3'(send)+3'(g_credit&&!(MUT==1&&G==1&&mc>=9));
 end
 always @(posedge hbm_clk or negedge hrst)if(!hrst)mc<=0;else if(G==1&&MUT==1&&g_v)mc<=mc+1;
endmodule

// the two hard-core masters of the split (d44v part 51): same pins, G fixed
module ot_wbq_root_s7_g0 #(parameter integer CRED=4, parameter integer MUT=0, parameter integer CBREG=0, parameter integer SSTOPREG=CBREG, parameter integer RSTCP=8, parameter integer O8=1)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,input wire [3:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire g_credit,
 output wire root_ready,
 output wire g_v,output wire [285:0] g_d
);
 ot_wbq_root_s7_grp #(.G(0),.CRED(CRED),.MUT(MUT),.CBREG(CBREG),.SSTOPREG(SSTOPREG),.RSTCP(RSTCP),.O8(O8)) u_grp(.*);
endmodule
module ot_wbq_root_g1__fcore #(parameter integer CRED=4, parameter integer MUT=0, parameter integer CBREG=0, parameter integer SSTOPREG=CBREG, parameter integer RSTCP=8, parameter integer O8=1)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,input wire [3:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire g_credit,
 output wire root_ready,
 output wire g_v,output wire [285:0] g_d
);
 ot_wbq_root_s7_grp #(.G(1),.CRED(CRED),.MUT(MUT),.CBREG(CBREG),.SSTOPREG(SSTOPREG),.RSTCP(RSTCP),.O8(O8)) u_grp(.*);
endmodule


`default_nettype wire
