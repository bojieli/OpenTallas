`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Behavioural, timing-faithful HBM model (simulation only) for the KV cache.
//
// NPC pseudo-channels of an HBM3/HBM3E stack.  Each is a 32-bit DDR channel
// moving one 32-byte burst (BL8) per sector; time is kept in picoseconds
// against the core clock (CLK_PS).  Per pseudo-channel it models
//   * 2 SIDs x 4 bank groups x 4 banks = 32 banks, 1 KB rows, open-page;
//   * ACT/PRE/RD/WR timing: tRCD (rd/wr), tRP, tRAS, tRC = tRAS + tRP, tRTP,
//     tWR, CL, CWL, tCCD_S (= burst), tCCD_L (same bank group), tRRD_S/L,
//     tFAW, write-to-read (tWTR) and read-to-write (tRTW) turnarounds;
//   * all-bank refresh (REFab) every tREFI, blocking the pseudo-channel for
//     tRFC (staggered across pseudo-channels by tREFI / NPC);
//   * a controller/PHY latency on the request path and on the response path;
//   * a reordering scheduler per pseudo-channel over the RW oldest queued
//     bursts: the burst whose column command can issue earliest goes next
//     (row hits, and bursts to other bank groups whose rows can open in
//     parallel), ties to the oldest; a burst never passes an older one to the
//     same sector when either is a write (so a read after a write sees the new
//     data), and the oldest is bypassed at most MAXSKIP times; ACT look-ahead:
//     a queued burst's row may open as soon as it arrives.
// All outputs are registered (sampled by the testbench/streamer at the edge).
// Address map (32-byte sector s, low to high): bank group [1:0], pseudo-
// channel, column (32 sectors = 1 KB row), bank-in-group and SID [2:0], row,
// with permutation (XOR) interleaving as memory controllers do: the bank
// group and bank take the low row bits, and the pseudo-channel folds the
// sector bits above it, so power-of-two strides (KV heads, rows of a head)
// spread over banks and pseudo-channels instead of aliasing onto one.
// A sequential stream rotates bank groups every sector (tCCD_S spacing) and
// pseudo-channels every 128 bytes.
//
// Request port (valid/ready): a read of req_len consecutive sectors, or a
// one-sector write; ready falls when a target pseudo-channel's queue lacks
// room (backpressure).  Beats of one read return per pseudo-channel, in order
// within it, on NPC response ports (valid/ready); a pseudo-channel stops
// issuing reads when its return queue is full.
//
// Parameters: bandwidth from configs/hardware/technology.json
// (hbm.hbm3e.stack_bandwidth_bytes_s = 1.0 TB/s over 32 pseudo-channels of
// 32 bits: 7.8125 Gb/s per pin, tCK 512 ps, a burst 1,024 ps).  Core DRAM
// timings (ns) from the HBM3 6400 Mb/s preset of Ramulator 2
// (CMU-SAFARI/ramulator2 python/ramulator/dram/hbm3.py, commit 72427a1, some
// marked there as estimates) and JESD238 refresh (tRFC 350 ns for 16 Gb dies
// 8-high, tREFI 3.9 us); controller latencies are assumed.  The values are
// restated in results/rtl/hdc_kv_stream_campaign.json.
// ---------------------------------------------------------------------------
module ot_hdc_hbm_model #(
    parameter integer NPC      = 2,
    parameter integer AW       = 24,          // sector address bits
    parameter integer DW       = 256,         // sector (burst) bits
    parameter integer MEM_WORDS = 4096,
    parameter integer TAGW     = 16,
    parameter integer LENW     = 5,
    parameter integer BEATW    = 4,
    parameter integer QD       = 64,          // queued beats per pseudo-channel
    parameter integer RQD      = 32,          // return queue per pseudo-channel
    parameter integer RW       = 16,          // reorder window (oldest queued bursts)
    parameter integer MAXSKIP  = 16,          // times the oldest burst may be bypassed
    parameter integer CLK_PS   = 1000,
    parameter integer BURST_PS = 1024,        // tCCD_S = nBL = 2 tCK at tCK 512 ps
    parameter integer TCCDL_PS = 2560,        // max(4 tCK, 2.5 ns) = 5 tCK
    parameter integer CL_PS    = 12500,
    parameter integer CWL_PS   = 6250,
    parameter integer RCDRD_PS = 19375,
    parameter integer RCDWR_PS = 9375,
    parameter integer RP_PS    = 16250,
    parameter integer RAS_PS   = 28125,
    parameter integer WR_PS    = 20625,
    parameter integer RTP_PS   = 5625,
    parameter integer RRDS_PS  = 2500,
    parameter integer RRDL_PS  = 3125,
    parameter integer FAW_PS   = 15000,
    parameter integer WTRS_PS  = 4375,
    parameter integer WTRL_PS  = 6250,
    parameter integer RTW_PS   = 9948,
    parameter integer RFC_PS   = 350000,
    parameter integer REFI_PS  = 3900000,
    parameter integer REQ_PS   = 10000,       // controller + PHY, request path (assumed)
    parameter integer RSP_PS   = 10000        // PHY + controller, response path (assumed)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 req_v,
    output reg                  req_rdy,
    input  wire                 req_we,
    input  wire [AW-1:0]        req_addr,
    input  wire [LENW-1:0]      req_len,
    input  wire [TAGW-1:0]      req_tag,
    input  wire [DW-1:0]        req_wdata,
    output reg  [NPC-1:0]       rsp_v,
    input  wire [NPC-1:0]       rsp_rdy,
    output reg  [NPC*TAGW-1:0]  rsp_tag,
    output reg  [NPC*BEATW-1:0] rsp_beat,
    output reg  [NPC*DW-1:0]    rsp_data
);
    localparam integer LPC = (NPC > 1) ? $clog2(NPC) : 0;
    localparam integer NB = 32;
    localparam integer ROW_SHIFT = 2 + LPC + 5 + 3;

    // backing store (sector granularity); public for the testbench
    reg [DW-1:0] mem [0:MEM_WORDS-1];

    // per pseudo-channel beat queue
    reg              q_we   [0:NPC-1][0:QD-1];
    reg [AW-1:0]     q_addr [0:NPC-1][0:QD-1];
    reg [TAGW-1:0]   q_tag  [0:NPC-1][0:QD-1];
    reg [BEATW-1:0]  q_beat [0:NPC-1][0:QD-1];
    reg [DW-1:0]     q_data [0:NPC-1][0:QD-1];
    longint          q_arr  [0:NPC-1][0:QD-1];
    integer          q_rp [0:NPC-1], q_n [0:NPC-1];
    // return queue
    longint          r_t    [0:NPC-1][0:RQD-1];
    reg [TAGW-1:0]   r_tag  [0:NPC-1][0:RQD-1];
    reg [BEATW-1:0]  r_beat [0:NPC-1][0:RQD-1];
    reg [DW-1:0]     r_data [0:NPC-1][0:RQD-1];
    integer          r_rp [0:NPC-1], r_n [0:NPC-1];
    // bank / channel timing state
    reg              b_open [0:NPC-1][0:NB-1];
    longint          b_row  [0:NPC-1][0:NB-1];
    longint          b_act  [0:NPC-1][0:NB-1];     // last ACT
    longint          b_actok[0:NPC-1][0:NB-1];     // earliest next ACT (tRC, refresh)
    longint          b_preok[0:NPC-1][0:NB-1];     // earliest PRE (tRAS, tRTP, write recovery)
    longint          last_act [0:NPC-1];
    longint          last_act_bg [0:NPC-1][0:3];
    longint          faw [0:NPC-1][0:3];
    longint          last_col [0:NPC-1];
    longint          last_col_bg [0:NPC-1][0:3];
    longint          last_rd [0:NPC-1], last_wr [0:NPC-1];
    reg              last_wr_bg_valid [0:NPC-1];
    reg [1:0]        last_wr_bg [0:NPC-1];
    longint          next_ref [0:NPC-1];
    // head scheduling
    reg              h_sched [0:NPC-1];
    integer          h_skip [0:NPC-1];
    longint          h_tcol [0:NPC-1];
    // statistics (public)
    longint st_rd [0:NPC-1], st_wr [0:NPC-1], st_act [0:NPC-1], st_hit [0:NPC-1], st_conf [0:NPC-1];
    longint st_ref [0:NPC-1], st_bp_cycles, st_rd_lat_sum, st_rd_lat_max;
    longint cyc;

    function automatic integer pc_of(input [AW-1:0] s);
        pc_of = (NPC > 1) ? (((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1)) : 0;
    endfunction
    function automatic longint row_of(input [AW-1:0] s);
        row_of = s >> ROW_SHIFT;
    endfunction
    function automatic integer bank_of(input [AW-1:0] s);
        longint row;
        begin
            row = s >> ROW_SHIFT;
            bank_of = ((((s >> (2 + LPC + 5)) ^ (row >> 2)) & 7) << 2) | ((s ^ row) & 3);
        end
    endfunction
    function automatic longint max2(input longint a, input longint b);
        max2 = (a > b) ? a : b;
    endfunction

    integer pi;
    localparam integer LENMAX = 1 << (LENW - 1);

    // Earliest column-command time of a queued burst, without committing it.
    function automatic longint estimate(input integer p, input reg we, input [AW-1:0] s, input longint arr,
                                        input longint tnow);
        longint tmin, tact, tcol, row;
        integer bg, bk;
        begin
            tmin = max2(arr + REQ_PS, tnow);
            bk = bank_of(s); bg = bk & 3; row = row_of(s);
            if (b_open[p][bk] && b_row[p][bk] == row) tact = b_act[p][bk];
            else begin
                tact = b_open[p][bk] ? max2(arr + REQ_PS, b_preok[p][bk]) + RP_PS : arr + REQ_PS;
                tact = max2(tact, b_actok[p][bk]);
                tact = max2(tact, last_act[p] + RRDS_PS);
                tact = max2(tact, last_act_bg[p][bg] + RRDL_PS);
                tact = max2(tact, faw[p][0] + FAW_PS);
            end
            tcol = max2(tmin, tact + (we ? RCDWR_PS : RCDRD_PS));
            tcol = max2(tcol, last_col[p] + BURST_PS);
            tcol = max2(tcol, last_col_bg[p][bg] + TCCDL_PS);
            estimate = tcol;
        end
    endfunction

    // Schedule the head beat of pseudo-channel p: returns its column-command time.
    function automatic longint schedule(input integer p, input reg we, input [AW-1:0] s, input longint arr,
                                        input longint tnow);
        longint tmin, tact, tcol, tr;
        integer bg, bk, b2;
        longint row;
        reg any_open;
        begin
            tmin = arr + REQ_PS;
            row = row_of(s);
            bk = bank_of(s);
            bg = bk & 3;
            // refresh(es) due before this burst: precharge all, REFab, tRFC
            while (next_ref[p] <= max2(tmin, last_col[p])) begin
                tr = next_ref[p];
                any_open = 1'b0;
                for (b2 = 0; b2 < NB; b2 = b2 + 1)
                    if (b_open[p][b2]) begin any_open = 1'b1; tr = max2(tr, b_preok[p][b2]); end
                tr = max2(tr, last_col[p] + BURST_PS);
                if (any_open) tr = tr + RP_PS;
                for (b2 = 0; b2 < NB; b2 = b2 + 1) begin
                    b_open[p][b2] = 1'b0;
                    b_actok[p][b2] = max2(b_actok[p][b2], tr + RFC_PS);
                end
                next_ref[p] = next_ref[p] + REFI_PS;
                st_ref[p] = st_ref[p] + 1;
            end
            if (b_open[p][bk] && b_row[p][bk] == row) begin
                st_hit[p] = st_hit[p] + 1;
                tact = b_act[p][bk];
            end else begin
                if (b_open[p][bk]) begin
                    st_conf[p] = st_conf[p] + 1;
                    tact = max2(tmin, b_preok[p][bk]) + RP_PS;      // PRE, then ACT
                end else tact = tmin;
                tact = max2(tact, b_actok[p][bk]);
                tact = max2(tact, last_act[p] + RRDS_PS);
                tact = max2(tact, last_act_bg[p][bg] + RRDL_PS);
                tact = max2(tact, faw[p][0] + FAW_PS);
                faw[p][0] = faw[p][1]; faw[p][1] = faw[p][2]; faw[p][2] = faw[p][3]; faw[p][3] = tact;
                last_act[p] = tact; last_act_bg[p][bg] = tact;
                b_open[p][bk] = 1'b1; b_row[p][bk] = row; b_act[p][bk] = tact;
                b_actok[p][bk] = tact + RAS_PS + RP_PS;
                b_preok[p][bk] = tact + RAS_PS;
                st_act[p] = st_act[p] + 1;
            end
            // a column command is never earlier than the cycle its burst reaches the head
            tcol = max2(max2(tmin, tnow), tact + (we ? RCDWR_PS : RCDRD_PS));
            tcol = max2(tcol, last_col[p] + BURST_PS);
            tcol = max2(tcol, last_col_bg[p][bg] + TCCDL_PS);
            if (!we && last_wr[p] >= 0)
                tcol = max2(tcol, last_wr[p] + CWL_PS + BURST_PS +
                                  ((last_wr_bg_valid[p] && last_wr_bg[p] == bg) ? WTRL_PS : WTRS_PS));
            if (we && last_rd[p] >= 0) tcol = max2(tcol, last_rd[p] + RTW_PS);
            last_col[p] = tcol; last_col_bg[p][bg] = tcol;
            if (we) begin
                last_wr[p] = tcol; last_wr_bg_valid[p] = 1'b1; last_wr_bg[p] = bg[1:0];
                b_preok[p][bk] = max2(b_preok[p][bk], tcol + CWL_PS + BURST_PS + WR_PS);
            end else begin
                last_rd[p] = tcol;
                b_preok[p][bk] = max2(b_preok[p][bk], tcol + RTP_PS);
            end
            schedule = tcol;
        end
    endfunction

    integer p, i, j, k, e, o, sel, slot, iter;
    reg ok, t_we;
    longint best, est;
    reg [AW-1:0] t_addr; reg [TAGW-1:0] t_tag; reg [BEATW-1:0] t_beat; reg [DW-1:0] t_data; longint t_arr;
    longint now;
    always @(posedge clk) begin
        if (!rst_n) begin
            cyc <= 0; rsp_v <= 0; req_rdy <= 1'b0;
            for (p = 0; p < NPC; p = p + 1) begin
                q_rp[p] = 0; q_n[p] = 0; r_rp[p] = 0; r_n[p] = 0; h_sched[p] = 1'b0; h_skip[p] = 0;
                last_act[p] = -1000000; last_col[p] = -1000000; last_rd[p] = -1; last_wr[p] = -1;
                last_wr_bg_valid[p] = 1'b0;
                next_ref[p] = REFI_PS + (longint'(REFI_PS) * p) / NPC;
                for (k = 0; k < 4; k = k + 1) begin
                    faw[p][k] = -1000000; last_act_bg[p][k] = -1000000; last_col_bg[p][k] = -1000000;
                end
                for (k = 0; k < NB; k = k + 1) begin
                    b_open[p][k] = 1'b0; b_actok[p][k] = 0; b_preok[p][k] = 0; b_act[p][k] = 0; b_row[p][k] = 0;
                end
                st_rd[p] = 0; st_wr[p] = 0; st_act[p] = 0; st_hit[p] = 0; st_conf[p] = 0; st_ref[p] = 0;
            end
            st_bp_cycles = 0; st_rd_lat_sum = 0; st_rd_lat_max = 0;
        end else begin
            cyc <= cyc + 1;
            now = cyc * CLK_PS;
            // responses taken this cycle (rsp_v is the registered offer)
            for (p = 0; p < NPC; p = p + 1)
                if (rsp_v[p] && rsp_rdy[p]) begin
                    r_rp[p] = (r_rp[p] + 1) % RQD; r_n[p] = r_n[p] - 1;
                end
            // requests
            if (req_v && !req_rdy) st_bp_cycles = st_bp_cycles + 1;
            if (req_v && req_rdy) begin
                for (i = 0; i < req_len; i = i + 1) begin
                    p = pc_of(req_addr + i);
                    slot = (q_rp[p] + q_n[p]) % QD;
                    q_we[p][slot] = req_we; q_addr[p][slot] = req_addr + i; q_tag[p][slot] = req_tag;
                    q_beat[p][slot] = i[BEATW-1:0]; q_data[p][slot] = req_wdata; q_arr[p][slot] = now;
                    q_n[p] = q_n[p] + 1;
                end
            end
            // issue: per pseudo-channel, in order, every head whose column time has come
            for (p = 0; p < NPC; p = p + 1) begin
                for (iter = 0; iter < 4; iter = iter + 1) begin
                    if (q_n[p] > 0 && r_n[p] < RQD) begin
                        if (!h_sched[p]) begin
                            // FR-FCFS: move the chosen burst to the head, the others keep their order
                            sel = 0;
                            e = q_rp[p];
                            best = estimate(p, q_we[p][e], q_addr[p][e], q_arr[p][e], now);
                            if (h_skip[p] < MAXSKIP)
                                for (i = 1; i < RW; i = i + 1)
                                    if (i < q_n[p]) begin
                                        e = (q_rp[p] + i) % QD;
                                        ok = 1'b1;
                                        for (j = 0; j < i; j = j + 1) begin
                                            o = (q_rp[p] + j) % QD;
                                            if (q_addr[p][o] == q_addr[p][e] && (q_we[p][o] || q_we[p][e])) ok = 1'b0;
                                        end
                                        if (ok) begin
                                            est = estimate(p, q_we[p][e], q_addr[p][e], q_arr[p][e], now);
                                            if (est < best) begin best = est; sel = i; end
                                        end
                                    end
                            if (sel != 0) begin
                                h_skip[p] = h_skip[p] + 1;
                                e = (q_rp[p] + sel) % QD;
                                t_we = q_we[p][e]; t_addr = q_addr[p][e]; t_tag = q_tag[p][e];
                                t_beat = q_beat[p][e]; t_data = q_data[p][e]; t_arr = q_arr[p][e];
                                for (i = sel; i >= 1; i = i - 1) begin
                                    e = (q_rp[p] + i) % QD; o = (q_rp[p] + i - 1) % QD;
                                    q_we[p][e] = q_we[p][o]; q_addr[p][e] = q_addr[p][o]; q_tag[p][e] = q_tag[p][o];
                                    q_beat[p][e] = q_beat[p][o]; q_data[p][e] = q_data[p][o]; q_arr[p][e] = q_arr[p][o];
                                end
                                e = q_rp[p];
                                q_we[p][e] = t_we; q_addr[p][e] = t_addr; q_tag[p][e] = t_tag;
                                q_beat[p][e] = t_beat; q_data[p][e] = t_data; q_arr[p][e] = t_arr;
                            end else h_skip[p] = 0;
                            h_tcol[p] = schedule(p, q_we[p][q_rp[p]], q_addr[p][q_rp[p]],
                                                 q_arr[p][q_rp[p]], now);
                            h_sched[p] = 1'b1;
                        end
                        if (h_tcol[p] <= now) begin
                            slot = q_rp[p];
                            if (q_we[p][slot]) begin
                                mem[q_addr[p][slot] % MEM_WORDS] = q_data[p][slot];
                                st_wr[p] = st_wr[p] + 1;
                            end else begin
                                k = (r_rp[p] + r_n[p]) % RQD;
                                r_t[p][k] = h_tcol[p] + CL_PS + BURST_PS + RSP_PS;
                                r_tag[p][k] = q_tag[p][slot]; r_beat[p][k] = q_beat[p][slot];
                                r_data[p][k] = mem[q_addr[p][slot] % MEM_WORDS];
                                r_n[p] = r_n[p] + 1;
                                st_rd[p] = st_rd[p] + 1;
                                st_rd_lat_sum = st_rd_lat_sum + (r_t[p][k] - q_arr[p][slot]);
                                if (r_t[p][k] - q_arr[p][slot] > st_rd_lat_max) st_rd_lat_max = r_t[p][k] - q_arr[p][slot];
                            end
                            q_rp[p] = (q_rp[p] + 1) % QD; q_n[p] = q_n[p] - 1; h_sched[p] = 1'b0;
                        end
                    end
                end
            end
            // registered outputs for the next cycle
            for (p = 0; p < NPC; p = p + 1) begin
                rsp_v[p] <= (r_n[p] > 0) && (r_t[p][r_rp[p]] <= (cyc + 1) * CLK_PS);
                rsp_tag[p*TAGW +: TAGW] <= r_tag[p][r_rp[p]];
                rsp_beat[p*BEATW +: BEATW] <= r_beat[p][r_rp[p]];
                rsp_data[p*DW +: DW] <= r_data[p][r_rp[p]];
            end
            ok = 1'b1;
            for (p = 0; p < NPC; p = p + 1) if (q_n[p] + LENMAX > QD) ok = 1'b0;
            req_rdy <= ok;
        end
    end
endmodule
