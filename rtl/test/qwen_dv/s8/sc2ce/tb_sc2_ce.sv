`timescale 1ns/1ps
// QC-P5-TIE 10-23: lockstep bench of the chain-end sc2 kit leaves (bounded k79 netlists regenerated without one chain
// face, tools/qwen_dv/gen_sc2_chain_end.py) against the as-built kit leaf qfd_dv_s5_sc2_leaf (netlist
// qfd_dv_s5_sc2_k79) with the die's literal 0 on that face (die_r56: dvs_W5 .sc_wi(48'h0); dvs_E5 sc_dn chain end).
// Every other input is random each edge (incl. the surviving chain face); every output is compared every edge.
//   VAR 0: qfd_dv_s5_sc2_leaf_dn0 (E5)   VAR 1: qfd_dv_s5_sc2_leaf_up0 (W5)
//   MUT 0: must PASS.  MUT 1 (runtime +mut1, same build): the reference sees random on the removed face (not the die's
//   0) -> must FAIL (the face is observable).  MUT 2 (+define+OT_S5_SC2CE_MUT_NETLIST): the CE_MUT=1 mutant netlist
//   (face folds to all-ones) -> must FAIL.
module tb_sc2_ce;
    parameter integer VAR = 0;
    parameter integer MUT_NET = 0;      // 1 = built with +define+OT_S5_SC2CE_MUT_NETLIST (reported as MUT 2)
    integer MUT = 0;
    initial MUT = $test$plusargs("mut1") ? 1 : (MUT_NET ? 2 : 0);
    parameter integer CYC = 20000;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [100:0] sc_cfg; reg [47:0] dn_i, up_i; reg red_we; reg [23:0] red_addr; reg [31:0] red_data; reg [7:0] vm_we;
    reg [1:0] vm_win0; reg [31:0] vm_wdata0; reg am_v; reg [23:0] am_idx; reg [31:0] am_val; reg [1:0] am_u;
    wire [47:0] r_dn = (VAR == 0 && MUT != 1) ? 48'h0 : dn_i;
    wire [47:0] r_up = (VAR == 1 && MUT != 1) ? 48'h0 : up_i;
`define SC_OUTS(p) wire [47:0] p``dn_o, p``up_o; wire p``w1_we, p``tok_v, p``tok_own, p``busy, p``fault; \
    wire [23:0] p``w1_addr, p``tok_idx; wire [31:0] p``w1_data, p``tok_val; wire [1:0] p``tok_user;
    `SC_OUTS(a_)
    `SC_OUTS(b_)
`define SC_COMMON .ck(clk), .rst_n(rst_n), .sc_cfg(sc_cfg), .red_we(red_we), .red_addr(red_addr), .red_data(red_data), \
    .vm_we(vm_we), .vm_win0(vm_win0), .vm_wdata0(vm_wdata0), .am_v(am_v), .am_idx(am_idx), .am_val(am_val), .am_u(am_u)
`define SC_OCONN(p) .dn_o(p``dn_o), .up_o(p``up_o), .w1_we(p``w1_we), .w1_addr(p``w1_addr), .w1_data(p``w1_data), \
    .tok_v(p``tok_v), .tok_idx(p``tok_idx), .tok_own(p``tok_own), .tok_val(p``tok_val), .tok_user(p``tok_user), \
    .busy(p``busy), .fault(p``fault)
    qfd_dv_s5_sc2_leaf u_ref (`SC_COMMON, .dn_i(r_dn), .up_i(r_up), `SC_OCONN(a_));
    generate if (VAR == 0) begin : g_dn0
        qfd_dv_s5_sc2_leaf_dn0 u_dut (`SC_COMMON, .up_i(up_i), `SC_OCONN(b_));
    end else begin : g_up0
        qfd_dv_s5_sc2_leaf_up0 u_dut (`SC_COMMON, .dn_i(dn_i), `SC_OCONN(b_));
    end endgenerate
    // stimulus: config words mostly stable (cfg_v pulses), chain words / pushes / argmax candidates random each edge
    reg [100:0] cfg_hold;
    task automatic drive(input integer c); begin
        if (c % 512 == 0) begin cfg_hold = {$urandom, $urandom, $urandom, $urandom}; end
        sc_cfg = cfg_hold; sc_cfg[100] = (c % 512 == 1) || ($urandom % 64 == 0);
        dn_i = {$urandom, $urandom}; up_i = {$urandom, $urandom};
        red_we = $urandom; red_addr = $urandom; red_data = $urandom; vm_we = $urandom; vm_win0 = $urandom;
        vm_wdata0 = $urandom; am_v = $urandom; am_idx = $urandom; am_val = $urandom; am_u = $urandom;
    end endtask
    integer cyc, nc, bad, act;
`define CMP(x) begin nc = nc + 1; if (a_``x !== b_``x) begin bad = bad + 1; if (bad <= 6) $display("SC2CE_MISMATCH port=%s cycle=%0d ref=%h dut=%h", `"x`", cyc, a_``x, b_``x); end end
    initial begin
        nc = 0; bad = 0; act = 0; cfg_hold = 0; drive(0);
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == 16) rst_n = 1'b1;
            drive(cyc);
            if (a_dn_o[47] || a_up_o[47] || a_tok_v || a_w1_we) act = act + 1;
            `CMP(dn_o) `CMP(up_o) `CMP(w1_we) `CMP(w1_addr) `CMP(w1_data) `CMP(tok_v) `CMP(tok_idx) `CMP(tok_own)
            `CMP(tok_val) `CMP(tok_user) `CMP(busy) `CMP(fault)
        end
        if (bad == 0 && nc > 0) $display("SC2_CE_LOCKSTEP PASS VAR=%0d MUT=%0d compared=%0d active_cycles=%0d cycles=%0d", VAR, MUT, nc, act, CYC);
        else $display("SC2_CE_LOCKSTEP FAIL VAR=%0d MUT=%0d mismatches=%0d of %0d", VAR, MUT, bad, nc);
        $finish;
    end
endmodule
