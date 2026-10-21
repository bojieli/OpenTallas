`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-LEPENH2 (2026-10-20): opt-in ring WRITER for chunked, reset-forest landings (lp.py landing_kept_enable).
// ot_pl_land_local_w gates every slot write with (rq && write_oh[s]); synthesis folds rq into each data bit's capture
// mux, so at CHUNK_BITS 24 the registered rq drives 120 actual load pins (pre-gate native census, dsdv_slice_lepe_nh
// d2 gate 10-20: 92 violations, max 120).  Here the slot enable is the registered one-hot write_oh[s] ALONE (W data +
// AW+1 epoch + rotation loads, 30 at W = 24, D = 4); rq only resets the control registers (wc, write_oh, valid: 11 loads).
// Equivalence with ot_pl_land_local_w at the read port: while rq is low write_oh holds 0..01, so slot 0 is written every
// edge but valid stays 0 (the reader ignores invalid slots and is not warm); at the first edge with rq high both write
// slot 0 with i and rotate to slot 1, and from then on the two writers are cycle-identical.  Slot contents differ only
// in an invalid slot during reset.  Same ports, bank layout, K/reset ages as ot_pl_land_vector_reset_w (reader unchanged:
// ot_pl_land_vector_reset_r).  Needs ot_pl_land.sv (no shared module is modified).
// ---------------------------------------------------------------------------------------------------------------------
module ot_pl_land_local_kw #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);
    reg rq;
    reg [AW:0] wc;
    (* keep *) reg [D-1:0] write_oh;
    reg [D-1:0] valid;
    reg [W-1:0] data [0:D-1];
    reg [AW:0] epoch [0:D-1];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin wc <= 0; write_oh <= {{(D-1){1'b0}},1'b1}; valid <= 0; end
        else begin
            wc <= wc + 1'b1;
            write_oh <= {write_oh[D-2:0], write_oh[D-1]};
            valid <= valid | write_oh;
        end
    genvar s;
    generate for (s=0;s<D;s=s+1) begin:g_slot
        always @(posedge ck) if (write_oh[s]) begin data[s] <= i; epoch[s] <= wc; end
        assign bank[s*W+:W] = data[s];
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
    assign vld = valid;
endmodule

module ot_pl_land_vector_reset_kw_w #(
    parameter integer W=1073,D=4,CHUNK_BITS=24,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer CHUNKS=(W+CHUNK_BITS-1)/CHUNK_BITS
)(
    input wire ck,input wire [CHUNKS-1:0] rsi,input wire [W-1:0] i,
    output wire [D*W-1:0] bank,output wire [D*(AW+1)-1:0] epo,
    output wire [D*CHUNKS-1:0] vld
);
    generate if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) begin:g_invalid_shape
        OT_LAND_VECTOR_RESET_KW_REQUIRES_EXACT_CHUNKS u_bad();
    end endgenerate
    generate for(genvar c=0;c<CHUNKS;c=c+1) begin:g_chunk
        localparam integer CW=(W-c*CHUNK_BITS<CHUNK_BITS)?W-c*CHUNK_BITS:CHUNK_BITS;
        wire [D*CW-1:0] cb;
        wire [D*(AW+1)-1:0] ce;
        (* keep_hierarchy="yes" *) ot_pl_land_local_kw #(.W(CW),.D(D)) u_local(
            .ck(ck),.rsi(rsi[c]),.i(i[c*CHUNK_BITS+:CW]),.bank(cb),.epo(ce),.vld(vld[c*D+:D]));
        for(genvar s=0;s<D;s=s+1) begin:g_slot
            assign bank[s*W+c*CHUNK_BITS+:CW]=cb[s*CW+:CW];
        end
        if(c==0) begin:g_tags assign epo=ce;end
    end endgenerate
`ifndef SYNTHESIS
    initial if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) $fatal(1,"LAND_VECTOR_RESET_KW_W_SHAPE");
`endif
endmodule
`default_nettype wire
