`timescale 1ns/1ps
// FABLE-FIX-S81-SEQHOST (2026-11-19): bounded miter, restructured dsdv_mu_hwin against the 11-18 source at a small
// table (yosys sat -seq from the all-zero state, every pin free on every edge; run_mu_hwin_eq.sh step 3).
module hwin_eq_miter (
    input  wire ck, rst_n,
    input  wire [52:0] f_ks, input wire [25:0] f_mc, f_mw, input wire [31:0] mu_rt,
    output wire ok
);
    localparam integer NSLOT = 3, NEV = 2, NEP = 2, NRT = 1;
    wire [NEP*34-1:0] c_r, c_d; wire [NEP*11-1:0] rc_r, rc_d; wire [1:0] wf_r, wf_d;
    dsdv_mu_hwin_ref_1119 #(.NSLOT(NSLOT), .NEV(NEV), .NEP(NEP), .NRT(NRT)) gold (.ck(ck), .rst_n(rst_n),
        .f_ks(f_ks), .f_mc(f_mc), .f_mw(f_mw), .mu_c(c_r), .mu_rc(rc_r), .mu_rt(mu_rt), .t_wf(wf_r));
    dsdv_mu_hwin #(.NSLOT(NSLOT), .NEV(NEV), .NEP(NEP), .NRT(NRT)) dut (.ck(ck), .rst_n(rst_n),
        .f_ks(f_ks), .f_mc(f_mc), .f_mw(f_mw), .mu_c(c_d), .mu_rc(rc_d), .mu_rt(mu_rt), .t_wf(wf_d));
    assign ok = c_r == c_d && rc_r == rc_d && wf_r == wf_d;
endmodule
