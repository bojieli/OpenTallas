// MODELED licensed PHY black box; functional simulation uses kv_phy_slices.sv.
(* blackbox *)
module qkd_hbm3e_phy_pc4 (
    input wire clk,
    input wire rst_n,
    input wire [327:0] po0,
    output wire [288:0] pi0,
    output wire [3:0] fh0,
    output wire [3:0] rh0,
    input wire [327:0] po1,
    output wire [288:0] pi1,
    output wire [3:0] fh1,
    output wire [3:0] rh1,
    input wire [327:0] po2,
    output wire [288:0] pi2,
    output wire [3:0] fh2,
    output wire [3:0] rh2,
    input wire [327:0] po3,
    output wire [288:0] pi3,
    output wire [3:0] fh3,
    output wire [3:0] rh3
);
endmodule
