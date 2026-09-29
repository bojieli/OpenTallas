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
module ot_gpu_issue #(
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
    output wire [$clog2(XDEPTH)-1:0] xa,
    output reg                   arrive,
    input  wire                  release_in,
    output wire                  released
);
    localparam integer SW = $clog2(IL);
    localparam integer RW = $clog2(RMAX);
    localparam integer XW = $clog2(XDEPTH);
    reg [RW:0]  rows_q;
    reg [15:0]  c_q;
    reg [7:0]   g_q;
    reg [SW-1:0] ph, si;
    reg [RW:0]  rb;
    reg [7:0]   gi;
    reg [15:0]  ti;
    reg         issuing;
    reg [RW:0]  retired;
    reg [XW-1:0] xa_r;
    reg          gs_q;
    assign released = (release_in == arrive) && !busy;
    // group-slot state: the wave's first item, the cursor that assigns items to slots at t = 0,
    // and each slot's item
    reg [RW+8:0] items_q, wb;
    reg [RW:0]   cr;
    reg [7:0]    cg;
    reg [XW-1:0] cxb;
    reg [RW:0]   s_row [0:IL-1];
    reg [7:0]    s_g   [0:IL-1];
    reg [XW-1:0] s_xb  [0:IL-1];
    wire [RW+8:0] item = wb + si;
    wire        gs_ok = item < items_q;
    wire [RW:0] gs_row = (ti == 0) ? cr : s_row[si];
    wire [7:0]  gs_g   = (ti == 0) ? cg : s_g[si];
    wire [XW-1:0] gs_xb = (ti == 0) ? cxb : s_xb[si];
    wire [RW:0] row_now = gs_q ? gs_row : rb + si;
    wire        row_ok = gs_q ? gs_ok : (row_now < rows_q);
    wire        my_turn = issuing && (ph == si);
    wire        need_line = my_turn && row_ok;
    wire        adv = my_turn && (!row_ok || w_valid);
    assign w_ready = need_line;
    wire        last_si = (si == IL - 1);
    wire        last_t = (ti == c_q - 1);
    wire        last_g = gs_q ? (gs_g == g_q - 1) : (gi == g_q - 1);
    assign iss_v = adv;
    assign iss_row_ok = row_ok;
    assign iss_slot = row_now[SW-1:0];
    assign iss_row = row_now;
    assign iss_first = (ti == 0);
    assign iss_last = last_t;
    assign iss_glast = last_g;
    assign xa = gs_q ? gs_xb + ti[XW-1:0] : xa_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= 0; busy <= 1'b0; issuing <= 1'b0; rb <= 0; gi <= 0; ti <= 0; si <= 0;
            rows_q <= 0; c_q <= 1; g_q <= 1; retired <= 0; arrive <= 1'b0; xa_r <= 0; gs_q <= 1'b0;
            items_q <= 0; wb <= 0; cr <= 0; cg <= 0; cxb <= 0;
        end else begin
            ph <= (ph == IL - 1) ? {SW{1'b0}} : ph + 1'b1;
            if (start && !busy) begin
                busy <= 1'b1; issuing <= 1'b1;
                rows_q <= op_rows; c_q <= op_c; g_q <= op_g; gs_q <= op_gs;
                rb <= 0; gi <= 0; ti <= 0; si <= 0; retired <= 0; xa_r <= 0;
                items_q <= op_rows * op_g; wb <= 0; cr <= 0; cg <= 0; cxb <= 0;
            end else begin
                if (adv && gs_q) begin
                    if (ti == 0) begin                      // assign this slot its item, advance the cursor
                        s_row[si] <= cr; s_g[si] <= cg; s_xb[si] <= cxb;
                        if (cg == g_q - 1) begin cg <= 0; cxb <= 0; cr <= cr + 1'b1; end
                        else begin cg <= cg + 1'b1; cxb <= cxb + c_q[XW-1:0]; end
                    end
                    if (!last_si) si <= si + 1'b1;
                    else begin
                        si <= 0;
                        if (!last_t) ti <= ti + 1'b1;
                        else begin
                            ti <= 0;
                            if (wb + IL >= items_q) issuing <= 1'b0;
                            else wb <= wb + IL;
                        end
                    end
                end else if (adv) begin
                    if (!last_si) si <= si + 1'b1;
                    else begin
                        si <= 0;
                        xa_r <= (last_t && last_g) ? {XW{1'b0}} : xa_r + 1'b1;
                        if (!last_t) ti <= ti + 1'b1;
                        else begin
                            ti <= 0;
                            if (!last_g) gi <= gi + 1'b1;
                            else begin
                                gi <= 0;
                                if (rb + IL >= rows_q) issuing <= 1'b0;
                                else rb <= rb + IL;
                            end
                        end
                    end
                end
                if (rdone && busy) retired <= retired + 1'b1;
                if (busy && !issuing && ((retired + (rdone ? 1 : 0)) == rows_q)) begin
                    busy <= 1'b0;
                    arrive <= ~arrive;
                end
            end
        end
    end
endmodule
