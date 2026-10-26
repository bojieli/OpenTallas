`timescale 1ns/1ps
// QC-P4 10-23: lockstep bench of the chain-end slice variants (tools/qwen_dv/gen_s8_chain_end.py) against the as-built
// slice qfd_dv_s8_flat with the die's literals on the chain-end inputs (die_r56: dvs_E1/E3/W1/W3/W5 .l9_wi(514'h0);
// dvs_E5 l9/st/ar*/dd/ag wi = 0).  Every other input is random each edge; every output is compared every edge.
//   VAR 0: qfd_dv_s8_ce_l9h   VAR 1: qfd_dv_s8_ce_e5 (QC-P5-TIE: also no sc_dn_i)   VAR 2: qfd_dv_s8_ce_w5 (l9h + no sc_up_i)
//   (die_r56 dvs_W5 .sc_wi(48'h0); E5 sc_dn chain end 0; the sc2 leaf of VAR 1/2 is the regenerated k79 netlist)
//   MUT 0: must PASS.  MUT 1: the reference sees random on the removed inputs (not the die's 0) -> must FAIL
//   (the removed inputs are observable, so the bench can see a wrong fold).  MUT 2: variant CE_MUT=1 (removed faces
//   fold to all-ones) -> must FAIL.
module tb_s8_ce;
    parameter integer VAR = 0;
    parameter integer MUT = 0;
    parameter integer CYC = 6000;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [115:0] cmd_i; reg [452:0] hr_i; reg [1027:0] rs_s, rs_n; reg [513:0] l9_i; reg [1087:0] st_up_i, st_dn_i;
    reg [47:0] sc_up_i, sc_dn_i; reg [1094:0] ch_up_i; reg [1037:0] ch_dn_i; reg [9:0] ag_up_i; reg [8:0] treq_i;
    // reference inputs: the die's literal on every removed port (MUT 1: the random value instead)
    wire [513:0]  r_l9    = (MUT == 1) ? l9_i : 514'h0;
    wire [1087:0] r_st_dn = (VAR == 1 && MUT != 1) ? 1088'h0 : st_dn_i;
    wire [1094:0] r_ch_up = (VAR == 1 && MUT != 1) ? 1095'h0 : ch_up_i;
    wire [9:0]    r_ag_up = (VAR == 1 && MUT != 1) ? 10'h0 : ag_up_i;
    wire [47:0]   r_sc_dn = (VAR == 1 && MUT != 1) ? 48'h0 : sc_dn_i;
    wire [47:0]   r_sc_up = (VAR == 2 && MUT != 1) ? 48'h0 : sc_up_i;
`define S8_OUTS(p) wire [115:0] p``cmd_o; wire [452:0] p``hr_o; wire [513:0] p``l9_o; wire [1087:0] p``st_up_o, p``st_dn_o; \
    wire [47:0] p``sc_up_o, p``sc_dn_o; wire [1094:0] p``ch_dn_o; wire [1037:0] p``ch_up_o; \
    wire [515:0] p``cw_n0, p``cw_n1, p``cw_n2, p``cw_n3, p``cw_s0, p``cw_s1, p``cw_s2, p``cw_s3; \
    wire [106:0] p``st; wire [49:0] p``cc_o; wire [9:0] p``ag_dn_o; wire [8:0] p``treq_o;
    `S8_OUTS(a_)
    `S8_OUTS(b_)
`define S8_OCONN(p) .cmd_o(p``cmd_o), .hr_o(p``hr_o), .l9_o(p``l9_o), .st_up_o(p``st_up_o), .st_dn_o(p``st_dn_o), \
    .sc_up_o(p``sc_up_o), .sc_dn_o(p``sc_dn_o), .ch_dn_o(p``ch_dn_o), .ch_up_o(p``ch_up_o), .cw_n0(p``cw_n0), \
    .cw_n1(p``cw_n1), .cw_n2(p``cw_n2), .cw_n3(p``cw_n3), .cw_s0(p``cw_s0), .cw_s1(p``cw_s1), .cw_s2(p``cw_s2), \
    .cw_s3(p``cw_s3), .st(p``st), .cc_o(p``cc_o), .ag_dn_o(p``ag_dn_o), .treq_o(p``treq_o)
    qfd_dv_s8_flat u_ref (.ck(clk), .rst_n(rst_n), .cmd_i(cmd_i), .hr_i(hr_i), .rs_s(rs_s), .rs_n(rs_n), .l9_i(r_l9),
        .st_up_i(st_up_i), .st_dn_i(r_st_dn), .sc_up_i(r_sc_up), .sc_dn_i(r_sc_dn), .ch_up_i(r_ch_up), .ch_dn_i(ch_dn_i),
        .ag_up_i(r_ag_up), .treq_i(treq_i), `S8_OCONN(a_));
    localparam integer CM = (MUT == 2) ? 1 : 0;
    generate if (VAR == 0) begin : g_l9h
        qfd_dv_s8_ce_l9h #(.CE_MUT(CM)) u_dut (.ck(clk), .rst_n(rst_n), .cmd_i(cmd_i), .hr_i(hr_i), .rs_s(rs_s),
            .rs_n(rs_n), .st_up_i(st_up_i), .st_dn_i(st_dn_i), .sc_up_i(sc_up_i), .sc_dn_i(sc_dn_i), .ch_up_i(ch_up_i),
            .ch_dn_i(ch_dn_i), .ag_up_i(ag_up_i), .treq_i(treq_i), `S8_OCONN(b_));
    end else if (VAR == 1) begin : g_e5
        qfd_dv_s8_ce_e5 #(.CE_MUT(CM)) u_dut (.ck(clk), .rst_n(rst_n), .cmd_i(cmd_i), .hr_i(hr_i), .rs_s(rs_s),
            .rs_n(rs_n), .st_up_i(st_up_i), .sc_up_i(sc_up_i), .ch_dn_i(ch_dn_i), .treq_i(treq_i),
            `S8_OCONN(b_));
    end else begin : g_w5
        qfd_dv_s8_ce_w5 #(.CE_MUT(CM)) u_dut (.ck(clk), .rst_n(rst_n), .cmd_i(cmd_i), .hr_i(hr_i), .rs_s(rs_s),
            .rs_n(rs_n), .st_up_i(st_up_i), .st_dn_i(st_dn_i), .sc_dn_i(sc_dn_i), .ch_up_i(ch_up_i),
            .ch_dn_i(ch_dn_i), .ag_up_i(ag_up_i), .treq_i(treq_i), `S8_OCONN(b_));
    end endgenerate
    wire [115:0] a_all_lo = a_cmd_o; // keep lint quiet on the macro-only names
    task automatic rnd(output reg [1099:0] v); integer i; begin for (i = 0; i < 1100; i = i + 32) v[i +: 32] = $urandom; end endtask
    reg [1099:0] t;
    task automatic drive; begin
        rnd(t); cmd_i = t[115:0]; rnd(t); hr_i = t[452:0]; rnd(t); rs_s = t[1027:0]; rnd(t); rs_n = t[1027:0];
        rnd(t); l9_i = t[513:0]; rnd(t); st_up_i = t[1087:0]; rnd(t); st_dn_i = t[1087:0]; rnd(t); sc_up_i = t[47:0];
        sc_dn_i = t[95:48]; rnd(t); ch_up_i = t[1094:0]; rnd(t); ch_dn_i = t[1037:0]; rnd(t); ag_up_i = t[9:0];
        treq_i = t[18:10];
    end endtask
    integer cyc, nc, bad, nz;
`define CMP(x) begin nc = nc + 1; if (a_``x !== b_``x) begin bad = bad + 1; if (bad <= 6) $display("CE_MISMATCH port=%s cycle=%0d", `"x`", cyc); end end
    initial begin
        nc = 0; bad = 0; nz = 0; drive;
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == 16) rst_n = 1'b1;
            drive;
            if (|a_l9_o || |a_st_dn_o || |a_ch_dn_o) nz = nz + 1;
            `CMP(cmd_o) `CMP(hr_o) `CMP(l9_o) `CMP(st_up_o) `CMP(st_dn_o) `CMP(sc_up_o) `CMP(sc_dn_o) `CMP(ch_dn_o)
            `CMP(ch_up_o) `CMP(cw_n0) `CMP(cw_n1) `CMP(cw_n2) `CMP(cw_n3) `CMP(cw_s0) `CMP(cw_s1) `CMP(cw_s2) `CMP(cw_s3)
            `CMP(st) `CMP(cc_o) `CMP(ag_dn_o) `CMP(treq_o)
        end
        if (bad == 0 && nc > 0) $display("S8_CE_LOCKSTEP PASS VAR=%0d MUT=%0d compared=%0d active_cycles=%0d cycles=%0d", VAR, MUT, nc, nz, CYC);
        else $display("S8_CE_LOCKSTEP FAIL VAR=%0d MUT=%0d mismatches=%0d of %0d", VAR, MUT, bad, nc);
        $finish;
    end
endmodule
