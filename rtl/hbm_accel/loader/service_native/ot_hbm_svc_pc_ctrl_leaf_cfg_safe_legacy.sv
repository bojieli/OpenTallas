`timescale 1ns/1ps
// Opt-in physical PC: native controller plus one previous-ready/same-edge collar.
module ot_hbm_svc_pc_ctrl_leaf_cfg_safe_legacy #(
    parameter integer MRKEY=1,
    // RQ (HBM-BW): read responses reserved per PC (posted + in flight + landed, untaken).  The as-built 32 covered only
    // the ~30-cycle column -> K-response round trip, so the queue ran nearly empty and no ACT could be issued ahead;
    // 128 (a power of two: ring pointers) covers the 64-entry queue + the round trip; the 128x256 response SRAM already
    // holds 128 rows.
    parameter integer RQ=128,
    // QD (HBM-BW): access-queue depth in sectors (leaf queue + sequencer queue).  The queue is the ACT lookahead: an
    // entry's bank is activated when it is queued, so QD cycles of column work must cover the ACT sequencing of a block's
    // four banks (tRRD/slot ~4 cycles each) + tRCD 19 + a refresh ACT-blocking window (16): 32 left no margin.
    // A deeper QD128 experiment uses existing SRAM capacity but lowers the
    // measured DS rate81.83..83.08 by reducing idle banks for refresh pull-in.
    // Keep the measured production-optimal64-sector queue as the default.
    parameter integer QD=64,
    parameter integer OREG=1,
    parameter integer KREG=1,
    parameter integer KRREG=1,
    parameter integer RREG=1,
    // WPAY=1 (H-DIE 2026-10-15 22:50, physical default): the 256-bit write payload of the 32-entry same-row queue lives
    // in a real 128x256 SRAM (rows 0..31) instead of 8,192 queue flops + a 32:1 x 256 head mux; the clock root drops
    // from 15,219 to ~7k sinks.  The payload is read continuously at the NEXT head (rp, or rp+1 on a column pop), so
    // the head word is valid one edge after any pop.  A write column issued less than two edges after its own payload
    // write would read the old word: that is checked (sticky fault), never silently stretched.  WPAY=0 = flops.
    parameter integer WPAY=1,
    // Negative-control witness: corrupt tag bit zero at pending identity write.
    parameter integer BW_MUT_ID_TAG=0,
    // Exact physical face landing is explicit in RTL; disable tool insertion.
    parameter integer RESET_LANDING=2
)(
    input wire clk,rst_n,
    input wire [4:0]pc_id,
    input wire [7:0]refresh_reload,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output reg k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output wire pc_fault,output reg[5:0]owner_fault_split
);
    wire core_rst_n;
    generate if(RESET_LANDING==2)begin:g_reset_face
      (* keep="true",dont_touch="true" *) reg rst_l0,rst_l1;
      always @(posedge clk)begin rst_l0<=rst_n;rst_l1<=rst_l0;end
      assign core_rst_n=rst_l1;
    end else begin:g_reset_diagnostic
      assign core_rst_n=rst_n;
    end endgenerate
    initial if(RESET_LANDING!=0&&RESET_LANDING!=2)$fatal(1,"RESET_LANDING must be0 or2");
    wire native_v,native_rdy,native_fault,bridge_fault;
    wire[17:0]native_v_regions;
    wire[16:0]native_tag;wire[3:0]native_beat;wire[255:0]native_data;
    ot_hbm_svc_pc_ctrl_leaf_cfg_safe #(.MRKEY(MRKEY),.RQ(RQ),.QD(QD),
      .OREG(OREG),.KREG(KREG),.KRREG(KRREG),.RREG(RREG),.WPAY(WPAY),
      .BW_MUT_ID_TAG(BW_MUT_ID_TAG)) u_native(
      .clk(clk),
      .rst_n(core_rst_n),
      .pc_id(pc_id),
      .refresh_reload(refresh_reload),
      .k_v(k_v),
      .k_rdy(k_rdy),
      .k_we(k_we),
      .k_addr(k_addr),
      .k_len(k_len),
      .k_tag(k_tag),
      .k_wdata(k_wdata),
      .k_wstrb(k_wstrb),
      .kr_v(native_v),
      .kr_rdy(native_rdy),
      .kr_tag(native_tag),
      .kr_beat(native_beat),
      .kr_data(native_data),
      .k_wr_done(k_wr_done),
      .row_v(row_v),
      .row_op(row_op),
      .row_bank(row_bank),
      .row_row(row_row),
      .col_v(col_v),
      .col_we(col_we),
      .col_bank(col_bank),
      .col_col(col_col),
      .col_data(col_data),
      .col_strb(col_strb),
      .dram_rvalid(dram_rvalid),
      .dram_rdata(dram_rdata),
      .pc_fault(native_fault),
      .owner_fault_split(owner_fault_split),
      .kr_v_regions(native_v_regions));
    // Exactly one compatibility collar, with real existing-edge producer
    // validity per region. These17 additional local wires stay inside the PC
    // physical master; the outer configuration/data pin ABI is unchanged.
    ot_hbm_svc_kr_ready_bridge #(.REGIONAL_VALID(1)) u_kr_bridge(
      .clk(clk),.rst_n(core_rst_n),.in_v(native_v),.in_v_regions(native_v_regions),
      .in_rdy(native_rdy),.in_data({native_tag,native_beat,native_data}),
      .out_v(kr_v),.out_rdy(kr_rdy),.out_data({kr_tag,kr_beat,kr_data}),
      .fault(bridge_fault),.occupancy());
    assign pc_fault=native_fault|bridge_fault;
endmodule
