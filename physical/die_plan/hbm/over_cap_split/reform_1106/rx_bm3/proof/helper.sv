module ot_pdie_serdes_rx_bm_native #(parameter integer BMTHC=1) (
    input wire clk, rs_n, input wire [3:0] ld, input wire [299:0] S,
    output wire [159:0] lam, output wire [149:0] om,
    output wire [4:0] L, output wire any, output wire [3:0] done
);
    ot_s81_kp4_bm #(.NG(4), .NCD(4), .THC(BMTHC)) u_native (
        .clk(clk), .rs_n(rs_n), .ld(ld), .S(S), .lam(lam), .om(om), .L(L), .any(any), .done(done));
endmodule
