`timescale 1ps/1fs
// HA4 (HBM accelerator, rung R5a): the routed-expert fetch path of one HBM3E stack on the streaming
// controller.  Default-off (ENABLE=0 ties every output to zero); nothing pinned instantiates it.
//
// Replaces the per-line request port of rtl/gpu/ot_gpu_expert_fetch.sv (c52ae6d7f) by one stream
// descriptor per (expert, pseudo-channel) on the 52ce3e9c1 r6 sequencer (successor
// ot_hbm_accel_expert_stream_pc: + static-schedule `notice`), and keeps that block's SM-side
// contract: per-SM staging ring, at most LAND sectors landed per SM per cycle with a rotating PC
// priority, in-order release of whole 128-B lines one a cycle (s_valid/s_ready).
//
// STATIC LAYOUT (load-time placement, exact: bytes are moved, never changed).  An expert's stack
// slice is NLINE = NSECT*NPC/4 lines of 128 B.  Line-order index L (0..NLINE-1) maps to
// (SM, line of that SM's per-expert stream) through cfg_lut[L] = {sm, line}; the loader orders L so
// that every SM's w1/w3 lines come before any w2 line.  Stack sector s = 4L + quarter lives on
// PC s mod NPC at PC-local sector j = s div NPC of row ROW_BASE + id, i.e. bank set 0, BG j[1:0],
// column j[6:2] (the 52ce3 PC map), so each expert is ONE descriptor (row, NSECT) per PC.
//
// CLOCKS.  clk: 1.2 GHz SM/streaming domain (ids in, staging out).  hclk: HBM controller CK/2.
// Crossings are real asynchronous FIFOs (ot_hbm_accel_cdc_fifo): ids clk->hclk, and per PC the
// landing FIFO hclk->clk, whose depth (32) is the sequencer's credit.  `notice` is in hclk: it is
// the static decode schedule's routed-expert window, raised before the router's top-6 is due.
module ot_hbm_accel_expert_fetch_stream #(
  parameter integer ENABLE = 0, REF_MODE = 1, PHASE = 0,
  parameter integer NSM = 8, NPC = 32, NSECT = 49, IW = 9, ROW_BASE = 0,
  parameter integer DEPTH = 512, LAND = 4, MAXL = 64
)(
  input  wire               clk, hclk, rst_n, hrst_n,
  // static configuration (held for the life of a task)
  input  wire [NSM*16-1:0]  cfg_lines,                    // lines per SM per expert
  input  wire [NSECT*NPC/4*16-1:0] cfg_lut,               // L -> {sm[15:8], line[7:0]}
  // expert ids (clk), the router's order
  input  wire               e_valid, output wire e_ready, input wire [IW-1:0] e_id,
  // static-schedule refresh notice (hclk)
  input  wire               notice,
  // HBM3E commands (hclk), per PC
  output wire [NPC-1:0]     row_v, output wire [NPC*3-1:0] row_op, output wire [NPC*5-1:0] row_bank,
  output wire [NPC*19-1:0]  row_row,
  output wire [NPC-1:0]     col_v, output wire [NPC*5-1:0] col_bank, output wire [NPC*5-1:0] col_col,
  // read data returned by the PHY (hclk), one 32-B sector per PC per cycle, in RD order
  input  wire [NPC-1:0]     rd_v, input wire [NPC*256-1:0] rd_data,
  // SM tensor-core streams (clk)
  output wire [NSM-1:0]     s_valid, input wire [NSM-1:0] s_ready, output wire [NSM*1024-1:0] s_data,
  output wire               fault
);
  generate if (!ENABLE) begin : off
    assign e_ready = 0; assign row_v = 0; assign row_op = 0; assign row_bank = 0; assign row_row = 0;
    assign col_v = 0; assign col_bank = 0; assign col_col = 0; assign s_valid = 0; assign s_data = 0;
    assign fault = 0;
  end else begin : on
    localparam integer NLINE = NSECT * NPC / 4;
    localparam integer SW = $clog2(DEPTH);
    localparam integer MW = (NSM > 1) ? $clog2(NSM) : 1;
    localparam integer PERIOD = REF_MODE ? 118 : 3808;
    // ---------------- ids: clk -> hclk ----------------
    wire id_full, id_empty; wire [IW-1:0] id_q; wire id_pop;
    ot_hbm_accel_cdc_fifo #(.W(IW), .AW(3)) u_ids (
      .wclk(clk), .wrst_n(rst_n), .we(e_valid), .wdata(e_id), .full(id_full), .rd_freed(),
      .rclk(hclk), .rrst_n(hrst_n), .re(id_pop), .rdata(id_q), .empty(id_empty));
    assign e_ready = !id_full;
    // ---------------- dispatch (hclk): one descriptor per (expert, PC) ----------------
    reg [IW-1:0] tab [0:7]; reg [3:0] cnt; reg [3:0] ptr [0:NPC-1];
    wire [NPC-1:0] pc_r, pc_busy, pc_fault, dv; wire [NPC-1:0] all_done_v;
    for (genvar p = 0; p < NPC; p = p + 1) begin : dsp
      assign dv[p] = (ptr[p] < cnt);
      assign all_done_v[p] = (ptr[p] == cnt) && !pc_busy[p];
    end
    wire retire = (cnt != 0) && (&all_done_v) && id_empty;
    assign id_pop = !id_empty && cnt < 8 && !retire;
    always @(posedge hclk or negedge hrst_n)
      if (!hrst_n) begin cnt <= 0; for (integer p = 0; p < NPC; p = p + 1) ptr[p] <= 0; end
      else begin
        if (retire) begin cnt <= 0; for (integer p = 0; p < NPC; p = p + 1) ptr[p] <= 0; end
        else begin
          if (id_pop) begin tab[cnt[2:0]] <= id_q; cnt <= cnt + 1'b1; end
          for (integer p = 0; p < NPC; p = p + 1) if (dv[p] && pc_r[p]) ptr[p] <= ptr[p] + 1'b1;
        end
      end
    // ---------------- 32 stream sequencers (hclk) and their landing crossings ----------------
    wire [NPC*3-1:0] cred_ret;
    wire [NPC-1:0] l_empty, l_full, l_re; wire [NPC*256-1:0] l_q;
    reg  land_fault;
    for (genvar p = 0; p < NPC; p = p + 1) begin : pc
      ot_hbm_accel_expert_stream_pc #(.ENABLE(1), .REF_MODE(REF_MODE), .PC(p), .CRED(32),
        .REF_PHASE((PHASE + (p * PERIOD) / 32) % PERIOD),
        .IDLE0(0), .IDLE1(3), .IDLE2(4), .IDLE3(2), .IDLE4(5), .IDLE5(1), .IDLE6(6), .IDLE7(7)) u (
        .clk(hclk), .rst_n(hrst_n), .desc_v(dv[p]), .desc_r(pc_r[p]),
        .desc_row(19'(ROW_BASE) + 19'(tab[ptr[p][2:0]])), .desc_n(11'(NSECT)),
        .go(1'b1), .next_posted(1'b0), .notice(notice),
        .row_v(row_v[p]), .row_prio(), .row_gnt(1'b1),
        .row_op(row_op[p*3 +: 3]), .row_bank(row_bank[p*5 +: 5]), .row_row(row_row[p*19 +: 19]),
        .col_v(col_v[p]), .col_bank(col_bank[p*5 +: 5]), .col_col(col_col[p*5 +: 5]),
        .cred_ret(cred_ret[p*3 +: 3]), .busy(pc_busy[p]), .ref_fault(pc_fault[p]));
      ot_hbm_accel_cdc_fifo #(.W(256), .AW(5)) u_land (
        .wclk(hclk), .wrst_n(hrst_n), .we(rd_v[p]), .wdata(rd_data[p*256 +: 256]), .full(l_full[p]),
        .rd_freed(cred_ret[p*3 +: 3]),
        .rclk(clk), .rrst_n(rst_n), .re(l_re[p]), .rdata(l_q[p*256 +: 256]), .empty(l_empty[p]));
    end
    always @(posedge hclk or negedge hrst_n)
      if (!hrst_n) land_fault <= 0; else if (|(rd_v & l_full)) land_fault <= 1;   // credit breach
    // ---------------- landing (clk): sector -> (SM, slot, quarter), <= LAND a SM a cycle ----------------
    reg [$clog2(NSECT+1)-1:0] j_c [0:NPC-1];        // PC-local sector within the current expert
    reg [15:0] k_c [0:NPC-1];                       // experts streamed by this PC since reset
    reg [$clog2(NPC)-1:0] prio;
    reg [3:0] mask [0:NSM-1][0:DEPTH-1];
    reg [255:0] ring [0:NSM-1][0:3][0:DEPTH-1];
    reg [SW:0] cons_p [0:NSM-1];
    reg [NPC-1:0] re_c; reg [MW-1:0] l_sm [0:NPC-1]; reg [SW-1:0] l_slot [0:NPC-1]; reg [1:0] l_qt [0:NPC-1];
    integer nland [0:NSM-1];
    always @* begin
      re_c = 0;
      for (integer m = 0; m < NSM; m = m + 1) nland[m] = 0;
      for (integer pp = 0; pp < NPC; pp = pp + 1) begin
        automatic integer p = (prio + pp) % NPC;
        automatic integer s = j_c[p] * NPC + p;
        automatic integer L = s >> 2;
        automatic integer sm = cfg_lut[L*16 + 8 +: 8];
        automatic integer ln = cfg_lut[L*16 +: 8];
        l_sm[p] = MW'(sm); l_qt[p] = 2'(s & 3);
        l_slot[p] = SW'(k_c[p] * cfg_lines[sm*16 +: 16] + ln);
        if (!l_empty[p] && nland[sm] < LAND) begin re_c[p] = 1; nland[sm] = nland[sm] + 1; end
      end
    end
    assign l_re = re_c;
    // ---------------- release (clk) ----------------
    wire [NSM-1:0] take;
    for (genvar m = 0; m < NSM; m = m + 1) begin : out
      wire [SW-1:0] cs = cons_p[m][SW-1:0];
      assign s_valid[m] = &mask[m][cs];
      assign s_data[m*1024 +: 1024] = {ring[m][3][cs], ring[m][2][cs], ring[m][1][cs], ring[m][0][cs]};
      assign take[m] = s_valid[m] && s_ready[m];
    end
    reg ring_fault;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        prio <= 0; ring_fault <= 0;
        for (integer p = 0; p < NPC; p = p + 1) begin j_c[p] <= 0; k_c[p] <= 0; end
        for (integer m = 0; m < NSM; m = m + 1) begin
          cons_p[m] <= 0; for (integer d = 0; d < DEPTH; d = d + 1) mask[m][d] <= 4'd0;
        end
      end else begin
        prio <= prio + 1'b1;
        for (integer m = 0; m < NSM; m = m + 1) if (take[m]) begin
          cons_p[m] <= cons_p[m] + 1'b1; mask[m][cons_p[m][SW-1:0]] <= 4'd0;
        end
        for (integer p = 0; p < NPC; p = p + 1) if (re_c[p]) begin
          if (mask[l_sm[p]][l_slot[p]][l_qt[p]]) ring_fault <= 1;      // staging overrun
          ring[l_sm[p]][l_qt[p]][l_slot[p]] <= l_q[p*256 +: 256];
          mask[l_sm[p]][l_slot[p]][l_qt[p]] <= 1'b1;
          if (j_c[p] == NSECT - 1) begin j_c[p] <= 0; k_c[p] <= k_c[p] + 1'b1; end
          else j_c[p] <= j_c[p] + 1'b1;
        end
      end
    reg pf_s1, pf_s2;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin pf_s1 <= 0; pf_s2 <= 0; end else begin pf_s1 <= (|pc_fault) || land_fault; pf_s2 <= pf_s1; end
    assign fault = pf_s2 || ring_fault;
  end endgenerate
endmodule
