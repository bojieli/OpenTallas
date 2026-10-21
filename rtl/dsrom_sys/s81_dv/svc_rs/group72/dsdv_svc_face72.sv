`timescale 1ns/1ps
`default_nettype none
// Existing mesochronous landing mechanism, banked at the existing 276-bit
// face-lane width. All payload/valid/control bits have the same D=4/K=2 age.
// No backpressure, arbitration, serialization or arithmetic transformation.
module dsdv_svc_face72 (
    input wire ck_w, ck_r, rst_w, rst_r,
    input wire [4544:0] i,
    output wire [4544:0] o
);
    localparam integer W=4545, B=276, N=(W+B-1)/B;
    wire [N-1:0] wrst, rrst;
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(N)) u_wr_reset
        (.ck(ck_w), .d(rst_w), .q(wrst));
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(N)) u_rd_reset
        (.ck(ck_r), .d(rst_r), .q(rrst));
    generate for(genvar b=0;b<N;b=b+1) begin:g_bank
        localparam integer BW=(W-b*B<B)?W-b*B:B;
        wire [4*BW-1:0] bank;
        wire [11:0] epo;
        wire [4*((BW+23)/24)-1:0] vld;
        ot_pl_land_n32_chunk_w #(.W(BW), .D(4), .CHUNK_BITS(24)) u_w
            (.ck(ck_w), .rsi(wrst[b]), .i(i[b*B+:BW]), .bank(bank), .epo(epo), .vld(vld));
        ot_pl_land_chunk_r #(.W(BW), .D(4), .K(2), .CHUNK_BITS(24)) u_r
            (.ck(ck_r), .rsi(rrst[b]), .bank(bank), .epo(epo), .vld(vld), .o(o[b*B+:BW]));
    end endgenerate
endmodule
`default_nettype wire
