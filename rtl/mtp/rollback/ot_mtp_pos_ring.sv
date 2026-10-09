`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Position-indexed row ring with exact MTP rollback (DS-V4.1, stream mtp-rollback 2026-10-08).
//
// Holds NRING independent rings of R rows (one ring a layer's sliding-window KV, or one a DSpark
// stage's window cache `dsk`).  Row of position p lives at slot p mod R with its absolute-position
// tag.  A speculative verify pass at committed count n writes positions n .. n+PMAX-1; a later read
// reaches back at most W-1 positions from a query at or after n (W the model window).  With
// R >= W + PMAX no rejected row ever lands on a slot a committed read still needs, so the golden's
// truncate() (Model.truncate) is ONE register write, n <= q + 2 + a, and needs no data movement:
// a rejected row is dead and is rewritten by the committed position that next owns its slot before
// any read reaches it.  R = W (the AR sizing, slot = p mod W) is NOT exact under MTP: a rejected
// position q+1+g overwrites slot (q+1+g) mod W, which holds committed row q+1+g-W, still inside the
// window of the next query q+2+a whenever g >= a + 2.
//
// Reads stream the rows of one window, one row a cycle (registered, latency 1):
//   ORDER 0  positions max(0, p-W+1) .. p, oldest first             (golden win[L][-W:])
//   ORDER 1  positions p-W+1 .. p in ring-slot (pos mod W) order    (golden dspark_window(anchor=p))
// Every row read is tag-checked: a slot whose tag is not the position asked for raises the sticky
// `err` (fail-closed; the bench requires err = 0).  Writes outside [n - (R - PMAX), n + PMAX) are
// errors too (they would alias a live row).
//
// R must be a power of two.  Cycles: write 1 (posted), read of a window W+1 (1 issue + W beats),
// commit 1 (n_set), rollback 0 data cycles.
// ---------------------------------------------------------------------------
module ot_mtp_pos_ring #(
    parameter integer NRING = 4,
    parameter integer R     = 256,
    parameter integer W     = 128,
    parameter integer PMAX  = 8,
    parameter integer DW    = 32,
    parameter integer ORDER = 0,
    parameter integer PW    = 32,
    parameter integer TAGCHK = 1,        // 0: no tag check (bench mutant: show the silent data error)
    parameter integer RIW   = (NRING > 1) ? $clog2(NRING) : 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            n_set,
    input  wire [PW-1:0]   n_val,
    input  wire            wr_v,
    input  wire [RIW-1:0]  wr_ring,
    input  wire [PW-1:0]   wr_pos,
    input  wire [DW-1:0]   wr_data,
    input  wire            rd_v,
    output wire            rd_ready,
    input  wire [RIW-1:0]  rd_ring,
    input  wire [PW-1:0]   rd_pos,
    output reg             o_v,
    output reg  [DW-1:0]   o_data,
    output reg  [PW-1:0]   o_pos,
    output reg             o_last,
    output reg             err
);
    localparam integer RB = $clog2(R);
    initial if ((1 << RB) != R || R < W || W < 1 || (ORDER == 1 && (W & (W - 1)) != 0))
        $fatal(1, "ot_mtp_pos_ring: R must be a power of two >= W (and W a power of two for ORDER 1)");

    reg [DW-1:0] mem [0:NRING*R-1];
    reg [PW-1:0] tag [0:NRING*R-1];
    reg          tv  [0:NRING*R-1];
    reg [PW-1:0] n;
    integer i;

    function automatic [RB-1:0] slot(input [PW-1:0] p);
        slot = p[RB-1:0];
    endfunction
    function automatic signed [PW:0] pdist(input [PW-1:0] p, input [PW-1:0] nn);
        pdist = $signed({1'b0, p}) - $signed({1'b0, nn});
    endfunction

    // read walker
    reg            busy, wrapped;
    reg [RIW-1:0]  ring;
    reg [PW-1:0]   p_cur, p_end, p_anchor, p_wrapto;
    assign rd_ready = !busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; err <= 1'b0; busy <= 1'b0; o_v <= 1'b0; o_last <= 1'b0; o_data <= 0; o_pos <= 0;
            for (i = 0; i < NRING * R; i = i + 1) tv[i] <= 1'b0;
        end else begin
            o_v <= 1'b0; o_last <= 1'b0;
            if (n_set) n <= n_val;
            if (wr_v) begin
                mem[wr_ring * R + slot(wr_pos)] <= wr_data;
                tag[wr_ring * R + slot(wr_pos)] <= wr_pos;
                tv[wr_ring * R + slot(wr_pos)]  <= 1'b1;
                if (TAGCHK && (pdist(wr_pos, n) >= PMAX || pdist(wr_pos, n) < -(R - PMAX))) err <= 1'b1;
            end
            if (!busy && rd_v) begin
                busy <= 1'b1; ring <= rd_ring; p_anchor <= rd_pos;
                if (ORDER == 0 || rd_pos + 1 <= W) begin
                    p_cur <= (rd_pos + 1 > W) ? rd_pos - W + 1 : 0;
                    p_end <= rd_pos; wrapped <= 1'b1;
                end else begin
                    // ring-slot order: from the position = 0 mod W up to the anchor, then the oldest
                    // position up to the one before that start
                    p_cur <= rd_pos - (rd_pos & (W - 1)); p_end <= rd_pos;
                    wrapped <= ((rd_pos & (W - 1)) == W - 1);
                    p_wrapto <= rd_pos - W + 1;
                end
            end else if (busy) begin
                o_v <= 1'b1; o_pos <= p_cur;
                o_data <= mem[ring * R + slot(p_cur)];
                if (TAGCHK && (!tv[ring * R + slot(p_cur)] || tag[ring * R + slot(p_cur)] != p_cur)) err <= 1'b1;
                if (TAGCHK && (pdist(p_cur, n) >= PMAX || pdist(p_cur, n) < -(R - PMAX))) err <= 1'b1;
                if (p_cur == p_end) begin
                    if (wrapped) begin busy <= 1'b0; o_last <= 1'b1; end
                    else begin
                        wrapped <= 1'b1; p_cur <= p_wrapto;
                        p_end <= p_anchor - (p_anchor & (W - 1)) - 1;
                    end
                end else p_cur <= p_cur + 1;
            end
        end
    end
endmodule
