`timescale 1ns/1ps
`default_nettype none
// ot_s81_retn_static -- S81 return-tree node on the compiler's fixed cycle calendar (S-NET, 2026-10-15).
//
// Replaces ot_v41_retn_w17w10 (ot_v41_ret_node D=64 queues + WAIT-timeout forwarding + "older side first" / "yield to an
// add result" arbitration) under the owner rule of 2026-10-14 18:59 (static cycle schedule, no credits/backpressure,
// no runtime arbitration).  Same ports and the same partial format/tag arithmetic (ot_v41_ret_pkg norm/sibling/parent,
// golden csum siblings, bit-identical ot_fp32_add_rne_pipe), so the die binding is unchanged.
//
// FIXED-SLOT RULE (the compiler's model is tools/s81/static_return_calendar.py, which reproduces it cycle for cycle):
//   * a word arriving at edge n (x_v sampled high) enters its side's sibling WINDOW of WIN fixed stages;
//   * it MERGES with its golden sibling if that sibling arrives on the other side at an edge in [n - WIN, n + WIN]
//     (same edge included); the merge issues the adder at the later arrival edge;
//   * a word whose sibling did not arrive within WIN edges leaves the window at edge n + WIN and is FORWARDED;
//   * every output word -- forwarded or summed -- is visible at edge  early + WIN + 10 + RST  (o_v sampled high), where early = the arrival edge of the word (of the EARLIER sibling for a sum).
//   PIPELINE (r2, 2026-10-15 n5, structural fix of the n2 routes TT -798..-2034 ps: port -> norm -> sibling match ->
//   parent(norm) -> adder stage 1 in one cycle, logic depth 1,615 ps): three fixed stages, uniform for every word, so
//   the slot rule is unchanged and only the constant moves from 7 to 10 (compiler model static_return_calendar.py):
//     P1 port register (raw words), P2 normalised-tag register (norm off the match path), P3 issue register in front
//     of the adder and the forward lane; parent() = norm(pre-parent) is applied at the 5-stage side-band output, off
//     the issue path.  A per-node exit
//     calendar (S slots, indexed by the exit edge) holds a sum whose late sibling arrived before the window end.
//   There is no queue, no occupancy counter, no timeout counter, no priority choice and no ready: the action of every
//   word and its output slot are pure functions of the compiled arrival edges.
//
// COMPILER OBLIGATIONS (asserted here; any violation sets the sticky fault and never re-times traffic):
//   F1 at most one exit-slot owner per edge: two unmerged words arriving at the same edge on a and b collide;
//   F2 at most one merge issue per edge (one adder);
//   F3 a word matches at most one sibling (unique golden tags);
//   F4 a calendar slot is written once (follows from F1/F2 for a correct implementation; checked independently).
// Storage is static: 2 x WIN window entries + S exit slots + the 5-stage adder / forward lanes (the D=64 x 2 x 65-bit
// queues of the dynamic node are gone).
module ot_s81_retn_static #(
    parameter integer WIN = 2,           // sibling window, edges (>= 1)
    parameter integer RST = 1,           // output register stages (wire reach), as ot_v41_retn_w17w10
    parameter integer MUT = 0,           // bench mutants only: 1 window off by one, 2 forward slot +1, 3 fault blind
    // DLR (S81U-CAP4 2026-10-17, default 0 = the shift form, netlist unchanged for every existing node tile): the two
    // AL-deep side-band lanes (q_asb + u_asb, q_fsb + u_fsb: (34+SW) + (66+SW) bits x 6 registers) as cycle-exact
    // register-file delay lines ot_hdc_delay_rf D = AL + 1 (input register = the old q_*sb, N = AL - 1 rows written once
    // and read through the N:1 mux, output register), so no zero-logic flop -> flop hop is left in them.  Same flop count,
    // same edges.  Why: s81sl_cap_tr route 9df7f8153 (3 nodes, 6,200 sinks) NEEDS_RTL FF hold -6.37 ps; all 188 violators
    // are flop -> INV -> flop pass hops (93 of them in u_fsb / u_asb), capture clock 14 ps after launch, ECO 7,489 cells.
    parameter integer DLR = 0,
    // ADDN (S81U-CAP5 2026-10-17, default 0 = ot_fp32_add_rne_pipe, netlist unchanged for every existing tile): 1 = the
    // bit-identical ot_s81_fadd_pipe below (valid-only reset: the adder's ~350 datapath reset flops made the node's reset
    // net 401 loads in s81sl_cap_rt; stage 3 is one add with the sub's inversion and the zero test moved into stage 2 and
    // the carry renormalize moved into stage 4: same 5 edges).
    parameter integer ADDN = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        a_v,
    input  wire [31:0] a_t,
    input  wire [31:0] a_d,
    input  wire        a_e,
    input  wire        b_v,
    input  wire [31:0] b_t,
    input  wire [31:0] b_d,
    input  wire        b_e,
    output wire        o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e,
    output reg         fault
);
    // ot_v41_ret_pkg norm / complete / sibling / parent, copied verbatim (the ORFS yosys front end has no package import)
    localparam integer TW = 3 + 16 + 5 + 3 + 5;   // {position, row, lo, k, nseg}
    // norm(): the ot_v41_ret_pkg loop "k++ while C(k)" (5 iterations, k < 5 only) in closed form (n5b: the serial loop
    // synthesised to 35 levels / ~1,275 ps).  C(j) for j = 0..4 are independent; k_final = the first j >= k with !C(j),
    // else 5; k >= 5 is never incremented.  Bit-identical to the loop (exhaustive check tools/s81/static_return_calendar.py
    // norm_closed_check).
    function automatic [TW-1:0] norm(input [TW-1:0] t);
        reg [18:0] row;
        reg [4:0] lo, n, c;
        reg [2:0] k, kf;
        integer j;
        begin
            {row, lo, k, n} = t;
            for (j = 0; j < 5; j = j + 1)
                c[j] = !(lo == 5'd0 && (6'd1 << j) >= {1'b0, n}) && lo[j] == 1'b0 && ({1'b0, lo} + (6'd1 << j)) >= {1'b0, n};
            kf = k;
            if (k < 3'd5) begin
                kf = 3'd5;
                for (j = 4; j >= 0; j = j - 1)
                    if (j >= k && !c[j]) kf = j;
            end
            norm = {row, lo, kf, n};
        end
    endfunction
    function automatic complete(input [TW-1:0] t);
        complete = t[12:8] == 5'd0 && (6'd1 << t[7:5]) >= {1'b0, t[4:0]};
    endfunction
    function automatic sibling(input [TW-1:0] a, input [TW-1:0] b);
        sibling = a[31:13] == b[31:13] && a[7:5] == b[7:5] && a[4:0] == b[4:0] &&
                  (a[12:8] ^ b[12:8]) == (5'd1 << a[7:5]);
    endfunction
    function automatic [TW-1:0] preparent(input [TW-1:0] a, input [TW-1:0] b);   // parent() before its norm()
        preparent = {a[31:13], (a[12:8] < b[12:8]) ? a[12:8] : b[12:8], a[7:5] + 3'd1, a[4:0]};
    endfunction
    function automatic [TW-1:0] parent(input [TW-1:0] a, input [TW-1:0] b);
        reg [4:0] lo;
        begin
            lo = (a[12:8] < b[12:8]) ? a[12:8] : b[12:8];
            parent = norm({a[31:13], lo, a[7:5] + 3'd1, a[4:0]});
        end
    endfunction
    localparam integer WE = (MUT == 1) ? WIN + 1 : WIN;      // mutant 1: window one edge too long
    localparam integer SL = (WIN + 2 <= 4) ? 4 : (WIN + 2 <= 8) ? 8 : 16;   // exit calendar slots (power of two)
    localparam integer SW = $clog2(SL);
    localparam integer AL = 5;                                 // ot_fp32_add_rne_pipe latency (edges)

    // ---------------- sibling windows: entry k holds the word that arrived k+1 edges ago --------------------------
    reg          wa_v [0:WE-1], wb_v [0:WE-1];
    reg [31:0]   wa_t [0:WE-1], wb_t [0:WE-1], wa_d [0:WE-1], wb_d [0:WE-1];
    reg          wa_e [0:WE-1], wb_e [0:WE-1];

    // ---------------- P1 port registers, P2 normalised tag registers ------------------------------------------------
    reg         p1a_v, p1b_v, p2a_v, p2b_v;
    reg  [31:0] p1a_t, p1a_d, p1b_t, p1b_d, na, nb, pa_d, pb_d;
    reg         p1a_e, p1b_e, pa_e, pb_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin p1a_v <= 1'b0; p1b_v <= 1'b0; p2a_v <= 1'b0; p2b_v <= 1'b0; end
        else begin p1a_v <= a_v; p1b_v <= b_v; p2a_v <= p1a_v; p2b_v <= p1b_v; end
    end
    always @(posedge clk) begin
        p1a_t <= a_t; p1a_d <= a_d; p1a_e <= a_e; p1b_t <= b_t; p1b_d <= b_d; p1b_e <= b_e;
        na <= norm(p1a_t); pa_d <= p1a_d; pa_e <= p1a_e; nb <= norm(p1b_t); pb_d <= p1b_d; pb_e <= p1b_e;
    end
    wire xa_v = p2a_v, xb_v = p2b_v;
    wire m_ab = xa_v && xb_v && sibling(na, nb);               // same-edge siblings
    reg  [WE-1:0] ma, mb;                                      // a vs window b, b vs window a
    integer k;
    always @* begin
        for (k = 0; k < WE; k = k + 1) begin
            ma[k] = xa_v && wb_v[k] && sibling(na, wb_t[k]);
            mb[k] = xb_v && wa_v[k] && sibling(nb, wa_t[k]);
        end
    end
    // one-hot picks (F3: more than one match is a fault; the lowest index is used, deterministically)
    function automatic integer first1(input [WE-1:0] v);
        integer i; begin first1 = -1; for (i = WE - 1; i >= 0; i = i - 1) if (v[i]) first1 = i; end
    endfunction
    function automatic integer cnt1(input [WE-1:0] v);
        integer i; begin cnt1 = 0; for (i = 0; i < WE; i = i + 1) cnt1 = cnt1 + v[i]; end
    endfunction
    integer ka, kb;
    always @* begin ka = first1(ma); kb = first1(mb); end
    wire a_win = !m_ab && ka >= 0;                             // a merges with an older b
    wire b_win = !m_ab && kb >= 0;                             // b merges with an older a
    wire add2 = a_win && b_win;                                // F2 violation
    wire multi = (cnt1(ma) + (m_ab ? 1 : 0) > 1) || (cnt1(mb) + (m_ab ? 1 : 0) > 1);   // F3 violation

    // merge issue this edge: operands, tag, error, and the earlier sibling's age (edges since its arrival)
    reg         is_add;
    reg  [31:0] add_x, add_y, add_t;
    reg         add_e;
    reg  [SW:0] add_age;
    always @* begin
        is_add = 1'b0; add_x = 32'd0; add_y = 32'd0; add_t = 32'd0; add_e = 1'b0; add_age = '0;
        if (m_ab) begin
            is_add = 1'b1; add_x = pa_d; add_y = pb_d; add_t = preparent(na, nb); add_e = pa_e | pb_e; add_age = '0;
        end else if (a_win) begin
            is_add = 1'b1; add_x = pa_d; add_y = wb_d[ka]; add_t = preparent(na, wb_t[ka]); add_e = pa_e | wb_e[ka];
            add_age = ka + 1;
        end else if (b_win) begin
            is_add = 1'b1; add_x = wa_d[kb]; add_y = pb_d; add_t = preparent(wa_t[kb], nb); add_e = wa_e[kb] | pb_e;
            add_age = kb + 1;
        end
    end
    // consumption of window entries this edge
    wire [WE-1:0] ca, cb;
    genvar g;
    generate for (g = 0; g < WE; g = g + 1) begin : g_c
        assign cb[g] = !m_ab && a_win && ka == g;
        assign ca[g] = !m_ab && b_win && !a_win && kb == g;
    end endgenerate
    // arrivals that stay in the window (not merged on arrival)
    wire a_in = xa_v && !m_ab && !a_win;
    wire b_in = xb_v && !m_ab && !(b_win && !a_win);
    // window exits (unmerged, age WE): forwarded
    wire fa = wa_v[WE-1] && !ca[WE-1];
    wire fb = wb_v[WE-1] && !cb[WE-1];
    wire fwd2 = fa && fb;                                      // F1 violation (two exit-slot owners)
    wire        is_fwd = fa | fb;
    wire [31:0] fw_t = fa ? wa_t[WE-1] : wb_t[WE-1];
    wire [31:0] fw_d = fa ? wa_d[WE-1] : wb_d[WE-1];
    wire        fw_e = fa ? wa_e[WE-1] : wb_e[WE-1];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < WE; k = k + 1) begin wa_v[k] <= 1'b0; wb_v[k] <= 1'b0; end
        end else begin
            wa_v[0] <= a_in; wb_v[0] <= b_in;
            for (k = 1; k < WE; k = k + 1) begin
                wa_v[k] <= wa_v[k-1] && !ca[k-1];
                wb_v[k] <= wb_v[k-1] && !cb[k-1];
            end
        end
    end
    always @(posedge clk) begin
        wa_t[0] <= na; wa_d[0] <= pa_d; wa_e[0] <= pa_e;
        wb_t[0] <= nb; wb_d[0] <= pb_d; wb_e[0] <= pb_e;
        for (k = 1; k < WE; k = k + 1) begin
            wa_t[k] <= wa_t[k-1]; wa_d[k] <= wa_d[k-1]; wa_e[k] <= wa_e[k-1];
            wb_t[k] <= wb_t[k-1]; wb_d[k] <= wb_d[k-1]; wb_e[k] <= wb_e[k-1];
        end
    end

    // ---------------- 5-stage lanes: adder + matched forward delay ---------------------------------------------------
    wire [31:0] sum; wire [1:0] err; wire sv;
    // P3 issue register: the adder, its side band and the forward lane start from flops (uniform +1 edge)
    reg         q_add, q_fwd;
    reg  [31:0] q_x, q_y;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin q_add <= 1'b0; q_fwd <= 1'b0; end
                                           else begin q_add <= is_add; q_fwd <= is_fwd; end
    always @(posedge clk) begin q_x <= add_x; q_y <= add_y; end
    generate if (ADDN != 0) begin : g_addn
        ot_s81_fadd_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(q_add), .a(q_x), .b(q_y),
                                .y(sum), .err(err), .valid_out(sv));
    end else begin : g_addr
        ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(q_add), .a(q_x), .b(q_y),
                                    .y(sum), .err(err), .valid_out(sv));
    end endgenerate
    // side band of the add: tag, error, wait-to-exit; forward lane: word + wait
    // exit edge = early + WIN + EXIT_C.  A sum issued at edge n whose earlier sibling arrived age edges before waits
    // WIN - age more edges than a forward (which issues at age WIN).
    localparam integer FWD_WAIT = (MUT == 2) ? 2 : 1;        // a forward issues at age WIN: one edge in the calendar
    localparam [SW:0] WIN1 = WIN + 1;
    wire [SW:0] add_wait = WIN1 - add_age;                     // sum: early + WIN + 6 = issue + 5 + (WIN + 1 - age)
    wire [32+1+SW:0] add_sb, add_sbq, asb_rf;
    reg  [32+1+SW:0] q_asb;
    always @(posedge clk) q_asb <= {add_t, add_e, add_wait};
    assign add_sb = (DLR != 0) ? asb_rf : q_asb;
    ot_hdc_delay #(.W(34 + SW), .D((DLR != 0) ? 0 : AL)) u_asb (.clk(clk), .rst_n(rst_n), .d(add_sb), .q(add_sbq));
    wire [65+SW:0] fw_sb, fw_sbq, fsb_rf;
    localparam [SW:0] FWW = FWD_WAIT;
    reg  [65+SW:0] q_fsb;
    always @(posedge clk) q_fsb <= {fw_t, fw_d, fw_e, FWW};
    assign fw_sb = (DLR != 0) ? fsb_rf : q_fsb;
    ot_hdc_delay #(.W(66 + SW), .D((DLR != 0) ? 0 : AL)) u_fsb (.clk(clk), .rst_n(rst_n), .d(fw_sb), .q(fw_sbq));
    generate if (DLR != 0) begin : g_dlr   // q_*sb + D = AL shift == rf D = AL + 1 (q_*sb unused, removed by synthesis)
        ot_hdc_delay_rf #(.W(34 + SW), .D(AL + 1)) u_asb_rf (.clk(clk), .rst_n(rst_n), .d({add_t, add_e, add_wait}),
                                                            .q(asb_rf));
        ot_hdc_delay_rf #(.W(66 + SW), .D(AL + 1)) u_fsb_rf (.clk(clk), .rst_n(rst_n), .d({fw_t, fw_d, fw_e, FWW}),
                                                            .q(fsb_rf));
    end else begin : g_shl
        assign asb_rf = '0;
        assign fsb_rf = '0;
    end endgenerate
    reg [AL-1:0] fv;
    always @(posedge clk or negedge rst_n) if (!rst_n) fv <= '0; else fv <= {fv[AL-2:0], q_fwd};
    wire fwd_v5 = fv[AL-1];

    // ---------------- exit calendar ---------------------------------------------------------------------------------
    reg [SW-1:0] now;                                          // free-running edge counter (mod SL)
    reg          cal_v [0:SL-1];
    reg [31:0]   cal_t [0:SL-1], cal_d [0:SL-1];
    reg          cal_e [0:SL-1];
    wire [SW-1:0] slot_a = now + add_sbq[SW-1:0];
    wire [SW-1:0] slot_f = now + fw_sbq[SW-1:0];
    wire coll = (sv && cal_v[slot_a]) || (fwd_v5 && cal_v[slot_f]) || (sv && fwd_v5 && slot_a == slot_f);   // F4
    reg         r_v, r_e;
    reg  [31:0] r_t, r_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            now <= '0; r_v <= 1'b0; fault <= 1'b0;
            for (k = 0; k < SL; k = k + 1) cal_v[k] <= 1'b0;
        end else begin
            now <= now + 1'b1;
            r_v <= cal_v[now];
            cal_v[now] <= 1'b0;
            if (sv && !cal_v[slot_a]) cal_v[slot_a] <= 1'b1;
            if (fwd_v5 && !(sv && slot_a == slot_f) && !cal_v[slot_f]) cal_v[slot_f] <= 1'b1;
            if (MUT != 3 && (fwd2 || add2 || multi || coll)) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        r_t <= cal_t[now]; r_d <= cal_d[now]; r_e <= cal_e[now];
        if (sv && !cal_v[slot_a]) begin
            cal_t[slot_a] <= norm(add_sbq[33+SW:2+SW]); cal_d[slot_a] <= sum;   // parent = norm(pre-parent)
            cal_e[slot_a] <= add_sbq[1+SW] | (err != 2'd0);
        end
        if (fwd_v5 && !(sv && slot_a == slot_f) && !cal_v[slot_f]) begin
            cal_t[slot_f] <= fw_sbq[65+SW:34+SW]; cal_d[slot_f] <= fw_sbq[33+SW:2+SW]; cal_e[slot_f] <= fw_sbq[1+SW];
        end
    end

    // ---------------- RST output register stages (as ot_v41_retn_w17w10) --------------------------------------------
    wire [65:0] rq;
    ot_hdc_delay #(.W(66), .D(RST)) u_rd (.clk(clk), .rst_n(rst_n), .d({r_t, r_d, r_e, 1'b0}), .q(rq));
    wire [RST:0] rv;
    assign rv[0] = r_v;
    genvar r;
    generate for (r = 0; r < RST; r = r + 1) begin : g_rv
        reg q;
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= rv[r];
        assign rv[r+1] = q;
    end endgenerate
    assign o_v = rv[RST];
    assign o_t = rq[65:34];
    assign o_d = rq[33:2];
    assign o_e = rq[1];
`ifndef SYNTHESIS
    initial if (WIN < 1 || WIN > 14) $fatal(1, "ot_s81_retn_static: 1 <= WIN <= 14");
`endif
endmodule


// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_fadd_pipe (S81U-CAP5 2026-10-17): ot_fp32_add_rne_pipe, bit-identical (y, err, valid_out at the same 5 edges;
// equivalence bench rtl/dsrom_sys/s81_dv/slice/test/tb_s81_fadd_eq.sv), restructured for the s81sl_cap_rt gate:
//   * reset only on the valid chain: the datapath registers carry no reset (the original resets all ~350 of them, which
//     made every node / finish reset net 384-401 loads);
//   * stage 2 registers the small operand already inverted for a subtraction and the exact-cancellation flag
//     (|a| == |b| <=> dist == 0 && big == small: for dist > 0 the big operand is normal, >= 2^26 in the 28-bit frame,
//     and the shifted small one is < 2^26), so stage 3 is ONE 28-bit add (big + small' + sub) with no sum/dif mux and
//     no 28-bit zero detect behind it (gate: u_add.s2_small -> s3_val 18 levels ~647 ps);
//   * the carry renormalize (shift right one, exponent + 1) moves into stage 4, where a carry excludes the cancellation
//     normalize (carry => add => no left shift), so stage 4 gains one final 2:1 mux and nothing else.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_fadd_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;
    integer k;
    // -- stage 1: decode, order by magnitude, resolve the zero operands (as ot_fp32_add_rne_pipe)
    wire        a_sign = a[31], b_sign = b[31];
    wire [7:0]  a_field = a[30:23], b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire s1_nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_is_zero = (a_man == 24'd0);
    wire b_is_zero = (b_man == 24'd0);
    wire s1_bypass = s1_nonfinite || a_is_zero || b_is_zero;
    wire [31:0] s1_bypass_code = s1_nonfinite ? 32'd0 : (a_is_zero ? (b_is_zero ? 32'd0 : b) : a);
    wire swap = (b_exp > a_exp) || ((b_exp == a_exp) && (b_man > a_man));
    reg        s1_v, s2_v, s3_v, s4_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v <= 1'b0; s2_v <= 1'b0; s3_v <= 1'b0; s4_v <= 1'b0; valid_out <= 1'b0; end
        else begin s1_v <= valid_in; s2_v <= s1_v; s3_v <= s2_v; s4_v <= s3_v; valid_out <= s4_v; end
    reg        s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp, s1_dist;
    reg [23:0] s1_big, s1_small;
    always @(posedge clk) begin
        s1_byp <= s1_bypass;
        s1_err <= s1_nonfinite ? E_NONFINITE : E_NONE;
        s1_code <= s1_bypass_code;
        s1_sub <= (a_sign != b_sign);
        s1_sign <= swap ? b_sign : a_sign;
        s1_exp <= swap ? b_exp : a_exp;
        s1_dist <= (swap ? b_exp : a_exp) - (swap ? a_exp : b_exp);
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? a_man : b_man;
    end
    // -- stage 2: align (jamming), invert for a subtraction, exact-cancellation flag
    function automatic [27:0] shift_right_jam_28(input [27:0] value, input [7:0] distance);
        reg discarded; reg [27:0] shifted; integer bit_index;
        begin
            discarded = 1'b0; shifted = 28'd0;
            if (distance == 8'd0) shifted = value;
            else if (distance >= 8'd28) shifted[0] = |value;
            else begin
                shifted = value >> distance;
                for (bit_index = 0; bit_index < 28; bit_index = bit_index + 1)
                    if ({24'd0, bit_index[7:0]} < distance) discarded = discarded | value[bit_index];
                shifted[0] = shifted[0] | discarded;
            end
            shift_right_jam_28 = shifted;
        end
    endfunction
    wire [27:0] s2_sh = shift_right_jam_28({1'b0, s1_small, 3'b000}, s1_dist);
    reg        s2_byp, s2_sub, s2_sign, s2_eq;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [27:0] s2_big, s2_smallx;
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_sub <= s1_sub; s2_sign <= s1_sign; s2_err <= s1_err; s2_code <= s1_code; s2_exp <= s1_exp;
        s2_big <= {1'b0, s1_big, 3'b000};
        s2_smallx <= s1_sub ? ~s2_sh : s2_sh;
        s2_eq <= (s1_dist == 8'd0) && (s1_big == s1_small);
    end
    // -- stage 3: ONE add (big + small + 0, or big + ~small + 1 = big - small: big >= small, no borrow)
    wire [27:0] s3_arith = s2_big + s2_smallx + {27'd0, s2_sub};
    reg        s3_byp, s3_sub, s3_sign, s3_zero, s3_carry;
    reg [1:0]  s3_err;
    reg [31:0] s3_code;
    reg [7:0]  s3_exp;
    reg [27:0] s3_raw;
    always @(posedge clk) begin
        s3_byp <= s2_byp; s3_sub <= s2_sub; s3_sign <= s2_sign; s3_err <= s2_err; s3_code <= s2_code;
        s3_zero <= s2_sub && s2_eq;
        s3_exp <= s2_exp;
        s3_raw <= s3_arith;
        s3_carry <= !s2_sub && s3_arith[27];
    end
    // -- stage 4: carry renormalize OR cancellation normalize (exclusive: a carry is an add)
    wire [26:0] s4_in = s3_raw[26:0];
    wire [26:0] s4_rsh = {s3_raw[27:2], s3_raw[1] | s3_raw[0]};
    reg [4:0] s4_lz;
    always @* begin
        s4_lz = 5'd27;
        for (k = 0; k <= 26; k = k + 1)
            if (s4_in[k]) s4_lz = 5'd26 - k[4:0];
    end
    wire [7:0] s4_room = s3_exp - 8'd1;
    wire [7:0] s4_shift = ({3'd0, s4_lz} > s4_room) ? s4_room : {3'd0, s4_lz};
    wire       s4_apply = s3_sub && !s3_zero && !s3_byp;
    reg        s4_byp, s4_sign, s4_zero;
    reg [1:0]  s4_err;
    reg [31:0] s4_code;
    reg [7:0]  s4_exp;
    reg [26:0] s4_val;
    always @(posedge clk) begin
        s4_byp <= s3_byp; s4_sign <= s3_sign; s4_zero <= s3_zero; s4_err <= s3_err; s4_code <= s3_code;
        s4_exp <= s3_carry ? (s3_exp + 8'd1) : s4_apply ? (s3_exp - s4_shift) : s3_exp;
        s4_val <= s3_carry ? s4_rsh : s4_apply ? (s4_in << s4_shift) : s4_in;
    end
    // -- stage 5: round to nearest even, encode, fail closed on overflow (as ot_fp32_add_rne_pipe)
    wire [24:0] s5_trunc = {1'b0, s4_val[26:3]};
    wire        s5_inc = s4_val[2] && ((|s4_val[1:0]) || s4_val[3]);
    wire [24:0] s5_round = s5_trunc + {24'd0, s5_inc};
    wire        s5_carry = s5_round[24];
    wire [23:0] s5_man = s5_carry ? s5_round[24:1] : s5_round[23:0];
    wire [7:0]  s5_exp = s5_carry ? (s4_exp + 8'd1) : s4_exp;
    wire        s5_subnormal = (s5_exp == 8'd1) && !s5_man[23];
    wire [31:0] s5_code = {s4_sign, s5_subnormal ? 8'd0 : s5_exp, s5_man[22:0]};
    wire        s5_over = (s4_exp >= 8'hff) || (s5_exp >= 8'hff);
    always @(posedge clk) begin
        if (s4_byp) begin y <= s4_code; err <= s4_err; end
        else if (s4_zero) begin y <= 32'd0; err <= E_NONE; end
        else if (s5_over) begin y <= 32'd0; err <= E_OVERFLOW; end
        else begin y <= (s5_code[30:0] == 31'd0) ? 32'd0 : s5_code; err <= E_NONE; end
    end
endmodule
`default_nettype wire
