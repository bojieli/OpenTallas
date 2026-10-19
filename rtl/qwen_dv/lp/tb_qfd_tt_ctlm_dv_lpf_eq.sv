`timescale 1ns/1ps
// HF-4 10-18: lockstep qfd_tt_ctlm_dv (HARD_HR 1, STAGE_ME 1, XPF 20; MUT = DMUT) vs the wires-only re-cut
// qfd_tt_ctlm_dv_lpf, same clock / reset / random inputs, every output compared every cycle (0 edges apart).
// PASS at DMUT 0 = the re-partition is cycle-exact; DMUT 5 / 6 / 8 (dc mutants of the original) must FAIL.
module tb_qfd_tt_ctlm_dv_lpf_eq;
    parameter integer DMUT = 0;
    parameter integer CYC = 4000;
    parameter integer NU = 4;                   // MU-ADOPT-CTLM 10-19: both sides at the cluster's NU, random dh_user
    parameter integer OPSEG = 1;                // MU-DQ-CTLMKIT 10-19: the die's OPSEG 1 leaf (ROM via +OT_ROM_DIR=<dir>)
    reg ck = 1'b0; always #0.5 ck = ~ck;
    reg rst_n = 1'b0;
    reg [1:0] dh_user;
    reg [74:0] pw; reg [186:0] dh; reg kok, kwd, fab; reg [94:0] native_ret; reg [106:0] ss5; reg [9:0] ag5;
    wire [75:0] a_program_obs, b_program_obs; wire a_csr, b_csr, a_lcv, b_lcv; wire [17:0] a_nt, b_nt, a_np, b_np;
    wire [5:0] a_cs, b_cs; wire [75:0] a_cpo, b_cpo; wire [68:0] a_cdo, b_cdo; wire a_cir, b_cir; wire [55:0] a_dc, b_dc;
    wire [379:0] a_nc, b_nc; wire [452:0] a_hr, b_hr; wire [115:0] a_cmd, b_cmd; wire a_es, b_es; wire [17:0] a_et, b_et;
    wire a_cf, b_cf;
    wire [1087:0] a_tl, b_tl;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(20), .STAGE_ME(1), .HARD_HR(1), .MUT(DMUT), .NU(NU), .OPSEG(OPSEG)) u_a (.ck(ck), .rst_n(rst_n),
        .pw(pw), .dh(dh), .dh_user(dh_user), .kok(kok), .kwd(kwd), .fab(fab), .program_obs(a_program_obs), .control_stores_ready(a_csr),
        .layer_context_v(a_lcv), .native_tok(a_nt), .native_pos(a_np), .command_stage(a_cs), .cal_program_obs(a_cpo),
        .cal_descriptor_obs(a_cdo), .cal_image_ready(a_cir), .dc(a_dc), .native_cmd(a_nc), .native_ret(native_ret),
        .hr(a_hr), .cmd(a_cmd), .tl(a_tl), .ss5(ss5), .ag5(ag5), .emb_start(a_es), .emb_token(a_et), .cf(a_cf));
    qfd_tt_ctlm_dv_lpf #(.XPF_TRANSPORT_EDGES(20), .STAGE_ME(1), .NU(NU), .OPSEG(OPSEG)) u_b (.ck(ck), .rst_n(rst_n),
        .pw(pw), .dh(dh), .dh_user(dh_user), .kok(kok), .kwd(kwd), .fab(fab), .program_obs(b_program_obs), .control_stores_ready(b_csr),
        .layer_context_v(b_lcv), .native_tok(b_nt), .native_pos(b_np), .command_stage(b_cs), .cal_program_obs(b_cpo),
        .cal_descriptor_obs(b_cdo), .cal_image_ready(b_cir), .dc(b_dc), .native_cmd(b_nc), .native_ret(native_ret),
        .hr(b_hr), .cmd(b_cmd), .tl(b_tl), .ss5(ss5), .ag5(ag5), .emb_start(b_es), .emb_token(b_et), .cf(b_cf));
    wire [3135:0] va = {a_tl, a_program_obs, a_csr, a_lcv, a_nt, a_np, a_cs, a_cpo, a_cdo, a_cir, a_dc, a_nc, a_hr, a_cmd, a_es, a_et, a_cf};
    wire [3135:0] vb = {b_tl, b_program_obs, b_csr, b_lcv, b_nt, b_np, b_cs, b_cpo, b_cdo, b_cir, b_dc, b_nc, b_hr, b_cmd, b_es, b_et, b_cf};
    integer act_tl, act_op, act_fill;
    integer cyc, bad, nc, act, act_nc, act_cmd, act_hr;
    reg [3135:0] vprev;
    task rnd; begin
        pw = {$urandom, $urandom, $urandom}; dh = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        // stage starts / program writes sparse enough that the calendar and head run segments, not only faults
        dh_user = $urandom;
        dh[42] = ($urandom % 61) == 0; dh[118] = ($urandom % 3) == 0; dh[186] = ($urandom % 5) == 0; pw[74] = ($urandom % 3) == 0;
        kok = $urandom; kwd = $urandom; fab = ($urandom % 97) == 0; native_ret = {$urandom, $urandom, $urandom};
        ss5 = {$urandom, $urandom, $urandom, $urandom}; ag5 = $urandom; ag5[8] = ($urandom % 53) == 0;
    end endtask
    initial begin
        act_tl = 0; act_op = 0; act_fill = 0;
        bad = 0; nc = 0; act = 0; act_nc = 0; act_cmd = 0; act_hr = 0; vprev = 0; rnd;
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge ck);
            if (cyc == 16) rst_n = 1'b1;
            rnd;
            if (cyc > 20) begin
                nc = nc + 1; if (va !== vprev) act = act + 1; if (va[968:589] !== vprev[968:589]) act_nc = act_nc + 1;
                vprev = va; if (a_tl != 0) act_tl = act_tl + 1;
                if (u_a.l_start) act_op = act_op + 1; if (u_a.r_fill) act_fill = act_fill + 1;
                if (va !== vb) begin bad = bad + 1;
                    if (bad <= 5) $display("EQ_MISMATCH cycle=%0d dc %h/%h hr_lo %h/%h cmd %h/%h cf %b/%b", cyc, a_dc, b_dc,
                        a_hr[72:0], b_hr[72:0], a_cmd, b_cmd, a_cf, b_cf); end
            end
        end
        $display("LPF_EQ ACTIVITY output-vector changes %0d of %0d cycles; native_cmd field changes %0d; tl words %0d; leaf op starts %0d; result-user fills %0d",
                 act, nc, act_nc, act_tl, act_op, act_fill);
        if (bad == 0 && nc > 0) $display("LPF_EQ PASS DMUT=%0d compared=%0d", DMUT, nc);
        else $display("LPF_EQ FAIL DMUT=%0d mismatches=%0d of %0d", DMUT, bad, nc);
        $finish;
    end
endmodule
