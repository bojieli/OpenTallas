`timescale 1ns/1ps
// Static full-rate level-6 -> level-7 transport for one eight-root slab half.
// Clock pins are independent compensated entries of one scheduled clock family.
// There is no dynamic admission or ready/credit path. Each root slot is sampled
// every edge; valid accompanies its data, including idle edges.
module qfd_slab_word_half_old #(
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
    genvar i,p,l;
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
    generate for(p=0;p<4;p=p+1) begin:g_pair
        localparam integer IA = MUTANT ? p : 2*p;
        localparam integer IB = MUTANT ? p+4 : 2*p+1;
        (* keep *) reg reset_q;
        always @(posedge pair_ck[p]) reset_q <= rst_n;
        wire valid_in = captured[514*IA+512] & captured[514*IB+512];
        wire [15:0] lv;
        wire [31:0] le;
        for(l=0;l<16;l=l+1) begin:g_lane
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT),.DRST(0)) u_add (
                .clk(pair_ck[p]), .rst_n(reset_q), .valid_in(valid_in),
                .a(captured[514*IA+32*l +: 32]), .b(captured[514*IB+32*l +: 32]),
                .y(summed[512*p+32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
        end
        reg mismatch;
        always @(posedge pair_ck[p])
            if(!reset_q) mismatch <= 1'b0;
            else mismatch <= mismatch | (captured[514*IA+512] ^ captured[514*IB+512])
                | captured[514*IA+513] | captured[514*IB+513];
        assign pv[p] = lv[0];
        assign pf[p] = mismatch | (lv[0] & (|le)) | (|(lv ^ {16{lv[0]}}));
    end endgenerate
    (* keep *) reg [2049:0] output_q;
    always @(posedge ck) begin
        output_q[2047:0] <= summed;
        output_q[2048] <= rst_n & pv[0];
        output_q[2049] <= rst_n & ((|pf) | (|(pv ^ {4{pv[0]}})));
    end
    assign cw = output_q;
endmodule
