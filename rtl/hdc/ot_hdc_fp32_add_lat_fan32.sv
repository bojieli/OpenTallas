`timescale 1ns/1ps
// Opt-in exact, same-edge arithmetic distribution experiment.  No additional
// pipeline cut and no arithmetic reordering.  Adoption requires mapped native
// all-driver census <=32; output pruning alone is not a qualification.
module ot_hdc_fp32_add_lat_fan32 #(
    parameter integer LAT=3, CUTS=-1, DRST=1,
    parameter integer SAFE_DIST=0, SLICE_W=4
)(input wire clk, rst_n, valid_in,
  input wire [31:0] a,b, output wire [31:0] y,
  output wire [1:0] err, output wire valid_out);
  generate if (SAFE_DIST==0) begin:g_legacy
    ot_hdc_fp32_add_lat #(.LAT(LAT),.CUTS(CUTS),.DRST(DRST)) u (.*);
  end else begin:g_dist
    if (SLICE_W<1 || SLICE_W>32 || (32%SLICE_W)!=0) begin:g_bad
      ot_hdc_fp32_add_lat_fan32_bad_slice_width u_trap();
    end
    genvar i;
    for(i=0;i<32/SLICE_W;i=i+1) begin:g_slice
      (* keep_hierarchy=1 *) ot_hdc_fp32_add_lat_fan32_slice #(
        .LAT(LAT),.CUTS(CUTS),.DRST(DRST),.BASE(i*SLICE_W),.WIDTH(SLICE_W)) u (
        .clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),
        .y(y[i*SLICE_W+:SLICE_W]));
    end
    (* keep_hierarchy=1 *) ot_hdc_fp32_add_lat_fan32_aux #(
      .LAT(LAT),.CUTS(CUTS),.DRST(DRST)) u_aux (
      .clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.err(err),.valid_out(valid_out));
  end endgenerate
endmodule

// BASE and WIDTH give every kept output partition a distinct paramod.  The
// legacy adder is flattened inside the partition, allowing dead output cones
// to be pruned without merging the registered controls across partitions.
(* keep_hierarchy=1 *) module ot_hdc_fp32_add_lat_fan32_slice #(
    parameter integer LAT=3,CUTS=-1,DRST=1,BASE=0,WIDTH=4
)(input wire clk,rst_n,valid_in,input wire [31:0] a,b,
  output wire [WIDTH-1:0] y);
  wire [31:0] whole;
  ot_hdc_fp32_add_lat #(.LAT(LAT),.CUTS(CUTS),.DRST(DRST)) u_arith (
    .clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(whole),.err(),.valid_out());
  assign y=whole[BASE+:WIDTH];
endmodule

(* keep_hierarchy=1 *) module ot_hdc_fp32_add_lat_fan32_aux #(
    parameter integer LAT=3,CUTS=-1,DRST=1
)(input wire clk,rst_n,valid_in,input wire [31:0] a,b,
  output wire [1:0] err,output wire valid_out);
  ot_hdc_fp32_add_lat #(.LAT(LAT),.CUTS(CUTS),.DRST(DRST)) u_arith (
    .clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(),.err(err),.valid_out(valid_out));
endmodule
