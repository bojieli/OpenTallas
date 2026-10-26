`timescale 1ps/1ps
`default_nettype none
// S-DIE-WFC 2026-10-16: die-parent equivalence of the --wfc-return256 u_wfc (dsfd_vm_static_wfc_select256 RETURN256 1:
// u_wfc.split_return.u_ret = dsfd_vm_wfc_return_split256, two dsfd_vm_wfc_return256 slices + dsfd_vm_native_valid_diag on
// three return roots) against the frozen die u_wfc (dsfd_vm_static_wfc: legacy dsfd_vm_wfc_return), real RTL both sides.
// Same f_wfc / e_v / e_d / vm_fault stimulus at the die clock ratio (stream 1.2 GHz : serial 0.9 GHz, 834 / 1112 ps):
//   * every stream edge: return s_v / s_d (u_ret outputs) and the request side w_* / a_* equal, cycle exact;
//   * every serial edge: t_wfc[1027:0] (x43 data + g_q) equal, cycle exact;
//   * sticky faults (fault, t_wfc[1028] = e_q): the split adds the diag's capture edges on the return fault only, so the
//     new rise must follow the reference rise within FAULT_SLACK edges and never precede it; no rise without a reference rise.
// RESPONSE_PAD by +define+RPAD=<n> with the parent's coupled RLAT 13 + READ_PIPE (die legacy parent READ_PIPE 0 -> RPAD 0;
// READ_PIPE 2 = the A2F hop-1 phase -> RPAD 2).  Mutants (must FAIL):
// +define+S81_RETURN256_MUT_HIGH (hi slice reads the lo half), +define+S81_RETURN256_MUT_TAIL (slice tail one edge short).
`ifndef RPAD
`define RPAD 0
`endif
module tb_die_wfc_return256_eq;
    localparam integer RP = `RPAD, EPOCHS = 12, EPOCH_T = 400, FAULT_SLACK_T = 6, FAULT_SLACK_S = 6;
    reg s_ck = 1, t_ck = 1, rst = 0, rss = 0;
    always #556 s_ck = ~s_ck;
    always #417 t_ck = ~t_ck;
    reg [559:0] f_wfc = 0; reg [3:0] e_v = 0; reg [2047:0] e_d = 0; reg vm_fault = 0;
    wire [1028:0] tw_a, tw_b; wire wv_a, wv_b, f_a, f_b; wire [13:0] wr_a, wr_b; wire [511:0] wd_a, wd_b;
    wire [3:0] av_a, av_b; wire [55:0] ar_a, ar_b;
`define WFC_PORTS(TW, WV, WR, WD, AV, AR, F) \
        .ck_control_s(s_ck), .ck_control_t(t_ck), .ck_fault_s(s_ck), .ck_fault_t(t_ck), .rst_fault_s(rst), .rss_fault_t(rss), \
        .ck_fault_x34_s(s_ck), .ck_fault_x34_t(t_ck), .ck_fault_x43_t(t_ck), .ck_fault_x43_s(s_ck), \
        .rst_fault_x34_s(rst), .rss_fault_x34_t(rss), .rss_fault_x43_t(rss), .rst_fault_x43_s(rst), \
        .ck_x34_s(s_ck), .ck_x34_t(t_ck), .ck_x43_s(s_ck), .ck_x43_t(t_ck), .rst_control_s(rst), .rss_control_t(rss), \
        .rst_x34_s(rst), .rss_x34_t(rss), .rst_x43_s(rst), .rss_x43_t(rss), .f_wfc(f_wfc), .t_wfc(TW), \
        .w_v(WV), .w_row(WR), .w_d(WD), .a_v(AV), .a_row(AR), .e_v(e_v), .e_d(e_d), .vm_fault(vm_fault), .fault(F)
    dsfd_vm_static_wfc #(.RLAT(13 + RP), .RESPONSE_PAD(RP)) ref_wfc (
        .ck_return_t(t_ck), .rss_return_t(rss), `WFC_PORTS(tw_a, wv_a, wr_a, wd_a, av_a, ar_a, f_a));
    dsfd_vm_static_wfc_select256 #(.RLAT(13 + RP), .RESPONSE_PAD(RP), .RETURN256(1)) new_wfc (
        .ck_return_t({3{t_ck}}), .rss_return_t({3{rss}}), `WFC_PORTS(tw_b, wv_b, wr_b, wd_b, av_b, ar_b, f_b));
    integer ep, n, j, seed, checks_t = 0, checks_s = 0, ret_both = 0, ret_any = 0, fault_epochs = 0;
    integer rise_fa, rise_fb, rise_ea, rise_eb, tcount = 0, scount = 0;
    reg [1:0] rv_seen; reg [3:0] ev_ok; reg [559:0] fw; integer n_xv = 0, n_rv = 0, ep_t0 = 0;
    // epoch modes: 0 random (request range / lane faults, malformed e_v, vm_fault); 1 clean requests + ONE malformed
    // e_v (the return fault alone: the split's diag path is what raises it); 2 clean, nothing malformed (no fault)
    integer seed0 = 0, mode = 0, inject_at = -1, ep_t = 0, ret_fault_epochs = 0, clean_epochs = 0;
    // consistent aux return valids from the (shared) request decode most of the time; malformed ones on purpose
    always @(negedge t_ck) begin
        rv_seen = ref_wfc.return_valid;
        ep_t = ep_t + 1;
        ev_ok = (ref_wfc.return_valid[0] ? (4'd1 << ref_wfc.return_lane[1:0]) : 4'd0) |
                (ref_wfc.return_valid[1] ? (4'd1 << ref_wfc.return_lane[3:2]) : 4'd0);
        e_v <= ((mode == 0 && $urandom() % 23 == 0) || (mode == 1 && ep_t == inject_at)) ?
               ev_ok ^ (4'($urandom()) | 4'd1) : ev_ok;      // malformed: differs from the decoded lanes
        for (j = 0; j < 64; j = j + 1) e_d[j*32 +: 32] <= $urandom();
        vm_fault <= mode == 0 && ($urandom() % 997 == 0);
    end
    always @(negedge s_ck) begin
        for (j = 0; j < 17; j = j + 1) fw[j*32 +: 32] = $urandom();
        fw[559:544] = 16'($urandom());
        if (mode != 0) begin
            fw[527] = 1'b0; fw[543] = 1'b0; fw[558] = 1'b0;      // write / read rows in range
            fw[545:544] = fw[530:529] + 2'd1;                    // row1 on another FSR lane than row0
        end
        f_wfc <= fw;
    end
    always @(posedge t_ck) begin
        #2;
        tcount = tcount + 1;
        if (rss) begin
            if (ref_wfc.sv !== new_wfc.sv || ref_wfc.sd !== new_wfc.sd)
                $fatal(1, "RETURN MISMATCH t%0d ref v%0b new v%0b", tcount, ref_wfc.sv, new_wfc.sv);
            if ({wv_a, wr_a, wd_a, av_a, ar_a} !== {wv_b, wr_b, wd_b, av_b, ar_b})
                $fatal(1, "REQUEST SIDE MISMATCH t%0d", tcount);
            if (ref_wfc.xv) n_xv = n_xv + 1;
            if (|ref_wfc.return_valid) n_rv = n_rv + 1;
            if (ref_wfc.sv) begin ret_any = ret_any + 1; if (ref_wfc.sd[1025] && ref_wfc.sd[512]) ret_both = ret_both + 1; end
            if (f_a && rise_fa < 0) rise_fa = tcount;
            if (f_b && rise_fb < 0) rise_fb = tcount;
            checks_t = checks_t + 1;
        end
    end
    always @(posedge s_ck) begin
        #2;
        scount = scount + 1;
        if (rst) begin
            if (tw_a[1027:0] !== tw_b[1027:0]) $fatal(1, "T_WFC DATA MISMATCH s%0d", scount);
            if (tw_a[1028] && rise_ea < 0) rise_ea = scount;
            if (tw_b[1028] && rise_eb < 0) rise_eb = scount;
            checks_s = checks_s + 1;
        end
    end
    task check_fault(input integer ra, input integer rb, input integer slack, input [8*8-1:0] nm);
        if (ra < 0 && rb >= 0) $fatal(1, "%0s: new fault without reference fault (epoch %0d)", nm, ep);
        if (ra >= 0 && (rb < ra || rb > ra + slack)) $fatal(1, "%0s: fault rise ref %0d new %0d (slack %0d, epoch %0d)", nm, ra, rb, slack, ep);
    endtask
    initial begin
        seed = 1;
        if ($value$plusargs("seed=%d", seed)) begin end
        seed0 = seed; void'($urandom(seed));      // seed the process RNG once
        for (ep = 0; ep < EPOCHS; ep = ep + 1) begin
            rise_fa = -1; rise_fb = -1; rise_ea = -1; rise_eb = -1;
            mode = ep % 3; ep_t = 0; ep_t0 = tcount; inject_at = 120 + ($urandom() & 127);
            rss = 0; rst = 0;
            // release both resets together 100 ps before a common 3336 ps epoch edge (the fixed 4:3 phase the
            // x34 / x43 transports are built for; tb_dsfd_sp_vm_a2f.sv convention)
            #((($time / 3336) + 4) * 3336 - 100 - $time); rst = 1; rss = 1;
            repeat (EPOCH_T) @(posedge t_ck);
            #3;
            check_fault(rise_fa, rise_fb, FAULT_SLACK_T, "fault");
            check_fault(rise_ea, rise_eb, FAULT_SLACK_S, "e_q");
            if (rise_fa >= 0) fault_epochs = fault_epochs + 1;
            if (mode == 1 && rise_fa >= 0) ret_fault_epochs = ret_fault_epochs + 1;
            if (mode == 2 && rise_fa < 0 && rise_ea < 0) clean_epochs = clean_epochs + 1;
            if (mode == 1 && rise_fa >= 0 && rise_fa - ep_t0 < inject_at)
                $fatal(1, "COVERAGE: return-fault epoch %0d faulted before the injection (t%0d < %0d)", ep, rise_fa - ep_t0, inject_at);
        end
        if (ret_fault_epochs != EPOCHS / 3 || clean_epochs != EPOCHS / 3)
            $fatal(1, "COVERAGE: return-fault-only epochs %0d, clean epochs %0d of %0d each", ret_fault_epochs, clean_epochs, EPOCHS / 3);
        if (ret_any == 0 || ret_both == 0) $fatal(1, "NO COVERAGE: returns %0d (both lanes %0d) xv %0d return_valid %0d", ret_any, ret_both, n_xv, n_rv);
        $display("DIE_WFC_RETURN256_EQ PASS rpad=%0d seed=%0d stream_checks=%0d serial_checks=%0d returns=%0d both=%0d fault_epochs=%0d/%0d return_fault_only=%0d clean=%0d",
                 RP, seed0, checks_t, checks_s, ret_any, ret_both, fault_epochs, EPOCHS, ret_fault_epochs, clean_epochs);
        $finish;
    end
endmodule
`default_nettype wire
