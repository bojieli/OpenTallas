// DISABLED standalone T7 LAND data-cut candidate (TOK-DS-3, 2026-11-02).  Never selected by production RTL/manifest.
//
// Replaces: the native 640x256 land helper (ot_bind_native_4c805, 4 async reads, 7 write slots in one process), the
// rowword/kc_w composition of its read data and the unconditional 1060-bit ekv_w capture.  Everything else (ekv_m,
// rel_bad/pres/spres, valid/ready, queues, job/reset control) stays in the parent.
//
// Algorithm (PREP 2b45fe0b1): three full-word writer channels (PC0 = slots 0-2, PC1 = 3-5, ROWS = 6), each with its own
// copy of every logical read bank: 12 real single-clock ot_sram_1r1w_256x256_m2_r2c2, [writer][bank], logical row r ->
// bank r&3, local row r>>2.  A reset-free 640x2 latest-writer table (LVT) is updated in source order PC0, PC1, ROWS
// (later wins on equal rows, as the native process).  At the capture edge every lane reads bank j, local row rc-1, from
// all three writer copies (synchronous read = OLD data, read-before-write), and captures the OLD LVT entry plus the live
// window/need/valid/scale facts as one 10-bit code per lane (773 states).  The lane word is reconstructed from the code
// and the three macro outputs.  Writes to rows >= 640 are dropped (native helper: out-of-range write ignored).
//
// Contract (checked by the bench, not assumed silently): each slot's 256 mask bits are copies of one scalar enable, and
// within one PC the three slots are mutually exclusive (tag type0 vs type2, beat0 vs beat1).
//
// MUT (bench negative controls only; the normal candidate is MUT=0):
//   1 wrong priority (LVT order ROWS < PC1)        2 drop the lower writer when two channels hit the same bank
//   3 post-write LVT (selection from the NEW LVT)    4 stale metadata (valid/window/need/scale sampled one edge late)
//   5 one-edge-late read address
module land_sram_candidate #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire [223:0]  WR_ADDR,
    input  wire [1791:0] WR_DATA,
    input  wire [1791:0] WR_EN,
    input  wire [9:0]    rc,
    input  wire [3:0]    valid,     // per lane: row < tjob          (parent's existing kc_m compare)
    input  wire [3:0]    win,       // per lane: row < wcount        (parent's existing rowword window compare)
    input  wire [3:0]    need,      // per lane: parent's existing need expression
    input  wire [31:0]   scale,     // per lane: wsc[8*(wfirst[6:0]+row[6:0]) +: 8] (parent's existing shifter)
    output wire [1059:0] q
);
    // ---------------------------------------------------------------- writer channels
    wire [6:0] se;
    genvar gs;
    for (gs = 0; gs < 7; gs = gs + 1) begin : g_se
        assign se[gs] = WR_EN[256*gs];
    end
    wire [2:0]   ch_en;
    wire [9:0]   ch_row [0:2];
    wire [255:0] ch_d   [0:2];
    assign ch_en[0] = se[0] | se[1] | se[2];
    assign ch_en[1] = se[3] | se[4] | se[5];
    assign ch_en[2] = se[6];
    assign ch_row[0] = se[0] ? {2'd0, WR_ADDR[7:0]}   : WR_ADDR[41:32];          // slots 1 and 2 share one address
    assign ch_row[1] = se[3] ? {2'd0, WR_ADDR[103:96]} : WR_ADDR[137:128];
    assign ch_row[2] = WR_ADDR[201:192];
    assign ch_d[0] = se[0] ? WR_DATA[255:0]    : se[1] ? WR_DATA[511:256]   : WR_DATA[767:512];
    assign ch_d[1] = se[3] ? WR_DATA[1023:768] : se[4] ? WR_DATA[1279:1024] : WR_DATA[1535:1280];
    assign ch_d[2] = WR_DATA[1791:1536];
    wire [2:0] ch_ok;
    genvar gc;
    for (gc = 0; gc < 3; gc = gc + 1) begin : g_ok
        assign ch_ok[gc] = ch_en[gc] && (ch_row[gc] < 10'd640);
    end
    // MUT 2: a single-writer-per-bank memory would lose the lower channel on a same-bank edge
    wire drop0 = (MUT == 2) && ch_ok[0] && ((ch_ok[1] && ch_row[1][1:0] == ch_row[0][1:0]) ||
                                            (ch_ok[2] && ch_row[2][1:0] == ch_row[0][1:0]));
    wire [2:0] w_ok = {ch_ok[2], ch_ok[1], ch_ok[0] && !drop0};

    // ---------------------------------------------------------------- read address (bank j, local row rc-1)
    wire [9:0] rc_used;
    if (MUT == 5) begin : g_rc_late
        reg [9:0] rc_d;
        always @(posedge clk) rc_d <= rc;
        assign rc_used = rc_d;
    end else begin : g_rc
        assign rc_used = rc;
    end
    wire [9:0] rbase = rc_used - 10'd1;

    // ---------------------------------------------------------------- 12 macros [writer][bank]
    wire [255:0] mq [0:11];
    genvar gw, gb;
    for (gw = 0; gw < 3; gw = gw + 1) begin : g_w
        for (gb = 0; gb < 4; gb = gb + 1) begin : g_b
            ot_sram_1r1w_256x256_m2_r2c2 ram (
                .clk(clk), .r_ce_in(1'b1), .r_addr_in(rbase[7:0]), .rd_out(mq[4*gw+gb]),
                .w_ce_in(w_ok[gw] && ch_row[gw][1:0] == gb), .w_addr_in(ch_row[gw][9:2]),
                .wd_in(ch_d[gw]), .w_mask_in({256{1'b1}}),
                .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(16'd0));
        end
    end

    // ---------------------------------------------------------------- latest-writer table (reset-free)
    reg [1:0] lvt [0:639];
    always @(posedge clk) begin
        if (MUT == 1) begin                       // wrong order: ROWS loses to PC1
            if (w_ok[0]) lvt[ch_row[0]] <= 2'd0;
            if (w_ok[2]) lvt[ch_row[2]] <= 2'd2;
            if (w_ok[1]) lvt[ch_row[1]] <= 2'd1;
        end else begin                            // source order PC0, PC1, ROWS: later wins
            if (w_ok[0]) lvt[ch_row[0]] <= 2'd0;
            if (w_ok[1]) lvt[ch_row[1]] <= 2'd1;
            if (w_ok[2]) lvt[ch_row[2]] <= 2'd2;
        end
    end
    // MUT 3: post-write LVT = the entry as it will be after this edge's writes
    function automatic [1:0] lvt_new(input [9:0] r, input [1:0] old);
        lvt_new = old;
        if (w_ok[0] && ch_row[0] == r) lvt_new = 2'd0;
        if (w_ok[1] && ch_row[1] == r) lvt_new = 2'd1;
        if (w_ok[2] && ch_row[2] == r) lvt_new = 2'd2;
    endfunction

    // ---------------------------------------------------------------- per-lane metadata code (10 bits, 773 states)
    // 0..767 = {writer2, scale8} window row; 768..770 = compressed-needed writer0..2; 771 = compressed ignored;
    // 772 = row outside the job.  Sampled from the LIVE pre-edge source values at the capture edge.
    reg [9:0]    mcode [0:3];
    wire [3:0] m_valid, m_win, m_need; wire [31:0] m_scale;
    if (MUT == 4) begin : g_meta_late
        reg [3:0] valid_d, win_d, need_d; reg [31:0] scale_d;
        always @(posedge clk) begin valid_d <= valid; win_d <= win; need_d <= need; scale_d <= scale; end
        assign m_valid = valid_d; assign m_win = win_d; assign m_need = need_d; assign m_scale = scale_d;
    end else begin : g_meta
        assign m_valid = valid; assign m_win = win; assign m_need = need; assign m_scale = scale;
    end
    integer j;
    reg [31:0] row; reg [1:0] wr; reg [9:0] code;
    always @(posedge clk) begin
        for (j = 0; j < 4; j = j + 1) begin
            row  = 4 * (32'(rc_used) - 1) + j;
            wr   = (row < 32'd640) ? lvt[row[9:0]] : 2'd0;
            if (MUT == 3) wr = lvt_new(row[9:0], wr);
            if (!m_valid[j])                 code = 10'd772;
            else if (m_win[j])               code = {wr, m_scale[8*j +: 8]};
            else if (m_need[j])              code = 10'd768 + 10'(wr);
            else                             code = 10'd771;
            mcode[j] <= code;
        end
    end

    // ---------------------------------------------------------------- reconstruction (combinational from captured state)
    genvar gl;
    for (gl = 0; gl < 4; gl = gl + 1) begin : g_lane
        wire [9:0]   c   = mcode[gl];
        wire [1:0]   sel = (c < 10'd768) ? c[9:8] : (c < 10'd771) ? 2'(c - 10'd768) : 2'd0;
        wire [255:0] l   = (sel == 2'd0) ? mq[gl] : (sel == 2'd1) ? mq[4+gl] : mq[8+gl];
        assign q[265*gl +: 265] = (c < 10'd768) ? {1'b0, c[7:0], l} :
                                  (c < 10'd771) ? {1'b1, 120'd0, l[143:0]} :
                                  (c == 10'd771) ? {1'b1, 264'd0} : 265'd0;
    end
endmodule
