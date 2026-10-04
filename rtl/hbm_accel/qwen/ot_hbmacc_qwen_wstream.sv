`timescale 1ps/1fs
// ---------------------------------------------------------------------------
// HA8 (Qwen3-8B HBM accelerator): the weight + KV PREFETCH STREAM of one die, in the HBM
// controller clock domain (CK/2, 1.024 ns).  Default-off: ENABLE = 0 ties every output to zero;
// selected only by the HA8 runtime die rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12.sv.
//
// The decode program is static, so every HBM byte a token reads (each layer's INT8 code words,
// and the KV window of positions < P) is known in advance and is stored in HBM as ONE STREAM in
// consumption order.  This module fetches that stream, in order, through NSTK stacks of the
// measured streaming-read controller ot_hbm_r14_stream_stack (52ce3e9c1: REFpb on schedule,
// per-channel row slot, one RD per PC per controller cycle), into a WINDOW of WINW stream words
// that the engine drains in the core clock domain.
//
// STREAM WORD.  One stream word is one engine code word: G = 6,144 groups x 16 INT8 = 98,304 B =
// 3,072 32-byte sectors, interleaved over the die's NPC = 32 * NSTK pseudo-channels, SPW sectors
// per PC (24 at 4 stacks).  PC-local stream sector s is read from descriptor s / 1024 (one 1 KB
// row in each of the PC's 32 banks: the controller's row-set descriptor), sector s mod 1024.
//
// FLOW CONTROL.  A PC issues an RD only against a credit (CRED outstanding).  A read lands RL
// controller cycles after its RD (CL + BL8 + response path, the bench's 23.5 ns).  A landed sector
// moves into the window (and returns its credit) only while the window has room: PC p may hold
// sectors up to ((C + WINW) * SPW) where C is the engine's consumed-word count.  A word is
// COMPLETE when every PC has moved its SPW sectors of it; A = complete words, a registered
// min over the PCs (MINLAT stages), Gray coded to the engine domain.  C arrives Gray coded and
// is synchronised here (two flops).
//
// Data are NOT carried: the window's contents are the engine's code banks (preloaded by the host
// with exactly the stream's words); this module times their arrival.  The DRAM command timing is
// the controller's own (its bench checks every command against a ps-accurate DRAM model).
// ---------------------------------------------------------------------------
module ot_hbmacc_qwen_wstream #(
    parameter integer ENABLE   = 0,
    parameter integer NSTK     = 4,       // HBM stacks attached to this die
    parameter integer REF_MODE = 1,       // 1: REFpb on schedule (the measured controller); 0: REFab
    parameter integer CRED     = 32,      // outstanding RDs per PC
    parameter integer RL       = 23,      // RD -> landed, controller cycles
    parameter integer SPW      = 24,      // sectors per PC per stream word
    parameter integer WINW     = 160,     // window, stream words
    parameter integer MINLAT   = 2,       // registered min-tree stages over the PCs
    parameter integer CW       = 32
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,                 // stream from word 0 (held high)
    input  wire [CW-1:0]     cfg_words,          // stream words of this run
    input  wire [CW-1:0]     c_gray,             // engine domain: consumed words (Gray)
    output wire [CW-1:0]     a_gray,             // complete words in the window (Gray)
    output wire              fault,
    output wire [CW-1:0]     st_cycles,          // controller cycles since go
    output wire [CW-1:0]     st_rd,              // RDs issued (all PCs)
    output wire [CW-1:0]     st_room_block,      // PC-cycles a landed sector waited for window room
    output wire [CW-1:0]     st_desc_gap,        // PC-cycles between descriptors (no RD possible)
    output wire [CW-1:0]     st_words            // A (binary)
);
    localparam integer NPC = 32 * NSTK;
    function automatic [CW-1:0] g2b(input [CW-1:0] g);
        integer i; begin g2b[CW-1] = g[CW-1]; for (i = CW - 2; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i]; end
    endfunction
    generate if (ENABLE == 0) begin : g_off
        assign a_gray = 0; assign fault = 0; assign st_cycles = 0; assign st_rd = 0; assign st_room_block = 0;
        assign st_desc_gap = 0; assign st_words = 0;
    end else begin : g_on
        // ---- consumed count from the engine domain (2-flop synchroniser of a Gray counter) ----------
        reg [CW-1:0] c_s1, c_s2;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin c_s1 <= 0; c_s2 <= 0; end else begin c_s1 <= c_gray; c_s2 <= c_s1; end
        wire [CW-1:0] c_bin = g2b(c_s2);
        wire [63:0] room_lim = (64'(c_bin) + 64'(WINW)) * 64'(SPW);      // per-PC sector bound
        // ---- descriptors: per PC, rows 0, 1, ... of 1,024 sectors (a per-PC descriptor counter, so no PC
        //      waits for another between row sets); one ot_hbm_r14_stream_pc per PC, the channel's two PCs
        //      sharing its row-command slot by cycle parity exactly as ot_hbm_r14_stream_stack wires them.
        wire [63:0] sec_total = 64'(cfg_words) * 64'(SPW);                // per-PC stream sectors
        localparam integer PERIOD = REF_MODE ? 118 : 3808;
        wire [NPC-1:0] col_v, busy, pc_desc_r, pc_fault, row_req;
        wire [3*NPC-1:0] cred_ret;
        reg  [18:0] nrow [0:NPC-1];
        reg  [63:0] posted [0:NPC-1];
        reg         going;
        reg         arb_fault;
        genvar s;
        for (s = 0; s < NPC; s = s + 1) begin : g_pc
            wire [63:0] left = sec_total - posted[s];
            wire        dv = going && (posted[s] < sec_total) && pc_desc_r[s];
            wire [10:0] dn = (left >= 64'd1024) ? 11'd1024 : 11'(left);
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin nrow[s] <= 0; posted[s] <= 0; end
                else if (dv) begin nrow[s] <= nrow[s] + 1'b1; posted[s] <= posted[s] + 64'(dn); end
            ot_hbm_r14_stream_pc #(.ENABLE(1), .REF_MODE(REF_MODE), .PC(s % 32), .CRED(CRED),
                .REF_PHASE((((s / 32) * 29) + ((s % 32) * PERIOD) / 32) % PERIOD)) u_pc (
                .clk(clk), .rst_n(rst_n), .desc_v(dv), .desc_r(pc_desc_r[s]), .desc_row(nrow[s]), .desc_n(dn),
                .go(going), .next_posted(1'b1),
                .row_v(row_req[s]), .row_prio(), .row_gnt(1'b1), .row_op(), .row_bank(), .row_row(),
                .col_v(col_v[s]), .col_bank(), .col_col(),
                .cred_ret(cred_ret[s*3 +: 3]), .busy(busy[s]), .ref_fault(pc_fault[s]));
        end
        wire [NPC-1:0] st_fault_v = pc_fault;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin going <= 0; arb_fault <= 0; end
            else begin
                going <= go;
                for (integer c = 0; c < NPC / 2; c = c + 1) if (row_req[2*c] && row_req[2*c+1]) arb_fault <= 1'b1;
            end
        // ---- per PC: return pipeline, landed count, window move with room ---------------------------
        reg [RL-1:0]  rpipe [0:NPC-1];
        reg [63:0]    landed [0:NPC-1];
        reg [63:0]    moved [0:NPC-1];
        reg [2:0]     cret [0:NPC-1];
        reg [CW-1:0]  n_rd, n_room, n_gap, n_cyc;
        integer p, q;
        reg [CW-1:0]  rd_now, room_now, gap_now;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                for (p = 0; p < NPC; p = p + 1) begin rpipe[p] <= 0; landed[p] <= 0; moved[p] <= 0; cret[p] <= 0; end
                n_rd <= 0; n_room <= 0; n_gap <= 0; n_cyc <= 0;
            end else begin
                rd_now = 0; room_now = 0; gap_now = 0;
                for (p = 0; p < NPC; p = p + 1) begin
                    rpipe[p] <= {rpipe[p][RL-2:0], col_v[p]};
                    if (rpipe[p][RL-1]) landed[p] <= landed[p] + 1;
                    // move one landed sector into the window when it has room (one per cycle per PC)
                    if (landed[p] > moved[p] && moved[p] < room_lim) begin moved[p] <= moved[p] + 1; cret[p] <= 3'd1; end
                    else begin
                        cret[p] <= 3'd0;
                        if (landed[p] > moved[p]) room_now = room_now + 1;
                    end
                    if (col_v[p]) rd_now = rd_now + 1;
                    if (going && !busy[p] && posted[p] < sec_total) gap_now = gap_now + 1;
                end
                n_rd <= n_rd + rd_now; n_room <= n_room + room_now; n_gap <= n_gap + gap_now;
                if (going) n_cyc <= n_cyc + 1;
            end
        end
        for (s = 0; s < NPC; s = s + 1) begin : g_cr
            assign cred_ret[s*3 +: 3] = cret[s];
        end
        // ---- complete words: registered min over the PCs, then Gray ---------------------------------
        reg [63:0] mn [0:MINLAT-1];
        reg [63:0] m;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin for (q = 0; q < MINLAT; q = q + 1) mn[q] <= 0; end
            else begin
                m = moved[0];
                for (p = 1; p < NPC; p = p + 1) if (moved[p] < m) m = moved[p];
                mn[0] <= m;
                for (q = 1; q < MINLAT; q = q + 1) mn[q] <= mn[q-1];
            end
        end
        wire [CW-1:0] a_bin = CW'(mn[MINLAT-1] / 64'(SPW));
        reg  [CW-1:0] a_g;
        always @(posedge clk or negedge rst_n) if (!rst_n) a_g <= 0; else a_g <= a_bin ^ (a_bin >> 1);
        assign a_gray = a_g;
        assign fault = (|st_fault_v) | arb_fault;
        assign st_cycles = n_cyc; assign st_rd = n_rd; assign st_room_block = n_room; assign st_desc_gap = n_gap;
        assign st_words = a_bin;
    end endgenerate
endmodule
