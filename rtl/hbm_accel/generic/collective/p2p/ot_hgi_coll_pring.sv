`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_pring (HBM peer-to-peer step 1, owner approval 2026-10-14 09:00 PT): one stop of the 2 x 2 registered
// COLL peer ring between the four quadrant collective engines.  The ring carries NO wide vector traffic: only
//   CTRL   record credits (a quadrant popped a broadcast record), record completions and faults, quadrant -> home;
//   CARRY  the bit-exact cross-quadrant reduction carry (B2 SPEC section 4, RED_CARRY): 8 FP32 lanes (256 b) a flit;
//   RESULT the folded result, broadcast to the other three quadrants.
//
// Topology: physical cycle SW(0) -> SE(1) -> NE(3) -> NW(2) -> SW (clockwise, CW) and the reverse (CCW); one 280-b link
// each way between ring neighbours: {v 1, kind 2, src 2, dst 2, ttl 2, tag 3, mode 1, aux 11, data 256}.  No diagonal
// (the die centre stays empty).  Every link leaves a flop and lands in a flop (registers at the pins); the die inserts
// plain relay registers (<= 500 um each) between stops, no flow control is needed: a SLOTTED ring, transit has priority,
// a stop injects only into an empty slot, and every sink accepts what reaches it (CTRL counters, carry slots indexed by
// (tag, source), one RESULT a cycle) so the ring can neither block nor deadlock.  Route: shortest way, a 2-hop pair CW.
//
// RED_CARRY fold (golden order, never re-associated; B2 section 4).  The client (the quadrant's SU) submits its local
// partial P_q of reduction tag t (8 FP32 lanes) with mode
//   SERIAL (0): ((P0 + P1) + P2) + P3: q0 sends P0 to q1, q1 adds and sends to q2, q2 to q3, q3 folds the last term;
//   TREE   (1): (P0 + P1) + (P2 + P3): q1 = P0 + P1 -> q3, q2 sends P2 -> q3, q3 = P2 + P3 then (P0 + P1) + that.
// Left operand = the earlier chunks (a), right = the later (b) of the golden adder ot_hdc_fp32_add_lat (operand order
// matters for NaN payloads).  The result returns on rr_* in every quadrant (q3 locally, the others by RESULT broadcast).
// A quadrant starts its fold as soon as its own partial and its carry are present (no barrier, B2 R1).
// Mutants: MUT_CARRY = 1 q1 / q2 / q3 forward their local partial without the carry (dropped carry); MUT_ORDER = 1 the
// serial fold runs in ring order 0, 1, 3, 2 (reordered sum).
module ot_hgi_coll_pring #(
    parameter integer NT        = 8,        // reduction tags in flight (client reuses a tag after its result)
    parameter integer HOME      = 0,        // quadrant that aggregates record credits / completions
    parameter integer LAT       = 8,        // golden adder latency
    parameter integer MUT_CARRY = 0,
    parameter integer MUT_ORDER = 0,
    parameter integer SPLIT_CLOCKS = 0,
    parameter integer RW        = 280
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [NT-1:0] clk_state,
    input  wire [7:0]    clk_add,
    input  wire [1:0]    qid,               // die strap
    // ring links (registered at both ends)
    input  wire [RW-1:0] cw_i,              // from the CW predecessor
    output reg  [RW-1:0] cw_o,              // to the CW successor
    input  wire [RW-1:0] ccw_i,
    output reg  [RW-1:0] ccw_o,
    // record control events of this quadrant (pulses) and, at HOME, the events of all four
    input  wire          ev_pop,            // this engine popped a broadcast record
    input  wire          ev_done,           // this engine retired a record
    input  wire          ev_fault,          // level: this engine faulted (sticky)
    output reg  [3:0]    h_pop,             // HOME: pops seen this edge per quadrant (pulse)
    output reg  [3:0]    h_done,            // HOME: completions this edge per quadrant (pulse)
    output reg  [3:0]    h_fault,           // HOME: sticky faults per quadrant
    // RED_CARRY client
    input  wire          rc_v,
    output wire          rc_rdy,
    input  wire [2:0]    rc_tag,
    input  wire          rc_mode,           // 0 SERIAL, 1 TREE
    input  wire [255:0]  rc_d,
    output reg           rr_v,
    output reg  [2:0]    rr_tag,
    output reg  [255:0]  rr_d,
    output reg           fault              // protocol fault (a carry into an occupied slot, tag reuse)
);
    localparam [1:0] K_CTRL = 2'd0, K_CARRY = 2'd1, K_RES = 2'd2;
    // flit fields
    function automatic [RW-1:0] mk(input [1:0] kind, input [1:0] src, input [1:0] dst, input [1:0] ttl, input [2:0] tag,
                                   input mode, input [10:0] aux, input [255:0] d);
        mk = {1'b1, kind, src, dst, ttl, tag, mode, aux, d};
    endfunction
    `define F_V(x)    x[RW-1]
    `define F_KIND(x) x[RW-2 -: 2]
    `define F_SRC(x)  x[RW-4 -: 2]
    `define F_DST(x)  x[RW-6 -: 2]
    `define F_TTL(x)  x[RW-8 -: 2]
    `define F_TAG(x)  x[RW-10 -: 3]
    `define F_MODE(x) x[RW-13]
    `define F_AUX(x)  x[RW-14 -: 11]
    `define F_D(x)    x[255:0]
    // ring position of a quadrant: SW 0, SE 1, NE 2, NW 3
    function automatic [1:0] pos(input [1:0] q);
        case (q) 2'd0: pos = 2'd0; 2'd1: pos = 2'd1; 2'd3: pos = 2'd2; default: pos = 2'd3; endcase
    endfunction
    function automatic is_ccw(input [1:0] s, input [1:0] d); is_ccw = (2'(pos(d) - pos(s)) == 2'd3); endfunction

    reg [1:0] me; always @(posedge clk) me <= qid;
    // ---- pin capture -------------------------------------------------------------------------------------------
    reg [RW-1:0] cwi, ccwi;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cwi <= '0; ccwi <= '0; end
        else begin cwi <= cw_i; ccwi <= ccw_i; end

    // ---- fold state ----------------------------------------------------------------------------------------------
    reg          lp_v [0:NT-1]; reg lp_m [0:NT-1]; wire [255:0] lp_d [0:NT-1];       // local partial
    reg          c_v [0:NT-1][0:3]; wire [255:0] c_d [0:NT-1][0:3];                  // carry slots by source quadrant
    reg          t_v [0:NT-1]; wire [255:0] t_d [0:NT-1];                             // q3 TREE: P2 + P3
    reg          busy [0:NT-1];                                                      // an add of this tag in flight
    assign rc_rdy = !lp_v[rc_tag] && !busy[rc_tag];
    // One payload leaf per tag. Common registered write streams keep the parent's payload root small.
    // A payload crosses one extra register edge; ready bits below prevent a fold before that edge lands.
    reg [NT-1:0] lp_wr, tree_wr; reg [255:0] lp_wdata, tree_wdata;
    reg [NT*4-1:0] carry_wr0, carry_wr1; reg [511:0] carry_wdata;
    reg lp_staged [0:NT-1], tree_staged [0:NT-1], lp_landed [0:NT-1], tree_landed [0:NT-1];
    reg carry_staged [0:NT-1][0:3], carry_landed [0:NT-1][0:3];
    always @(posedge clk) begin
        for (integer t = 0; t < NT; t = t + 1) begin
            lp_staged[t] <= lp_v[t]; tree_staged[t] <= t_v[t]; lp_landed[t] <= lp_staged[t]; tree_landed[t] <= tree_staged[t];
            for (integer q = 0; q < 4; q = q + 1) begin carry_staged[t][q] <= c_v[t][q]; carry_landed[t][q] <= carry_staged[t][q]; end
        end
    end
    for (genvar t = 0; t < NT; t = t + 1) begin : g_state
        wire leaf_clk = SPLIT_CLOCKS ? clk_state[t] : clk;
        ot_hgi_coll_pring_state u_state (.clk(leaf_clk),
            .lp_wr(lp_wr[t]), .lp_data(lp_wdata), .tree_wr(tree_wr[t]), .tree_data(tree_wdata),
            .carry_wr0(carry_wr0[t*4 +: 4]), .carry_wr1(carry_wr1[t*4 +: 4]), .carry_data(carry_wdata),
            .lp(lp_d[t]), .tree(t_d[t]), .c0(c_d[t][0]), .c1(c_d[t][1]), .c2(c_d[t][2]), .c3(c_d[t][3]));
    end
    // serial order: next quadrant after q (golden 0,1,2,3; MUT_ORDER ring order 0,1,3,2)
    function automatic [1:0] nxt(input [1:0] q);
        if (MUT_ORDER != 0) case (q) 2'd0: nxt = 2'd1; 2'd1: nxt = 2'd3; 2'd3: nxt = 2'd2; default: nxt = 2'd0; endcase
        else nxt = q + 2'd1;
    endfunction
    function automatic [1:0] prv(input [1:0] q);
        if (MUT_ORDER != 0) case (q) 2'd1: prv = 2'd0; 2'd3: prv = 2'd1; 2'd2: prv = 2'd3; default: prv = 2'd2; endcase
        else prv = q - 2'd1;
    endfunction
    wire [1:0] first = 2'd0, last = (MUT_ORDER != 0) ? 2'd2 : 2'd3;

    // golden adder, 8 lanes, with a tag / step side pipe (one issue a cycle)
    reg          a_iv; reg [255:0] a_a, a_b; reg [2:0] a_it; reg [1:0] a_is;     // step: 0 send-on, 1 final, 2 q3 tree t
    wire [255:0] a_y;
    for (genvar l = 0; l < 8; l = l + 1) begin : g_add
        ot_hgi_coll_pring_add_lane #(.LAT(LAT)) u_add (.clk(SPLIT_CLOCKS ? clk_add[l] : clk), .rst_n(rst_n), .valid_in(a_iv), .a(a_a[32*l +: 32]),
            .b(a_b[32*l +: 32]), .y(a_y[32*l +: 32]), .valid_out());
    end
    reg [LAT-1:0] sp_v; reg [2:0] sp_t [0:LAT-1]; reg [1:0] sp_s [0:LAT-1];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sp_v <= '0;
        else begin
            sp_v <= {sp_v[LAT-2:0], a_iv}; sp_t[0] <= a_it; sp_s[0] <= a_is;
            for (integer i = 1; i < LAT; i = i + 1) begin sp_t[i] <= sp_t[i-1]; sp_s[i] <= sp_s[i-1]; end
        end
    wire       ao_v = sp_v[LAT-1]; wire [2:0] ao_t = sp_t[LAT-1]; wire [1:0] ao_s = sp_s[LAT-1];

    // ---- injection queues (one per direction) -----------------------------------------------------------------------
    localparam integer QD = 2 * NT + 4;
    reg [RW-1:0] iq [0:1][0:QD-1];
    function automatic [$clog2(QD)-1:0] inc(input [$clog2(QD)-1:0] p); inc = (p == QD - 1) ? '0 : p + 1'b1; endfunction
    reg [$clog2(QD):0] iq_n [0:1]; reg [$clog2(QD)-1:0] iq_h [0:1], iq_t [0:1];
    // CTRL counters (to HOME)
    reg [2:0] n_pop, n_done; reg f_sent;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cw_o <= '0; ccw_o <= '0; rr_v <= 1'b0; fault <= 1'b0; a_iv <= 1'b0;
            h_pop <= '0; h_done <= '0; h_fault <= '0; n_pop <= '0; n_done <= '0; f_sent <= 1'b0;
            lp_wr <= 0; tree_wr <= 0; carry_wr0 <= 0; carry_wr1 <= 0;
            for (i = 0; i < NT; i = i + 1) begin
                lp_v[i] <= 1'b0; t_v[i] <= 1'b0; busy[i] <= 1'b0;
                for (integer s = 0; s < 4; s = s + 1) c_v[i][s] <= 1'b0;
            end
            for (i = 0; i < 2; i = i + 1) begin iq_n[i] <= '0; iq_h[i] <= '0; iq_t[i] <= '0; end
        end else begin : step
            reg [RW-1:0] x, fo [0:1], inq [0:1];
            reg [3:0] hp, hd; reg [$clog2(QD):0] qn [0:1]; reg [$clog2(QD)-1:0] qh [0:1], qt [0:1];
            reg lpv [0:NT-1]; reg cv [0:NT-1][0:3]; reg tv [0:NT-1]; reg bz [0:NT-1];
            reg issued; reg [1:0] dir;
            rr_v <= 1'b0; a_iv <= 1'b0; issued = 1'b0; lp_wr <= 0; tree_wr <= 0; carry_wr0 <= 0; carry_wr1 <= 0;
            hp = '0; hd = '0;
            for (i = 0; i < 2; i = i + 1) begin qn[i] = iq_n[i]; qh[i] = iq_h[i]; qt[i] = iq_t[i]; fo[i] = '0; end
            for (i = 0; i < NT; i = i + 1) begin lpv[i] = lp_v[i]; tv[i] = t_v[i]; bz[i] = busy[i];
                for (integer s = 0; s < 4; s = s + 1) cv[i][s] = c_v[i][s]; end
            // -- arrivals: eject or forward (transit fills this edge's output slot first)
            inq[0] = cwi; inq[1] = ccwi;
            for (integer d = 0; d < 2; d = d + 1) begin
                x = inq[d];
                if (`F_V(x)) begin
                    if (`F_KIND(x) == K_RES) begin                     // broadcast: copy out, pass on while ttl > 1
                        rr_v <= 1'b1; rr_tag <= `F_TAG(x); rr_d <= `F_D(x);
                        bz[`F_TAG(x)] = 1'b0;
                        if (`F_TTL(x) > 2'd1) begin fo[d] = x; fo[d][RW-8 -: 2] = `F_TTL(x) - 2'd1; end
                    end else if (`F_DST(x) != me) fo[d] = x;           // transit
                    else if (`F_KIND(x) == K_CTRL) begin
                        if (`F_AUX(x)[0]) h_fault[`F_SRC(x)] <= 1'b1;
                        hp[`F_SRC(x)] = `F_AUX(x)[1]; hd[`F_SRC(x)] = `F_AUX(x)[2];
                    end else begin                                     // CARRY into slot (tag, src)
                        if (cv[`F_TAG(x)][`F_SRC(x)]) fault <= 1'b1;
                        cv[`F_TAG(x)][`F_SRC(x)] = 1'b1;
                        if (d == 0) carry_wr0[int'(`F_TAG(x))*4 + int'(`F_SRC(x))] <= 1;
                        else carry_wr1[int'(`F_TAG(x))*4 + int'(`F_SRC(x))] <= 1;
                        carry_wdata[d*256 +: 256] <= `F_D(x);
                    end
                end
            end
            // -- client partial
            if (rc_v) begin
                if (lpv[rc_tag] || bz[rc_tag]) fault <= 1'b1;
                lpv[rc_tag] = 1'b1; lp_m[rc_tag] <= rc_mode; lp_wr[rc_tag] <= 1; lp_wdata <= rc_d; bz[rc_tag] = 1'b1;
            end
            // -- adder results
            if (ao_v) begin
                if (ao_s == 2'd2) begin tv[ao_t] = 1'b1; tree_wr[ao_t] <= 1; tree_wdata <= a_y; end            // q3 TREE: P2 + P3
                else if (ao_s == 2'd1) begin                                              // final: local + broadcast
                    rr_v <= 1'b1; rr_tag <= ao_t; rr_d <= a_y; bz[ao_t] = 1'b0;
                    dir = 2'd0;
                    iq[0][qt[0]] <= mk(K_RES, me, me, 2'd3, ao_t, 1'b0, 11'd0, a_y); qt[0] = inc(qt[0]); qn[0] = qn[0] + 1'b1;
                end else begin                                                            // send on (serial / q1 tree)
                    reg [1:0] dq; dq = lp_m[ao_t] ? 2'd3 : nxt(me);
                    dir = is_ccw(me, dq) ? 2'd1 : 2'd0;
                    iq[dir][qt[dir]] <= mk(K_CARRY, me, dq, 2'd0, ao_t, lp_m[ao_t], 11'd0, a_y);
                    qt[dir] = inc(qt[dir]); qn[dir] = qn[dir] + 1'b1;
                end
            end
            // -- fold issue: at most one add (or one raw send) per edge, lowest ready tag first
            // a partial / carry / tree sum is folded from the edge after it landed (its data is a non-blocking write)
            for (i = 0; i < NT; i = i + 1) if (!issued && lpv[i] && lp_v[i] && lp_landed[i]) begin : fold
                reg [1:0] src_c; reg mode_; reg [255:0] carry_d;
                mode_ = lp_m[i];
                if (!mode_) begin                                                         // SERIAL
                    if (me == first) begin                                                // send P0 raw
                        dir = is_ccw(me, nxt(me)) ? 2'd1 : 2'd0;
                        iq[dir][qt[dir]] <= mk(K_CARRY, me, nxt(me), 2'd0, 3'(i), 1'b0, 11'd0, lp_d[i]);
                        qt[dir] = inc(qt[dir]); qn[dir] = qn[dir] + 1'b1; lpv[i] = 1'b0; issued = 1'b1;
                    end else if ((cv[i][prv(me)] && c_v[i][prv(me)] && carry_landed[i][prv(me)]) || MUT_CARRY != 0) begin
                        src_c = prv(me);
                        a_iv <= 1'b1; a_a <= (MUT_CARRY != 0) ? 256'd0 : c_d[i][src_c]; a_b <= lp_d[i]; a_it <= 3'(i);
                        a_is <= (me == last) ? 2'd1 : 2'd0;
                        lpv[i] = 1'b0; cv[i][src_c] = 1'b0; issued = 1'b1;
                    end
                end else begin                                                            // TREE
                    case (me)
                        2'd0, 2'd2: begin                                                 // P0 -> q1, P2 -> q3 raw
                            reg [1:0] dq; dq = (me == 2'd0) ? 2'd1 : 2'd3;
                            dir = is_ccw(me, dq) ? 2'd1 : 2'd0;
                            iq[dir][qt[dir]] <= mk(K_CARRY, me, dq, 2'd0, 3'(i), 1'b1, 11'd0, lp_d[i]);
                            qt[dir] = inc(qt[dir]); qn[dir] = qn[dir] + 1'b1; lpv[i] = 1'b0; issued = 1'b1;
                        end
                        2'd1: if ((cv[i][0] && c_v[i][0] && carry_landed[i][0]) || MUT_CARRY != 0) begin                       // P0 + P1 -> q3
                            a_iv <= 1'b1; a_a <= (MUT_CARRY != 0) ? 256'd0 : c_d[i][0]; a_b <= lp_d[i]; a_it <= 3'(i); a_is <= 2'd0;
                            lpv[i] = 1'b0; cv[i][0] = 1'b0; issued = 1'b1;
                        end
                        default: if ((cv[i][2] && c_v[i][2] && carry_landed[i][2]) || MUT_CARRY != 0) begin                    // q3: P2 + P3 first
                            a_iv <= 1'b1; a_a <= (MUT_CARRY != 0) ? 256'd0 : c_d[i][2]; a_b <= lp_d[i]; a_it <= 3'(i); a_is <= 2'd2;
                            lpv[i] = 1'b0; cv[i][2] = 1'b0; issued = 1'b1;
                        end
                    endcase
                end
            end
            // q3 TREE second add: (P0 + P1) + (P2 + P3)
            for (i = 0; i < NT; i = i + 1) if (!issued && tv[i] && t_v[i] && tree_landed[i] && cv[i][1] && c_v[i][1] && carry_landed[i][1]) begin
                a_iv <= 1'b1; a_a <= c_d[i][1]; a_b <= t_d[i]; a_it <= 3'(i); a_is <= 2'd1;
                tv[i] = 1'b0; cv[i][1] = 1'b0; issued = 1'b1;
            end
            // -- CTRL to HOME (counters; the HOME stop reports its own events directly)
            if (me == 2'(HOME)) begin
                hp[me] = ev_pop; hd[me] = ev_done; if (ev_fault) h_fault[me] <= 1'b1;
            end else begin : ctl
                reg [2:0] np, nd;
                np = n_pop + (ev_pop ? 3'd1 : 3'd0); nd = n_done + (ev_done ? 3'd1 : 3'd0);
                dir = is_ccw(me, 2'(HOME)) ? 2'd1 : 2'd0;
                // one CTRL flit an edge carries one pop and / or one done and the fault level; queued only when the
                // direction's queue is empty so CTRL never crowds out carries
                if ((np != 0 || nd != 0 || (ev_fault && !f_sent)) && qn[dir] == 0) begin
                    iq[dir][qt[dir]] <= mk(K_CTRL, me, 2'(HOME), 2'd0, 3'd0, 1'b0, {8'd0, nd != 0, np != 0, ev_fault}, 256'd0);
                    qt[dir] = inc(qt[dir]); qn[dir] = qn[dir] + 1'b1;
                    if (np != 0) np = np - 3'd1; if (nd != 0) nd = nd - 3'd1; if (ev_fault) f_sent <= 1'b1;
                end
                n_pop <= np; n_done <= nd;
            end
            h_pop <= hp; h_done <= hd;
            // -- outputs: transit first, else the queue head
            for (integer d = 0; d < 2; d = d + 1) begin
                if (fo[d][RW-1]) begin if (d == 0) cw_o <= fo[d]; else ccw_o <= fo[d]; end
                else if (iq_n[d] != 0) begin       // entries written before this edge only (an entry queued this edge is
                                                     // a non-blocking write: it can leave from the next edge on)
                    if (d == 0) cw_o <= iq[d][qh[d]]; else ccw_o <= iq[d][qh[d]];
                    qh[d] = inc(qh[d]); qn[d] = qn[d] - 1'b1;
                end else begin if (d == 0) cw_o <= '0; else ccw_o <= '0; end
                if (qn[d] > QD) fault <= 1'b1;
            end
            for (i = 0; i < 2; i = i + 1) begin iq_n[i] <= qn[i]; iq_h[i] <= qh[i]; iq_t[i] <= qt[i]; end
            for (i = 0; i < NT; i = i + 1) begin lp_v[i] <= lpv[i]; t_v[i] <= tv[i]; busy[i] <= bz[i];
                for (integer s = 0; s < 4; s = s + 1) c_v[i][s] <= cv[i][s]; end
        end
    end
    `undef F_V
    `undef F_KIND
    `undef F_SRC
    `undef F_DST
    `undef F_TTL
    `undef F_TAG
    `undef F_MODE
    `undef F_AUX
    `undef F_D
endmodule

// One tag payload leaf: direct pin capture for every data/control input, then storage.
// Four kept control copies bound every enable/mux net to one 64-bit region.
module ot_hgi_coll_pring_state (
    input wire clk,
    input wire lp_wr, tree_wr,
    input wire [255:0] lp_data, tree_data,
    input wire [3:0] carry_wr0, carry_wr1,
    input wire [511:0] carry_data,
    output reg [255:0] lp, tree, c0, c1, c2, c3
);
    reg [255:0] lp_pin, tree_pin; reg [511:0] carry_pin;
    (* keep = 1, dont_touch = 1 *) reg [9:0] enable_pin [0:3];
    always @(posedge clk) begin
        lp_pin <= lp_data; tree_pin <= tree_data; carry_pin <= carry_data;
        for (integer r = 0; r < 4; r = r + 1) begin
            enable_pin[r] <= {carry_wr1,carry_wr0,tree_wr,lp_wr};
            if (enable_pin[r][0]) lp[r*64 +: 64] <= lp_pin[r*64 +: 64];
            if (enable_pin[r][1]) tree[r*64 +: 64] <= tree_pin[r*64 +: 64];
            if (enable_pin[r][2]) c0[r*64 +: 64] <= carry_pin[r*64 +: 64];
            if (enable_pin[r][3]) c1[r*64 +: 64] <= carry_pin[r*64 +: 64];
            if (enable_pin[r][4]) c2[r*64 +: 64] <= carry_pin[r*64 +: 64];
            if (enable_pin[r][5]) c3[r*64 +: 64] <= carry_pin[r*64 +: 64];
            if (enable_pin[r][6]) c0[r*64 +: 64] <= carry_pin[256+r*64 +: 64];
            if (enable_pin[r][7]) c1[r*64 +: 64] <= carry_pin[256+r*64 +: 64];
            if (enable_pin[r][8]) c2[r*64 +: 64] <= carry_pin[256+r*64 +: 64];
            if (enable_pin[r][9]) c3[r*64 +: 64] <= carry_pin[256+r*64 +: 64];
        end
    end
endmodule

// Pin capture + seven real FP cuts at LAT8, one independent native adder root per lane.
module ot_hgi_coll_pring_add_lane #(parameter integer LAT = 8) (
    input wire clk, rst_n, valid_in,
    input wire [31:0] a, b,
    output wire [31:0] y,
    output wire valid_out
);
    reg [31:0] a_pin, b_pin; reg v_pin;
    always @(posedge clk) begin a_pin <= a; b_pin <= b; end
    always @(posedge clk or negedge rst_n) if (!rst_n) v_pin <= 0; else v_pin <= valid_in;
    ot_hdc_fp32_add_lat #(.LAT(LAT-1), .DRST(0)) u_fp (.clk(clk), .rst_n(rst_n), .valid_in(v_pin),
        .a(a_pin), .b(b_pin), .y(y), .err(), .valid_out(valid_out));
endmodule

`default_nettype wire
