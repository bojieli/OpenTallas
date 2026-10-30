
// ot_hdc_mul24_rows with the operands supplied as K copies: partial product i reads copy i*K/24 (identical values)
module ot_hdc_mul24_rows_k #(parameter integer K = 2) (
    input  wire [K*24-1:0] a,
    input  wire [K*24-1:0] b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a[24*(i*K/24) +: 24] & {24{b[24*(i*K/24) + i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule
