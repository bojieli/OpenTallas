// Signed MIF0 metadata only. Canonical functional RTL and child proof remain authoritative.
// FT arcs are die-owned physical ports; VDD/VSS are explicit LEF POWER/GROUND, not functional ports.
(* blackbox *) module qfd_dv_s8_crh_rp1 #(parameter integer MIF = 0) (
    input wire ck,
    input wire rst_n,
    input wire [7:0] cr_re,
    input wire [191:0] cr_addr,
    output wire [255:0] q,
    input wire tw_we,
    input wire [1:0] tw_kind,
    input wire [23:0] tw_addr,
    input wire [511:0] tw_d,
    output wire fault,
    input wire ft_ck_i,
    output wire ft_ck_o,
    input wire ft_rst_i,
    output wire ft_rst_o
);
endmodule
