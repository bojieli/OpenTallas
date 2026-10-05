`timescale 1ps/1fs
// ---------------------------------------------------------------------------
// ot_hbm_pc_dram_check -- SIMULATION ONLY.  An independent per-pseudo-channel HBM3/HBM3E DRAM
// command checker for the cycle-based streaming sequencers (ot_hbm_r14_stream_pc and its
// descendants ot_hbm_accel_{stream_pc, stream_pc_wb, expert_stream_pc, expert_stream_pc_la}),
// attached by the `bind` statements at the end of this file (bind to a module absent from a
// build is ignored), so every bench that adds this file to its source list checks every
// command of every PC without any change to the sequencers or the benches.
//
// Time = (controller clock edges since time 0) x CLK_PS (1,024 ps: every family-B sequencer runs at
// HBM CK/2), so the checker also works under C++ harnesses that do not advance simulation time
// (the REAL_MEM benches' gated hclk); a command is sampled at the edge that registers it.
// Timing (ps): the ot_hdc_hbm_model.sv defaults used by rtl/test/model_ready_hbm_r14/
// tb_hbm_stream_bw.sv and ot_qwen_hbm_stream_ack.sv (tRFCpb 200 ns JESD238 16 Gb; tRREFD 8 ns).
// Rules:
//   ACT   bank closed; tRP; tRC; tRRD_S; tRRD_L; tFAW (ACT-only window: REFpb is not counted,
//         Ramulator 2 HBM3); not during the bank's tRFCpb / the PC's tRFC; tRREFD after the PC's
//         last REFpb.
//   PRE   bank open; tRAS; tRTP; tWR.   PREab: the same for every open bank.
//   REFab every bank closed; tRP; tRC; not during refresh.
//   REFpb bank closed; tRP; tRC; NOT while the bank is still in its previous REFpb's tRFCpb;
//         tRRD_S after the PC's last ACT and tRRD_L after its bank group's last ACT (Ramulator 2
//         HBM3: ACT -> REFsb nRRDS+1 / nRRDL+1); tRREFD after its last REFpb (other bank); every
//         bank once per 32-REFpb round.  (The benches' inline checkers hold ACT -> REFpb to the
//         stricter 8 ns tRREFD.)
//   RD/WR bank open; tRCD (RD/WR); tCCD_S; tCCD_L; tWTR_S/L (RD after WR); tRTW (WR after RD);
//         not during the bank's refresh.
//   Liveness: refresh never more than 2 intervals behind the tREFIpb (tREFI for REFab) schedule
//         counted from reset; the largest gap between consecutive refreshes is reported.
// final: one line per active instance
//   DRAMCHK_PC <path> viol=.. act=.. pre=.. ref=.. rd=.. wr=.. ref_gap_max_ps=..
// plus the first VMAX violation texts of each instance (DRAMCHK_VIOLATION ...).
// ---------------------------------------------------------------------------
module ot_hbm_pc_dram_check #(
    parameter longint BURST = 1024, TCCDL = 2560, CWL = 6250, RCD = 19375, RCDW = 9375,
    parameter longint RP = 16250, RAS = 28125, RTP = 5625, WR = 20625, WTRS = 4375, WTRL = 6250,
    parameter longint RTW = 9948, RRDS = 2500, RRDL = 3125, FAW = 15000, RFC = 350000,
    parameter longint RFCPB = 200000, REFI = 3900000, RREFD = 8000,
    parameter longint CLK_PS = 1024,
    parameter integer REF_MODE = 1,          // the sequencer's REF_MODE (0 REFab, 1 REFpb): liveness interval
    parameter integer VMAX = 4
) (
    input wire       clk,
    input wire       rst_n,
    input wire       row_fire,
    input wire [2:0] row_op,
    input wire [4:0] row_bank,
    input wire       col_fire,
    input wire [4:0] col_bank,
    input wire       col_we
);
    localparam longint NEG = -64'sd1000000000;
    bit     b_open [0:31];
    longint b_act [0:31], b_pre [0:31], b_rd [0:31], b_wr [0:31], b_ref_end [0:31];
    longint last_act, last_ref_any, last_col, last_rd, last_wr, ref_end_all, t_rst, last_ref;
    longint act_bg [0:3], col_bg [0:3], fw [0:3];
    integer last_wr_bg;
    bit [31:0] round;
    longint n_viol, n_act, n_pre, n_ref, n_rd, n_wr, ref_gap_max;
    bit     refab_mode, started;
    longint ncyc = 0;
    longint live_forgiven;

    task automatic v(input string what, input integer bk, input longint t);
        if (n_viol < VMAX) $display("DRAMCHK_VIOLATION %m t=%0d ps bank=%0d %s", t, bk, what);
        n_viol = n_viol + 1;
    endtask

    task automatic reset_state();
        for (int b = 0; b < 32; b++) begin
            b_open[b] = 0; b_act[b] = NEG; b_pre[b] = NEG; b_rd[b] = NEG; b_wr[b] = NEG; b_ref_end[b] = NEG;
        end
        for (int g = 0; g < 4; g++) begin act_bg[g] = NEG; col_bg[g] = NEG; fw[g] = NEG; end
        last_act = NEG; last_ref_any = NEG; last_col = NEG; last_rd = NEG; last_wr = NEG; ref_end_all = NEG;
        last_wr_bg = -1; round = 0; last_ref = -1;
    endtask

    initial begin
        reset_state();
        n_viol = 0; n_act = 0; n_pre = 0; n_ref = 0; n_rd = 0; n_wr = 0; ref_gap_max = 0;
        refab_mode = 0; started = 0; t_rst = 0; live_forgiven = 0;
    end

    always @(posedge clk) begin
        automatic longint now = ncyc * CLK_PS;
        ncyc = ncyc + 1;
        if (!rst_n) begin
            reset_state(); started = 0;
        end else begin
            if (!started) begin started = 1; t_rst = now; end
            if (row_fire) begin
                automatic int bk = row_bank, g = row_bank & 3;
                case (row_op)
                    3'd1: begin // ACT
                        n_act++;
                        if (b_open[bk]) v("ACT to an open bank", bk, now);
                        if (now < b_pre[bk] + RP) v("tRP", bk, now);
                        if (now < b_act[bk] + RAS + RP) v("tRC", bk, now);
                        if (now < last_act + RRDS) v("tRRD_S", bk, now);
                        if (now < act_bg[g] + RRDL) v("tRRD_L", bk, now);
                        if (now < fw[0] + FAW) v("tFAW", bk, now);
                        if (now < b_ref_end[bk] || now < ref_end_all) v("ACT during refresh", bk, now);
                        if (now < last_ref_any + RREFD) v("tRREFD (REFpb -> ACT)", bk, now);
                        b_open[bk] = 1; b_act[bk] = now; last_act = now; act_bg[g] = now;
                        fw[0] = fw[1]; fw[1] = fw[2]; fw[2] = fw[3]; fw[3] = now;
                    end
                    3'd0: begin // PRE
                        n_pre++;
                        if (!b_open[bk]) v("PRE to a closed bank", bk, now);
                        if (now < b_act[bk] + RAS) v("tRAS", bk, now);
                        if (now < b_rd[bk] + RTP) v("tRTP", bk, now);
                        if (now < b_wr[bk] + CWL + BURST + WR) v("tWR", bk, now);
                        b_open[bk] = 0; b_pre[bk] = now;
                    end
                    3'd5: begin // PREab
                        n_pre++;
                        for (int b = 0; b < 32; b++) if (b_open[b]) begin
                            if (now < b_act[b] + RAS) v("tRAS (PREab)", b, now);
                            if (now < b_rd[b] + RTP) v("tRTP (PREab)", b, now);
                            if (now < b_wr[b] + CWL + BURST + WR) v("tWR (PREab)", b, now);
                            b_open[b] = 0; b_pre[b] = now;
                        end
                    end
                    3'd4: begin // REFab
                        n_ref++; refab_mode = 1;
                        for (int b = 0; b < 32; b++) begin
                            if (b_open[b]) v("REFab with an open bank", b, now);
                            if (now < b_pre[b] + RP) v("tRP (REFab)", b, now);
                            if (now < b_act[b] + RAS + RP) v("tRC (REFab)", b, now);
                            if (now < b_ref_end[b]) v("REFab during refresh", b, now);
                        end
                        if (now < ref_end_all) v("REFab during refresh", 0, now);
                        if (last_ref >= 0 && now - last_ref > ref_gap_max) ref_gap_max = now - last_ref;
                        last_ref = now; ref_end_all = now + RFC;
                    end
                    3'd6: begin // REFpb
                        n_ref++;
                        if (b_open[bk]) v("REFpb to an open bank", bk, now);
                        if (now < b_pre[bk] + RP) v("tRP (REFpb)", bk, now);
                        if (now < b_act[bk] + RAS + RP) v("tRC (REFpb)", bk, now);
                        if (now < b_ref_end[bk]) v("REFpb during the bank's refresh (tRFCpb)", bk, now);
                        if (now < ref_end_all) v("REFpb during REFab", bk, now);
                        if (now < last_act + RRDS) v("tRRD_S (ACT -> REFpb)", bk, now);
                        if (now < act_bg[g] + RRDL) v("tRRD_L (ACT -> REFpb, same bank group)", bk, now);
                        if (now < last_ref_any + RREFD) v("tRREFD (REFpb -> REFpb)", bk, now);
                        if (round[bk]) v("REFpb bank twice in one round", bk, now);
                        round[bk] = 1'b1; if (&round) round = 0;
                        if (last_ref >= 0 && now - last_ref > ref_gap_max) ref_gap_max = now - last_ref;
                        last_ref = now; last_ref_any = now; b_ref_end[bk] = now + RFCPB;
                    end
                    default: v("row op not modelled by this checker", bk, now);
                endcase
            end
            if (col_fire) begin
                automatic int bk = col_bank, g = col_bank & 3;
                if (!b_open[bk]) v(col_we ? "WR to a closed bank" : "RD to a closed bank", bk, now);
                if (now < b_act[bk] + (col_we ? RCDW : RCD)) v("tRCD", bk, now);
                if (now < last_col + BURST) v("tCCD_S", bk, now);
                if (now < col_bg[g] + TCCDL) v("tCCD_L", bk, now);
                if (now < b_ref_end[bk] || now < ref_end_all) v("column command during refresh", bk, now);
                if (!col_we) begin
                    n_rd++;
                    if (now < last_wr + CWL + BURST + ((last_wr_bg == g) ? WTRL : WTRS)) v("tWTR", bk, now);
                    last_rd = now; b_rd[bk] = now;
                end else begin
                    n_wr++;
                    if (now < last_rd + RTW) v("tRTW", bk, now);
                    last_wr = now; last_wr_bg = g; b_wr[bk] = now;
                end
                last_col = now; col_bg[g] = now;
            end
            // liveness: refreshes issued keep up with the schedule from reset (2 intervals slack)
            if (n_act + n_rd + n_ref > 0) begin
                automatic longint per = (refab_mode || REF_MODE == 0) ? REFI : REFI / 32;
                if ((now - t_rst) / per > n_ref + 2 + live_forgiven) begin
                    v("refresh behind schedule", 0, now);
                    live_forgiven = (now - t_rst) / per - n_ref - 2;   // report once per new deficit
                end
            end
        end
    end

    final if (n_act + n_rd + n_wr + n_ref > 0)
        $display("DRAMCHK_PC %m viol=%0d act=%0d pre=%0d ref=%0d rd=%0d wr=%0d ref_gap_max_ps=%0d",
                 n_viol, n_act, n_pre, n_ref, n_rd, n_wr, ref_gap_max);
endmodule

// Attach to every streaming sequencer (ignored for modules not in the build).
bind ot_hbm_r14_stream_pc ot_hbm_pc_dram_check #(.REF_MODE(REF_MODE)) u_dramchk (
    .clk(clk), .rst_n(rst_n), .row_fire(row_v && row_gnt), .row_op(row_op), .row_bank(row_bank),
    .col_fire(col_v), .col_bank(col_bank), .col_we(col_we));
bind ot_hbm_accel_stream_pc ot_hbm_pc_dram_check #(.REF_MODE(REF_MODE)) u_dramchk (
    .clk(clk), .rst_n(rst_n), .row_fire(row_v && row_gnt), .row_op(row_op), .row_bank(row_bank),
    .col_fire(col_v && col_gnt), .col_bank(col_bank), .col_we(1'b0));
bind ot_hbm_accel_stream_pc_wb ot_hbm_pc_dram_check #(.REF_MODE(REF_MODE)) u_dramchk (
    .clk(clk), .rst_n(rst_n), .row_fire(row_v && row_gnt), .row_op(row_op), .row_bank(row_bank),
    .col_fire(col_v), .col_bank(col_bank), .col_we(col_we));
bind ot_hbm_accel_expert_stream_pc ot_hbm_pc_dram_check #(.REF_MODE(REF_MODE)) u_dramchk (
    .clk(clk), .rst_n(rst_n), .row_fire(row_v && row_gnt), .row_op(row_op), .row_bank(row_bank),
    .col_fire(col_v), .col_bank(col_bank), .col_we(1'b0));
bind ot_hbm_accel_expert_stream_pc_la ot_hbm_pc_dram_check #(.REF_MODE(REF_MODE)) u_dramchk (
    .clk(clk), .rst_n(rst_n), .row_fire(row_v && row_gnt), .row_op(row_op), .row_bank(row_bank),
    .col_fire(col_v), .col_bank(col_bank), .col_we(1'b0));
