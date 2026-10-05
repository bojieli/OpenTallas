`timescale 1ps/1fs
// Physical connectivity context only; no added registers, handshakes or engine RTL.
// All span/publication/visibility authority remains explicit at the real leaf ports.
module ot_qwen_hbm_code_pair_context #(
  parameter integer ENABLE=0, COLUMN_BASE=0, ROWS=4496
)(
  input wire clk, por_n,
  input wire wr_v, output wire wr_r,
  input ot_hbm_r14_pkg::owned_t wr_owned,
  input wire wr_span_bound, wr_kind,
  input wire [12:0] wr_row, input wire [11:0] wr_column,
  output wire visible_v, input wire visible_r,
  output ot_hbm_r14_pkg::identity_t visible_id,
  output wire [11:0] visible_tag, output wire [4:0] visible_beat,
  output wire [12:0] visible_row, output wire [11:0] visible_column,
  input wire [1:0] rd_v, rd_span_bound, rd_published,
  input wire [25:0] rd_row, output wire [1:0] rd_r, rsp_v,
  input wire [5:0] virtual_bank,
  output wire [2659:0] rom_rd,
  output wire [1:0] rd_corrected, rd_uncorrectable,
  output wire fault
);
  wire [1:0] leaf_rsp_v;
  wire [511:0] leaf_data;
  wire leaf_fault, pipeline_fault;
  ot_qwen_hbm_code_payload_pair_directcapture #(
    .ENABLE(ENABLE), .COLUMN_BASE(COLUMN_BASE), .ROWS(ROWS)
  ) u_leaf (
    .clk(clk), .por_n(por_n), .wr_v(wr_v), .wr_r(wr_r),
    .wr_owned(wr_owned), .wr_span_bound(wr_span_bound), .wr_kind(wr_kind),
    .wr_row(wr_row), .wr_column(wr_column),
    .visible_v(visible_v), .visible_r(visible_r), .visible_id(visible_id),
    .visible_tag(visible_tag), .visible_beat(visible_beat),
    .visible_row(visible_row), .visible_column(visible_column),
    .rd_v(rd_v), .rd_span_bound(rd_span_bound), .rd_published(rd_published),
    .rd_row(rd_row), .rd_r(rd_r), .rd_rsp_v(leaf_rsp_v), .rd_data(leaf_data),
    .rd_corrected(rd_corrected), .rd_uncorrectable(rd_uncorrectable),
    .fault(leaf_fault)
  );
  ot_qwen_hbm_code_read_pipeline #(.ENABLE(ENABLE)) u_read_pipeline (
    .clk(clk), .por_n(por_n), .rd_fire(rd_v & rd_r),
    .virtual_bank(virtual_bank), .leaf_rd_rsp_v(leaf_rsp_v),
    .leaf_rd_data(leaf_data), .leaf_fault(leaf_fault),
    .rom_rd(rom_rd), .rsp_v(rsp_v), .fault(pipeline_fault)
  );
  assign fault = leaf_fault | pipeline_fault;
endmodule
