// Private opt-in (S81-SERDES5 10-20, lp spec "landing_reg_we": true; needs landing_reset_forest).
// Writer ring with REGISTERED per-slot write enables. In ot_pl_land_local_w the ring reset rq gates every slot
// bit (rq && write_oh[s] -> D*W enables; mapped census: 120 loads per chunk at W=24). Here we[s] is its own flop,
// computed one edge early from the same next-state terms:
//   we_next[s] = rsi && write_oh_next[s],  write_oh_next = rq ? rotate(write_oh) : 1-hot slot 0
// so we[s] == rq && write_oh[s] at every edge after the first: slot data, epochs, valid, K and the reset ages are
// cycle-identical to ot_pl_land_local_w (no schedule change). Each we[s] drives W (<= 24) data enables; rq drives
// the counter, one-hot, valid and the we next-state (~15). Requires ot_pl_land.sv and ot_pl_land_reset_forest.sv
// (reader side stays ot_pl_land_vector_reset_r). Shared files are untouched; default generation is byte-identical.
`default_nettype none
module ot_pl_land_local_we_w #(
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
    (* keep *) reg [D-1:0] we;
    reg [D-1:0] valid;
    reg [W-1:0] data [0:D-1];
    reg [AW:0] epoch [0:D-1];
    wire [D-1:0] write_oh_n = rq ? {write_oh[D-2:0], write_oh[D-1]} : {{(D-1){1'b0}},1'b1};
    always @(posedge ck) rq <= rsi;
    always @(posedge ck) we <= rsi ? write_oh_n : {D{1'b0}};
    always @(posedge ck)
        if (!rq) begin wc <= 0; write_oh <= {{(D-1){1'b0}},1'b1}; valid <= 0; end
        else begin
            wc <= wc + 1'b1;
            write_oh <= write_oh_n;
            valid <= valid | write_oh;
        end
    genvar s;
    generate for (s=0;s<D;s=s+1) begin:g_slot
        always @(posedge ck) if (we[s]) begin data[s] <= i; epoch[s] <= wc; end
        assign bank[s*W+:W] = data[s];
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
    assign vld = valid;
`ifndef SYNTHESIS
    // the equivalence the module relies on (checked in every bench that uses it)
    reg seen = 0;
    always @(posedge ck) begin
        seen <= 1'b1;
        if (seen && !$isunknown({rq, write_oh, we}) && we != ({D{rq}} & write_oh)) $error("LAND_WE_FAULT %m: we %b rq %b oh %b", we, rq, write_oh);
    end
`endif
endmodule

module ot_pl_land_vector_reset_we_w #(
    parameter integer W=1073,D=4,CHUNK_BITS=24,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer CHUNKS=(W+CHUNK_BITS-1)/CHUNK_BITS
)(
    input wire ck,input wire [CHUNKS-1:0] rsi,input wire [W-1:0] i,
    output wire [D*W-1:0] bank,output wire [D*(AW+1)-1:0] epo,
    output wire [D*CHUNKS-1:0] vld
);
    generate if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) begin:g_invalid_shape
        OT_LAND_VECTOR_RESET_REQUIRES_EXACT_CHUNKS u_bad();
    end endgenerate
    generate for(genvar c=0;c<CHUNKS;c=c+1) begin:g_chunk
        localparam integer CW=(W-c*CHUNK_BITS<CHUNK_BITS)?W-c*CHUNK_BITS:CHUNK_BITS;
        wire [D*CW-1:0] cb;
        wire [D*(AW+1)-1:0] ce;
        (* keep_hierarchy="yes" *) ot_pl_land_local_we_w #(.W(CW),.D(D)) u_local(
            .ck(ck),.rsi(rsi[c]),.i(i[c*CHUNK_BITS+:CW]),.bank(cb),.epo(ce),.vld(vld[c*D+:D]));
        for(genvar s=0;s<D;s=s+1) begin:g_slot
            assign bank[s*W+c*CHUNK_BITS+:CW]=cb[s*CW+:CW];
        end
        if(c==0) begin:g_tags assign epo=ce;end
    end endgenerate
`ifndef SYNTHESIS
    initial if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) $fatal(1,"LAND_VECTOR_RESET_WE_W_SHAPE");
`endif
endmodule
`default_nettype wire
