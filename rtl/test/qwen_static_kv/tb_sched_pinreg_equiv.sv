// sched_s8 (KV-SCHED8 2026-10-17): qkd_ctrl_pc_sched PINREG=1 (flop-first pins) against the CLOSED sched_s7b reference
// (qkd_ctrl_pc_sched_s7b_ref). Contract: po, p_w_v, p_w_d, physical_context, physical_col_sr, expected_sr, idle_hbm, fo
// and ko are the s7b outputs exactly ONE pll_hbm edge later; every other output is the s7b output on the same edge.
// PINREG=0 is also checked same-cycle against the reference (s7b logic unchanged). Driven over repeated reset episodes:
// QUIET episodes (nothing inside the strap delay, then lone p_em_v / obs_commit_valid / native_commit_valid pulses spaced
// so idle_hbm re-asserts between them, mode 1 a single fault on one fault pin, mode 2 a lone static command and a kc GO)
// reach idle_hbm and drop it; RANDOM episodes drive every input (columns, writes, returns, faults).
// Mutant: +define+OT_SCHED_PINREG_MUT (the D-form idle veto drops the p_em_v pin flop) must FAIL.
`timescale 1ns/1ps
module tb_sched_pinreg_equiv;
    reg pll_hbm = 0;
    always #0.4165 pll_hbm = ~pll_hbm;
    reg hrst = 0;
    reg [4:0] pc = 0;
    reg [62:0] ci_c = 0;
    reg pi_v = 0;
    reg [32:0] ki = 0;
    reg fi = 0;
    reg static_cmd_owner = 0;
    reg [42:0] static_cmd = 0;
    reg reserved_rd = 0, reserved_static_col = 0, reserved_write_col = 0;
    reg [15:0] static_epoch = 0;
    reg expected_raw_valid = 0;
    reg [287:0] p_wd = 0;
    reg p_kv_v = 0, p_em_v = 0, p_fault = 0, e_l_v = 0, e_fault = 0;
    reg c_v = 0;
    reg [286:0] c_d = 0;
    reg [61:0] c_context = 0;
    reg f_ecdc = 0, obs_commit_valid = 0, native_commit_valid = 0, native_observer_fault = 0;

`define SCHED_OUTS(sfx) \
    wire [11:0] co_c_``sfx; wire [327:0] po_``sfx; wire [32:0] ko_``sfx; wire fo_``sfx; wire [15:0] cep_``sfx; \
    wire idle_``sfx, dfh_``sfx, pcv_``sfx, pcwe_``sfx, pcsr_``sfx, pwv_``sfx; wire [255:0] pwd_``sfx; \
    wire [16:0] esec_``sfx; wire [7:0] erow_``sfx; wire [4:0] pcq_``sfx; wire scr_``sfx; \
    wire [346:0] pctx_``sfx; wire phsr_``sfx, esr_``sfx;
    `SCHED_OUTS(n)
    `SCHED_OUTS(z)
    `SCHED_OUTS(r)
`define SCHED_PORTS(sfx) \
        .pll_hbm(pll_hbm), .hrst(hrst), .pc(pc), .ci_c(ci_c), .co_c(co_c_``sfx), .po(po_``sfx), .pi_v(pi_v), .ki(ki), \
        .ko(ko_``sfx), .fi(fi), .fo(fo_``sfx), .static_cmd_owner(static_cmd_owner), .static_cmd(static_cmd), \
        .reserved_rd(reserved_rd), .reserved_static_col(reserved_static_col), .reserved_write_col(reserved_write_col), \
        .static_epoch(static_epoch), .expected_raw_valid(expected_raw_valid), .corrected_epoch(cep_``sfx), \
        .idle_hbm(idle_``sfx), .drain_fault_hbm(dfh_``sfx), .p_col_v(pcv_``sfx), .p_col_we(pcwe_``sfx), \
        .p_col_sr(pcsr_``sfx), .p_w_v(pwv_``sfx), .p_w_d(pwd_``sfx), .p_wd(p_wd), .p_kv_v(p_kv_v), .p_em_v(p_em_v), \
        .p_fault(p_fault), .e_sec(esec_``sfx), .e_row(erow_``sfx), .e_l_v(e_l_v), .e_fault(e_fault), .pc_q(pcq_``sfx), \
        .s_cr_o(scr_``sfx), .c_v(c_v), .c_d(c_d), .c_context(c_context), .f_ecdc(f_ecdc), \
        .physical_context(pctx_``sfx), .physical_col_sr(phsr_``sfx), .expected_sr(esr_``sfx), \
        .obs_commit_valid(obs_commit_valid), .native_commit_valid(native_commit_valid), \
        .native_observer_fault(native_observer_fault)
    qkd_ctrl_pc_sched #(.PROFILE(0), .ELASTIC(1), .RAW_WD(256), .TQD(64), .DRAIN_PIPE(1), .STRAP_CDC(1), .PINREG(1)) dut (
        `SCHED_PORTS(n));
    qkd_ctrl_pc_sched #(.PROFILE(0), .ELASTIC(1), .RAW_WD(256), .TQD(64), .DRAIN_PIPE(1), .STRAP_CDC(1), .PINREG(0)) dut0 (
        `SCHED_PORTS(z));
    qkd_ctrl_pc_sched_s7b_ref #(.PROFILE(0), .ELASTIC(1), .RAW_WD(256), .TQD(64), .DRAIN_PIPE(1), .STRAP_CDC(1)) ref0 (
        `SCHED_PORTS(r));

    // one-edge-later group (P) and same-edge group (S)
    localparam integer PW = 328 + 1 + 256 + 347 + 1 + 1 + 1 + 1 + 33;
    localparam integer SW = 12 + 16 + 1 + 3 + 17 + 8 + 5 + 1;
    wire [PW-1:0] p_n = {po_n, pwv_n, pwd_n, pctx_n, phsr_n, esr_n, idle_n, fo_n, ko_n};
    wire [PW-1:0] p_z = {po_z, pwv_z, pwd_z, pctx_z, phsr_z, esr_z, idle_z, fo_z, ko_z};
    wire [PW-1:0] p_r = {po_r, pwv_r, pwd_r, pctx_r, phsr_r, esr_r, idle_r, fo_r, ko_r};
    wire [SW-1:0] s_n = {co_c_n, cep_n, dfh_n, pcv_n, pcwe_n, pcsr_n, esec_n, erow_n, pcq_n, scr_n};
    wire [SW-1:0] s_z = {co_c_z, cep_z, dfh_z, pcv_z, pcwe_z, pcsr_z, esec_z, erow_z, pcq_z, scr_z};
    wire [SW-1:0] s_r = {co_c_r, cep_r, dfh_r, pcv_r, pcwe_r, pcsr_r, esec_r, erow_r, pcq_r, scr_r};
    reg [PW-1:0] p_r_prev;
    reg prev_ok = 0;
    integer compares = 0, mism = 0, mism0 = 0, idle_cycles = 0, idle_drops = 0, cols = 0, fo_rises = 0, pw_beats = 0;
    reg idle_r_prev = 0, fo_r_prev = 0;
    always @(posedge pll_hbm) begin
        #0.1;
        compares = compares + 1;
        if (prev_ok && (p_n !== p_r_prev || s_n !== s_r)) begin
            mism = mism + 1;
            if (mism <= 6) $display("MISMATCH t=%0t idle new=%b ref(prev)=%b fo new=%b ref(prev)=%b po_eq=%b same_eq=%b",
                $time, idle_n, p_r_prev[34], fo_n, p_r_prev[33], po_n === p_r_prev[PW-1 -: 328], s_n === s_r);
        end
        if (p_z !== p_r || s_z !== s_r) begin
            mism0 = mism0 + 1;
            if (mism0 <= 3) $display("MISMATCH0 t=%0t (PINREG=0 vs s7b same-cycle)", $time);
        end
        if (idle_r === 1'b1) idle_cycles = idle_cycles + 1;
        if (idle_r_prev === 1'b1 && idle_r === 1'b0) idle_drops = idle_drops + 1;
        if (po_r[28] === 1'b1) cols = cols + 1;
        if (fo_r_prev === 1'b0 && fo_r === 1'b1) fo_rises = fo_rises + 1;
        if (pwv_r === 1'b1) pw_beats = pw_beats + 1;
        idle_r_prev = idle_r; fo_r_prev = fo_r;
        p_r_prev = p_r; prev_ok = 1;
    end

    function automatic [287:0] rnd288; integer i; begin for (i = 0; i < 9; i = i + 1) rnd288[i*32 +: 32] = $urandom; end endfunction
    function automatic [286:0] rnd287; integer i; begin rnd287 = 0; for (i = 0; i < 9; i = i + 1) rnd287[i*32 +: 32] = $urandom; end endfunction

    task automatic clear_pulses;
        begin
            ki[0] = 0; ci_c[3] = 0; ci_c[28] = 0; ci_c[62] = 0; static_cmd[0] = 0; static_cmd_owner = 0; pi_v = 0;
            p_kv_v = 0; p_em_v = 0; p_fault = 0; e_l_v = 0; e_fault = 0; c_v = 0; f_ecdc = 0; fi = 0;
            obs_commit_valid = 0; native_commit_valid = 0; native_observer_fault = 0; expected_raw_valid = 0;
            reserved_rd = 0; reserved_static_col = 0; reserved_write_col = 0;
        end
    endtask

    integer ep, k, len, mode, fault_at, fault_sel;
    initial begin
        for (ep = 0; ep < 900; ep = ep + 1) begin
            mode = ep % 4;                       // 0,1,2 quiet; 3 random
            @(negedge pll_hbm); hrst = 0; clear_pulses();
            pc = $urandom;
            repeat (3 + ($urandom % 3)) @(negedge pll_hbm);
            hrst = 1;
            len = 260 + ($urandom % 200);
                        fault_at = (mode == 1) ? 160 + ($urandom % 80) : -1; fault_sel = $urandom % 5;
            for (k = 0; k < len; k = k + 1) begin
                @(negedge pll_hbm);
                // data buses always random (data must follow the s7b timing bit for bit)
                p_wd = rnd288(); c_d = rnd287(); c_context = {$urandom, $urandom}; static_epoch = $urandom;
                ci_c[61:4] = {$urandom, $urandom}; ci_c[2:0] = $urandom; ki[32:1] = $urandom;
                static_cmd[42:1] = {$urandom, $urandom};
                if (mode == 3) begin
                    ci_c[3] = $urandom; ci_c[28] = $urandom; ci_c[62] = ($urandom % 64) == 0;
                    ki[0] = $urandom; pi_v = $urandom; fi = ($urandom % 64) == 0; static_cmd_owner = ($urandom % 8) == 0;
                    static_cmd[0] = $urandom; reserved_rd = $urandom; reserved_static_col = $urandom;
                    reserved_write_col = $urandom; expected_raw_valid = $urandom; p_kv_v = $urandom; p_em_v = $urandom;
                    p_fault = ($urandom % 64) == 0; e_l_v = $urandom; e_fault = ($urandom % 64) == 0; c_v = $urandom;
                    f_ecdc = ($urandom % 64) == 0; obs_commit_valid = $urandom; native_commit_valid = $urandom;
                    native_observer_fault = ($urandom % 64) == 0;
                end else begin
                    clear_pulses();
                    // legal quiet traffic: nothing inside the strap delay (<= 119 edges), then lone veto pulses spaced
                    // so idle_hbm re-asserts between them; mode 2 ends with a lone static command (c_v) and a kc GO
                    if (k >= 140 && (k % 9) == ($urandom % 2)) case ($urandom % 3)
                        0: p_em_v = 1; 1: obs_commit_valid = 1; default: native_commit_valid = 1;
                    endcase
                    if (mode == 2 && k == len - 30) c_v = 1;
                    if (mode == 2 && k == len - 15) begin ki[0] = 1; ki[32:31] = 2'd1; end
                    if (k == fault_at) case (fault_sel)
                        0: p_fault = 1; 1: e_fault = 1; 2: f_ecdc = 1; 3: fi = 1; default: native_observer_fault = 1;
                    endcase
                end
            end
        end
        repeat (4) @(negedge pll_hbm);
        if (mism0 != 0) $display("FAIL sched pinreg equiv: PINREG=0 differs from s7b on %0d samples", mism0);
        else if (mism != 0) $display("FAIL sched pinreg equiv: %0d mismatching samples of %0d", mism, compares);
        else if (idle_cycles < 5000 || idle_drops < 200 || cols < 1000 || fo_rises < 200 || pw_beats < 1000)
            $display("FAIL sched pinreg equiv: coverage idle %0d drops %0d cols %0d fo_rises %0d pw %0d",
                     idle_cycles, idle_drops, cols, fo_rises, pw_beats);
        else $display("PASS sched pinreg equiv: %0d samples, PINREG=1 = s7b (+1 hclk on po/p_w/physical/expected_sr/idle_hbm/fo/ko, same edge elsewhere), PINREG=0 = s7b; idle %0d cycles, %0d idle drops, %0d columns, %0d fo rises, %0d p_w beats",
                      compares, idle_cycles, idle_drops, cols, fo_rises, pw_beats);
        $finish;
    end
endmodule
