`timescale 1ps/1fs
// HA4 R5a-LA (HBM accelerator): the routed-expert fetch path of one HBM3E stack at full stack
// bandwidth.  Successor of ot_hbm_accel_expert_fetch_stream (R5a); default-off (ENABLE=0 ties every
// output to zero); nothing pinned instantiates it.  The SM-side contract is R5a's: per-SM staging
// ring, at most LAND sectors landed per SM per cycle with a rotating PC priority, in-order release
// of whole 128-B lines (s_valid/s_ready), lines of the k-th expert of a task in staging slot
// (task * TOPK + k) * lines + line, so every SM releases exactly R5a's byte sequence.
//
// R5a measured 0.395 TB/s of the 1.0 TB/s stack (results/rtl/hbm_accel_ha4_20261004): every expert
// sat in bank set 0, so each (expert, PC) descriptor of 49 sectors re-closed and re-opened the same
// four banks, and the 32-entry landing crossing could not cover the ~40-cycle credit round trip.
// R5a-LA changes five things, none of which touches a byte:
//  1. LAYOUT (load-time placement): expert e sits in bank set e mod NSETS at row ROW_BASE + e div
//     NSETS (NSETS = 7 leaves set 7 empty as the refresh parking set).  Within the set, PC-local
//     sector j -> BG j[1:0] ^ {e[0], 0}, column j[6:2] (the R5a map with a BG swizzle by id parity).
//  2. Sequencers with a one-deep descriptor lookahead (ot_hbm_accel_expert_stream_pc_la): the next
//     expert's banks open while the current expert streams; the switch costs no cycle.
//  3. FETCH ORDER: the dispatcher streams the router's first expert first, then, among the arrived
//     experts, the earliest one whose set (and, once all ids are in, BG swizzle id[0]) differs from
//     the previous one (an expert whose set equals
//     the previous one's is taken only when no other is available and all TOPK ids are in, or the
//     id queue is empty).  Each descriptor carries its router index k as a tag through a per-PC tag
//     queue to the landing crossing, so the slot (hence the release order) is the router order.
//  4. Landing crossings are 2**LAW deep (64): the credit round trip (PHY + CL + response + two
//     synchronisers each way) exceeds 32 cycles.
//  3a. PICK (default 2): PICK 2 keeps the router order except where that would force two same-set
//     experts to be adjacent later (a feasibility test on the remaining sets); PICK 1: after the router's first, the expert taken next is the one whose set has the
//     most unpicked experts left (among sets differing from the previous one), once all TOPK ids are
//     in; the greedy earliest-first order (PICK 0) left same-set pairs for the end.
//  5. REPICK (default 1): a REFpb's bank is latched LEAD (48) cycles before it is due, usually before
//     the later router ids (hence `prot`) arrive; the sequencer moves a pending REFpb off a bank that
//     has become protected onto a closed unprotected one.  Without it one REFpb in each routed
//     window landed on a needed set and stalled that PC for tRFCpb (200 ns).
// `prot` (sets of the task's experts) and `notice` keep refresh off the sets the task needs.
module ot_hbm_accel_expert_fetch_stream_la #(
  parameter integer ENABLE = 0, REF_MODE = 1, PHASE = 0,
  parameter integer NSM = 8, NPC = 32, NSECT = 49, IW = 9, ROW_BASE = 0,
  parameter integer DEPTH = 512, LAND = 4, MAXL = 64,
  parameter integer TOPK = 6, NSETS = 7, LAW = 6, PICK = 2, REPICK = 1, RESERVE = 1, PULL = 0, TAILPULL = 12,
  parameter integer PCPROT = 0, STEER = 0, NWIN = 0,
  parameter [7:0]   NOTICE_PROT = 8'h7F
)(
  input  wire               clk, hclk, rst_n, hrst_n,
  input  wire [NSM*16-1:0]  cfg_lines,
  input  wire [NSECT*NPC/4*16-1:0] cfg_lut,
  input  wire               e_valid, output wire e_ready, input wire [IW-1:0] e_id,
  input  wire               notice,
  output wire [NPC-1:0]     row_v, output wire [NPC*3-1:0] row_op, output wire [NPC*5-1:0] row_bank,
  output wire [NPC*19-1:0]  row_row,
  output wire [NPC-1:0]     col_v, output wire [NPC*5-1:0] col_bank, output wire [NPC*5-1:0] col_col,
  input  wire [NPC-1:0]     rd_v, input wire [NPC*256-1:0] rd_data,
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
    localparam integer JW = $clog2(NSECT + 1);
    function automatic [2:0] set_of(input [IW-1:0] id);  set_of = 3'(id % NSETS); endfunction
    function automatic [18:0] row_of(input [IW-1:0] id); row_of = 19'(ROW_BASE) + 19'(id / NSETS); endfunction
    // ---------------- ids: clk -> hclk ----------------
    wire id_full, id_empty; wire [IW-1:0] id_q; wire id_pop;
    ot_hbm_accel_cdc_fifo #(.W(IW), .AW(3)) u_ids (
      .wclk(clk), .wrst_n(rst_n), .we(e_valid), .wdata(e_id), .full(id_full), .rd_freed(),
      .rclk(hclk), .rrst_n(hrst_n), .re(id_pop), .rdata(id_q), .empty(id_empty));
    assign e_ready = !id_full;
    // ---------------- dispatch (hclk): arrival table, fetch order, one descriptor per (expert, PC) --
    reg [IW-1:0] tab [0:7]; reg [2:0] tset [0:7]; reg [3:0] cnt;
    reg [2:0] ord [0:7]; reg [3:0] oc; reg [7:0] picked; reg [2:0] lset; reg lbgx; reg [7:0] prot;
    reg [3:0] ptr [0:NPC-1];
    wire [NPC-1:0] pc_r, pc_busy, pc_fault, dv; wire [NPC-1:0] all_done_v;
    for (genvar p = 0; p < NPC; p = p + 1) begin : dsp
      assign dv[p] = (ptr[p] < oc);
      assign all_done_v[p] = (ptr[p] == oc) && !pc_busy[p];
    end
    // picker: the earliest arrived, unpicked k whose set differs from the last picked set, preferring
    // one whose BG swizzle (id[0]) also differs (its first RD then meets no tCCD_L from the last one)
    reg pk_v; reg [2:0] pk_k; reg pb_v; reg [2:0] pb_k; reg any_v; reg [2:0] any_k;
    reg [2:0] rem [0:7];                         // unpicked arrived experts sharing k's set
    reg [3:0] nun; reg [7:0] feas;               // unpicked count; k can be next with a valid rest order
    always @* begin
      nun = 0;
      for (integer r = 0; r < 8; r = r + 1) if (r < cnt && !picked[r]) nun = nun + 1'b1;
      for (integer q = 0; q < 8; q = q + 1) begin
        rem[q] = 0;
        for (integer r = 0; r < 8; r = r + 1) if (r < cnt && !picked[r] && tset[r] == tset[q]) rem[q] = rem[q] + 1'b1;
      end
      // after taking q (rest n = nun-1, last set = tset[q]): every set's rest count must be <= ceil(n/2),
      // and q's own set (which may not lead the rest) <= floor(n/2)
      for (integer q = 0; q < 8; q = q + 1) begin
        feas[q] = 1'b1;
        for (integer r = 0; r < 8; r = r + 1)
          if (r < cnt && !picked[r] && r != q)
            if (tset[r] == tset[q] ? (4'(rem[r]) - 4'd1 > (nun - 4'd1) / 2) : (4'(rem[r]) > nun / 2)) feas[q] = 1'b0;
      end
    end
    always @* begin
      pk_v = 0; pk_k = 0; pb_v = 0; pb_k = 0; any_v = 0; any_k = 0;
      for (integer q = 7; q >= 0; q = q - 1)
        if (q < cnt && !picked[q]) begin
          any_v = 1; any_k = 3'(q);
          if (tset[q] != lset) begin
            pk_v = 1; pk_k = 3'(q);
            if (tab[q][0] != lbgx) begin pb_v = 1; pb_k = 3'(q); end
          end
        end
      if (pb_v && (cnt >= 4'(TOPK) || id_empty)) begin pk_v = 1; pk_k = pb_k; end
      if (PICK != 0 && oc != 0) begin
        // PICK 1: once all TOPK ids are in, the unpicked expert whose set differs from the last one and
        // has the most unpicked experts left (ties: BG swizzle differs, then earliest); same-set pairs
        // are then adjacent only when one set holds more than half of the remaining experts.
        pk_v = 0; pk_k = 0;
        if (cnt >= 4'(TOPK) && PICK == 2) begin
          // PICK 2: the earliest (router order) unpicked expert whose set differs from the last one and
          // after which the rest can still be ordered with no same-set neighbours; else PICK 1's choice
          for (integer q = 7; q >= 0; q = q - 1)
            if (q < cnt && !picked[q] && tset[q] != lset && feas[q]) begin pk_v = 1; pk_k = 3'(q); end
        end
        if (cnt >= 4'(TOPK) && !pk_v) begin
          for (integer q = 7; q >= 0; q = q - 1)
            if (q < cnt && !picked[q] && tset[q] != lset &&
                (!pk_v || {rem[q], tab[q][0] != lbgx} >= {rem[pk_k], tab[pk_k][0] != lbgx})) begin
              pk_v = 1; pk_k = 3'(q);
            end
          if (!pk_v && any_v) begin pk_v = 1; pk_k = any_k; end
        end
      end
      if (oc == 0) begin pk_v = any_v && !picked[0] && cnt != 0; pk_k = 3'd0; end   // router's first first
      else if (!pk_v && any_v && (cnt >= 4'(TOPK) || id_empty) && PICK == 0) begin pk_v = 1; pk_k = any_k; end
    end
    wire retire = (cnt != 0) && (oc == cnt) && (&all_done_v) && id_empty;
    assign id_pop = !id_empty && cnt < 8 && !retire;
    always @(posedge hclk or negedge hrst_n)
      if (!hrst_n) begin
        cnt <= 0; oc <= 0; picked <= 0; lset <= 0; lbgx <= 0; prot <= 0;
        for (integer p = 0; p < NPC; p = p + 1) ptr[p] <= 0;
      end else begin
        if (retire) begin
          cnt <= 0; oc <= 0; picked <= 0; prot <= 0;
          for (integer p = 0; p < NPC; p = p + 1) ptr[p] <= 0;
        end else begin
          if (id_pop) begin
            tab[cnt[2:0]] <= id_q; tset[cnt[2:0]] <= set_of(id_q); cnt <= cnt + 1'b1;
            prot <= prot | (8'b1 << set_of(id_q));
          end
          if (pk_v) begin ord[oc[2:0]] <= pk_k; oc <= oc + 1'b1; picked[pk_k] <= 1'b1; lset <= tset[pk_k]; lbgx <= tab[pk_k][0]; end
          for (integer p = 0; p < NPC; p = p + 1) if (dv[p] && pc_r[p]) ptr[p] <= ptr[p] + 1'b1;
        end
      end
    // ---------------- 32 stream sequencers (hclk), tag queues and landing crossings ----------------
    wire [NPC*3-1:0] cred_ret;
    wire [NPC-1:0] l_empty, l_full, l_re; wire [NPC*259-1:0] l_q;
    reg  land_fault;
    for (genvar p = 0; p < NPC; p = p + 1) begin : pc
      wire [2:0] dk = ord[ptr[p][2:0]];
      wire [IW-1:0] did = tab[dk];
      // PCPROT (default 0): refresh protection per PC -- only the sets this PC still has to stream
      // (picked but not yet accepted by it, plus arrived unpicked experts); a set whose experts this PC
      // has finished stops being protected, so a due REFpb (or a REPICK) lands on it instead of on a
      // set that is still needed (one such REFpb stalls the PC for tRFCpb, 196 cycles).
      reg [7:0] prot_pc;
      always @* begin
        prot_pc = 8'b0;
        for (integer i = 0; i < 8; i = i + 1)
          if (4'(i) >= ptr[p] && 4'(i) < oc) prot_pc = prot_pc | (8'b1 << tset[ord[i]]);
        for (integer r = 0; r < 8; r = r + 1)
          if (r < cnt && !picked[r]) prot_pc = prot_pc | (8'b1 << tset[r]);
      end
      ot_hbm_accel_expert_stream_pc_la #(.ENABLE(1), .REF_MODE(REF_MODE), .PC(p), .CRED(1 << LAW),
        .REF_PHASE((PHASE + (p * PERIOD) / 32) % PERIOD), .NOTICE_PROT(NOTICE_PROT), .REPICK(REPICK), .RESERVE(RESERVE), .PULL(PULL), .TAILPULL(TAILPULL), .STEER(STEER), .NWIN(NWIN)) u (
        .clk(hclk), .rst_n(hrst_n), .desc_v(dv[p]), .desc_r(pc_r[p]),
        .desc_row(row_of(did)), .desc_set(set_of(did)), .desc_bgx(did[0]), .desc_n(11'(NSECT)),
        .go(1'b1), .next_posted(1'b0), .notice(notice), .prot(PCPROT != 0 ? prot_pc : prot),
        .row_v(row_v[p]), .row_prio(), .row_gnt(1'b1),
        .row_op(row_op[p*3 +: 3]), .row_bank(row_bank[p*5 +: 5]), .row_row(row_row[p*19 +: 19]),
        .col_v(col_v[p]), .col_bank(col_bank[p*5 +: 5]), .col_col(col_col[p*5 +: 5]),
        .cred_ret(cred_ret[p*3 +: 3]), .busy(pc_busy[p]), .ref_fault(pc_fault[p]));
      // tag queue: router index of each accepted descriptor, popped after its NSECT returns
      reg [2:0] tq [0:3]; reg [2:0] tq_w, tq_r; reg [JW-1:0] rcnt; reg tq_fault;
      wire tq_push = dv[p] && pc_r[p] && !retire;
      wire tq_pop  = rd_v[p] && (rcnt == JW'(NSECT - 1));
      always @(posedge hclk or negedge hrst_n)
        if (!hrst_n) begin tq_w <= 0; tq_r <= 0; rcnt <= 0; tq_fault <= 0; end
        else begin
          if (tq_push) begin tq[tq_w[1:0]] <= dk; tq_w <= tq_w + 1'b1; end
          if (rd_v[p]) rcnt <= tq_pop ? '0 : rcnt + 1'b1;
          if (tq_pop) tq_r <= tq_r + 1'b1;
          if ((tq_push && (tq_w - tq_r) == 3'd4) || (rd_v[p] && tq_w == tq_r)) tq_fault <= 1;
        end
      ot_hbm_accel_cdc_fifo #(.W(259), .AW(LAW)) u_land (
        .wclk(hclk), .wrst_n(hrst_n), .we(rd_v[p]), .wdata({tq[tq_r[1:0]], rd_data[p*256 +: 256]}),
        .full(l_full[p]), .rd_freed(cred_ret[p*3 +: 3]),
        .rclk(clk), .rrst_n(rst_n), .re(l_re[p]), .rdata(l_q[p*259 +: 259]), .empty(l_empty[p]));
    end
    wire [NPC-1:0] tqf; for (genvar p = 0; p < NPC; p = p + 1) begin : tqfo assign tqf[p] = pc[p].tq_fault; end
    always @(posedge hclk or negedge hrst_n)
      if (!hrst_n) land_fault <= 0; else if (|(rd_v & l_full) || |tqf) land_fault <= 1;
    // ---------------- landing (clk): sector -> (SM, slot, quarter), <= LAND a SM a cycle ----------------
    reg [JW-1:0] j_c [0:NPC-1];                     // PC-local sector within the current expert
    reg [2:0] e_c [0:NPC-1];                        // experts of the current task landed by this PC
    reg [15:0] t_c [0:NPC-1];                       // tasks landed by this PC since reset
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
        automatic integer kk = l_q[p*259 + 256 +: 3];
        l_sm[p] = MW'(sm); l_qt[p] = 2'(s & 3);
        l_slot[p] = SW'((t_c[p] * TOPK + kk) * cfg_lines[sm*16 +: 16] + ln);
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
        for (integer p = 0; p < NPC; p = p + 1) begin j_c[p] <= 0; e_c[p] <= 0; t_c[p] <= 0; end
        for (integer m = 0; m < NSM; m = m + 1) begin
          cons_p[m] <= 0; for (integer d = 0; d < DEPTH; d = d + 1) mask[m][d] <= 4'd0;
        end
      end else begin
        prio <= prio + 1'b1;
        for (integer m = 0; m < NSM; m = m + 1) if (take[m]) begin
          cons_p[m] <= cons_p[m] + 1'b1; mask[m][cons_p[m][SW-1:0]] <= 4'd0;
        end
        for (integer p = 0; p < NPC; p = p + 1) if (re_c[p]) begin
          if (mask[l_sm[p]][l_slot[p]][l_qt[p]]) ring_fault <= 1;
          ring[l_sm[p]][l_qt[p]][l_slot[p]] <= l_q[p*259 +: 256];
          mask[l_sm[p]][l_slot[p]][l_qt[p]] <= 1'b1;
          if (j_c[p] == JW'(NSECT - 1)) begin
            j_c[p] <= 0;
            if (e_c[p] == 3'(TOPK - 1)) begin e_c[p] <= 0; t_c[p] <= t_c[p] + 1'b1; end
            else e_c[p] <= e_c[p] + 1'b1;
          end else j_c[p] <= j_c[p] + 1'b1;
        end
      end
    reg pf_s1, pf_s2;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin pf_s1 <= 0; pf_s2 <= 0; end else begin pf_s1 <= (|pc_fault) || land_fault; pf_s2 <= pf_s1; end
    assign fault = pf_s2 || ring_fault;
  end endgenerate
endmodule
