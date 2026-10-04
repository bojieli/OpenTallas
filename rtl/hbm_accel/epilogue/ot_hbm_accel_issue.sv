`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Issue sequencer of a GPU-organised SM's tensor core (row-slot schedule).
// IL slots, slot s holds row rb + s of row block rb; the op walks the fixed
// lockstep order  rb, g (group), t (k-step in the chunk), s (slot), one
// weight line per issue.  Slot s may issue only in the cycle whose phase is
// s (the circulating accumulators revisit a slot every IL cycles); a line that
// is not yet in the staging when its slot comes round waits one revolution,
// and so does everything after it (the stream order is fixed).  A slot past
// the op's rows is a bubble and needs no line.  `xa` = g * c + t addresses
// the x store.  `busy` falls, and `arrive` toggles for the barrier network,
// when the op's last row result has been retired (`rdone`).
//
// Group-slot mode (op_gs): the IL slots hold consecutive (row, group) items
// in the order  row-major, group-minor  instead of IL rows, so a one- or
// two-row slice does not walk its groups serially (a K-chain).  The weight
// stream order is then  wave, t, s  over items; each slot remembers its
// item's row, group and x-store base when the wave starts (t = 0).  A row's
// group partials leave the column trees in group order on consecutive
// cycles, which is the order the streaming stack needs (keyed by row mod IL),
// so the result is the same golden tree.  It needs a new x fragment every
// cycle (the model sizes the x store for it).
// ---------------------------------------------------------------------------
module ot_hbm_accel_issue #(
    parameter integer ENABLE = 0,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer XDEPTH = 96
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire [$clog2(RMAX):0] op_rows,
    input  wire [15:0]           op_c,
    input  wire [7:0]            op_g,
    input  wire                  op_gs,          // group-slot issue
    input  wire                  w_valid,
    input  wire                  x_rdy,          // the x fragment the next issue needs is there (1 = no x store gate)
    output wire                  w_ready,
    input  wire                  rdone,          // one row result retired this cycle
    output reg                   busy,
    output wire                  iss_v,          // a line (or a bubble) is issued this cycle
    output wire                  iss_row_ok,
    output wire [$clog2(IL)-1:0] iss_slot,        // stack stream key: row mod IL
    output wire [$clog2(RMAX):0] iss_row,
    output wire                  iss_first,
    output wire                  iss_last,
    output wire                  iss_glast,
    output wire                  iss_rev_end,    // this issue ends a slot revolution (the x fragment is done)
    output wire [$clog2(XDEPTH)-1:0] xa,
    output reg                   arrive,
    input  wire                  release_in,
    output wire                  released
);
    generate if (ENABLE == 0) begin : g_original
        ot_gpu_issue #(.IL(IL), .RMAX(RMAX), .XDEPTH(XDEPTH)) u_original (.*);
    end else begin : g_lookahead
    // Look-ahead successor (HA3, retimed 2026-10-04 for 1.2 GHz SS):
    //  * every cursor's increment is held in a pre-incremented register (x_n = x + step), so the
    //    issue decision (adv) only selects between registered values and never feeds an adder;
    //  * the slot-turn compare, chunk-end, wave-end and retire-done tests are registered flags;
    //  * wave-valid flags are computed a wave ahead (next_mask), outside adv's cursor feedback;
    //  * the group-slot item count (rows x groups) is four 2-bit-group partial products in the setup
    //    cycle, summed over the next two edges; it is first read at a wave end, >= IL (8) edges after
    //    setup, and is valid 3 edges after setup (next_mask / lw_q 4 edges after).
    // Issue order, records and the one-issue-per-cycle rate are unchanged; setup is +1 cycle per op.
    localparam integer SW = $clog2(IL);
    localparam integer RW = $clog2(RMAX);
    localparam integer XW = $clog2(XDEPTH);
    reg [RW:0]  rows_q;
    reg [15:0]  c_q;
    reg [7:0]   g_q;
    reg [SW-1:0] ph, si;
    reg [RW:0]  rb, rb_n;
    reg [7:0]   gi, gi_n;
    reg [15:0]  ti, ti_n;
    reg         issuing;
    reg [RW:0]  rem;                 // rows still to retire
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
    reg  [RW:0] rsi_q;                // rb + si, carried as a register (row-slot mode)
    (* keep *) wire [RW:0] rsi_inc; assign rsi_inc = rsi_q + 1'b1;
    wire [RW:0] row_now = gs_q ? gs_row : rsi_q;
    reg [IL-1:0] valid_mask, next_mask;
    reg init_q;
    reg [15:0] c_end;
    reg [7:0] g_end;
    reg [IL-1:0] slot_glast;
    reg turn_q;                       // ph == si
    reg lt_q, lt_n_q, c1_q;           // ti == c_end ; ti + 1 == c_end ; c_end == 0
    reg lw_q;                         // this wave/row block is the op's last
    reg lg_q, lg_n_q, g1_q;           // gi == g_end ; gi + 1 == g_end ; g_end == 0 (row-slot mode)
    integer f;
    wire [SW-1:0] ph_nx = (ph == IL - 1) ? {SW{1'b0}} : ph + 1'b1;
    wire [SW-1:0] si_nx = (si == IL - 1) ? {SW{1'b0}} : si + 1'b1;
    // min(rows, IL) * min(g, IL) decides f < rows * g for every f < IL without the wide multiply
    wire [SW:0] rs_sat = (rows_q >= IL) ? IL[SW:0] : rows_q[SW:0];
    wire [SW:0] gq_sat = (g_q >= IL) ? IL[SW:0] : g_q[SW:0];
    wire [2*SW+1:0] init_items = rs_sat * gq_sat;
    reg [RW+2:0] pp0, pp1, pp2, pp3;
    reg [RW+4:0] s01, s23;
    // kept increment nets: the issue decision selects them, it is never merged into their carry chains
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
    reg row_ok_q, ls_q;               // valid_mask[si] ; si == IL-1, both carried with si
    wire row_ok = row_ok_q;
    wire        my_turn = issuing && turn_q && x_rdy;
    wire        need_line = my_turn && row_ok;
    wire        adv = my_turn && (!row_ok || w_valid);
    assign w_ready = need_line;
    wire        last_si = ls_q;
    wire        last_t = lt_q;
    wire        cg_last = (cg == g_end);
    wire        last_g = gs_q ? ((ti == 0) ? cg_last : slot_glast[si]) : lg_q;
    wire        start_go = start && !busy;
    wire        wave_adv = adv && last_si && last_t && (gs_q || last_g) && !lw_q;
    assign iss_v = adv;
    assign iss_row_ok = row_ok;
    assign iss_slot = row_now[SW-1:0];
    assign iss_row = row_now;
    assign iss_first = (ti == 0);
    assign iss_last = last_t;
    assign iss_glast = last_g;
    assign iss_rev_end = adv && last_si;
    assign xa = gs_q ? gs_xb + ti[XW-1:0] : xa_r;
    // a slot's item record is captured on its issuing edge and written one edge later; it is
    // read only from the next revolution on (ti != 0), >= IL edges later
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
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= 0; busy <= 1'b0; issuing <= 1'b0; rb <= 0; gi <= 0; ti <= 0; si <= 0;
            rb_n <= IL; gi_n <= 1; ti_n <= 1; xa_n <= 1; wb_n <= IL; cr_n <= 1; cxb_n <= 0;
            rows_q <= 0; c_q <= 1; g_q <= 1; rem <= 0; arrive <= 1'b0; xa_r <= 0; gs_q <= 1'b0;
            wb <= 0; cr <= 0; cg <= 0; cxb <= 0; pp0 <= 0; pp1 <= 0; pp2 <= 0; pp3 <= 0;
            valid_mask <= 0; init_q <= 0; c_end <= 0; g_end <= 0; slot_glast <= 0;
            turn_q <= 1'b1; lt_q <= 1'b0; lg_q <= 1'b0; row_ok_q <= 1'b0; ls_q <= (IL == 1); rsi_q <= 0;
        end else begin
            ph <= ph_nx;
            if (sw_q) slot_glast[sw_slot] <= sw_last;
            // row_ok / last-slot flags follow si (and valid_mask at a wave change) one step ahead
            if (init_q) begin
                row_ok_q <= gs_q ? (init_items != 0) : (rows_q != 0); ls_q <= (IL == 1);
                rsi_q <= 0;
            end else if (adv) begin
                rsi_q <= !last_si ? rsi_inc : (wave_adv && !gs_q) ? rb_n : rb;
                row_ok_q <= wave_adv ? next_mask[0] : valid_mask[si_nx];
                ls_q <= (si_nx == IL - 1);
            end
            // turn flag: ph and si both step on an issue; otherwise only ph steps
            turn_q <= init_q ? (ph_nx == 0) : (adv ? (ph_nx == si_nx) : (ph_nx == si));
            if (start_go) begin
                busy <= 1'b1; issuing <= 1'b0; init_q <= 1;
                c_end <= op_c - 1'b1; g_end <= op_g - 1'b1;
                rows_q <= op_rows; c_q <= op_c; g_q <= op_g; gs_q <= op_gs; rem <= op_rows;
            end else if (init_q) begin
                // cursors are cleared here, from registers only (no issue happens in this cycle)
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
                    if (ti == 0) begin                      // assign this slot its item, advance the cursor
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
                if (rdone && busy) rem <= rem - 1'b1;
                if (busy && !issuing && (rdone ? (rem == 1) : (rem == 0))) begin
                    busy <= 1'b0;
                    arrive <= ~arrive;
                end
            end
        end
    end
    end endgenerate
endmodule
