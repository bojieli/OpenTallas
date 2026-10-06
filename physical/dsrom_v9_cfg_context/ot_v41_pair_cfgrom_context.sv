`timescale 1ns/1ps
// Finite enclosing configuration provider. HARD_CFG is off by default.
// The physical characterization selects HARD_CFG=1; original f471 loader
// state/GO/fault behavior is retained in the additive port companion.
module ot_v41_pair_cfgrom_context #(
    parameter integer HARD_CFG = 0,
    parameter integer PQ = 0,
    parameter string VIAMAP = ""
) (
    input wire clk, rst_n, cfg_go,
    input wire [5:0] cfg_ph,
    input wire [2:0] cfg_np,
    input wire go, e_sh_free, e_bank_free,
    input wire [47:0] external_cfg_q,
    output wire [10:0] cfg_rom_a,
    output wire [11:0] cfg_rom_read_a,
    output wire cfg_rom_read_ce,
    output wire c_v,
    output wire [4:0] c_a,
    output wire [47:0] c_d,
    output wire go_e, ld_busy, fault
);
    wire [47:0] cfg_q;
    ot_v41_pair_pq_ld_cfgrom #(.PHW(6), .PQ(PQ)) u_ld (
        .clk(clk), .rst_n(rst_n), .cfg_go(cfg_go), .cfg_ph(cfg_ph), .cfg_np(cfg_np),
        .go(go), .e_sh_free(e_sh_free), .e_bank_free(e_bank_free),
        .cm_a(cfg_rom_a), .cm_read_a(cfg_rom_read_a), .cm_read_ce(cfg_rom_read_ce),
        .cm_q(cfg_q), .c_v(c_v), .c_a(c_a), .c_d(c_d),
        .go_e(go_e), .ld_busy(ld_busy), .fault(fault)
    );
    if (HARD_CFG != 0) begin : g_hard_cfg
        wire [71:0] q;
        (* keep, dont_touch = "true" *)
        ot_rom_4096x72_m8 #(.VIAMAP(VIAMAP)) u_cfg (
            .clk(clk), .ce_in(cfg_rom_read_ce), .addr_in(cfg_rom_read_a), .rd_out(q)
        );
        assign cfg_q = q[47:0];
    end else begin : g_external_cfg
        assign cfg_q = external_cfg_q;
    end
endmodule
