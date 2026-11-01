// Signed MIF0 metadata only. Canonical functional RTL and child proof remain authoritative.
// FT arcs are die-owned physical ports; VDD/VSS are explicit LEF POWER/GROUND, not functional ports.
(* blackbox *) module qfd_dv_s8x_vmr #(parameter integer MUT = 0, parameter integer MIF = 0) (
    input wire ck,
    input wire rst_n,
    input wire [7:0] re,
    input wire [191:0] addr,
    output wire [255:0] q,
    input wire [7:0] vm_we,
    input wire [191:0] vm_waddr,
    input wire [255:0] vm_wdata,
    input wire w16_we,
    input wire [23:0] w16_addr,
    input wire [511:0] w16_data,
    input wire w1_we,
    input wire [23:0] w1_addr,
    input wire [31:0] w1_data,
    output wire fault,
    input wire ft_ck_i,
    output wire ft_ck_o,
    input wire ft_rst_i,
    output wire ft_rst_o
);
endmodule
