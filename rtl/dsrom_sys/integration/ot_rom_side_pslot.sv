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
// Timing (1.2 GHz): the lookup for the pending HIDDEN job is REGISTERED in two stages and reads only registers:
// sel_* is the controller's HELD header (hdr_user / hdr_pos); stage 1 registers that user's slot slice, stage 2
// the slot test.  ok_q is forced low for two edges after a new header (sel_new = rx_hdr) and whenever an update of
// that user is in flight through the two stages.  The generation check (`conflict`) is likewise two-stage, one
// edge later than the header (it can miss a conflicting header that immediately follows its slot's previous
// message, before that message's increment is visible; it is a fail-closed detector, not the ordering itself).  Increments (a SIDE message's last flit) and decrements (a
// job start) are registered here and applied one edge later; ok_q is computed for the state after the edge (the
// registered increment / decrement applied).  Both delays only make ok_q later, never early: a decrement lags
// its start by one edge while that job runs (no second start of the user's slot can follow within it), and an
// increment lags by one edge.  A HIDDEN payload takes >= 1 cycle after its header.
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
    input  wire              sel_new,      // a new header is captured on this edge (the held one changes)
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
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer IW = UB + PSL;
    localparam integer N = 1 << IW;          // entry {user, slot}; users >= MAXU are never written
    reg [CW-1:0] cnt [0:N-1];
    reg          gen [0:N-1];
    // registered update requests
    reg          inc_r, dec_r, inc_g;
    reg [IW-1:0] inc_i, dec_i;
    // the same requests pre-decoded (user one-hot x slot one-hot): an entry's enable is one AND of two registers
    reg [MAXU-1:0] inc_uh, dec_uh;
    reg [NSL-1:0]  inc_sh, dec_sh;
    wire [IW-1:0] i_sel = {sel_user[UB-1:0], sel_pos[PSL-1:0]};
    reg          chk_r, chk_g;               // the arriving header, registered (checked one edge later)
    reg [IW-1:0] i_chk;
    // two-stage lookup (MAXU up to 866): stage 1 registers the selected user's slot slice (a user-wide mux),
    // stage 2 picks the slot.  ok_q is asserted only when neither stage saw an update of that user nor a new
    // header (late, never early: the next cycle without one recomputes it).
    reg [NSL*CW-1:0] sl_c;  reg [NSL-1:0] sl_g;  reg sl_dirty;  reg new1;
    reg [NSL*CW-1:0] ck_c;  reg [NSL-1:0] ck_g;  reg ck_v;  reg ck_gen;  reg [PSL-1:0] ck_s;
    wire [UB-1:0] u_sel = sel_user[UB-1:0];
    wire touch_sel = (inc_r && inc_i[IW-1:PSL] == u_sel) || (dec_r && dec_i[IW-1:PSL] == u_sel);
    integer j;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < N; k = k + 1) begin cnt[k] <= {CW{1'b0}}; gen[k] <= 1'b0; end
            ok_q <= 1'b0; conflict <= 1'b0; inc_r <= 1'b0; dec_r <= 1'b0; inc_g <= 1'b0; inc_i <= 0; dec_i <= 0;
            chk_r <= 1'b0; chk_g <= 1'b0; i_chk <= 0;
            sl_c <= 0; sl_g <= 0; sl_dirty <= 1'b1; new1 <= 1'b1; ck_c <= 0; ck_g <= 0; ck_v <= 1'b0;
            ck_gen <= 1'b0; ck_s <= 0;
            inc_uh <= {MAXU{1'b0}}; dec_uh <= {MAXU{1'b0}}; inc_sh <= {NSL{1'b0}}; dec_sh <= {NSL{1'b0}};
        end else begin
            inc_r <= inc_v && inc_user < MAXU;
            inc_i <= {inc_user[UB-1:0], inc_pos[PSL-1:0]}; inc_g <= inc_pos[PSL];
            dec_r <= dec_v && dec_user < MAXU;
            dec_i <= {dec_user[UB-1:0], dec_pos[PSL-1:0]};
            inc_uh <= (inc_v && inc_user < MAXU) ? (MAXU'(1) << inc_user) : {MAXU{1'b0}};
            inc_sh <= NSL'(1) << inc_pos[PSL-1:0];
            dec_uh <= (dec_v && dec_user < MAXU) ? (MAXU'(1) << dec_user) : {MAXU{1'b0}};
            dec_sh <= NSL'(1) << dec_pos[PSL-1:0];
            for (k = 0; k < MAXU * NSL; k = k + 1) begin
                if ((inc_uh[k / NSL] && inc_sh[k % NSL]) || (dec_uh[k / NSL] && dec_sh[k % NSL]))
                    cnt[IW'(k / NSL * (1 << PSL) + k % NSL)] <= cnt[IW'(k / NSL * (1 << PSL) + k % NSL)]
                        + ((inc_uh[k / NSL] && inc_sh[k % NSL]) ? CW'(1) : CW'(0))
                        - ((dec_uh[k / NSL] && dec_sh[k % NSL]) ? CW'(SIDE_IN) : CW'(0));
                if (inc_uh[k / NSL] && inc_sh[k % NSL]) gen[IW'(k / NSL * (1 << PSL) + k % NSL)] <= inc_g;
            end
            for (j = 0; j < NSL; j = j + 1) begin
                sl_c[j*CW +: CW] <= cnt[{u_sel, PSL'(j)}]; sl_g[j] <= gen[{u_sel, PSL'(j)}];
                ck_c[j*CW +: CW] <= cnt[{i_chk[IW-1:PSL], PSL'(j)}]; ck_g[j] <= gen[{i_chk[IW-1:PSL], PSL'(j)}];
            end
            sl_dirty <= touch_sel;
            new1 <= sel_new;
            ok_q <= !sel_new && !new1 && !sl_dirty && !touch_sel && sel_user < MAXU &&
                    sl_c[sel_pos[PSL-1:0]*CW +: CW] >= CW'(SIDE_IN) && sl_g[sel_pos[PSL-1:0]] == sel_pos[PSL];
            // a message for another generation of a slot that still holds unconsumed messages
            chk_r <= chk_v && chk_user < MAXU;
            i_chk <= {chk_user[UB-1:0], chk_pos[PSL-1:0]}; chk_g <= chk_pos[PSL];
            ck_v <= chk_r; ck_gen <= chk_g; ck_s <= i_chk[PSL-1:0];
            conflict <= ck_v && ck_c[ck_s*CW +: CW] != {CW{1'b0}} && ck_g[ck_s] != ck_gen;
        end
    end
endmodule
