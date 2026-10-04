`timescale 1ps/1fs
// HA4 R5a successor of ot_hbm_accel_expert_fetch_stream (ff7e3e298, sha256 af772855...): the same
// routed-expert fetch path of one HBM3E stack, with the SM staging ring mapped to compiled ASAP7
// 1R1W SRAM macros and the landing path re-timed for 1.2 GHz.  Default-off (ENABLE=0 ties every
// output to zero); nothing pinned instantiates it, and the original module is unchanged.
//
// What changed against the original (dispatch, the 32 stream sequencers and the CDC FIFOs are the
// same modules with the same parameters):
//   * notice is registered once at the element boundary (one hclk; the static lead is 300 ns).
//   * STAGING.  ring[sm][quarter][slot] (8 x 4 x 512 x 256 b of flops) becomes one bank per
//     (sm, quarter) of two ot_sram_1r1w_512x128_m4_r2c2 (64 macros).  A stack sector s = 32j + p
//     always lands in quarter s mod 4 = p mod 4, so the PCs of quarter class c (p = 4i + c) are the
//     only writers of bank (sm, c): landing grants at most ONE PC per (sm, class) per cycle (the
//     original's "<= LAND sectors per SM" becomes "<= 1 per bank", still <= 4 per SM), by a rotating
//     priority among the 8 PCs of the class (pairwise compare, no serial chain).
//   * LOOK-AHEAD LOCATIONS.  The original computed (sm, slot) per PC combinationally from j_c, k_c
//     through a 392-way lut select and a 16x16 multiply.  Here each PC holds the location of its
//     next sector in registers (cur_*) and a look-ahead counter g_j with per-SM expert bases g_kb
//     (k * lines[sm] mod DEPTH, by addition at each expert boundary), so the decision path starts
//     at registers.  Same placement: slot = k*lines[sm] + line, mod DEPTH.
//   * WRITE STAGE.  The granted sector is registered per bank and written one clk later; the mask
//     bit is set on the same edge as the macro write.
//   * RELEASE.  The macro read is synchronous with read-before-write: each SM reads the line it
//     will hold next cycle (cons_p, or cons_p+1 on a take) every cycle, and s_valid is registered
//     from the mask as it stood BEFORE that edge, so a released line was fully written at an
//     earlier edge.  s_data is the macros' rd_out.
//   Latency cost against the original: +2 clk (write register, registered read) on every line.
module ot_hbm_accel_expert_fetch_stream_sram #(
  parameter integer ENABLE = 0, REF_MODE = 1, PHASE = 0,
  parameter integer NSM = 8, NPC = 32, NSECT = 49, IW = 9, ROW_BASE = 0,
  parameter integer DEPTH = 512, MAXL = 64
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
    if (NPC % 4 != 0 || DEPTH != 512 || NSM > 256) begin : bad_params
      $error("ot_hbm_accel_expert_fetch_stream_sram: NPC must be a multiple of 4, DEPTH 512 (macro depth)");
    end
    localparam integer SW = $clog2(DEPTH);
    localparam integer MW = (NSM > 1) ? $clog2(NSM) : 1;
    localparam integer NI = NPC / 4;                       // PCs per quarter class
    localparam integer IWD = (NI > 1) ? $clog2(NI) : 1;
    localparam integer JW = $clog2(NSECT + 1);
    localparam integer PERIOD = REF_MODE ? 118 : 3808;
    // ---------------- ids: clk -> hclk ----------------
    wire id_full, id_empty; wire [IW-1:0] id_q; wire id_pop;
    ot_hbm_accel_cdc_fifo #(.W(IW), .AW(3)) u_ids (
      .wclk(clk), .wrst_n(rst_n), .we(e_valid), .wdata(e_id), .full(id_full), .rd_freed(),
      .rclk(hclk), .rrst_n(hrst_n), .re(id_pop), .rdata(id_q), .empty(id_empty));
    assign e_ready = !id_full;
    // ---------------- dispatch (hclk): one descriptor per (expert, PC), as the original ----------------
    reg [IW-1:0] tab [0:7]; reg [3:0] cnt; reg [3:0] ptr [0:NPC-1];
    reg notice_r;
    wire [NPC-1:0] pc_r, pc_busy, pc_fault, dv; wire [NPC-1:0] all_done_v;
    for (genvar p = 0; p < NPC; p = p + 1) begin : dsp
      assign dv[p] = (ptr[p] < cnt);
      assign all_done_v[p] = (ptr[p] == cnt) && !pc_busy[p];
    end
    wire retire = (cnt != 0) && (&all_done_v) && id_empty;
    assign id_pop = !id_empty && cnt < 8 && !retire;
    always @(posedge hclk or negedge hrst_n)
      if (!hrst_n) begin cnt <= 0; notice_r <= 0; for (integer p = 0; p < NPC; p = p + 1) ptr[p] <= 0; end
      else begin
        notice_r <= notice;
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
        .go(1'b1), .next_posted(1'b0), .notice(notice_r),
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
    // ---------------- look-ahead landing locations (clk) ----------------
    // cur_*: where this PC's next landed sector goes; g_j / g_kb: the sector after it.
    wire [NPC-1:0] cur_v; wire [MW-1:0] cur_sm [0:NPC-1]; wire [SW-1:0] cur_slot [0:NPC-1];
    wire [NPC-1:0] grant;
    for (genvar p = 0; p < NPC; p = p + 1) begin : loc
      reg cv; reg [MW-1:0] csm; reg [SW-1:0] cslot; reg [JW-1:0] gj; reg [NSM*SW-1:0] gkb;
      // lut entry of line L = NI*g_j + p/4 (s = NPC g_j + p): a NSECT-way select from registers
      reg [15:0] ent;
      always @* begin
        ent = 16'd0;
        for (integer jj = 0; jj < NSECT; jj = jj + 1)
          if (gj == JW'(jj)) ent = cfg_lut[(jj * NI + p / 4) * 16 +: 16];
      end
      wire [MW-1:0] n_sm = ent[8 +: MW];
      wire [SW-1:0] n_slot = gkb[n_sm * SW +: SW] + SW'(ent[7:0]);
      wire adv = grant[p] || !cv;
      reg [NSM*SW-1:0] gkb_n;
      always @* for (integer m = 0; m < NSM; m = m + 1) gkb_n[m*SW +: SW] = gkb[m*SW +: SW] + cfg_lines[m*16 +: SW];
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 1'b0; csm <= 0; cslot <= 0; gj <= 0; gkb <= '0; end
        else if (adv) begin
          cv <= 1'b1; csm <= n_sm; cslot <= n_slot;
          if (gj == JW'(NSECT - 1)) begin gj <= 0; gkb <= gkb_n; end
          else gj <= gj + 1'b1;
        end
      assign cur_v[p] = cv; assign cur_sm[p] = csm; assign cur_slot[p] = cslot;
    end
    // ---------------- landing grant: <= 1 PC per (sm, quarter class), rotating priority ----------------
    reg [IWD-1:0] rot;                                     // highest-priority index within a class
    reg [NI*NI-1:0] beats;                                 // beats[a*NI+b]: index a outranks b (for rot)
    wire [IWD-1:0] rot_n = (rot == IWD'(NI - 1)) ? '0 : rot + 1'b1;
    reg [NI*NI-1:0] beats_n;
    always @* begin
      for (integer a = 0; a < NI; a = a + 1) for (integer b = 0; b < NI; b = b + 1)
        beats_n[a*NI + b] = ((a - rot_n + NI) % NI) < ((b - rot_n + NI) % NI);
    end
    wire [NPC-1:0] req = cur_v & ~l_empty;
    for (genvar p = 0; p < NPC; p = p + 1) begin : arb
      localparam integer C = p % 4, I = p / 4;
      wire [NI-1:0] lose;
      for (genvar a = 0; a < NI; a = a + 1) begin : cmp
        if (a == I) begin : self assign lose[a] = 1'b0; end
        else begin : other
          assign lose[a] = req[4*a + C] && (cur_sm[4*a + C] == cur_sm[p]) && beats[a*NI + I];
        end
      end
      assign grant[p] = req[p] && !(|lose);
    end
    assign l_re = grant;
    // ---------------- write stage: one register per bank (sm, class) ----------------
    wire [NSM*4-1:0] w_v; wire [SW-1:0] w_a [0:NSM*4-1]; wire [255:0] w_d [0:NSM*4-1];
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin rot <= 0; beats <= '0; end
      else begin rot <= rot_n; beats <= beats_n; end
    for (genvar m = 0; m < NSM; m = m + 1) begin : wb
      for (genvar c = 0; c < 4; c = c + 1) begin : q
        // one-hot (at most one grant per bank): AND-OR select of the winner's slot and sector
        reg v; reg [SW-1:0] a; reg [255:0] d;
        always @* begin
          v = 1'b0; a = '0; d = '0;
          for (integer i = 0; i < NI; i = i + 1)
            if (grant[4*i + c] && cur_sm[4*i + c] == MW'(m)) begin
              v = 1'b1; a = a | cur_slot[4*i + c]; d = d | l_q[(4*i + c)*256 +: 256];
            end
        end
        reg v_r; reg [SW-1:0] a_r; reg [255:0] d_r;
        always @(posedge clk or negedge rst_n) if (!rst_n) v_r <= 1'b0; else v_r <= v;
        always @(posedge clk) begin a_r <= a; d_r <= d; end
        assign w_v[m*4 + c] = v_r; assign w_a[m*4 + c] = a_r; assign w_d[m*4 + c] = d_r;
      end
    end
    // ---------------- banks, mask, release (clk) ----------------
    reg [3:0] mask [0:NSM-1][0:DEPTH-1];
    reg [SW-1:0] cons_p [0:NSM-1]; reg [NSM-1:0] v_q;
    wire [NSM-1:0] take = v_q & s_ready;
    assign s_valid = v_q;
    reg ring_fault;
    for (genvar m = 0; m < NSM; m = m + 1) begin : sm
      wire [SW-1:0] cs = cons_p[m], cs1 = cons_p[m] + 1'b1;
      wire [SW-1:0] ra = take[m] ? cs1 : cs;
      for (genvar c = 0; c < 4; c = c + 1) begin : bank
        for (genvar h = 0; h < 2; h = h + 1) begin : half
          ot_sram_1r1w_512x128_m4_r2c2 u_ram (
            .clk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(s_data[m*1024 + c*256 + h*128 +: 128]),
            .w_ce_in(w_v[m*4 + c]), .w_addr_in(w_a[m*4 + c]), .wd_in(w_d[m*4 + c][h*128 +: 128]),
            .w_mask_in({128{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
        end
      end
    end
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        ring_fault <= 0; v_q <= '0;
        for (integer m = 0; m < NSM; m = m + 1) begin
          cons_p[m] <= 0; for (integer d = 0; d < DEPTH; d = d + 1) mask[m][d] <= 4'd0;
        end
      end else begin
        for (integer m = 0; m < NSM; m = m + 1) begin
          // valid for the line read at this edge, from the mask before this edge's writes
          v_q[m] <= take[m] ? (&mask[m][SW'(cons_p[m] + 1'b1)]) : (&mask[m][cons_p[m]]);
          if (take[m]) begin cons_p[m] <= cons_p[m] + 1'b1; mask[m][cons_p[m]] <= 4'd0; end
          for (integer c = 0; c < 4; c = c + 1) if (w_v[m*4 + c]) begin
            if (mask[m][w_a[m*4 + c]][c]) ring_fault <= 1;              // staging overrun
            mask[m][w_a[m*4 + c]][c] <= 1'b1;
          end
        end
      end
    reg pf_s1, pf_s2;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin pf_s1 <= 0; pf_s2 <= 0; end else begin pf_s1 <= (|pc_fault) || land_fault; pf_s2 <= pf_s1; end
    assign fault = pf_s2 || ring_fault;
  end endgenerate
endmodule
