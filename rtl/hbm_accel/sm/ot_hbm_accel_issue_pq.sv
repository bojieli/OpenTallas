`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_issue_pq: the pipelined-issue (PQ) successor of ot_hbm_accel_issue ENABLE = 1 (the HA3 look-ahead
// sequencer) for the DS HBM SM element ot_hbm_accel_sm_pq.  The HBM counterpart of the ROM's field-phase overlap:
// op N+1 is LAUNCHED (its parameters latched, its setup cycle run) as soon as op N has issued its last line, while
// op N still drains through the column macros, the combine tree and the streaming stack.  The per-op issue order,
// x-store addressing and line order are exactly those of ot_hbm_accel_issue ENABLE = 1 (the body below is that
// module's, line for line, except where marked PQ), so every result bit is unchanged.
//
// PQ changes against ot_hbm_accel_issue ENABLE = 1:
//   * `start` is a valid (`start_v`) with a pop (`launch`): the op waits in the caller's queue (a credit channel in
//     ot_hbm_accel_sm_pq) until the issue can take it;
//   * launch condition: no op is issuing or in setup, fewer than NOUT ops are outstanding, the head has been visible
//     for one full cycle (its hazard figures are registered), and the RETIRE-ORDER HAZARD is clear (below);
//   * `rem` (rows still to retire) becomes an in-order table of NOUT outstanding ops; `rdone` always retires a row
//     of the OLDEST op; an op completes (arrive toggles, as before, once per op) when it has issued its last line and
//     retired its last row; `busy` = an op is in setup, issuing or outstanding.
// Retire-order hazard.  Rows of different ops cannot share the streaming stack's output cycle (ot_gpu_stack faults on
// two levels retiring at once) and must leave in op order (results are attributed to ops by order).  A row of an op
// with G groups retires from stack level L(G) = ceil(log2 G); from its last issue its final partial reaches the stack
// output D(op) = COLLAT(fmt) + SLAT * L(G) cycles later, COLLAT(fmt) = CL_BD for the block-dot column, CL_BD + DBF
// for the BF16 column (the leaf gather and combine tree are common).  Two ops' items also share the leaf gather
// (G1 faults on both columns valid in one cycle).  So op N+1's first issue must come more than
//     need = max(0, DBF*(bf_N - bf_N1), D(N) - D(N1))
// cycles after op N's last issue.  Ops whose D does not decrease (the token's independent runs: fp8 -> fp8 -> bf16,
// fp4 x 12 -> fp8, fp4 w2 x 6 -> fp8 w2) need no gap; the setup cycle and the slot-phase wait already separate them.
// HAZ = 0 disables the check (negative test only: a falling-D pair then faults or mis-attributes).
// Every input of the hazard decision is a register: need_q / d_q are computed from the queue head one cycle after
// it appears (hv_q), the since-last-issue counter is a saturating register.
// ---------------------------------------------------------------------------
module ot_hbm_accel_issue_pq #(
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer XDEPTH = 96,
    parameter integer NOUT = 4,         // outstanding ops (one issuing + draining ones); drain <= 100 < 2 spans
    parameter integer HAZ  = 1,
    parameter integer SLAT = 7,         // stack level latency (ot_gpu_stack ALAT)
    parameter integer DBF  = 14         // BF16 column latency - block-dot column latency (measured drains: 72 vs 58)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start_v,        // PQ: an op is waiting (queue head)
    output wire                  launch,         // PQ: the head is taken this cycle (pop)
    input  wire [$clog2(RMAX):0] op_rows,
    input  wire [15:0]           op_c,
    input  wire [7:0]            op_g,
    input  wire                  op_gs,
    input  wire                  op_bf,          // PQ: the op runs on the BF16 column (fmt 0)
    input  wire                  w_valid,
    input  wire                  x_rdy,
    output wire                  w_ready,
    input  wire                  rdone,
    output reg                   busy,
    output wire                  iss_v,
    output wire                  iss_row_ok,
    output wire [$clog2(IL)-1:0] iss_slot,
    output wire [$clog2(RMAX):0] iss_row,
    output wire                  iss_first,
    output wire                  iss_last,
    output wire                  iss_glast,
    output wire                  iss_rev_end,
    output wire [$clog2(XDEPTH)-1:0] xa,
    output reg                   arrive,
    input  wire                  release_in,
    output wire                  released,
    output wire                  hz_wait         // PQ: the head is held by the hazard check (visibility only)
);
    localparam integer SW = $clog2(IL);
    localparam integer RW = $clog2(RMAX);
    localparam integer XW = $clog2(XDEPTH);
    localparam integer NW = (NOUT <= 2) ? 1 : $clog2(NOUT);
    localparam integer DWD = 8;                  // D / need / since width (D <= DBF + 4 * SLAT = 42)
    reg [RW:0]  rows_q;
    reg [15:0]  c_q;
    reg [7:0]   g_q;
    reg [SW-1:0] ph, si;
    reg [RW:0]  rb, rb_n;
    reg [7:0]   gi, gi_n;
    reg [15:0]  ti, ti_n;
    reg         issuing;
    reg [XW-1:0] xa_r, xa_n;
    reg          gs_q;
    assign released = (release_in == arrive) && !busy;
    reg [RW+8:0] items_q, wb, wb_n;
    reg [RW:0]   cr, cr_n;
    reg [7:0]    cg;
    reg [XW-1:0] cxb, cxb_n;
    reg [RW:0]   s_row [0:IL-1];
    reg [7:0]    s_g   [0:IL-1];
    reg [XW-1:0] s_xb  [0:IL-1];
    wire [RW:0] gs_row = (ti == 0) ? cr : s_row[si];
    wire [XW-1:0] gs_xb = (ti == 0) ? cxb : s_xb[si];
    reg  [RW:0] rsi_q;
    (* keep *) wire [RW:0] rsi_inc; assign rsi_inc = rsi_q + 1'b1;
    wire [RW:0] row_now = gs_q ? gs_row : rsi_q;
    reg [IL-1:0] valid_mask, next_mask;
    reg init_q;
    reg [15:0] c_end;
    reg [7:0] g_end;
    reg [IL-1:0] slot_glast;
    reg turn_q;
    reg lt_q, lt_n_q, c1_q;
    reg lw_q;
    reg lg_q, lg_n_q, g1_q;
    integer f;
    wire [SW-1:0] ph_nx = (ph == IL - 1) ? {SW{1'b0}} : ph + 1'b1;
    wire [SW-1:0] si_nx = (si == IL - 1) ? {SW{1'b0}} : si + 1'b1;
    wire [SW:0] rs_sat = (rows_q >= IL) ? IL[SW:0] : rows_q[SW:0];
    wire [SW:0] gq_sat = (g_q >= IL) ? IL[SW:0] : g_q[SW:0];
    wire [2*SW+1:0] init_items = rs_sat * gq_sat;
    reg [RW+2:0] pp0, pp1, pp2, pp3;
    reg [RW+4:0] s01, s23;
    (* keep *) wire [RW:0] cr_n_inc; assign cr_n_inc = cr_n + 1'b1;
    (* keep *) wire [XW-1:0] cxb_n_inc; assign cxb_n_inc = cxb_n + c_q[XW-1:0];
    (* keep *) wire [15:0] ti_n_inc; assign ti_n_inc = ti_n + 1'b1;
    (* keep *) wire [7:0] gi_n_inc; assign gi_n_inc = gi_n + 1'b1;
    (* keep *) wire [7:0] cg_inc; assign cg_inc = cg + 1'b1;
    (* keep *) wire [RW:0] rb_n_inc; assign rb_n_inc = rb_n + IL;
    (* keep *) wire [RW+8:0] wb_n_inc; assign wb_n_inc = wb_n + IL;
    (* keep *) wire [XW-1:0] xa_n_inc; assign xa_n_inc = xa_n + 1'b1;
    always @(posedge clk) begin
        s01 <= pp0 + {pp1, 2'b0};
        s23 <= pp2 + {pp3, 2'b0};
        items_q <= s01 + {s23, 4'b0};
        for (f=0; f<IL; f=f+1)
            next_mask[f] <= gs_q ? (wb_n + f < items_q) : (rb_n + f < rows_q);
        lt_n_q <= (ti_n == c_end);
        lw_q <= gs_q ? (wb_n >= items_q) : (rb_n >= rows_q);
        c1_q <= (c_end == 0);
        lg_n_q <= (gi_n == g_end);
        g1_q <= (g_end == 0);
    end
    reg row_ok_q, ls_q;
    wire row_ok = row_ok_q;
    wire        my_turn = issuing && turn_q && x_rdy;
    wire        need_line = my_turn && row_ok;
    wire        adv = my_turn && (!row_ok || w_valid);
    assign w_ready = need_line;
    wire        last_si = ls_q;
    wire        last_t = lt_q;
    wire        cg_last = (cg == g_end);
    wire        last_g = gs_q ? ((ti == 0) ? cg_last : slot_glast[si]) : lg_q;
    wire        wave_adv = adv && last_si && last_t && (gs_q || last_g) && !lw_q;
    // PQ: the op's last issue (the cycle `issuing` falls)
    wire        op_end = adv && last_si && last_t && (gs_q || last_g) && lw_q;
    assign iss_v = adv;
    assign iss_row_ok = row_ok;
    assign iss_slot = row_now[SW-1:0];
    assign iss_row = row_now;
    assign iss_first = (ti == 0);
    assign iss_last = last_t;
    assign iss_glast = last_g;
    assign iss_rev_end = adv && last_si;
    assign xa = gs_q ? gs_xb + ti[XW-1:0] : xa_r;
    reg sw_q; reg [SW-1:0] sw_slot; reg [RW:0] sw_row; reg [7:0] sw_g; reg [XW-1:0] sw_xb; reg sw_last;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) sw_q <= 1'b0;
        else sw_q <= adv && gs_q && (ti == 0);
    end
    always @(posedge clk) begin
        sw_slot <= si; sw_row <= cr; sw_g <= cg; sw_xb <= cxb; sw_last <= cg_last;
        if (sw_q) begin
            s_row[sw_slot] <= sw_row; s_g[sw_slot] <= sw_g; s_xb[sw_slot] <= sw_xb;
        end
    end

    // ---------------- PQ: hazard figures of the queue head (registered) ----------------
    function [2:0] lvl;                          // ceil(log2 g), g <= 16
        input [7:0] g;
        lvl = (g > 8) ? 3'd4 : (g > 4) ? 3'd3 : (g > 2) ? 3'd2 : (g > 1) ? 3'd1 : 3'd0;
    endfunction
    wire [DWD-1:0] d_head = (op_bf ? DBF : 0) + SLAT * lvl(op_g);
    reg  [DWD-1:0] d_cur;                        // D of the op launched last
    reg            bf_cur;
    reg  [DWD-1:0] need_q, since;
    reg            hv_q;                         // the head has been visible a full cycle (need_q is its own)
    wire [DWD-1:0] need_d = (d_cur > d_head) ? d_cur - d_head : {DWD{1'b0}};
    wire [DWD-1:0] need_c = (bf_cur && !op_bf) ? DBF[DWD-1:0] : {DWD{1'b0}};
    // outstanding-op table (in order): rows left to retire, last line issued
    reg [RW:0]     ocnt [0:NOUT-1];
    reg [NOUT-1:0] ofin;
    reg [NW-1:0]   oh, ot;                       // head (oldest), tail (next free)
    reg [NW:0]     on;                           // entries in use
    wire           gap_ok = (HAZ == 0) || (since > need_q);
    assign launch = start_v && hv_q && !init_q && !issuing && (on < NOUT) && gap_ok;
    assign hz_wait = start_v && hv_q && !init_q && !issuing && (on < NOUT) && !gap_ok;
    wire           head_v = (on != 0);
    wire           head_done = head_v && ofin[oh] && (rdone ? (ocnt[oh] == 1) : (ocnt[oh] == 0));
    wire [NW-1:0]  oh_nx = (oh == NOUT - 1) ? {NW{1'b0}} : oh + 1'b1;
    wire [NW-1:0]  ot_nx = (ot == NOUT - 1) ? {NW{1'b0}} : ot + 1'b1;
    wire [NW-1:0]  ot_pv = (ot == 0) ? NOUT[NW-1:0] - 1'b1 : ot - 1'b1;   // the youngest (issuing) entry
    integer e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            need_q <= 0; hv_q <= 1'b0; since <= {DWD{1'b1}}; d_cur <= 0; bf_cur <= 1'b0;
            ofin <= 0; oh <= 0; ot <= 0; on <= 0;
            for (e = 0; e < NOUT; e = e + 1) ocnt[e] <= 0;
        end else begin
            need_q <= (need_d > need_c) ? need_d : need_c;
            hv_q <= start_v && !launch;
            if (op_end) since <= 0;
            else if (since != {DWD{1'b1}}) since <= since + 1'b1;
            if (launch) begin d_cur <= d_head; bf_cur <= op_bf; end
            // table: retire into the oldest, allocate at launch, mark the issuing op's last line, pop on completion
            if (rdone && head_v) ocnt[oh] <= ocnt[oh] - 1'b1;
            if (op_end) ofin[ot_pv] <= 1'b1;
            if (launch) begin ocnt[ot] <= op_rows; ofin[ot] <= 1'b0; ot <= ot_nx; end
            if (head_done) oh <= oh_nx;
            on <= on + launch - head_done;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= 0; busy <= 1'b0; issuing <= 1'b0; rb <= 0; gi <= 0; ti <= 0; si <= 0;
            rb_n <= IL; gi_n <= 1; ti_n <= 1; xa_n <= 1; wb_n <= IL; cr_n <= 1; cxb_n <= 0;
            rows_q <= 0; c_q <= 1; g_q <= 1; arrive <= 1'b0; xa_r <= 0; gs_q <= 1'b0;
            wb <= 0; cr <= 0; cg <= 0; cxb <= 0; pp0 <= 0; pp1 <= 0; pp2 <= 0; pp3 <= 0;
            valid_mask <= 0; init_q <= 0; c_end <= 0; g_end <= 0; slot_glast <= 0;
            turn_q <= 1'b1; lt_q <= 1'b0; lg_q <= 1'b0; row_ok_q <= 1'b0; ls_q <= (IL == 1); rsi_q <= 0;
        end else begin
            ph <= ph_nx;
            if (sw_q) slot_glast[sw_slot] <= sw_last;
            if (init_q) begin
                row_ok_q <= gs_q ? (init_items != 0) : (rows_q != 0); ls_q <= (IL == 1);
                rsi_q <= 0;
            end else if (adv) begin
                rsi_q <= !last_si ? rsi_inc : (wave_adv && !gs_q) ? rb_n : rb;
                row_ok_q <= wave_adv ? next_mask[0] : valid_mask[si_nx];
                ls_q <= (si_nx == IL - 1);
            end
            turn_q <= init_q ? (ph_nx == 0) : (adv ? (ph_nx == si_nx) : (ph_nx == si));
            // PQ: busy covers setup, issue and every outstanding op; arrive toggles once per completed op
            busy <= launch || init_q || issuing || (on + launch - head_done != 0);
            if (head_done) arrive <= ~arrive;
            if (launch) begin
                issuing <= 1'b0; init_q <= 1;
                c_end <= op_c - 1'b1; g_end <= op_g - 1'b1;
                rows_q <= op_rows; c_q <= op_c; g_q <= op_g; gs_q <= op_gs;
            end else if (init_q) begin
                init_q <= 0; issuing <= 1;
                rb <= 0; gi <= 0; ti <= 0; si <= 0; xa_r <= 0;
                rb_n <= IL; gi_n <= 1; ti_n <= 1; xa_n <= 1; wb_n <= IL; cr_n <= 1;
                wb <= 0; cr <= 0; cg <= 0; cxb <= 0;
                lg_q <= (g_end == 0);
                pp0 <= rows_q * g_q[1:0]; pp1 <= rows_q * g_q[3:2];
                pp2 <= rows_q * g_q[5:4]; pp3 <= rows_q * g_q[7:6];
                cxb_n <= c_q[XW-1:0];
                lt_q <= (c_end == 0);
                for (f=0; f<IL; f=f+1) valid_mask[f] <= gs_q ? (f < init_items) : (f < rows_q);
            end else begin
                if (adv && gs_q) begin
                    if (ti == 0) begin
                        if (cg_last) begin
                            cg <= 0; cxb <= 0; cxb_n <= c_q[XW-1:0]; cr <= cr_n; cr_n <= cr_n_inc;
                        end else begin
                            cg <= cg_inc; cxb <= cxb_n; cxb_n <= cxb_n_inc;
                        end
                    end
                    if (!last_si) si <= si_nx;
                    else begin
                        si <= 0;
                        if (!last_t) begin ti <= ti_n; ti_n <= ti_n_inc; lt_q <= lt_n_q; end
                        else begin
                            ti <= 0; ti_n <= 1; lt_q <= c1_q;
                            if (lw_q) issuing <= 1'b0;
                            else begin wb <= wb_n; wb_n <= wb_n_inc; valid_mask <= next_mask; end
                        end
                    end
                end else if (adv) begin
                    if (!last_si) si <= si_nx;
                    else begin
                        si <= 0;
                        if (last_t && last_g) begin xa_r <= 0; xa_n <= 1; end
                        else begin xa_r <= xa_n; xa_n <= xa_n_inc; end
                        if (!last_t) begin ti <= ti_n; ti_n <= ti_n_inc; lt_q <= lt_n_q; end
                        else begin
                            ti <= 0; ti_n <= 1; lt_q <= c1_q;
                            if (!last_g) begin gi <= gi_n; gi_n <= gi_n_inc; lg_q <= lg_n_q; end
                            else begin
                                gi <= 0; gi_n <= 1; lg_q <= g1_q;
                                if (lw_q) issuing <= 1'b0;
                                else begin rb <= rb_n; rb_n <= rb_n_inc; valid_mask <= next_mask; end
                            end
                        end
                    end
                end
            end
        end
    end
endmodule
