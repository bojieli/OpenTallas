`timescale 1ns/1ps
`default_nettype none
// Experimental source-forwarded payload transfer. This is not a qualified hard
// view. Only odd hop counts are supported: the local ring writer then has the
// same logical phase/epoch as ck_src, avoiding an unproved half-phase reset age.
// Each hop and its forwarded clock must be placed within 405um of its driver.
module ot_pl_stream_hop #(parameter integer W=24) (
    input wire ck_i, input wire [W-1:0] d, output wire ck_o,
    output reg [W-1:0] q
);
    // Hierarchy and clock net must survive mapping; actual native clock entry
    // and phase compensation are separate physical release obligations.
    (* keep *) wire inv_ck = ~ck_i;
    assign ck_o = inv_ck;
    always @(posedge ck_i) q <= d;
endmodule

module ot_pl_stream_land #(
    parameter integer W=24, HOPS=1, CHUNK_BITS=24,
    parameter integer K=(HOPS==1 ? 2 : 1)
) (
    input wire ck_src, ck_dst, rsi,
    input wire [W-1:0] i, output wire [W-1:0] o
);
    (* keep *) wire [HOPS:0] fck;
    wire [W-1:0] payload[0:HOPS];
    assign fck[0] = ~ck_src;
    assign payload[0] = i;
    genvar h;
    generate for(h=0; h<HOPS; h=h+1) begin:g_hop
        (* keep_hierarchy="yes" *) ot_pl_stream_hop #(.W(W)) u_hop (
            .ck_i(fck[h]), .ck_o(fck[h+1]), .d(payload[h]), .q(payload[h+1]));
    end endgenerate
    wire [4*W-1:0] bank;
    wire [11:0] epo;
    wire [4*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld;
    // Establish release away from either positive-edge root. Parent reset
    // normally changes on its source rising edge; using it directly could
    // make a delayed forwarded clock observe the next reset epoch. The kept
    // falling-edge source leaf removes that ambiguity. This half-cycle reset
    // crossing is timed normally and needs the same native phase receipt.
    (* keep *) reg reset_epoch;
    always @(negedge ck_src) reset_epoch <= rsi;
    // Distinct retained release leaves bound each physical reset load to at
    // most 32 chunks. Two additional boot edges conservatively cover the
    // falling-edge stage and these leaves; steady-state data latency is zero.
    (* keep *) reg wrsi, rrsi;
    always @(posedge fck[HOPS]) wrsi <= reset_epoch;
    always @(posedge ck_dst) rrsi <= reset_epoch;
    ot_pl_land_chunk_w #(.W(W),.CHUNK_BITS(CHUNK_BITS)) u_w (
        .ck(fck[HOPS]),.rsi(wrsi),.i(payload[HOPS]),.bank(bank),.epo(epo),.vld(vld));
    ot_pl_land_chunk_r #(.W(W),.K(K),.CHUNK_BITS(CHUNK_BITS)) u_r (
        .ck(ck_dst),.rsi(rrsi),.bank(bank),.epo(epo),.vld(vld),.o(o));
`ifndef SYNTHESIS
    initial begin
        if(HOPS!=1 && HOPS!=3) $fatal(1,"stream_land supports only odd HOPS1/3");
        if(K!=(HOPS==1 ? 2 : 1)) $fatal(1,"stream_land K does not preserve three-edge latency");
        if((W+CHUNK_BITS-1)/CHUNK_BITS>32) $fatal(1,"stream_land reset leaf exceeds32 loads");
    end
`endif
endmodule
`default_nettype wire
