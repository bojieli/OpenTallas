`timescale 1ps/1ps
// Bench model of ONE HBM3E pseudo-channel behind qfd_ctrl_emb_<pc> (emb-hbm 2026-10-08): an independent JEDEC timing
// checker in picoseconds (the ot_qwen_hbm_stream4_tagged checker's rules and HBM3E values, NOT the scheduler's cycle
// constants), per-bank open row, a sparse backing store (CAM list: Icarus has no associative arrays) of 288-b sectors
// (256 data + 32 ECC side-band) keyed {bank, row, column}, and the read return pipe (CL + BL + RSP, in issue order).
// Static WRs store the pcport's head data; KV writes are not exercised here.  flip(): fault injection on a stored word.
module tb_emb_dram_pc #(
    parameter integer NMEM = 1024,
    parameter integer CYC = 1024            // ps a controller cycle (CK/2, 976.5625 MHz)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         row_v,
    input  wire [2:0]   row_op,
    input  wire [4:0]   row_bank,
    input  wire [18:0]  row_row,
    input  wire         col_v,
    input  wire         col_we,
    input  wire         col_sr,
    input  wire [4:0]   col_bank,
    input  wire [4:0]   col_col,
    input  wire [287:0] wd,
    output reg          r_v,
    output reg  [287:0] r_d
);
    localparam longint BURST=1024, TCCDL=2560, CL=12500, CWL=6250, RCD=19375, RCDW=9375, RP=16250, RAS=28125,
                       RTP=5625, WR=20625, WTRS=4375, WTRL=6250, RTW=9948, RRDS=2500, RRDL=3125, FAW=15000,
                       RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;
    reg [28:0]  mk [0:NMEM-1];
    reg [287:0] md [0:NMEM-1];
    integer nm = 0;
    integer viol = 0, n_act = 0, n_rd = 0, n_wr = 0, n_ref = 0, n_srd = 0, n_swr = 0;
    longint now, cyc;
    bit     b_open [0:31]; int b_row [0:31];
    longint b_act [0:31], b_pre [0:31], b_rd [0:31], b_wr [0:31], b_ref_end [0:31];
    longint p_last_act, p_last_rd, p_last_wr, p_last_col, p_last_ref, p_last_refpb_any;
    int p_wr_bg;
    longint p_act_bg [0:3], p_col_bg [0:3], p_faw [0:3];
    bit [31:0] p_round;
    // return pipe
    longint rq_due [0:63]; reg [287:0] rq_d [0:63]; integer rq_w = 0, rq_r = 0;
    function automatic integer find(input [28:0] k);
        integer i;
        begin find = -1; for (i = 0; i < nm; i = i + 1) if (mk[i] == k) find = i; end
    endfunction
    task automatic store(input [28:0] k, input [287:0] d);
        integer i;
        begin
            i = find(k);
            if (i < 0) begin
                if (nm >= NMEM) begin $display("DRAM_MODEL FULL"); viol = viol + 1; end
                else begin mk[nm] = k; md[nm] = d; nm = nm + 1; end
            end else md[i] = d;
        end
    endtask
    task automatic flip(input [4:0] bk, input [18:0] rw, input [4:0] cl, input integer bit_a, input integer bit_b);
        integer i;
        begin
            i = find({bk, rw, cl});
            if (i < 0) $display("DRAM_MODEL flip: no such word");
            else begin
                md[i][bit_a] = ~md[i][bit_a];
                if (bit_b >= 0) md[i][bit_b] = ~md[i][bit_b];
            end
        end
    endtask
    task automatic v(input string what, input integer bk);
        if (viol < 10) $display("DRAM_TIMING VIOLATION %m t=%0d ps bank=%0d %s", now, bk, what);
        viol = viol + 1;
    endtask
    integer b, g, bk, gg, ix;
    reg [28:0] key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cyc = 0; r_v <= 1'b0;
            p_last_act = -1000000; p_last_rd = -1000000; p_last_wr = -1000000; p_last_col = -1000000;
            p_last_refpb_any = -1000000; p_last_ref = 0; p_round = 0; p_wr_bg = 0;
            for (g = 0; g < 4; g = g + 1) begin p_act_bg[g] = -1000000; p_col_bg[g] = -1000000; p_faw[g] = -1000000; end
            for (b = 0; b < 32; b = b + 1) begin
                b_open[b] = 0; b_act[b] = -1000000; b_pre[b] = -1000000; b_rd[b] = -1000000; b_wr[b] = -1000000;
                b_ref_end[b] = 0; b_row[b] = 0;
            end
        end else begin
            now = cyc * CYC;
            if (row_v) begin
                bk = row_bank; gg = row_bank & 3;
                case (row_op)
                    3'd1: begin
                        n_act++;
                        if (b_open[bk]) v("ACT to open bank", bk);
                        if (now < b_pre[bk] + RP) v("tRP", bk);
                        if (now < b_act[bk] + RAS + RP) v("tRC", bk);
                        if (now < p_last_act + RRDS) v("tRRD_S", bk);
                        if (now < p_act_bg[gg] + RRDL) v("tRRD_L", bk);
                        if (now < p_faw[0] + FAW) v("tFAW", bk);
                        if (now < b_ref_end[bk]) v("ACT during refresh", bk);
                        if (now < p_last_refpb_any + RREFD) v("tRREFD", bk);
                        b_open[bk] = 1; b_row[bk] = row_row; b_act[bk] = now;
                        p_last_act = now; p_act_bg[gg] = now;
                        p_faw[0] = p_faw[1]; p_faw[1] = p_faw[2]; p_faw[2] = p_faw[3]; p_faw[3] = now;
                    end
                    3'd0: begin
                        if (!b_open[bk]) v("PRE closed bank", bk);
                        if (now < b_act[bk] + RAS) v("tRAS", bk);
                        if (now < b_rd[bk] + RTP) v("tRTP", bk);
                        if (now < b_wr[bk] + CWL + BURST + WR) v("tWR", bk);
                        b_open[bk] = 0; b_pre[bk] = now;
                    end
                    3'd6: begin
                        n_ref++;
                        if (b_open[bk]) v("REFpb to open bank", bk);
                        if (now < b_pre[bk] + RP) v("tRP (REFpb)", bk);
                        if (now < b_act[bk] + RAS + RP) v("tRC (REFpb)", bk);
                        if (now < b_ref_end[bk]) v("REFpb during refresh", bk);
                        if (now < p_last_act + RREFD) v("tRREFD (REFpb after ACT)", bk);
                        if (now < p_last_refpb_any + RREFD) v("tRREFD (REFpb after REFpb)", bk);
                        if (p_round[bk]) v("REFpb bank twice in one round", bk);
                        p_round[bk] = 1; if (&p_round) p_round = 0;
                        if (p_last_ref != 0 && now - p_last_ref > REFI / 32) v("REFpb late", bk);
                        p_last_ref = now; p_last_refpb_any = now;
                        b_ref_end[bk] = now + RFCPB;
                    end
                    default: v("row op not used by this controller", bk);
                endcase
            end
            if (p_last_ref != 0 && now - p_last_ref > REFI / 32 + CYC) begin v("refresh overdue", 0); p_last_ref = now; end
            if (col_v) begin
                bk = col_bank; gg = col_bank & 3;
                key = {col_bank, 19'(b_row[col_bank]), col_col};
                if (!b_open[bk]) v(col_we ? "WR closed bank" : "RD closed bank", bk);
                if (now < b_act[bk] + (col_we ? RCDW : RCD)) v("tRCD", bk);
                if (now < p_last_col + BURST) v("tCCD_S", bk);
                if (now < p_col_bg[gg] + TCCDL) v("tCCD_L", bk);
                if (now < b_ref_end[bk]) v("column command during refresh", bk);
                p_last_col = now; p_col_bg[gg] = now;
                if (!col_we) begin
                    if (now < p_last_wr + CWL + BURST + ((p_wr_bg == gg) ? WTRL : WTRS)) v("tWTR", bk);
                    n_rd++; if (col_sr) n_srd++;
                    p_last_rd = now; b_rd[bk] = now;
                    ix = find(key);
                    rq_due[rq_w % 64] = (now + CL + BURST + RSP + CYC - 1) / CYC;
                    rq_d[rq_w % 64] = (ix < 0) ? 288'd0 : md[ix];
                    rq_w = rq_w + 1;
                end else begin
                    if (now < p_last_rd + RTW) v("tRTW", bk);
                    n_wr++;
                    p_last_wr = now; p_wr_bg = gg; b_wr[bk] = now;
                    if (col_sr) begin n_swr++; store(key, wd); end
                end
            end
            r_v <= 1'b0;
            if (rq_r != rq_w && rq_due[rq_r % 64] <= cyc + 1) begin
                r_v <= 1'b1; r_d <= rq_d[rq_r % 64]; rq_r = rq_r + 1;
            end
            cyc = cyc + 1;
        end
    end
endmodule
