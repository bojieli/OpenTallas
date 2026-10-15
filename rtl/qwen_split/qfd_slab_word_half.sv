`timescale 1ns/1ps
// Static full-rate level-6 -> level-7 transport for one eight-root slab half.
// Clock pins are independent compensated entries of one scheduled clock family.
// There is no dynamic admission or ready/credit path. Each root slot is sampled
// every edge; valid accompanies its data, including idle edges.
module qfd_slab_word_half #(
    parameter integer ADD_LAT = 7,
    parameter integer MUTANT = 0
) (
    input wire ck,
    input wire ck_bw0, ck_bw1, ck_bw2, ck_bw3,
    input wire ck_bw4, ck_bw5, ck_bw6, ck_bw7,
    input wire ck_pair0, ck_pair1, ck_pair2, ck_pair3,
    input wire rst_n,
    input wire [8*514-1:0] bw,
    output wire [2049:0] cw
);
    wire [7:0] bw_ck = {ck_bw7,ck_bw6,ck_bw5,ck_bw4,ck_bw3,ck_bw2,ck_bw1,ck_bw0};
    wire [3:0] pair_ck = {ck_pair3,ck_pair2,ck_pair1,ck_pair0};
    wire [8*514-1:0] captured;
    genvar i,p;
    generate for(i=0;i<8;i=i+1) begin:g_root
        (* keep *) reg [513:0] q;
        (* keep *) reg reset_q;
        always @(posedge bw_ck[i]) reset_q <= rst_n;
        always @(posedge bw_ck[i]) begin
            q[511:0] <= bw[514*i +: 512];
            q[513:512] <= reset_q ? bw[514*i+512 +: 2] : 2'b0;
        end
        assign captured[514*i +: 514] = q;
    end endgenerate
    wire [2047:0] summed;
    wire [3:0] pv,pf;
    // q15: each pair is the hardened leaf qfd_slab_pair_add on its own clock entry (same logic and latency).
    generate for(p=0;p<4;p=p+1) begin:g_pair
        localparam integer IA = MUTANT ? p : 2*p;
        localparam integer IB = MUTANT ? p+4 : 2*p+1;
        qfd_slab_pair_add #(.ADD_LAT(ADD_LAT)) u_pair (
            .ck(pair_ck[p]), .rst_n(rst_n),
            .wa(captured[514*IA +: 514]), .wb(captured[514*IB +: 514]),
            .y(summed[512*p +: 512]), .pv(pv[p]), .pf(pf[p]));
    end endgenerate
    (* keep *) reg [2049:0] output_q;
    always @(posedge ck) begin
        output_q[2047:0] <= summed;
        output_q[2048] <= rst_n & pv[0];
        output_q[2049] <= rst_n & ((|pf) | (|(pv ^ {4{pv[0]}})));
    end
    assign cw = output_q;
endmodule
