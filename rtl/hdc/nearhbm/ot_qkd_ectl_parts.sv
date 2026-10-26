`timescale 1ns/1ps
`ifndef KVD_HEADS
`define KVD_HEADS 2
`endif
`ifndef KVD_Q_FP32
`define KVD_Q_FP32 0
`endif
`ifndef KVD_QK_ONLY
`define KVD_QK_ONLY 0
`endif
// ---------------------------------------------------------------------------------------------------------------------
// q13-kvleaves 2026-10-13: the near-HBM row-engine control cell qkd_ectl as THREE die leaves (A | B | C, west to east).
// The one-tile form (qkd_ectl_slot-q13r3: 648 x 129.6 um, 14,806 sinks on one root, TritonCTS insertion 357..538 ps /
// spread 181, declared spine 616..654 ps; CTS hold repair stalled on 8,710 endpoints) cannot give a 648-um strip one
// short clock.  Split by the SRAM row (2 + 2 + 0 macros: 254.88 + 254.88 + 138.24 um), each leaf with its own clock root:
//   A (W face)  row response pin flops, row FIFO slice [511:0] (2 SRAMs), its S1 / S1b copies, the request relay (rq)
//   B (middle)  row FIFO slice [1023:512] (2 SRAMs), its S1 / S1b copies, the control / decision words t_c / t_lt
//   C (E face)  E-face pin stages, the q beat path, the e FIFO (its 128 x 64 level in registers: no macro), scores /
//               running max / tags, node-beat tags
// No timing loop crosses a seam: every leaf carries a COPY OF THE CONTROL (the same RTL below; synthesis prunes what a
// leaf does not drive) and a control-only copy of the FIFOs it does not hold.  The copies are identical machines because
// every die input reaches each of them the same number of flops after its pin (three: pin flop in the leaf at the
// face, pin flop of each seam crossed, local flops to make up three):
//   start, exp_done, nb_cr   1 -> 3 flops (+2 cycles)       q beat   2 -> 3 (+1)       row response   2 -> 3 (+1)
//   cyc8 is re-based (+3), T is static.  Everything else is the one-tile ot_qwen_nearhbm_ectl_h (KVD_ECTL_SLOT) cycle for
//   cycle: tb_qkd_ectl3 checks every output against it with the inputs delayed as above.
// S / E (stack, engine) are STRAP pins (cfg_s, cfg_e): one hardened set serves the 32 slots.
// Reset: each leaf synchronises rst_n itself; the copies agree from the first start (>= 64 cycles after reset).
// Mutants (bench only): KVD_ECTL3_MUT_A / _B / _C.
// ---------------------------------------------------------------------------------------------------------------------

// control-only copy of ot_nhb_fifo_rows2_h (its SRAM level + D1-row flop level): the same counters, no data
module ot_qkd_fifo2_sh #(parameter integer D = 128, parameter integer D1 = 8) (
    input  wire clk,
    input  wire rst_n,
    input  wire push,
    input  wire pop,
    output wire nonempty
);
    reg  [7:0] scnt;
    reg        rd_v;
    reg  [3:0] l1_pend;
`ifdef KVD_RMUT
    wire       to_l1   = push && !rd_v && l1_pend < D1;
`else
    wire       to_l1   = push && scnt == 8'd0 && !rd_v && l1_pend < D1;
`endif
    wire       to_sram = push && !to_l1;
    wire       rd      = (scnt != 8'd0) && (l1_pend + (to_l1 ? 1 : 0) < D1);
    wire       l1_push = to_l1 || rd_v;
    reg        pr;                                         // the flop level's count (ot_nhb_fifo_rows_r_h)
    reg  [$clog2(D1+1)-1:0] l1c;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin scnt <= 0; rd_v <= 1'b0; l1_pend <= 0; pr <= 1'b0; l1c <= 0; end
        else begin
            scnt <= scnt + (to_sram ? 8'd1 : 8'd0) - (rd ? 8'd1 : 8'd0);
            rd_v <= rd;
            l1_pend <= l1_pend + ((to_l1 || rd) ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0);
            pr <= l1_push;
            l1c <= l1c + (pr ? 1 : 0) - (pop ? 1 : 0);
        end
    end
    assign nonempty = (l1c != 0);
endmodule

module ot_qkd_ectl_part #(
    // Static native QK profile: compiler reserves the return and consume edges.
    // Ages count edges after the control-copy start edge (age register is zero there).
    parameter integer STATIC_QK = 0,
    parameter integer QK_ISSUE_AGE = 34,
    parameter integer ROW_RETURN_LAT = 9, // rq_valid generator -> rsp_valid at this control copy
    parameter integer HEADS = `KVD_HEADS,
    parameter integer Q_FP32 = `KVD_Q_FP32,
    parameter integer PART = 1,          // 1 = A (W leaf), 2 = B (middle leaf), 3 = C (E leaf)
    parameter integer HD = 128,
    parameter integer R = 8,             // row engines in the stack
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 128,          // row / e FIFO depth = outstanding-request credit
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer LFB = 4,
    parameter integer ND = 1,
    parameter integer HXK = 0,
    parameter integer HXN = 0,
    parameter integer RWD = (PART == 3) ? 32 : 512,    // row bits held here (C holds none: a pruned dummy slice)
    parameter integer XB2 = 0            // B (PART 2) only: x_i already carries the stage-2 word (direct seams: C's x2), so
                                         // B's stage 3 is its own pin flop x1 (kvsys-elements r3)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [1:0]           cfg_s,        // straps: stack index, engine (were the parameters S / E)
    input  wire [2:0]           cfg_e,
    // E face (leaf C)
    input  wire                 start_in,
    input  wire [13:0]          T_in,
    input  wire [2:0]           cyc8_in,
    input  wire                 q_valid_in,
    input  wire [5:0]           q_beat_in,
    input  wire [511:0]         q_data_in,
    input  wire [31:0]          exp_done,
    input  wire                 nb_cr,
    input  wire [63:0]          er_data,
    output wire                 er_valid,
    output wire [11:0]          er_addr,
    output reg                  sc_valid,
    output reg  [11:0]          sc_addr,
    output reg  [127:0]         sc_data,
    output reg  [2*4*32-1:0]    lmax,
    output reg  [1:0]           lmax_any,
    output reg                  nb_valid,
    output reg  [3:0]           nb_beat,
    output reg                  nb_g,
    output reg  [3:0]           nb_gam,
    output reg                  k_done,
    output reg                  v_done,
    output reg                  fault,
    output reg                  ev_k_first,
    output reg                  ev_v_first,
    // W face (leaf A)
    output wire                 req_epoch,          // alternating layer identity at the request pin
    output wire                 req_valid,
    output wire                 req_v,
    output wire                 req_g,
    output wire [12:0]          req_t,
    input  wire                 rsp_valid_in,
    input  wire [HD*8-1:0]      rsp_data_in,
    // seams: the E-face control word west (C pin flops -> B pin flops -> A pin flops), the row response east
    input  wire [51:0]          x_i,
    output wire [51:0]          x_o,
    output wire [51:0]          x2_o,        // optional stage-2 launch: direct C -> A seam, existing x2 state
    input  wire                 rsv_i,        // rsp_valid: A stage 2 -> B pin (B) | B feed-through -> C pin (C)
    output wire                 rsv_o,        // A: stage 2 (E-face flop); B: the feed-through flop (to C)
    input  wire                 rvm_i,        // B: A's second capture flop of rsp_valid (stage 1) -> the feed-through
    output wire                 rvm_o,        // A: second capture flop of rsp_valid (stage 1, mid-leaf: not a pin flop)
    input  wire [511:0]         rsd_i,
    output wire [511:0]         rsd_o,        // A: E-face flops (stage 2) of row bits [1023:512]
    // head-tile faces (S: t0, N: t1)
    output wire [3:0]           t0_c,
    output wire [3:0]           t1_c,
    output wire [RWD-1:0]       t0_row,
    output wire [RWD-1:0]       t1_row,
    output wire [31:0]          t0_e,
    output wire [31:0]          t1_e,
    output wire [11:0]          t0_lt,
    output wire [11:0]          t1_lt,
    output wire                 t0_qv,
    output wire                 t1_qv,
    output wire [5:0]           t0_qb,
    output wire [5:0]           t1_qb,
    output wire [511:0]         t0_qd,
    output wire [511:0]         t1_qd,
    input  wire [2*32-1:0]      ts0_sc,
    input  wire [2*32-1:0]      ts1_sc,
    input  wire [1:0]           ts0_sf,
    input  wire [1:0]           ts1_sf,
    input  wire [1:0]           ts0_gf,
    input  wire [1:0]           ts1_gf
);
    localparam integer RLO = (PART == 2) ? 512 : 0;      // first row bit of this leaf's slice
    reg  [1:0] s_q;                                      // strap pin flops (static)
    reg  [2:0] e_q;
    always @(posedge clk) begin s_q <= cfg_s; e_q <= cfg_e; end
    wire [1:0]  S  = s_q;
    wire [11:0] E  = {9'd0, e_q};
    localparam integer LN = 4 * HD;
    localparam integer LV = $clog2(HD);
    localparam integer KDRAIN = (LV - 1) * ADD_LAT + 1;   // a K row's tree leaves the lane adders
    localparam integer KDEPTH = 4 + LV * ADD_LAT + MUL_LAT + HXK;     // product, lane adder (level 1), levels 2..LV, scale
    wire [1:0]         SB = S;

    localparam integer LANE_D = 4;                         // issue -> lane inputs (S1, S1b, S2 at the tile pin, S3)
    localparam integer PLAT = 4;
    localparam integer GPH = HD / 16;                      // 16-lane groups per head
    localparam integer NG = 4 * GPH;
    // ---- reset tree: root, central control leaf, halves, heads, groups -----------------------------------------------
    // kvsys-elements r2 2026-10-14 (native pin audit, qkd_ectl_b_tp8: rst_n capture 307.0 ps > 190): ONE synchroniser at
    // the rst_n pin (ot_rst_relay 2 + 1); every reset leaf and pin-register block below takes rp, not the raw pin.
    // Release is 3 cycles later in all three leaves alike (the copies still agree from the first start).
    wire [0:0] rp_v;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rpin (.clk(clk), .rst_n_in(rst_n), .rst_n(rp_v));
    wire rp = rp_v[0];
    wire r0, rc;
    wire [1:0] rhalf;
    wire [3:0] rhead;
    wire [NG-1:0] rgrp;
    (* keep_hierarchy *) ot_nhb_rleaf_h u_r0 (.clk(clk), .arst_n(rp), .d(1'b1), .q(r0));
    (* keep_hierarchy *) ot_nhb_rleaf_h u_rc (.clk(clk), .arst_n(rp), .d(r0), .q(rc));
    wire rsc;                                                         // the score / running-max block's own leaf
    (* keep_hierarchy *) ot_nhb_rleaf_h u_rsc (.clk(clk), .arst_n(rp), .d(r0), .q(rsc));
    genvar gr;
    generate
        for (gr = 0; gr < 2; gr = gr + 1) begin : g_rhalf
            (* keep_hierarchy *) ot_nhb_rleaf_h u_l (.clk(clk), .arst_n(rp), .d(r0), .q(rhalf[gr]));
        end
        for (gr = 0; gr < 4; gr = gr + 1) begin : g_rhead
            (* keep_hierarchy *) ot_nhb_rleaf_h u_l (.clk(clk), .arst_n(rp), .d(rhalf[gr / 2]), .q(rhead[gr]));
        end
        for (gr = 0; gr < NG; gr = gr + 1) begin : g_rgrp
            (* keep_hierarchy *) ot_nhb_rleaf_h u_l (.clk(clk), .arst_n(rp), .d(rhead[gr / GPH]), .q(rgrp[gr]));
        end
    endgenerate
    // ---- registered boundary: every control copy sees each die input THREE flops after its pin ----------------------------
    // E face (leaf C): {q_valid, nb_cr, exp_done 32, cyc8 3, T 14, start}: C pin -> C +2 | C pin -> B pin -> B +1 | -> A pin
    // W face (leaf A): rsp_valid (+ the row word for the leaves that hold a slice): A pin -> A +2 | A pin -> A E face -> B pin | A mid -> B mid -> C pin
    localparam integer XW = 52;
    reg  [XW-1:0] x1, x2, x3;
    wire [XW-1:0] x_d = (PART == 3) ? {q_valid_in, nb_cr, exp_done, cyc8_in, T_in, start_in} : x_i;
    always @(posedge clk or negedge rp)
        if (!rp) begin x1 <= {XW{1'b0}}; x2 <= {XW{1'b0}}; x3 <= {XW{1'b0}}; end
        else begin x1 <= x_d; x2 <= x1; x3 <= x2; end
`ifdef KVD_ECTL3_MUT_B
    wire [XW-1:0] xv = (PART == 3) ? x3 : (PART == 2 && XB2 != 0) ? x_i : x1;   // mutant: leaf B's control one cycle early
`else
    wire [XW-1:0] xv = (PART == 3) ? x3 : (PART == 2) ? ((XB2 != 0) ? x1 : x2) : x1;
`endif
    assign x_o = x1;
    assign x2_o = x2;
    wire        start      = xv[0];
    wire [13:0] T          = xv[14:1];
    wire [2:0]  cyc8_r     = xv[17:15];
    wire [31:0] exp_done_r = xv[49:18];
    wire        ocr_q      = xv[50];
    wire        qv_r       = xv[51];
    wire [2:0]  cyc8 = cyc8_r + 3'd3;                     // the free-running counter's current value
    // rsp_valid: A rv1 (W pin) -> rv2 (E face, to B) -> rv3 | B rv1 (pin, from A rv2) | C rv1 (pin, from B's feed-through)
    // A's second capture flop rvm and B's feed-through bf (one flop each, placed mid-leaf by the placer: 128 um a side)
    // carry stage 1 / stage 2 of the valid to C, so that C's pin flop is the third as well.
    reg             rv1, rv2, rv3, rvm, bf;
    reg  [HD*8-1:0] rsp_data_p;                           // A: W-face pin flops of the whole word
    reg  [511:0]    rse;                                  // A: E-face flops of B's half (stage 2)
    reg  [RWD-1:0]  rd2, rd3;
    wire            rv_d = (PART == 1) ? rsp_valid_in : rsv_i;
    always @(posedge clk or negedge rp)
        if (!rp) begin rv1 <= 1'b0; rv2 <= 1'b0; rv3 <= 1'b0; rvm <= 1'b0; bf <= 1'b0; end
        else begin rv1 <= rv_d; rv2 <= rv1; rv3 <= rv2; rvm <= rsp_valid_in; bf <= rvm_i; end
    wire            rsp_valid = (PART == 1) ? rv3 : rv1;
    assign rsv_o = (PART == 1) ? rv2 : bf;
    assign rvm_o = rvm;
    assign rsd_o = rse;
    always @(posedge clk) begin
        rsp_data_p <= rsp_data_in;
        rse <= rsp_data_p[HD*8-1 -: 512];
        rd2 <= (PART == 1) ? rsp_data_p[RLO +: RWD] : rsd_i[RWD-1:0];
        rd3 <= rd2;
    end
`ifdef KVD_ECTL3_MUT_A
    wire [RWD-1:0]  rsp_data = (PART == 1) ? rd2 : rd2;   // mutant: leaf A's row slice one cycle early against its push
`else
    wire [RWD-1:0]  rsp_data = (PART == 1) ? rd3 : rd2;   // third flop after the W pin: A local, B its pin flop
`endif
    reg             er_valid_g, er_valid_o;     // generator register, E-face pin flop
    reg  [11:0]     er_addr_g, er_addr_o;
    reg  [63:0]     er_data_p;                  // E-face pin flops of the e word
    reg  [1:0]      er_pd;                      // the push follows the word through both pin stages
    assign er_valid = er_valid_o;
    assign er_addr = er_addr_o;
    always @(posedge clk or negedge rp)
        if (!rp) begin er_valid_o <= 1'b0; er_pd <= 2'b00; end
        else begin er_valid_o <= er_valid_g; er_pd <= {er_pd[0], er_valid_g}; end
    always @(posedge clk) begin er_addr_o <= er_addr_g; er_data_p <= er_data; end
    // the q beat (leaf C): pin flops, mid stage, third stage (with qv_r of the control word), then the S1b copies
    localparam integer NQB = 4 * HEADS * HD * (Q_FP32 ? 32 : 16) / 512;
    reg  [5:0]        qb_p, qb_m, qb_r;
    reg  [511:0]      qd_p, qd_m, qd_r;
    reg  [6:0]        qcnt;
    always @(posedge clk) begin
        qb_p <= q_beat_in; qd_p <= q_data_in; qb_m <= qb_p; qd_m <= qd_p; qb_r <= qb_m;
`ifdef KVD_ECTL3_MUT_C
        qd_r <= qd_p;                                     // mutant: leaf C's q word one cycle early against its beat valid
`else
        qd_r <= qd_m;
`endif
    end
    always @(posedge clk or negedge rp)
        if (!rp) qcnt <= 7'd0;
        else if (start) qcnt <= 7'd0;
        else if (qv_r) qcnt <= qcnt + 7'd1;
    wire q_ready = (qcnt == NQB);
    reg [15:0] schedule_age;
    reg schedule_active;
    always @(posedge clk or negedge rc)
        if (!rc) begin schedule_age <= 0; schedule_active <= 0; end
        else if (start) begin schedule_age <= 0; schedule_active <= 1; end
        else if (schedule_active && schedule_age != 16'hffff) schedule_age <= schedule_age + 1'b1;
    initial begin
        if (STATIC_QK && (HEADS != 1 || QK_ISSUE_AGE < 2 || ROW_RETURN_LAT < 1 || DQ != 128))
            $fatal(1, "invalid static QK profile");
    end

    // ---- stack geometry ----------------------------------------------------------------------------------------------
    wire [13:0] base_s = {5'd0, S, 7'd0};
    wire        any_s = (T > base_s);
    wire [13:0] rem = T - base_s;                                        // positions at or after this stack's base
    wire [4:0]  gmax_c = !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));   // nonempty groups
    reg  [4:0]  gmax;
    // positions in this stack: 128 per full 512 round, plus the partial round's share
    wire [13:0] tail = {5'd0, T[8:0]};
    wire [13:0] part = (tail > base_s) ? ((tail - base_s > 14'd128) ? 14'd128 : (tail - base_s)) : 14'd0;
    wire [11:0] n_s_c = {T[13:9], 7'd0} + part[11:0];
    reg  [11:0] n_s;
    always @(posedge clk) begin n_s <= n_s_c; gmax <= gmax_c; end
    function automatic [13:0] tpos(input [3:0] k, input [6:0] r);
        tpos = {1'b0, k, SB, r};
    endfunction
    function automatic [3:0] klast(input [3:0] gam);     // last round of residue group gam (group nonempty)
        reg [13:0] b;
        begin
            b = base_s + {7'd0, gam, 3'd0};
            klast = (T - 14'd1 - b) >> 9;
        end
    endfunction

    // ---- request generator -------------------------------------------------------------------------------------------
    reg        rq_valid, rq_v, rq_g;                    // the generator's request (relayed to the W-face pin flops below)
    reg [12:0] rq_t;
    reg        rg_run, rg_vph, rg_g;
    reg [11:0] rg_idx;                                  // K: local index
    reg [4:0]  rg_gam;
    reg [3:0]  rg_k;
    reg [2:0]  rg_j;
    reg [$clog2(DQ+1)-1:0] credit_used;
    wire       consume;                                 // a row popped this cycle
`ifdef KVD_VMUT
    wire [13:0] rg_vt = tpos(klast(rg_gam[3:0]) - rg_k, {rg_gam[3:0], rg_j});
`else
    wire [13:0] rg_vt = tpos(rg_k, {rg_gam[3:0], rg_j});
`endif
    wire       kord = (n_s > 12'd1024);                  // stream order for the K pass (see above)
    wire [11:0] rg_pidx = kord ? {rg_idx[11], rg_idx[9:6], rg_idx[10], rg_idx[5:0]} : rg_idx;
    wire       rg_klim = kord ? (rg_idx < 12'd2048) : (rg_idx < n_s);
    wire       rg_k_ok = rg_run && !rg_vph && rg_klim && (rg_pidx < n_s);
    wire       rg_v_valid_row = (rg_vt < T);
    wire       rg_v_gate = exp_done_r[{rg_g, rg_gam[3:0]}];
    wire       has_credit = (credit_used < DQ);
    reg        issue;
    always @(posedge clk or negedge rc) begin
        if (!rc) begin
            rg_run <= 1'b0; rg_vph <= 1'b0; rg_g <= 1'b0; rg_idx <= 0; rg_gam <= 0; rg_k <= 0; rg_j <= 0;
            rq_valid <= 1'b0; er_valid_g <= 1'b0; credit_used <= 0;
        end else begin
            rq_valid <= 1'b0; er_valid_g <= 1'b0;
            issue = 1'b0;
            if (start) begin
                rg_run <= 1'b1; rg_vph <= 1'b0; rg_g <= 1'b0; rg_idx <= E; rg_gam <= E; rg_k <= 0; rg_j <= 0;
            end else if (rg_run && !rg_vph) begin
                if (rg_klim) begin
                    if (rg_pidx >= n_s) rg_idx <= rg_idx + R;             // not a position: skip
                    else if (STATIC_QK || has_credit) begin
                        issue = 1'b1;
                        rq_valid <= 1'b1; rq_v <= 1'b0; rq_g <= rg_g;
                        rq_t <= tpos(rg_pidx[10:7], rg_pidx[6:0]);
                        rg_idx <= rg_idx + R;
                    end
                end else if (HEADS == 2 && !rg_g) begin
                    rg_g <= 1'b1; rg_idx <= E;
                end else begin
                    if (STATIC_QK || `KVD_QK_ONLY) rg_run <= 1'b0;
                    else begin rg_vph <= 1'b1; rg_g <= 1'b0; rg_gam <= E; rg_k <= 0; rg_j <= 0; end
                end
            end else if (rg_run && rg_vph) begin
                if (rg_gam < gmax) begin
                    if (!rg_v_valid_row || (rg_v_gate && has_credit)) begin
                        if (rg_v_valid_row) begin
                            issue = 1'b1;
                            rq_valid <= 1'b1; rq_v <= 1'b1; rq_g <= rg_g; rq_t <= rg_vt[12:0];
                            er_valid_g <= 1'b1; er_addr_g <= {rg_g, rg_k, rg_gam[3:0], rg_j};
                        end
                        rg_j <= rg_j + 3'd1;
                        if (rg_j == 3'd7) begin
                            if (rg_k == klast(rg_gam[3:0])) begin
                                rg_k <= 0;
                                rg_gam <= rg_gam + R;
                            end else rg_k <= rg_k + 4'd1;
                        end
                    end
                end else if (HEADS == 2 && !rg_g) begin
                    rg_g <= 1'b1; rg_gam <= E; rg_k <= 0; rg_j <= 0;
                end else rg_run <= 1'b0;
            end
            credit_used <= credit_used + (issue ? 1 : 0) - (consume ? 1 : 0);
        end
    end

    // ---- request relay: RQD registered stages from the generator to the W-face pin flops (the last stage) -------------
    localparam integer RQD = 2;
    wire [RQD:0]        rqv_s;
    wire [15*(RQD+1)-1:0] rqd_s;
    assign rqv_s[0] = rq_valid;
    assign rqd_s[14:0] = {rq_v, rq_g, rq_t};
    genvar gq;
    generate for (gq = 0; gq < RQD; gq = gq + 1) begin : g_rq
        (* keep_hierarchy *) ot_nhb_repr_h #(.W(1)) u_v (.clk(clk), .rst_n(rc), .d(rqv_s[gq]), .q(rqv_s[gq + 1]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(15)) u_d (.clk(clk), .d(rqd_s[15*gq +: 15]), .q(rqd_s[15*(gq + 1) +: 15]));
    end endgenerate
    // First start after reset is layer zero (even); NL=36 preserves parity at the token wrap.
    reg layer_epoch;
    always @(posedge clk or negedge rc)
        if (!rc) layer_epoch <= 1'b1;
        else if (start) layer_epoch <= ~layer_epoch;
    wire [RQD:0] epoch_s;
    assign epoch_s[0] = layer_epoch;
    for (genvar ep = 0; ep < RQD; ep = ep + 1) begin : g_epoch
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(1)) u_ep (.clk(clk), .d(epoch_s[ep]), .q(epoch_s[ep+1]));
    end
    assign req_epoch = epoch_s[RQD];
    assign req_valid = rqv_s[RQD];
    assign {req_v, req_g, req_t} = rqd_s[15*RQD +: 15];

    reg [ROW_RETURN_LAT-1:0] return_slots;
    always @(posedge clk or negedge rc)
        if (!rc) return_slots <= 0;
        else if (start) return_slots <= 0;
        else return_slots <= (return_slots << 1) | rq_valid;
    wire row_slot = return_slots[ROW_RETURN_LAT-1];
    wire ring_fault;
    // ---- row and e FIFOs ---------------------------------------------------------------------------------------------
    // c_started / c_fin (K-pass state, below) are declared HERE, before g_static_rows reads them: used before their
    // declaration they were implicit 1-bit nets, which yosys-slang (the synthesis frontend) leaves undriven, so the
    // synthesised static row ring never saw read_slot (LEC lint 10-25: -Wimplicit-net at this read_slot line).
    reg             c_started, c_fin;
    wire [RWD-1:0]  row;
    wire            row_ne;
    reg             er_pend;
    wire [63:0]     e_word;
    wire            e_ne;
    wire            pop_e;
    always @(posedge clk or negedge rc) if (!rc) er_pend <= 1'b0; else er_pend <= er_pd[1];
    // the row FIFO is sliced by word bits (its control does not depend on the data): leaves A / B hold a 512-bit slice
    // (2 SRAM macros each), leaf C a control-only copy; the e FIFO is whole in leaf C, control-only in A / B
    generate if (STATIC_QK) begin : g_static_rows
        // All copies advance the same reserved pointers, even on a missing response.
        ot_qkd_static_row_ring #(.W(RWD), .DATA(PART != 3)) u_rows (
            .clk(clk), .rst_n(rc), .clear(start), .write_slot(row_slot), .write_valid(rsp_valid),
            .din(rsp_data), .read_slot(c_started && !c_fin && schedule_age >= QK_ISSUE_AGE-2),
            .consume_slot(consume), .dout(row), .nonempty(row_ne), .fault(ring_fault));
        assign e_word = 64'd0;
        assign e_ne = 1'b0;
    end else if (PART != 3) begin : g_rows2
        assign ring_fault = 1'b0;
        ot_nhb_fifo_rows2_h #(.W(RWD), .D(DQ), .D1(4)) u_rows (.clk(clk), .rst_n(rc), .push(rsp_valid), .din(rsp_data),
                                                 .pop(consume), .dout(row), .nonempty(row_ne), .count());
        ot_qkd_fifo2_sh #(.D(DQ), .D1(4)) u_e (.clk(clk), .rst_n(rc), .push(er_pend), .pop(pop_e), .nonempty(e_ne));
        assign e_word = 64'd0;
    end else begin : g_rowsh
        assign ring_fault = 1'b0;
        ot_qkd_fifo2_sh #(.D(DQ), .D1(4)) u_rows (.clk(clk), .rst_n(rc), .push(rsp_valid), .pop(consume), .nonempty(row_ne));
        assign row = {RWD{1'b0}};
        ot_qkd_efifo2 #(.D1(4)) u_e (.clk(clk), .rst_n(rc), .push(er_pend), .din(er_data_p), .pop(pop_e), .dout(e_word),
                                     .nonempty(e_ne));
    end endgenerate

    // ---- consumption: K pass -----------------------------------------------------------------------------------------
    reg        c_vph, c_g;
    reg [11:0] c_idx;
    reg [4:0]  c_gam;
    reg [3:0]  c_k;
    reg [2:0]  c_j;
    reg [7:0]  pend;                                    // slot holds a finished chunk (blocks the slot)
    reg [7:0]  arm;                                     // ... and its final value has reached the loop output
    reg [7:0]  pend_g;
    reg [3:0]  pend_gam [0:7];
    wire [11:0] c_pidx = kord ? {c_idx[11], c_idx[9:6], c_idx[10], c_idx[5:0]} : c_idx;
    wire       c_klim = kord ? (c_idx < 12'd2048) : (c_idx < n_s);
    wire       k_issue = c_started && !c_vph && !c_fin && c_klim && (c_pidx < n_s) && (STATIC_QK ? (schedule_age >= QK_ISSUE_AGE-1) : (row_ne && q_ready));
    // V pass
`ifdef KVD_VMUT
    wire [3:0]  c_kk = klast(c_gam[3:0]) - c_k;              // MUTANT: the V pass k order reversed (P.V sum reordered)
`else
    wire [3:0]  c_kk = c_k;
`endif
    wire [13:0] c_vt = tpos(c_kk, {c_gam[3:0], c_j});
    wire        c_vrow = (c_vt < T);
    reg  [7:0]  kdrain;                                 // cycles since the last K issue, saturating
    wire        v_here = c_started && c_vph && !c_fin && (c_gam < gmax) && (c_j == cyc8) && (kdrain >= KDRAIN);
    // The loop value of slot s is at the pad output fb when cyc8 = s + 4 (product LAT 4 + adder LAT + pad = 12 cycles
    // after the issue at slot s's turn).  A slot's last issue sets pend; one offer turn later (arm) the value in fb is
    // final, and it is offered to the tree each turn until taken.  The slot takes no new chain while pend is set.
    wire [2:0]  os = cyc8 - 3'd4 - LANE_D;
    wire        offer = pend[os] && arm[os];
    wire        take;                                   // re-cut H: the local tree's decision (below)
    wire        slot_ok = (c_k != 4'd0) || !pend[cyc8] || (take && (os == cyc8));
    wire        data_ok = !c_vrow || (row_ne && e_ne);
    wire        v_issue = v_here && slot_ok && data_ok;
    wire        v_pop = v_issue && c_vrow;
    assign consume = k_issue || v_pop;
    assign pop_e = v_pop;
    wire        v_last_k = (c_k == klast(c_gam[3:0]));

    always @(posedge clk or negedge rc) begin
        if (!rc) kdrain <= 8'd255;
        else if (k_issue) kdrain <= 8'd0;
        else if (kdrain != 8'd255) kdrain <= kdrain + 8'd1;
    end
    always @(posedge clk or negedge rc) begin
        if (!rc) begin
            c_started <= 1'b0; c_vph <= 1'b0; c_g <= 1'b0; c_fin <= 1'b0; c_idx <= 0; c_gam <= 0; c_k <= 0; c_j <= 0;
            pend <= 8'd0; arm <= 8'd0; pend_g <= 8'd0; k_done <= 1'b0; v_done <= 1'b0; ev_k_first <= 1'b0; ev_v_first <= 1'b0;
        end else begin
            ev_k_first <= 1'b0; ev_v_first <= 1'b0;
            if (start) begin
                c_started <= 1'b1; c_vph <= 1'b0; c_g <= 1'b0; c_fin <= 1'b0; c_idx <= E; c_gam <= E; c_k <= 0;
                c_j <= 0; pend <= 8'd0; arm <= 8'd0; k_done <= 1'b0; v_done <= 1'b0;
            end else if (c_started && !c_fin) begin
                if (!c_vph) begin
                    if (c_klim) begin
                        if (c_pidx >= n_s) c_idx <= c_idx + R;            // not a position: skip
                        else if (k_issue) begin
                            c_idx <= c_idx + R;
                            if (c_idx == E && !c_g) ev_k_first <= 1'b1;
                        end
                    end else if (HEADS == 2 && !c_g) begin
                        c_g <= 1'b1; c_idx <= E;
                    end else begin
                        k_done <= 1'b1;
                        if (STATIC_QK || `KVD_QK_ONLY) c_fin <= 1'b1;
                        else begin c_vph <= 1'b1; c_g <= 1'b0; c_gam <= E; c_k <= 0; c_j <= 0; end
                    end
                end else begin
                    if (c_gam < gmax) begin
                        if (v_issue) begin
                            if (c_k == 0 && c_j == 0 && c_gam == E && !c_g) ev_v_first <= 1'b1;
                            c_j <= c_j + 3'd1;
                            if (c_j == 3'd7) begin
                                if (v_last_k) begin c_k <= 0; c_gam <= c_gam + R; end
                                else c_k <= c_k + 4'd1;
                            end
                        end
                    end else if (HEADS == 2 && !c_g) begin
                        c_g <= 1'b1; c_gam <= E; c_k <= 0; c_j <= 0;
                    end else begin
                        c_fin <= 1'b1; v_done <= 1'b1;
                    end
                end
            end
            // pending leaves: set by the last-round issue, armed one offer turn later, cleared when the tree takes it
            if (pend[os] && !arm[os]) arm[os] <= 1'b1;
            if (take) begin pend[os] <= 1'b0; arm[os] <= 1'b0; end
            if (v_issue && v_last_k) begin
                pend[cyc8] <= 1'b1; arm[cyc8] <= 1'b0; pend_g[cyc8] <= c_g; pend_gam[cyc8] <= c_gam[3:0];
            end
        end
    end

    // ---- re-cut H: S1 (control, row, e, decision word) and its two S1b copies, one per head-tile pair ---------------
    localparam integer LTW = 12;
    reg  [3:0]       c1;
    reg  [RWD-1:0]   row1;
    reg  [63:0]      e1;
    reg  [LTW-1:0]   lt1;
    wire [LTW-1:0]   ltw;
    always @(posedge clk or negedge rc)
        if (!rc) begin c1[3:1] <= 3'd0; lt1 <= {LTW{1'b0}}; end
        else begin c1[3:1] <= {k_issue, v_issue && c_vrow, v_issue && (c_k == 4'd0)}; lt1 <= ltw; end
    always @(posedge clk) begin c1[0] <= c_g; row1 <= row; e1 <= e_word; end
    wire [2*4-1:0]    t_c;
    wire [2*RWD-1:0]  t_row;
    wire [2*32-1:0]   t_e;
    wire [2*12-1:0]   t_lt;
    wire [1:0]        t_qv;
    wire [2*6-1:0]    t_qb;
    wire [2*512-1:0]  t_qd;
    // the returns enter at the W end of the S / N faces, the scores leave on the E face: pin stage + mid relay
    wire [135:0]      ts_p, ts_m;
    (* keep_hierarchy *) ot_nhb_rep_h #(.W(68)) u_tsp0 (.clk(clk), .d({ts0_gf, ts0_sf, ts0_sc}), .q(ts_p[67:0]));
    (* keep_hierarchy *) ot_nhb_rep_h #(.W(68)) u_tsp1 (.clk(clk), .d({ts1_gf, ts1_sf, ts1_sc}), .q(ts_p[135:68]));
    (* keep_hierarchy *) ot_nhb_rep_h #(.W(136)) u_tsm (.clk(clk), .d(ts_p), .q(ts_m));
    wire [4*32-1:0]   t_sc = {ts_m[68 +: 64], ts_m[0 +: 64]};
    wire [3:0]        t_sf = {ts_m[132 +: 2], ts_m[64 +: 2]};
    wire [3:0]        t_gf = {ts_m[134 +: 2], ts_m[66 +: 2]};
    assign {t1_c, t0_c} = t_c;
    assign {t1_row, t0_row} = t_row;
    assign {t1_e, t0_e} = t_e;
    assign {t1_lt, t0_lt} = t_lt;
    assign {t1_qv, t0_qv} = t_qv;
    assign {t1_qb, t0_qb} = t_qb;
    assign {t1_qd, t0_qd} = t_qd;
    genvar gg, h;
    generate for (gg = 0; gg < 2; gg = gg + 1) begin : g_s1b
        (* keep_hierarchy *) ot_nhb_repr_h #(.W(3)) u_c (.clk(clk), .rst_n(rhalf[gg]), .d(c1[3:1]), .q(t_c[4*gg+1 +: 3]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(1)) u_g (.clk(clk), .d(c1[0]), .q(t_c[4*gg]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(RWD)) u_r (.clk(clk), .d(row1), .q(t_row[RWD*gg +: RWD]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(32)) u_e (.clk(clk), .d(e1[32*gg +: 32]), .q(t_e[32*gg +: 32]));
        (* keep_hierarchy *) ot_nhb_repr_h #(.W(LTW)) u_t (.clk(clk), .rst_n(rhalf[gg]), .d(lt1), .q(t_lt[LTW*gg +: LTW]));
        (* keep_hierarchy *) ot_nhb_repr_h #(.W(1)) u_qv (.clk(clk), .rst_n(rhalf[gg]), .d(qv_r), .q(t_qv[gg]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(6 + 512)) u_qd (.clk(clk), .d({qb_r, qd_r}), .q({t_qb[6*gg +: 6], t_qd[512*gg +: 512]}));
    end endgenerate
    // ---- re-cut H: the P.V tree's levels 1-3 -- the DECISIONS here, the data in the head tiles' lanes ---------------------
    // The decision logic is re-cut D's, term for term (leaves in slot order, a pending left node per level, a completing
    // pair always issues, a colliding leaf waits in its loop); the lanes execute it 8 edges later (the header).
    localparam integer NLL = 3;
    reg  [2:0]       lt_rho;
    reg  [NLL-1:0]   LPv;
    reg  [3:0]       lt_infl;
    reg              lt_g;
    reg  [3:0]       lt_gam;
    reg              lt_fault;
    wire [2:0]       lt_tag;
    wire             lt_arr_v = lt_tag[2];
    wire [1:0]       lt_arr_l = lt_tag[1:0] + 2'd1;
    wire             lt_arr_issue = lt_arr_v && (lt_arr_l < NLL) && LPv[lt_arr_l];
    reg              ob_busy;
    reg              ob_g;
    reg  [3:0]       ob_gam;
    reg  [3:0]       ob_b;
    reg  [3:0]       ob_wait;
    reg  [$clog2(ND+1)-1:0] ocred;
    wire             lt_room = (lt_rho != 3'd0) || (!ob_busy && (LPv == 0) && (lt_infl == 0) && !lt_arr_v);
    assign take = offer && (os == lt_rho) && lt_room && (!LPv[0] || !lt_arr_issue);
    wire             lt_leaf_issue = take && LPv[0];
    wire             lt_issue = lt_arr_issue || lt_leaf_issue;
    wire [1:0]       lt_l = lt_arr_issue ? lt_arr_l : 2'd0;
    ot_hdc_delay #(.W(3), .D(ADD_LAT), .RESET(1)) u_lttag (.clk(clk), .rst_n(rc), .d({lt_issue, lt_l}), .q(lt_tag));
    wire             ob_send = ob_busy && (ob_wait == 4'd0) && ((ob_b != 4'd0) || (ocred != 0));
    // decision word {ob beat[1:0], osend, lob, lsl[1:0], lsty, lst0, lal[1:0], lsel, lis}
    wire             d_lst0 = take && !LPv[0];
    wire             d_lob  = lt_arr_v && (lt_arr_l == NLL);
    wire             d_lsty = lt_arr_v && (lt_arr_l < NLL) && !LPv[lt_arr_l];
    assign ltw = {ob_b[1:0], ob_send, d_lob, (d_lsty ? lt_arr_l : 2'd0), d_lsty, d_lst0, lt_l, lt_arr_issue, lt_issue};
    // the node beat: the tiles register their slice 8 edges after the decision (valid at t + 9); the tags follow (1 + 7 + 1)
    reg              nbv_n;
    reg  [3:0]       nbb_n;
    reg              nbg_n;
    reg  [3:0]       nbgam_n;
    wire [9:0]       nbt;
    always @(posedge clk or negedge rc)
        if (!rc) nbv_n <= 1'b0;
        else nbv_n <= ob_send;
    always @(posedge clk) begin nbb_n <= ob_b; nbg_n <= ob_g; nbgam_n <= ob_gam; end
    ot_hdc_delay #(.W(10), .D(7 + HXN), .RESET(1)) u_nbt (.clk(clk), .rst_n(rc), .d({nbv_n, nbb_n, nbg_n, nbgam_n}), .q(nbt));
    always @(posedge clk or negedge rc) begin
        if (!rc) begin
            lt_rho <= 3'd0; LPv <= 0; lt_infl <= 0; lt_fault <= 1'b0; ob_busy <= 1'b0; ob_b <= 4'd0; ob_wait <= 4'd0;
            ocred <= ND; nb_valid <= 1'b0;
        end else begin
            nb_valid <= nbt[9];
            nb_beat <= nbt[8:5]; nb_g <= nbt[4]; nb_gam <= nbt[3:0];
            lt_infl <= lt_infl + (lt_issue ? 4'd1 : 4'd0) - (lt_arr_v ? 4'd1 : 4'd0);
            if (start) lt_rho <= 3'd0;
            if (lt_arr_v) begin
                if (lt_arr_l == NLL) begin
                    ob_busy <= 1'b1; ob_b <= 4'd0; ob_g <= lt_g; ob_gam <= lt_gam; ob_wait <= 4'd9;
                    if (ob_busy) lt_fault <= 1'b1;
                end else if (LPv[lt_arr_l]) LPv[lt_arr_l] <= 1'b0;
                else LPv[lt_arr_l] <= 1'b1;
            end else if (ob_wait != 4'd0) ob_wait <= ob_wait - 4'd1;
            if (take) begin
                if (LPv[0]) LPv[0] <= 1'b0;
                else LPv[0] <= 1'b1;
                lt_rho <= lt_rho + 3'd1;
                if (lt_rho == 3'd0) begin lt_g <= pend_g[os]; lt_gam <= pend_gam[os]; end
                else if ((pend_g[os] != lt_g) || (pend_gam[os] != lt_gam)) lt_fault <= 1'b1;
            end
            if (ob_send) begin
                if (ob_b == 4'(LFB - 1)) begin ob_busy <= 1'b0; ob_b <= 4'd0; end
                else ob_b <= ob_b + 4'd1;
            end
            ocred <= ocred - ((ob_send && ob_b == 4'd0) ? 1'b1 : 1'b0) + (ocr_q ? 1'b1 : 1'b0);
        end
    end
    // ---- K pass: the scores come back from the head tiles (their scd1); tags as before ---------------------------------------
    localparam integer SCD = KDEPTH + LANE_D + 2 + 2;
    wire [11:0] tag_sc;
    wire        sc_v_n;
    ot_hdc_delay #(.W(12), .D(SCD - 1)) u_tag (.clk(clk), .rst_n(rc), .d({c_g, c_pidx[10:0]}), .q(tag_sc));
    ot_hdc_delay #(.W(1), .D(SCD - 1), .RESET(1)) u_scv (.clk(clk), .rst_n(rc), .d(k_issue), .q(sc_v_n));
    reg tf2;
    wire [3:0] tf = 4'd0;
    always @(posedge clk or negedge rsc)
        if (!rsc) begin sc_valid <= 1'b0; tf2 <= 1'b0; end
        else begin sc_valid <= sc_v_n; tf2 <= |t_sf; end
    always @(posedge clk) begin sc_data <= t_sc; sc_addr <= tag_sc; end

    // running max per [g][h] of this engine's scores
    wire [3:0] gtv;
    generate
        for (h = 0; h < 4; h = h + 1) begin : g_mx
            ot_nhb_fgt_h u_gt (.a(sc_data[32*h +: 32]), .b(lmax[32*(4*sc_addr[11] + h) +: 32]), .gt(gtv[h]));
        end
    endgenerate
    // product refusals (K or V issues) and the lane adders' faults, ORed per group then here
    reg gfault_any;
    always @(posedge clk or negedge rc) if (!rc) gfault_any <= 1'b0; else gfault_any <= |t_gf;
    wire mac_fault = gfault_any || tf2;
    integer hh;
    always @(posedge clk or negedge rsc) begin
        if (!rsc) begin lmax <= 0; lmax_any <= 2'b00; fault <= 1'b0; end
        else begin
            if (start) begin lmax_any <= 2'b00; fault <= 1'b0; end
            else begin
                if (sc_valid) begin
                    for (hh = 0; hh < 4; hh = hh + 1)
                        if (!lmax_any[sc_addr[11]] || gtv[hh]) lmax[32*(4*sc_addr[11] + hh) +: 32] <= sc_data[32*hh +: 32];
                    lmax_any[sc_addr[11]] <= 1'b1;
                end
                if ((|tf) || mac_fault || lt_fault || ring_fault || (STATIC_QK && ((k_issue && !q_ready) || (PART == 3 && qv_r && (qcnt >= NQB || qb_r != qcnt[5:0]))))) fault <= 1'b1;
            end
        end
    end
endmodule

// the e FIFO of leaf C: ot_nhb_fifo_rows2_h (W 64) with its 128-row SRAM level held in registers (128 x 64 flops, read
// registered as the macro's: r_ce at edge n, word at n + 1) -- same control, same cycles, no macro in the 138-um leaf
// (a 94.8-um macro cannot keep 20 um to both core edges there).
module ot_qkd_efifo2 #(parameter integer D1 = 4) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        push,
    input  wire [63:0] din,
    input  wire        pop,
    output wire [63:0] dout,
    output wire        nonempty
);
    reg  [6:0] swp, srp;
    reg  [7:0] scnt;
    reg        rd_v;
    reg  [3:0] l1_pend;
`ifdef KVD_RMUT
    wire       to_l1   = push && !rd_v && l1_pend < D1;
`else
    wire       to_l1   = push && scnt == 8'd0 && !rd_v && l1_pend < D1;
`endif
    wire       to_sram = push && !to_l1;
    wire       rd      = (scnt != 8'd0) && (l1_pend + (to_l1 ? 1 : 0) < D1);
    // 128 explicit 64-bit registers (no memory array: synthesis needs no memory-bits override) and, per pair of word bits,
    // a 7-level read mux tree with its OWN kept copy of the read pointer (ot_nhb_rp_h advances with rd exactly as srp;
    // one pointer for all 64 trees drove 8,194 select loads).  Heap order: node i selects on rp[6 - depth(i)], leaves
    // 127 .. 254 = entries 0 .. 127.
    wire [64*128-1:0] ent;
    wire [63:0] srd_n;
    reg  [63:0] srd;
    genvar e, b;
    generate
        for (e = 0; e < 128; e = e + 1) begin : g_ent
            reg [63:0] r;
            always @(posedge clk) if (to_sram && swp == e) r <= din;
            assign ent[64*e +: 64] = r;
        end
        for (b = 0; b < 32; b = b + 1) begin : g_rd
            wire [6:0] rp;
            (* keep_hierarchy *) ot_nhb_rp_h #(.AW(7), .D(128)) u_rp (.clk(clk), .rst_n(rst_n), .pop(rd), .q(rp));
            wire [1:0] mx [0:254];
            for (e = 0; e < 128; e = e + 1) begin : g_leaf
                assign mx[127 + e] = ent[64*e + 2*b +: 2];
            end
            for (e = 0; e < 127; e = e + 1) begin : g_mx
                assign mx[e] = rp[6 - ($clog2(e + 2) - 1)] ? mx[2*e + 2] : mx[2*e + 1];
            end
            assign srd_n[2*b +: 2] = mx[0];
        end
    endgenerate
    always @(posedge clk) if (rd) srd <= srd_n;
    wire        l1_push = to_l1 || rd_v;
    wire [63:0] l1_din = rd_v ? srd : din;
    ot_nhb_fifo_rows_r_h #(.W(64), .D(D1)) u_l1 (.clk(clk), .rst_n(rst_n), .push(l1_push), .din(l1_din), .pop(pop),
                                              .dout(dout), .nonempty(nonempty), .count());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin swp <= 0; srp <= 0; scnt <= 0; rd_v <= 1'b0; l1_pend <= 0; end
        else begin
            if (to_sram) swp <= swp + 7'd1;
            if (rd) srp <= srp + 7'd1;
            scnt <= scnt + (to_sram ? 8'd1 : 8'd0) - (rd ? 8'd1 : 8'd0);
            rd_v <= rd;
            l1_pend <= l1_pend + ((to_l1 || rd) ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0);
        end
    end
endmodule

// ---- the three hard leaves (fixed names, no parameters) ---------------------------------------------------------------
module qkd_ectl_a (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,            // {e 3, s 2} strap
    output wire [15:0]   rq,             // W: {req_t 13, req_g, req_v, req_valid}
    input  wire [1024:0] rs,             // W: {rsp_data 1024, rsp_valid}
    output wire [511:0]  t0_row,         // S / N: row bits [511:0] for the two head-tile pairs
    output wire [511:0]  t1_row,
    input  wire [51:0]   x_i,            // E seam: control word from B
    output wire [512:0]  rs_o,           // E seam: {row bits [1023:512] 512, rsp_valid}, E-face flops (stage 2), to B
    output wire          rvm_o           // E seam: rsp_valid stage 1 (for C, through B's feed-through)
);
    ot_qkd_ectl_part #(.PART(1)) u (.clk(ck), .rst_n(rst_n), .cfg_s(cfg[1:0]), .cfg_e(cfg[4:2]),
        .start_in(1'b0), .T_in(14'd0), .cyc8_in(3'd0), .q_valid_in(1'b0), .q_beat_in(6'd0), .q_data_in(512'd0),
        .exp_done(32'd0), .nb_cr(1'b0), .er_data(64'd0), .er_valid(), .er_addr(), .sc_valid(), .sc_addr(), .sc_data(),
        .lmax(), .lmax_any(), .nb_valid(), .nb_beat(), .nb_g(), .nb_gam(), .k_done(), .v_done(), .fault(), .ev_k_first(),
        .ev_v_first(), .req_valid(rq[0]), .req_v(rq[1]), .req_g(rq[2]), .req_t(rq[15:3]), .rsp_valid_in(rs[0]),
        .rsp_data_in(rs[1024:1]), .x_i(x_i), .x_o(), .rsv_i(1'b0), .rsv_o(rs_o[0]), .rvm_i(1'b0), .rvm_o(rvm_o), .rsd_i(512'd0), .rsd_o(rs_o[512:1]),
        .t0_c(), .t1_c(), .t0_row(t0_row), .t1_row(t1_row), .t0_e(), .t1_e(), .t0_lt(), .t1_lt(), .t0_qv(), .t1_qv(),
        .t0_qb(), .t1_qb(), .t0_qd(), .t1_qd(), .ts0_sc(64'd0), .ts1_sc(64'd0), .ts0_sf(2'd0), .ts1_sf(2'd0),
        .ts0_gf(2'd0), .ts1_gf(2'd0));
endmodule

module qkd_ectl_b (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,
    output wire [511:0]  t0_row,         // S / N: row bits [1023:512]
    output wire [511:0]  t1_row,
    output wire [15:0]   t0_cl,          // S / N: {lt 12, c 4}
    output wire [15:0]   t1_cl,
    input  wire [512:0]  rs_i,           // W seam: from A
    input  wire          rvm_i,          // W seam: rsp_valid stage 1 from A (feed-through to C)
    output wire [51:0]   x_o,            // W seam: control word to A (the feed-through flops of x_i)
    input  wire [51:0]   x_i,            // E seam: control word from C
    output wire          rsv_o           // E seam: rsp_valid to C
);
    ot_qkd_ectl_part #(.PART(2)) u (.clk(ck), .rst_n(rst_n), .cfg_s(cfg[1:0]), .cfg_e(cfg[4:2]),
        .start_in(1'b0), .T_in(14'd0), .cyc8_in(3'd0), .q_valid_in(1'b0), .q_beat_in(6'd0), .q_data_in(512'd0),
        .exp_done(32'd0), .nb_cr(1'b0), .er_data(64'd0), .er_valid(), .er_addr(), .sc_valid(), .sc_addr(), .sc_data(),
        .lmax(), .lmax_any(), .nb_valid(), .nb_beat(), .nb_g(), .nb_gam(), .k_done(), .v_done(), .fault(), .ev_k_first(),
        .ev_v_first(), .req_valid(), .req_v(), .req_g(), .req_t(), .rsp_valid_in(1'b0), .rsp_data_in(1024'd0),
        .x_i(x_i), .x_o(x_o), .rsv_i(rs_i[0]), .rsv_o(rsv_o), .rvm_i(rvm_i), .rvm_o(), .rsd_i(rs_i[512:1]), .rsd_o(),
        .t0_c(t0_cl[3:0]), .t1_c(t1_cl[3:0]), .t0_row(t0_row), .t1_row(t1_row), .t0_e(), .t1_e(), .t0_lt(t0_cl[15:4]),
        .t1_lt(t1_cl[15:4]), .t0_qv(), .t1_qv(), .t0_qb(), .t1_qb(), .t0_qd(), .t1_qd(), .ts0_sc(64'd0), .ts1_sc(64'd0),
        .ts0_sf(2'd0), .ts1_sf(2'd0), .ts0_gf(2'd0), .ts1_gf(2'd0));
endmodule

module qkd_ectl_c (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    cfg,
    input  wire [633:0]  si,             // E: as qkd_ectl
    output wire [424:0]  so,             // E: as qkd_ectl
    output wire [15:0]   e0, e1, e2, e3, // S / N: e of head 0..3
    input  wire [33:0]   s0, s1, s2, s3, // S / N: {g_f, sc_f, sc 32} of head 0..3
    output wire [518:0]  t0_q,           // S / N: {q_data 512, q_beat 6, q_valid}
    output wire [518:0]  t1_q,
    input  wire          rsv_i,          // W seam: rsp_valid from B
    output wire [51:0]   x_o             // W seam: control word to B
);
    ot_qkd_ectl_part #(.PART(3)) u (.clk(ck), .rst_n(rst_n), .cfg_s(cfg[1:0]), .cfg_e(cfg[4:2]),
        .start_in(si[0]), .T_in(si[14:1]), .cyc8_in(si[17:15]), .q_valid_in(si[18]), .q_beat_in(si[24:19]),
        .q_data_in(si[536:25]), .exp_done(si[568:537]), .er_data(si[632:569]), .nb_cr(si[633]),
        .er_valid(so[0]), .er_addr(so[12:1]), .sc_valid(so[13]), .sc_addr(so[25:14]), .sc_data(so[153:26]),
        .lmax(so[409:154]), .lmax_any(so[411:410]), .nb_valid(so[412]), .nb_beat(so[416:413]), .nb_g(so[417]),
        .nb_gam(so[421:418]), .k_done(so[422]), .v_done(so[423]), .fault(so[424]), .ev_k_first(), .ev_v_first(),
        .req_valid(), .req_v(), .req_g(), .req_t(), .rsp_valid_in(1'b0), .rsp_data_in(1024'd0),
        .x_i(52'd0), .x_o(x_o), .rsv_i(rsv_i), .rsv_o(), .rvm_i(1'b0), .rvm_o(), .rsd_i(512'd0), .rsd_o(),
        .t0_c(), .t1_c(), .t0_row(), .t1_row(), .t0_e({e1, e0}), .t1_e({e3, e2}), .t0_lt(), .t1_lt(),
        .t0_qv(t0_q[0]), .t1_qv(t1_q[0]), .t0_qb(t0_q[6:1]), .t1_qb(t1_q[6:1]), .t0_qd(t0_q[518:7]), .t1_qd(t1_q[518:7]),
        .ts0_sc({s1[31:0], s0[31:0]}), .ts0_sf({s1[32], s0[32]}), .ts0_gf({s1[33], s0[33]}),
        .ts1_sc({s3[31:0], s2[31:0]}), .ts1_sf({s3[32], s2[32]}), .ts1_gf({s3[33], s2[33]}));
endmodule

// the three leaves behind the one-tile cell's ports (wiring only): the bench / composition view of qkd_ectl
module qkd_ectl3 #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 8,
    parameter integer E = 0,
    parameter integer DQ = 128
) (
    input  wire          ck,
    input  wire          rst_n,
    output wire [15:0]   e0, e1, e2, e3,
    input  wire [33:0]   s0, s1, s2, s3,
    output wire [1558:0] t0, t1,
    output wire [15:0]   rq,
    input  wire [1024:0] rs,
    input  wire [633:0]  si,
    output wire [424:0]  so
);
    wire [4:0]   cfg = {3'(E), 2'(S)};
    wire [51:0]  x_cb, x_ba;
    wire [512:0] rs_ab;
    wire         rsv_bc, rvm_ab;
    wire [511:0] a0, a1, b0, b1;
    wire [15:0]  c0, c1;
    wire [518:0] q0, q1;
    qkd_ectl_a u_a (.ck(ck), .rst_n(rst_n), .cfg(cfg), .rq(rq), .rs(rs), .t0_row(a0), .t1_row(a1), .x_i(x_ba), .rs_o(rs_ab), .rvm_o(rvm_ab));
    qkd_ectl_b u_b (.ck(ck), .rst_n(rst_n), .cfg(cfg), .t0_row(b0), .t1_row(b1), .t0_cl(c0), .t1_cl(c1), .rs_i(rs_ab), .rvm_i(rvm_ab),
        .x_o(x_ba), .x_i(x_cb), .rsv_o(rsv_bc));
    qkd_ectl_c u_c (.ck(ck), .rst_n(rst_n), .cfg(cfg), .si(si), .so(so), .e0(e0), .e1(e1), .e2(e2), .e3(e3), .s0(s0),
        .s1(s1), .s2(s2), .s3(s3), .t0_q(q0), .t1_q(q1), .rsv_i(rsv_bc), .x_o(x_cb));
    // t [1558:0] = {q_data 512, q_beat 6, q_valid, lt 12, row 1024, c 4}
    assign t0 = {q0[518:7], q0[6:1], q0[0], c0[15:4], b0, a0, c0[3:0]};
    assign t1 = {q1[518:7], q1[6:1], q1[0], c1[15:4], b1, a1, c1[3:0]};
endmodule

`ifndef SYNTHESIS
// the three leaves behind ot_qwen_nearhbm_ectl_h's own ports: the row engine's control instance when the stack is built
// with +define+KVD_ECTL3 (layer bench).  The leaves are hard (no parameters): the engine must use their configuration.
module ot_qkd_ectl3_h #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 1,
    parameter integer E = 0,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer LFB = 4,
    parameter integer ND = 1,
    parameter integer HXK = 0,
    parameter integer HXN = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start_in,
    input  wire [13:0]          T_in,
    input  wire [2:0]           cyc8_in,
    input  wire                 q_valid_in,
    input  wire [5:0]           q_beat_in,
    input  wire [511:0]         q_data_in,
    input  wire [31:0]          exp_done,
    output wire                 req_valid,
    output wire                 req_v,
    output wire                 req_g,
    output wire [12:0]          req_t,
    input  wire                 rsp_valid_in,
    input  wire [HD*8-1:0]      rsp_data_in,
    output wire                 er_valid,
    output wire [11:0]          er_addr,
    input  wire [63:0]          er_data,
    output wire                 sc_valid,
    output wire [11:0]          sc_addr,
    output wire [127:0]         sc_data,
    output wire [2*4*32-1:0]    lmax,
    output wire [1:0]           lmax_any,
    output wire                 nb_valid,
    output wire [3:0]           nb_beat,
    output wire                 nb_g,
    output wire [3:0]           nb_gam,
    input  wire                 nb_cr,
    output wire                 k_done,
    output wire                 v_done,
    output wire                 fault,
    output wire                 ev_k_first,
    output wire                 ev_v_first,
    output wire [3:0]           t0_c,
    output wire [3:0]           t1_c,
    output wire [HD*8-1:0]      t0_row,
    output wire [HD*8-1:0]      t1_row,
    output wire [31:0]          t0_e,
    output wire [31:0]          t1_e,
    output wire [11:0]          t0_lt,
    output wire [11:0]          t1_lt,
    output wire                 t0_qv,
    output wire                 t1_qv,
    output wire [5:0]           t0_qb,
    output wire [5:0]           t1_qb,
    output wire [511:0]         t0_qd,
    output wire [511:0]         t1_qd,
    input  wire [2*32-1:0]      ts0_sc,
    input  wire [2*32-1:0]      ts1_sc,
    input  wire [1:0]           ts0_sf,
    input  wire [1:0]           ts1_sf,
    input  wire [1:0]           ts0_gf,
    input  wire [1:0]           ts1_gf
);
    initial if (HD != 128 || R != 8 || DQ != 128 || ADD_LAT != 7 || MUL_LAT != 6 || LFB != 4 || ND != 1 || HXK != 0 || HXN != 0) begin
        $display("ERROR ot_qkd_ectl3_h: the hard leaves are HD 128 R 8 DQ 128 ADD_LAT 7 MUL_LAT 6 LFB 4 ND 1 HXK 0 HXN 0"); $fatal(1);
    end
    wire [15:0]   e0, e1, e2, e3;
    wire [1558:0] t0, t1;
    wire [15:0]   rq;
    wire [424:0]  so;
    qkd_ectl3 #(.S(S), .E(E)) u3 (.ck(clk), .rst_n(rst_n), .e0(e0), .e1(e1), .e2(e2), .e3(e3),
        .s0({ts0_gf[0], ts0_sf[0], ts0_sc[31:0]}), .s1({ts0_gf[1], ts0_sf[1], ts0_sc[63:32]}),
        .s2({ts1_gf[0], ts1_sf[0], ts1_sc[31:0]}), .s3({ts1_gf[1], ts1_sf[1], ts1_sc[63:32]}), .t0(t0), .t1(t1), .rq(rq),
        .rs({rsp_data_in, rsp_valid_in}),
        .si({nb_cr, er_data, exp_done, q_data_in, q_beat_in, q_valid_in, cyc8_in, T_in, start_in}), .so(so));
    assign {req_t, req_g, req_v, req_valid} = rq;
    assign er_valid = so[0];  assign er_addr = so[12:1];  assign sc_valid = so[13];  assign sc_addr = so[25:14];
    assign sc_data = so[153:26];  assign lmax = so[409:154];  assign lmax_any = so[411:410];  assign nb_valid = so[412];
    assign nb_beat = so[416:413];  assign nb_g = so[417];  assign nb_gam = so[421:418];  assign k_done = so[422];
    assign v_done = so[423];  assign fault = so[424];
    assign ev_k_first = u3.u_c.u.ev_k_first;  assign ev_v_first = u3.u_c.u.ev_v_first;     // bench cycle markers
    assign t0_c = t0[3:0];  assign t0_row = t0[1027:4];  assign t0_lt = t0[1039:1028];  assign t0_qv = t0[1040];
    assign t0_qb = t0[1046:1041];  assign t0_qd = t0[1558:1047];
    assign t1_c = t1[3:0];  assign t1_row = t1[1027:4];  assign t1_lt = t1[1039:1028];  assign t1_qv = t1[1040];
    assign t1_qb = t1[1046:1041];  assign t1_qd = t1[1558:1047];
    assign t0_e = {e1, e0};  assign t1_e = {e3, e2};
endmodule
`endif

// Compiler-reserved 128-row ring. No demand refill, bypass, ready or credit path.
// Reads occupy the compiler-reserved QK window for the NEXT consume pointer; the current SRAM
// output is captured by S1 on the consume edge. Writes must precede that read.
module ot_qkd_static_row_ring #(parameter integer W=512, parameter integer DATA=1) (
    input wire clk, rst_n, clear, write_slot, write_valid,
    input wire [W-1:0] din, input wire read_slot, consume_slot,
    output wire [W-1:0] dout, output wire nonempty, output reg fault
);
    reg [6:0] wp, rp;
    reg [7:0] occupancy;
    reg read_visible;
    wire [6:0] read_addr = rp + (consume_slot ? 7'd1 : 7'd0);
    assign nonempty = occupancy != 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp<=0; rp<=0; occupancy<=0; fault<=0; read_visible<=0; end
        else if (clear) begin wp<=0; rp<=0; occupancy<=0; fault<=0; read_visible<=0; end
        else begin
            if (read_slot) read_visible <= occupancy > (consume_slot ? 8'd1 : 8'd0);
            if (write_slot) wp <= wp + 1'b1;
            if (consume_slot) rp <= rp + 1'b1;
            occupancy <= occupancy + (write_slot ? 8'd1 : 8'd0) - (consume_slot ? 8'd1 : 8'd0);
            if (write_valid != write_slot || (consume_slot && (occupancy == 0 || !read_visible)) ||
                (write_slot && occupancy == 128 && !consume_slot)) fault <= 1'b1;
        end
    generate if (DATA) begin : g_data
        localparam integer NM=(W+255)/256;
        wire [NM*256-1:0] padded = {{(NM*256-W){1'b0}},din};
        wire [NM*256-1:0] rd;
        for (genvar m=0;m<NM;m=m+1) begin : g_macro
            ot_sram_1r1w_128x256_m1_r2c2 u_s (.clk(clk), .r_ce_in(read_slot), .r_addr_in(read_addr),
                .rd_out(rd[m*256+:256]), .w_ce_in(write_slot && !clear), .w_addr_in(wp),
                .wd_in(padded[m*256+:256]), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
        assign dout=rd[W-1:0];
    end else begin : g_shadow
        assign dout={W{1'b0}};
    end endgenerate
endmodule
