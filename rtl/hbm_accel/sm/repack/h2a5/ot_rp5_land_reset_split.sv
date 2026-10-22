`timescale 1ns/1ps
`default_nettype none
// SMH r5 source-local native reset repair. Original rq/control and per-slot
// data write guards remain at the same edge; reader, ring D/K, data/epoch
// storage, reset run, valid masks and static calendars are unchanged.
// Each rq_slot flop drives one W24 + epoch/selector slice (~30 mapped loads),
// replacing the original D4-wide rq fanout120. Reset forest leaves drive five
// same-edge reset captures. No new latency, no global primitive replacement.
module ot_rp5_land_local_w #(
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
    wire [D-1:0] rq_slot;
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
        // Identical reset capture edge; kept per-slot flop prevents ABC from
        // redistributing one control rq to every data/epoch mux in D slots.
        (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(8192+s)) u_reset(
            .ck(ck), .d(rsi), .q(rq_slot[s]));
        always @(posedge ck) if (rq_slot[s] && write_oh[s]) begin data[s] <= i; epoch[s] <= wc; end
        assign bank[s*W+:W] = data[s];
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
    assign vld = valid;
endmodule

// Private opt-in: bounded reset distribution using the existing run depth.
// Requires ot_pl_land_field_copy_bit from ot_pl_land_field_copies.sv.
`default_nettype none
module ot_pl_land_reset_forest #(
    parameter integer DEPTH=8, LEAVES=47, ROOT_LOADS=1
)(input wire ck,d, output wire [LEAVES-1:0] q);
    localparam integer BRANCHES=(LEAVES+31)/32;
    wire [DEPTH-2:0] prefix;
    wire [BRANCHES-1:0] branch;
    assign prefix[0]=d;
    generate if(DEPTH<2 || LEAVES<1 || LEAVES>1024 || ROOT_LOADS<1 || ROOT_LOADS>32) begin:g_invalid_shape
        OT_LAND_RESET_FOREST_REQUIRES_DEPTH2_LEAVES1_TO1024 u_bad();
    end endgenerate
    generate for(genvar s=0;s<DEPTH-2;s=s+1) begin:g_prefix
        (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(s)) u_ff(
            .ck(ck),.d(prefix[s]),.q(prefix[s+1]));
    end
    for(genvar b=0;b<BRANCHES;b=b+1) begin:g_branch
        (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(1024+b)) u_ff(
            .ck(ck),.d(prefix[DEPTH-2]),.q(branch[b]));
    end
    for(genvar l=0;l<LEAVES;l=l+1) begin:g_leaf
        (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(2048+l)) u_ff(
            .ck(ck),.d(branch[l/32]),.q(q[l]));
    end endgenerate
`ifndef SYNTHESIS
    initial if(DEPTH<2 || LEAVES<1 || LEAVES>1024 || ROOT_LOADS<1 || ROOT_LOADS>32) $fatal(1,"LAND_RESET_FOREST_SHAPE");
`endif
endmodule

module ot_pl_land_vector_reset_w #(
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
        (* keep_hierarchy="yes" *) ot_rp5_land_local_w #(.W(CW),.D(D)) u_local(
            .ck(ck),.rsi(rsi[c]),.i(i[c*CHUNK_BITS+:CW]),.bank(cb),.epo(ce),.vld(vld[c*D+:D]));
        for(genvar s=0;s<D;s=s+1) begin:g_slot
            assign bank[s*W+c*CHUNK_BITS+:CW]=cb[s*CW+:CW];
        end
        if(c==0) begin:g_tags assign epo=ce;end
    end endgenerate
`ifndef SYNTHESIS
    initial if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) $fatal(1,"LAND_VECTOR_RESET_W_SHAPE");
`endif
endmodule

module ot_pl_land_vector_reset_r #(
    parameter integer W=1073,D=4,K=2,CHUNK_BITS=24,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer CHUNKS=(W+CHUNK_BITS-1)/CHUNK_BITS
)(
    input wire ck,input wire [CHUNKS-1:0] rsi,
    input wire [D*W-1:0] bank,input wire [D*(AW+1)-1:0] epo,
    input wire [D*CHUNKS-1:0] vld,output wire [W-1:0] o
);
    generate if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) begin:g_invalid_shape
        OT_LAND_VECTOR_RESET_REQUIRES_EXACT_CHUNKS u_bad();
    end endgenerate
    generate for(genvar c=0;c<CHUNKS;c=c+1) begin:g_chunk
        localparam integer CW=(W-c*CHUNK_BITS<CHUNK_BITS)?W-c*CHUNK_BITS:CHUNK_BITS;
        wire [D*CW-1:0] cb;
        for(genvar s=0;s<D;s=s+1) begin:g_slot
            assign cb[s*CW+:CW]=bank[s*W+c*CHUNK_BITS+:CW];
        end
        (* keep_hierarchy="yes" *) ot_pl_land_local_r #(.W(CW),.D(D),.K(K)) u_local(
            .ck(ck),.rsi(rsi[c]),.bank(cb),.epo(epo),.vld(vld[c*D+:D]),.o(o[c*CHUNK_BITS+:CW]));
    end endgenerate
`ifndef SYNTHESIS
    initial if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) $fatal(1,"LAND_VECTOR_RESET_R_SHAPE");
`endif
endmodule
`default_nettype wire
