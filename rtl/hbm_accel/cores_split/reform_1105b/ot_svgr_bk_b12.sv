`timescale 1ps/1fs
`default_nettype none
// HBM-REFORM-B12 (HBM-B12-SVGRBK 2026-11-05): ot_svgr_bk forms after the B8 head-register kit signed NOT
// (TT -72.95 ps, 407 endpoints).  Measured on the B8 routed DB (signoff TT re-run):
//   345 x  packet -> identity_ok -> fifo_pop -> 285-bit head load enable (-61.7)
//    16 x  rbin -> 8:1 FIFO read mux over a 285-bit word (rbin buffer tree ~400 ps) (-72.9)
//    18 x  hbm reset_pipe -> FIFO mem write enable (async-reset always block puts the reset in the enable) (-24.8)
//    28 x  packet -> identity_ok -> pop -> rgray/rbin incrementer, received_q (-28 / -6)
// Both variants keep ports, outline and pins of ot_svgr_bk; the B8 source (ot_svgr_split.sv) is not changed.
//
// VARIANT 0 (vA, targeted, 0 pin cycles, every output cycle-identical to B8):
//   * FIFO: mem written in its own always block (no reset term), read mux from replicated one-hot select registers
//     (SL slices, each its own kept 8-bit one-hot copy of rbin[2:0]), pointer next-state as a mux of precomputed +1.
//   * head data bits load on !empty && !stop && !sticky (no identity_ok in the 283-bit enable); the bank bits keep the
//     B8 enable (fifo_pop).  The two enables differ only on the edge where sticky sets (head fails its identity check),
//     after which every output except complete_bank is gated by sticky, and complete_bank reads the bank bits.
// VARIANT 1 (vB, safe by construction):
//   * same FIFO; identity check registered: head loaded -> next cycle id_q = identity_ok (state is quiet: a reserve
//     clears chk) -> next cycle the head is taken with id_q.  At most one packet per two stream cycles per landing bank.
//     Every path is reg -> one level of control logic -> reg.  The FIFO still never pops past a failing head.
//   * reset tree: one ot_reset_sync pair per landing bank (same release edge).
//   PIN CYCLES vs B8: landing write / complete / bank fault +1 stream_clk per packet (packets 2 cycles apart),
//   credits (cr) follow the later pops.
module ot_svgr_b12_fifo #(parameter integer W = 285, parameter integer SL = 9, parameter integer MUT = 0) (
  input  wire          wclk, wrst_n, input wire we, input wire [W-1:0] wdata, output wire full,
  output wire [2:0]    rd_freed,
  input  wire          rclk, rrst_n, input wire re, output wire [W-1:0] rdata, output wire empty
);
  localparam integer AW = 3, D = 8, SW = (W + SL - 1) / SL;
  reg [W-1:0] mem [0:D-1];
  reg [AW:0] wbin, wgray, rbin, rgray;
  (* async_reg = "true" *) reg [AW:0] rg_w1, rg_w2;
  (* async_reg = "true" *) reg [AW:0] wg_r1, wg_r2;
  function automatic [AW:0] g2b(input [AW:0] g);
    for (integer i = AW; i >= 0; i = i - 1) g2b[i] = (i == AW) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  wire wpush = we && !full;
  wire [AW:0] wbin_n = wbin + (wpush ? 1'b1 : 1'b0);
  assign full  = (wgray == {~rg_w2[AW:AW-1], rg_w2[AW-2:0]});
  assign empty = (rgray == wg_r2);
  reg [AW:0] rsync_bin_q;
  wire [AW:0] rsync_bin = g2b(rg_w2);
  assign rd_freed = 3'(rsync_bin - rsync_bin_q);
  // array write: no reset term in the enable (an entry is only read after wbin has passed it, so a write while the
  // write domain is in reset is never observable: wbin stays 0 and entry 0 is rewritten before it is published).
  always @(posedge wclk) if (wpush) mem[wbin[AW-1:0]] <= wdata;
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; rsync_bin_q <= 0; end
    else begin
      wbin <= wbin_n; wgray <= wbin_n ^ (wbin_n >> 1);
      rg_w1 <= rgray; rg_w2 <= rg_w1; rsync_bin_q <= rsync_bin;
    end
  wire rpop = re && !empty;
  wire [AW:0] rbin_p1 = rbin + 1'b1;
  wire [AW:0] rgray_p1 = rbin_p1 ^ (rbin_p1 >> 1);
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; end
    else begin
      if (rpop) begin rbin <= rbin_p1; rgray <= rgray_p1; end
      wg_r1 <= wgray; wg_r2 <= wg_r1;
    end
  // replicated one-hot read select: sel[s] == onehot(rbin[2:0]) for every slice s (reset 1, rotate on pop)
  genvar s, k;
  generate for (s = 0; s < SL; s = s + 1) begin : g_sl
    (* keep *) reg [D-1:0] sel;
    always @(posedge rclk or negedge rrst_n)
      if (!rrst_n) sel <= {{(D-1){1'b0}}, 1'b1};
      else if (rpop) sel <= (MUT == 1 && s == 3) ? {sel[D-3:0], sel[D-1:D-2]} : {sel[D-2:0], sel[D-1]};
    localparam integer LO = s * SW;
    localparam integer HI = ((s + 1) * SW > W) ? W : (s + 1) * SW;
    if (LO < W) begin : g_mux
      wire [HI-LO-1:0] term [0:D-1];
      for (k = 0; k < D; k = k + 1) begin : g_k
        assign term[k] = {(HI-LO){sel[k]}} & mem[k][HI-1:LO];
      end
      assign rdata[HI-1:LO] = term[0] | term[1] | term[2] | term[3] | term[4] | term[5] | term[6] | term[7];
    end
  end endgenerate
endmodule

module ot_svgr_b12_landing #(parameter integer LBANKS=4,parameter integer LB=2,parameter integer IW=283+LB,
  parameter integer VARIANT=0,parameter integer MUT=0)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,input wire [2:0] bank_id,
 input wire in_v,input wire [IW-1:0] in_data,output wire [1:0] freed,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,output wire [255:0] read_data
);
 wire packet_take,fifo_pop,full,empty;wire [IW-1:0] fifo_q;reg [IW-1:0] packet;reg head_v;wire [2:0] rf;reg ov;
 ot_svgr_b12_fifo #(.W(IW),.SL(9),.MUT(MUT==1?1:0)) u_response(.wclk(hbm_clk),.wrst_n(hbm_rst_n),.we(in_v),.wdata(in_data),.full(full),.rd_freed(rf),
  .rclk(stream_clk),.rrst_n(stream_rst_n),.re(fifo_pop),.rdata(fifo_q),.empty(empty));
 assign freed=rf[1:0];
 reg [LBANKS-1:0] valid_q;reg [15:0] epoch_q[0:LBANKS-1];reg [6:0] count_q[0:LBANKS-1],received_q[0:LBANKS-1];
 reg [63:0] seen_q[0:LBANKS-1];reg sticky;
 wire [10:0] ordinal=packet[IW-1:IW-11];wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];wire [5:0] row=ordinal[8:3];
 wire identity_c=valid_q[bank]&&epoch_q[bank]==epoch&&ordinal[2:0]==bank_id&&{1'b0,row}<count_q[bank]&&!seen_q[bank][row];
 wire identity_ok,landing_write;
 generate if (VARIANT == 0) begin : g_va
  // vA: B8 control (identity checked in the take cycle); only the head data enable is decoupled from identity_ok
  assign identity_ok=identity_c;
  assign packet_take=head_v&&!stop&&!sticky;
  assign landing_write=packet_take&&identity_ok;
  assign fifo_pop=!empty&&!stop&&!sticky&&(!head_v||(packet_take&&identity_ok));
  // data load: (!head_v || packet_take) == 1 under !stop && !sticky, so no identity term
  wire data_load_m=(MUT==3)?(!empty&&!sticky):(!empty&&!stop&&!sticky);
  always @(posedge stream_clk or negedge stream_rst_n)begin
   if(!stream_rst_n)begin head_v<=0;packet<=0;end
   else begin
    if(fifo_pop)head_v<=1;else if(packet_take)head_v<=0;
    if((MUT==2)?data_load_m:fifo_pop)packet[271+LB:272]<=fifo_q[271+LB:272];
    if(data_load_m)begin packet[IW-1:272+LB]<=fifo_q[IW-1:272+LB];packet[271:0]<=fifo_q[271:0];end
   end
  end
 end else begin : g_vb
  // vB: registered identity check; chk = id_q is valid for the current head and state
  reg chk,id_q;
  assign identity_ok=id_q;
  assign packet_take=head_v&&chk&&!stop&&!sticky;
  assign landing_write=packet_take&&identity_ok;
  assign fifo_pop=!empty&&!stop&&!sticky&&(!head_v||(packet_take&&((MUT==2)?1'b1:identity_ok)));
  always @(posedge stream_clk or negedge stream_rst_n)begin
   if(!stream_rst_n)begin head_v<=0;packet<=0;chk<=0;id_q<=0;end
   else begin
    if(fifo_pop)begin head_v<=1;packet<=fifo_q;end
    else if(packet_take)head_v<=0;
    if(fifo_pop||packet_take)chk<=0;
    else if(head_v)begin chk<=(MUT==3)?1'b1:!reserve_v;id_q<=identity_c;end
   end
  end
 end endgenerate
 assign complete_v=landing_write&&received_q[bank]+1'b1==count_q[bank];
 assign complete_bank=bank;assign fault=sticky||ov;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)ov<=0;else if(in_v&&full)ov<=1;
 integer b;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   valid_q<=0;sticky<=0;
   for(b=0;b<LBANKS;b=b+1)begin epoch_q[b]<=0;count_q[b]<=0;received_q[b]<=0;seen_q[b]<=0;end
  end else begin
   if(reserve_v)begin
    valid_q[reserve_bank]<=1;epoch_q[reserve_bank]<=reserve_epoch;
    count_q[reserve_bank]<=reserve_total>12'(bank_id)?(reserve_total+12'd7-12'(bank_id))/8:0;
    received_q[reserve_bank]<=0;seen_q[reserve_bank]<=0;
   end
   if(packet_take)begin
    if(!identity_ok)sticky<=1;
    else begin seen_q[bank][row]<=1;received_q[bank]<=received_q[bank]+1'b1;end
   end
  end
 end
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(.clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(landing_write),.w_addr_in({bank,row}),.wd_in(packet[255:0]),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
endmodule

module ot_svgr_bk #(parameter integer LBANKS=4,parameter integer LB=2,parameter integer IW=283+LB,
  parameter integer VARIANT=0,parameter integer MUT=0)(
 input wire hbm_clk,stream_clk,stream_rst_n,hbm_rst_n,input wire bk_hi,
 input wire [3:0] in_v,input wire [4*IW-1:0] in_data,output reg [3:0] cr,
 input wire res_v,input wire [LB-1:0] res_bank,input wire [15:0] res_epoch,input wire [11:0] res_total,input wire stop,
 input wire [3:0] read_v,input wire [LB-1:0] read_bank,input wire [23:0] read_row,
 output wire [3:0] complete,output wire [7:0] complete_bank,output wire [3:0] bfault,output wire [1023:0] read_data
);
 wire reset_both=stream_rst_n&&hbm_rst_n;wire [3:0] srst,hrst;
 genvar g;
 generate if (VARIANT == 0) begin : g_rst_shared
  ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst[0]));
  ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst[0]));
  assign srst[3:1]={3{srst[0]}};assign hrst[3:1]={3{hrst[0]}};
 end else begin : g_rst_tree
  // reset tree: one synchroniser pair per landing bank, same input, same release edge
  for(g=0;g<4;g=g+1)begin : r
   ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst[g]));
   ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst[g]));
  end
 end endgenerate
 wire [1:0] fr[0:3];reg [3:0] owe[0:3];
 generate for(g=0;g<4;g=g+1)begin:u
  ot_svgr_b12_landing #(.LBANKS(LBANKS),.LB(LB),.IW(IW),.VARIANT(VARIANT),.MUT(g==1?MUT:0)) u_bank(.hbm_clk(hbm_clk),.hbm_rst_n(hrst[g]),.stream_clk(stream_clk),.stream_rst_n(srst[g]),.bank_id({bk_hi,2'(g)}),
   .in_v(in_v[g]),.in_data(in_data[IW*g+:IW]),.freed(fr[g]),.reserve_v(res_v),.reserve_bank(res_bank),.reserve_epoch(res_epoch),.reserve_total(res_total),.stop(stop),
   .complete_v(complete[g]),.complete_bank(complete_bank[2*g+:2]),.fault(bfault[g]),.read_v(read_v[g]),.read_bank(read_bank),.read_row(read_row[6*g+:6]),.read_data(read_data[256*g+:256]));
  always @(posedge hbm_clk or negedge hrst[g])begin
   if(!hrst[g])begin owe[g]<=0;cr[g]<=0;end
   else begin cr[g]<=(owe[g]!=0)||(fr[g]!=0);owe[g]<=owe[g]+4'(fr[g])-4'((owe[g]!=0)||(fr[g]!=0));end
  end
 end endgenerate
endmodule
`default_nettype wire
