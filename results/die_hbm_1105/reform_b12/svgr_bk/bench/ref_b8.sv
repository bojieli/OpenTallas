
// Four landing banks of one fifo clock group: the response FIFO returns one credit per freed entry, in the write domain.
module ot_svgr_landing_ref #(parameter integer LBANKS=4,parameter integer LB=2,parameter integer IW=283+LB)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,input wire [2:0] bank_id,
 input wire in_v,input wire [IW-1:0] in_data,output wire [1:0] freed,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,output wire [255:0] read_data
);
 // HBM-REFORM-B8 head register: the FIFO read (rbin -> 8-entry mux) and the identity/seen check sit in separate stream cycles.
 // landing write, complete and fault come one stream cycle later; credits return no later; FIFO pops only into a free head.
 wire packet_v,packet_take,fifo_pop,full,empty;wire [IW-1:0] fifo_q;reg [IW-1:0] packet;reg head_v;wire [2:0] rf;reg ov;
 ot_hbm_accel_cdc_fifo #(.W(IW),.AW(3)) u_response(.wclk(hbm_clk),.wrst_n(hbm_rst_n),.we(in_v),.wdata(in_data),.full(full),.rd_freed(rf),
  .rclk(stream_clk),.rrst_n(stream_rst_n),.re(fifo_pop),.rdata(fifo_q),.empty(empty));
 assign packet_v=head_v;assign freed=rf[1:0];
 reg [LBANKS-1:0] valid_q;reg [15:0] epoch_q[0:LBANKS-1];reg [6:0] count_q[0:LBANKS-1],received_q[0:LBANKS-1];
 reg [63:0] seen_q[0:LBANKS-1];reg sticky;
 wire [10:0] ordinal=packet[IW-1:IW-11];wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];wire [5:0] row=ordinal[8:3];
 wire identity_ok=valid_q[bank]&&epoch_q[bank]==epoch&&ordinal[2:0]==bank_id&&{1'b0,row}<count_q[bank]&&!seen_q[bank][row];
 wire landing_write=packet_v&&!stop&&!sticky&&identity_ok;
 assign packet_take=packet_v&&!stop&&!sticky;
 assign fifo_pop=!empty&&!stop&&!sticky&&(!head_v||(packet_take&&identity_ok));
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin head_v<=0;packet<=0;end
  else if(fifo_pop)begin head_v<=1;packet<=fifo_q;end
  else if(packet_take)head_v<=0;
 end
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

module ot_svgr_bk_ref #(parameter integer LBANKS=4,parameter integer LB=2,parameter integer IW=283+LB)(
 input wire hbm_clk,stream_clk,stream_rst_n,hbm_rst_n,input wire bk_hi,
 input wire [3:0] in_v,input wire [4*IW-1:0] in_data,output reg [3:0] cr,
 input wire res_v,input wire [LB-1:0] res_bank,input wire [15:0] res_epoch,input wire [11:0] res_total,input wire stop,
 input wire [3:0] read_v,input wire [LB-1:0] read_bank,input wire [23:0] read_row,
 output wire [3:0] complete,output wire [7:0] complete_bank,output wire [3:0] bfault,output wire [1023:0] read_data
);
 wire reset_both=stream_rst_n&&hbm_rst_n;wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 wire [1:0] fr[0:3];reg [3:0] owe[0:3];
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:u
  ot_svgr_landing_ref #(.LBANKS(LBANKS),.LB(LB)) u_bank(.hbm_clk(hbm_clk),.hbm_rst_n(hrst),.stream_clk(stream_clk),.stream_rst_n(srst),.bank_id({bk_hi,2'(g)}),
   .in_v(in_v[g]),.in_data(in_data[IW*g+:IW]),.freed(fr[g]),.reserve_v(res_v),.reserve_bank(res_bank),.reserve_epoch(res_epoch),.reserve_total(res_total),.stop(stop),
   .complete_v(complete[g]),.complete_bank(complete_bank[2*g+:2]),.fault(bfault[g]),.read_v(read_v[g]),.read_bank(read_bank),.read_row(read_row[6*g+:6]),.read_data(read_data[256*g+:256]));
  // one credit per edge on the seam; owe holds what the synchroniser freed together
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)begin owe[g]<=0;cr[g]<=0;end
   else begin cr[g]<=(owe[g]!=0)||(fr[g]!=0);owe[g]<=owe[g]+4'(fr[g])-4'((owe[g]!=0)||(fr[g]!=0));end
  end
 end endgenerate
endmodule
`timescale 1ps/1fs
// HA4: asynchronous FIFO (Gray-coded pointers, two-flop synchronisers) for the crossings between the
// 1.2 GHz streaming/SM domain and the HBM controller's CK/2 (976.6 MHz) domain.  One write per wclk
// and one read per rclk at most, so each synchronised pointer moves by one Gray step.  Read data is
// the registered array word at the read pointer (first-word fall-through on the array).
// rd_freed is the number of entries the reader freed, as seen in the write domain after
// synchronisation (0..2 per wclk), for credit return to a producer that counts credits.
module ot_hbm_accel_cdc_fifo #(parameter integer W = 32, parameter integer AW = 5) (
  input  wire          wclk, wrst_n, input wire we, input wire [W-1:0] wdata, output wire full,
  output wire [2:0]    rd_freed,
  input  wire          rclk, rrst_n, input wire re, output wire [W-1:0] rdata, output wire empty
);
  localparam integer D = 1 << AW;
  reg [W-1:0] mem [0:D-1];
  reg [AW:0] wbin, wgray, rbin, rgray;
  (* async_reg = "true" *) reg [AW:0] rg_w1, rg_w2;   // read pointer in the write domain
  (* async_reg = "true" *) reg [AW:0] wg_r1, wg_r2;   // write pointer in the read domain
  function automatic [AW:0] g2b(input [AW:0] g);
    for (integer i = AW; i >= 0; i = i - 1) g2b[i] = (i == AW) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  wire [AW:0] wbin_n = wbin + ((we && !full) ? 1'b1 : 1'b0);
  wire [AW:0] rbin_n = rbin + ((re && !empty) ? 1'b1 : 1'b0);
  assign full  = (wgray == {~rg_w2[AW:AW-1], rg_w2[AW-2:0]});
  assign empty = (rgray == wg_r2);
  assign rdata = mem[rbin[AW-1:0]];
  reg [AW:0] rsync_bin_q;
  wire [AW:0] rsync_bin = g2b(rg_w2);
  assign rd_freed = 3'(rsync_bin - rsync_bin_q);
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; rsync_bin_q <= 0; end
    else begin
      if (we && !full) mem[wbin[AW-1:0]] <= wdata;
      wbin <= wbin_n; wgray <= wbin_n ^ (wbin_n >> 1);
      rg_w1 <= rgray; rg_w2 <= rg_w1; rsync_bin_q <= rsync_bin;
    end
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; end
    else begin
      rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
      wg_r1 <= wgray; wg_r2 <= wg_r1;
    end
endmodule
`timescale 1ns/1ps
// Asynchronous-assert, synchronous-deassert reset conditioner.  ASYNC_STAGES
// includes the output stage and must be at least two for a CDC/RDC boundary.
module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2,
    parameter integer OUTPUT_COPIES = 1,
    // TREE 1 (S81-SHLK12 2026-10-20, default 0 = unchanged): with OUTPUT_COPIES > 1 the first stage is itself
    // ceil(OUTPUT_COPIES / 16) kept copies (D = 1), so after the synthesis copy pass no flop of the synchroniser drives
    // more than 16 loads.  Same release edge (still ASYNC_STAGES = 2 edges).
    parameter integer TREE = 0
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;

    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            reset_pipe <= {ASYNC_STAGES{1'b0}};
        else
            reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0],1'b1};
    end

    generate if (OUTPUT_COPIES > 1 && TREE != 0 && ASYNC_STAGES == 2) begin : g_tree
        localparam integer L1 = (OUTPUT_COPIES + 15) / 16;
        (* keep = "true", async_reg = "true" *) reg [L1-1:0] reset_l1__ot_rlv;
        (* keep = "true" *) reg [OUTPUT_COPIES-1:0] reset_regions__ot_rlv;
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_l1__ot_rlv <= '0;
            else reset_l1__ot_rlv <= {L1{1'b1}};
        // every output copy takes the first-stage copy 0 in RTL: both families are identical registers, and the
        // synthesis copy pass (physical/common_flow/ot_rst_copies.tcl) spreads the output copies over the first-stage
        // copies and the reset loads over the output copies (<= OT_RST_COPIES_MAX each)
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_regions__ot_rlv <= '0;
            else reset_regions__ot_rlv <= {OUTPUT_COPIES{reset_l1__ot_rlv[0]}};
        assign sync_rst_n = reset_regions__ot_rlv[0];
    end else if (OUTPUT_COPIES > 1) begin : g_regions
        // Same release edge as reset_pipe's last stage. The canonicalizer
        // proves identical D/clock/reset and partitions reset loads <=256.
        (* keep = "true" *) reg [OUTPUT_COPIES-1:0] reset_regions__ot_rlv;
        always @(posedge clk or negedge async_rst_n)
            if (!async_rst_n) reset_regions__ot_rlv <= '0;
            else reset_regions__ot_rlv <= {OUTPUT_COPIES{reset_pipe[ASYNC_STAGES-2]}};
        assign sync_rst_n = reset_regions__ot_rlv[0];
    end else begin : g_original
        assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];
    end endgenerate

`ifndef SYNTHESIS
    initial begin
        if (ASYNC_STAGES < 2)
            $error("ot_reset_sync requires at least two stages");
    end
`endif
endmodule
