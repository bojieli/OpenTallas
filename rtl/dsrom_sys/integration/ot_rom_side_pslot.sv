`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_rom_side_pslot: POSITION-SLOTTED SIDE staging bookkeeping of the wavefront package controller
// (rtl/dsrom_sys/integration/ot_rom_pkg_ctrl_wf_ps.sv, SIDE_PSL > 0; DS-ROM correctness, 2026-10-04).
//
// Why: SIDE carries per-user cross-stage state a producing stage shares with later stages (the reuse-layer
// index selections L2 -> L3..19, L20 -> L21..23, L24 -> L25..27, ..., compressed-KV rows, index keys).  The
// as-built controller stages it at one slot per user (user << SIDE_USH) with one per-user message count.  Under
// the wavefront (WAVE = 1, WIN = 6) up to WIN positions of a user are in flight one stage apart, so the
// producer's SIDE for q+1 .. q+WIN-1 lands while the consumer still runs (or has not started) q: one slot is
// overwritten, and a per-user count lets q start on q+1's message.
//
// With 2^PSL >= WIN slots per user the payload of position p goes to slot p mod 2^PSL (the controller adds
// slot << SIDE_PSH to the write address; the memory wrapper adds the running job's slot to the core's staging
// reads, core_side_off), and the message count is kept per (user, slot).  At most WIN issued instances of a user
// are unreduced at the SOURCE (wnf < WIN), every instance runs every stage in issue order and a newer instance
// of a position exists only after the older one was squashed, so a slot is reused only by its own position's
// re-issue (overwriting a squashed instance) or by p + 2^PSL after p has left every stage.  A generation bit
// (position bit PSL) per slot makes any other reuse fail closed (`conflict`).
//
// Timing: the lookup for the pending HIDDEN job (sel_*) is REGISTERED: ok_q is the exact count test of the
// state after this edge (this cycle's increment and decrement applied), for the header registered on this edge
// (the controller presents the arriving header on its rx_hdr cycle, else the held one).  It is never early: a
// HIDDEN payload takes >= 1 cycle after its header, and the controller starts a received job no sooner than the
// cycle after the header.
// ---------------------------------------------------------------------------
module ot_rom_side_pslot #(
    parameter integer MAXU    = 16,
    parameter integer USER_W  = 8,
    parameter integer NW      = 16,
    parameter integer PSL     = 3,       // log2 slots per user
    parameter integer SIDE_IN = 1,       // messages a step waits for
    parameter integer CW      = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    // lookup for the next cycle's pending HIDDEN job
    input  wire [USER_W-1:0] sel_user,
    input  wire [NW-1:0]     sel_pos,
    output reg               ok_q,
    // a SIDE message's last flit was written for (user, position)
    input  wire              inc_v,
    input  wire [USER_W-1:0] inc_user,
    input  wire [NW-1:0]     inc_pos,
    // a received job started: its SIDE messages are consumed
    input  wire              dec_v,
    input  wire [USER_W-1:0] dec_user,
    input  wire [NW-1:0]     dec_pos,
    // an arriving SIDE header (checked against the slot's generation)
    input  wire              chk_v,
    input  wire [USER_W-1:0] chk_user,
    input  wire [NW-1:0]     chk_pos,
    output reg               conflict
);
    localparam integer NSL = 1 << PSL;
    localparam integer N = MAXU * NSL;
    localparam integer IW = $clog2(N);
    reg [CW-1:0] cnt [0:N-1];
    reg          gen [0:N-1];
    function automatic [IW-1:0] idx(input [USER_W-1:0] u, input [NW-1:0] p);
        idx = IW'(u) * IW'(NSL) + IW'(p[PSL-1:0]);
    endfunction
    wire [IW-1:0] i_inc = idx(inc_user, inc_pos), i_dec = idx(dec_user, dec_pos), i_sel = idx(sel_user, sel_pos),
                  i_chk = idx(chk_user, chk_pos);
    wire inc_ok = inc_v && inc_user < MAXU;
    wire dec_ok = dec_v && dec_user < MAXU;
    // lookup of the state after this edge
    wire [CW-1:0] c_sel = cnt[i_sel];
    wire          g_sel = gen[i_sel];
    wire [CW-1:0] c_nx = c_sel + ((inc_ok && i_inc == i_sel) ? CW'(1) : CW'(0))
                               - ((dec_ok && i_dec == i_sel) ? CW'(SIDE_IN) : CW'(0));
    wire          g_nx = (inc_ok && i_inc == i_sel) ? inc_pos[PSL] : g_sel;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < N; k = k + 1) begin cnt[k] <= {CW{1'b0}}; gen[k] <= 1'b0; end
            ok_q <= 1'b0; conflict <= 1'b0;
        end else begin
            if (inc_ok && dec_ok && i_inc == i_dec) begin
                cnt[i_inc] <= cnt[i_inc] + CW'(1) - CW'(SIDE_IN);
            end else begin
                if (inc_ok) cnt[i_inc] <= cnt[i_inc] + CW'(1);
                if (dec_ok) cnt[i_dec] <= cnt[i_dec] - CW'(SIDE_IN);
            end
            if (inc_ok) gen[i_inc] <= inc_pos[PSL];
            ok_q <= sel_user < MAXU && c_nx >= CW'(SIDE_IN) && g_nx == sel_pos[PSL];
            // a message for another generation of a slot that still holds unconsumed messages
            conflict <= chk_v && chk_user < MAXU && cnt[i_chk] != {CW{1'b0}} && gen[i_chk] != chk_pos[PSL];
        end
    end
endmodule
