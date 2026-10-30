
module ot_hdc_mul24_sum (
    input  wire [48*8-1:0] rows,
    output wire [47:0]     p
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(rows[144*i +: 48], rows[144*i + 48 +: 48], rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire unused_cout;
    ot_hdc_ksa #(.W(48)) u_cpa (.a(l7[47:0]), .b(l7[95:48]), .cin(1'b0), .s(p), .cout(unused_cout));
endmodule
