`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT3 (2026-10-17): dsdv_gunit_l0r -- G-unit side leaf L0r (E of L0): the HP root store (2 window buffers x 16
// slices x 2 halves x 6 words of 32 bits = 12,288 flops) and the level-5 group stream, split out of L0 (the one-leaf L0
// was 15,319 sinks on one root, TT insertion 333 ps: clock-rule FAIL).  W face only (L0): every input lands in a flop,
// every output leaves a flop.
//   wr_*   store writes (L0 registers them on the edge the one-leaf form wrote): slot {g, h} = wr_?gh, buffer wr_b,
//          words j = 0..5 = wr_?d[32 j +: 32]; two writes (a, b) an edge.
//   go_*   window complete (accumulation go_acc in buffer go_b): the 16-group stream starts on the edge after it lands.
//   r_*    the stream, one group a cycle (L0 relays it to L4):  group i = 4 k + m = slices 4m .. 4m+3, half k >> 1,
//          words (k & 1) * 3 + 0..2: {D32, D8, C8, C16b, C16a, B16b, B16a, B8, A8, A32}.
// Timing: a write lands in the store 2 edges after L0's register, a go starts the stream 2 edges after L0's register,
// so a window's last write is in the store before the stream's first read (the same order as the one-leaf form).
// The read select is replicated per output byte (40 copies, keep; S81U-GUNIT4: the per-word copy drove 3,059 loads,
// the leaf's worst reg->reg path): one copy drives 8 bits of a 32:1 word mux (R13: registered one-hot copy, AND-OR read).
// S81U-GUNIT6 (10-17, native pin rules): rst_n drives only ot_rst_relay (2 kept region copies: input flops, stream);
// release +3 edges after the port (transaction-level exact).  0 data edges.
// r_f (sticky): a go while the previous stream still runs.  MUT (bench only): 6 = roots 1 / 2 of g = 1 mod 4 swapped.
// ---------------------------------------------------------------------------------------------------------------------
// S81-RF1 RE-FORM (DIE-S81-51/RF-D 11-03, S81-064, OWNER TWO-STRIKES): the last full run failed GRT TT -101.64 ps
// (TNS -777 ns: the store's write side), path bgh -> 6 * bgh + 192 * wb + j address adder (HA/FA chain) -> 384-word
// write decode -> a/b priority -> ~12k store flop enables.  RF = 1 (default): the write slot is decoded ONE edge
// earlier into registered one-hot enables (wa_oh / wb_oh, 64 slots = {wb, gh}) beside a data copy (ad2 / bd2), so a
// store flop's D is a flop -> 2:1 priority mux -> flop (no address arithmetic, no decode on the path); b still wins over
// a on the same slot.  The window go is delayed by the same edge (ga2 / gacc2 / gb2), so a window's last write still
// lands on the edge its stream's first one-hot read select does (same order as RF 0).  Ports and transactions
// unchanged; every r_* output is +1 edge (RF 1 == RF 0 one edge later, bench results/rfd_1103/l0r): gunit HC latency
// +1 (lower_gu HC_LAT_N / HC_LAT_S +1, parent contract).  RF = 0: the old form.
// RF = 2 (form 2, 11-03; RF 1 build oth-ubuntu-1507612 met setup (GRT SS ws +168.5) but stopped at OT_HOLD_STRUCTURAL GRT
// FF hold ws -154.31 / 408 ep: the input faces (rst_n -> u_rst removal, go_a -> ga, wr_* -> input flops) captured on
// the rising edge with the core insertion ~281 ps vs vclk 250): RF 1 + a NEGEDGE IN-FACE: every input (incl. rst_n) lands
// in a negative-edge flop, then the unchanged posedge input flop (0 cycles: the posedge flop takes the value it took
// before; pin hold window ~T/2 by construction, as dsdv_bk_g RF 1).  rst_n assertion lands half an edge later, the
// release edge is unchanged (rst_n leaves a posedge flop).  Outputs / latency identical to RF 1.
module dsdv_gunit_l0r #(
    parameter integer MUT = 0,
`ifdef OT_GUNIT_L0R_RF0
    parameter integer RF  = 0         // benches: +define+OT_GUNIT_L0R_RF0 = the old form under an unchanged parent
`elsif OT_GUNIT_L0R_RF1
    parameter integer RF  = 1         // benches: form 1 (posedge in-face)
`else
    parameter integer RF  = 2
`endif
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          wr_av, input wire [4:0] wr_agh, input wire [191:0] wr_ad,
    input  wire          wr_bv, input wire [4:0] wr_bgh, input wire [191:0] wr_bd, input wire wr_b,
    input  wire          go_a, input wire [4:0] go_acc, input wire go_b,
    output reg           r_v, output reg [3:0] r_i, output reg [4:0] r_acc, output reg [319:0] r_d, output reg r_f
);
    // Private sticky state; the r_f boundary flop drives only the output pin.
    // Both capture the same next value, so this adds one FF and zero cycles.
    (* keep = "true" *) reg fault_hold;
    integer j;
    wire [1:0] rq;
    // ---------------------------------------------------------------- RF 2: negedge in-face
    wire i_rst, i_av, i_bv, i_wb, i_ga, i_gb; wire [4:0] i_agh, i_bgh, i_gacc; wire [191:0] i_ad, i_bd;
    generate if (RF >= 2) begin : g_ifn
        reg n_rst, n_av, n_bv, n_wb, n_ga, n_gb; reg [4:0] n_agh, n_bgh, n_gacc; reg [191:0] n_ad, n_bd;
`ifdef OT_RFD_MUT_L0R2   // RF-D bench mutant: the in-face on the RISING edge (+1 cycle on every input)
        always @(posedge clk) begin
`else
        always @(negedge clk) begin
`endif
            n_rst <= rst_n; n_av <= wr_av; n_bv <= wr_bv; n_wb <= wr_b; n_ga <= go_a; n_gb <= go_b;
            n_agh <= wr_agh; n_bgh <= wr_bgh; n_gacc <= go_acc; n_ad <= wr_ad; n_bd <= wr_bd;
        end
        assign i_rst = n_rst; assign i_av = n_av; assign i_bv = n_bv; assign i_wb = n_wb; assign i_ga = n_ga;
        assign i_gb = n_gb; assign i_agh = n_agh; assign i_bgh = n_bgh; assign i_gacc = n_gacc; assign i_ad = n_ad;
        assign i_bd = n_bd;
    end else begin : g_ifw
        assign i_rst = rst_n; assign i_av = wr_av; assign i_bv = wr_bv; assign i_wb = wr_b; assign i_ga = go_a;
        assign i_gb = go_b; assign i_agh = wr_agh; assign i_bgh = wr_bgh; assign i_gacc = go_acc; assign i_ad = wr_ad;
        assign i_bd = wr_bd;
    end endgenerate
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(i_rst), .rst_n(rq));
    // ---------------------------------------------------------------- input flops
    reg av, bv, wb, ga; reg [4:0] agh, bgh, gacc; reg [191:0] ad, bd; reg gb;
    always @(posedge clk or negedge rq[0])
        if (!rq[0]) begin av <= 1'b0; bv <= 1'b0; ga <= 1'b0; end
        else begin av <= i_av; bv <= i_bv; ga <= i_ga; end
    always @(posedge clk) begin agh <= i_agh; ad <= i_ad; bgh <= i_bgh; bd <= i_bd; wb <= i_wb; gacc <= i_gacc; gb <= i_gb; end
    // ---------------------------------------------------------------- root store (2 window buffers)
    wire [31:0] rsw [0:2*16*2*6-1];                     // the store words as the read side sees them
    wire ga_s, gb_s; wire [4:0] gacc_s;                 // the go as the stream sees it (RF 1: one edge later)
    generate if (RF == 0) begin : g_w0
        reg [31:0] rs [0:2*16*2*6-1];                   // buffer b, slice g, half h, word j (0..5)
        genvar ri;
        for (ri = 0; ri < 384; ri = ri + 1) begin : g_rw0 assign rsw[ri] = rs[ri]; end
        always @(posedge clk) begin
            if (av) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 6 * agh + j] <= ad[32 * j +: 32];
            if (bv) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 6 * bgh + j] <= bd[32 * j +: 32];
        end
        assign ga_s = ga; assign gb_s = gb; assign gacc_s = gacc;
    end else begin : g_w1
        reg [63:0] wa_oh, wb_oh; reg [191:0] ad2, bd2;    // registered one-hot write slots {wb, gh} + data copies
        always @(posedge clk or negedge rq[0])
            if (!rq[0]) begin wa_oh <= 64'd0; wb_oh <= 64'd0; end
            else begin wa_oh <= av ? 64'd1 << {wb, agh} : 64'd0; wb_oh <= bv ? 64'd1 << {wb, bgh} : 64'd0; end
        always @(posedge clk) begin ad2 <= ad; bd2 <= bd; end
        genvar sl, wj;
        for (sl = 0; sl < 64; sl = sl + 1) begin : g_sl
            for (wj = 0; wj < 6; wj = wj + 1) begin : g_wj
                reg [31:0] w;                               // store word 6 sl + wj (plain flops, no memory inference)
                always @(posedge clk)
                    if (wb_oh[sl]) w <= bd2[32 * wj +: 32];
                    else if (wa_oh[sl]) w <= ad2[32 * wj +: 32];
                assign rsw[6 * sl + wj] = w;
            end
        end
        reg ga2, gb2; reg [4:0] gacc2;
        always @(posedge clk or negedge rq[0]) if (!rq[0]) ga2 <= 1'b0; else ga2 <= ga;
        always @(posedge clk) begin gb2 <= gb; gacc2 <= gacc; end
`ifdef OT_RFD_MUT_L0R   // RF-D bench mutant: the go is NOT delayed with the write (the first group reads before the last write)
        assign ga_s = ga; assign gb_s = gb; assign gacc_s = gacc;
`else
        assign ga_s = ga2; assign gb_s = gb2; assign gacc_s = gacc2;
`endif
    end endgenerate
    // ---------------------------------------------------------------- group stream (16 groups an accumulation)
    reg a_on; reg [3:0] a_i; reg [4:0] a_acc;
    // S81-CORE-LAT-R13 (10-27): REGISTERED ONE-HOT read select.  The old read rs[wad(sel)] computed a 9-bit word address
    // (x192/x12/x6/x3 adder) from the 5-bit select and indexed the 384-word store, so synthesis built a computed-address
    // 384-word decode + mux per byte (select cone 5,233 cells / 14 levels for g_sel[34].q[2]; place repair_design then
    // grew BUFx2 fanout chains 16/24/24 and l0r failed reg->reg setup -385.6 ps, g_sel[34].q -> r_d[278]).  Now each
    // copy also registers oh = onehot(next q) (oh == decode(q) on every edge after the first go, same cycle), and each
    // output byte is a 32-term AND-OR over CONSTANT store words (addresses fixed at elaboration): select fanout = 8 AND
    // terms per one-hot bit, no address arithmetic, no decode on the path.  Ports, cycles and transaction behaviour
    // unchanged (r_d is only read while r_v = 1, i.e. after a go).
    wire [32*40-1:0] ohs;                               // one-hot {b, i} per output byte (40 kept copies)
    genvar c;
    generate for (c = 0; c < 40; c = c + 1) begin : g_sel
        (* keep = "true" *) reg [4:0] q;
        (* keep = "true" *) reg [31:0] oh;
        // RF >= 1 (form 2b, 11-03: RF 2 build oth-ubuntu-3202643 routed TT -21.68 / 25 ep on g_w1.ga2 -> ~1,500-load buffer
        // tree (40 copies x 37 q / oh flops) -> g_sel[*].oh): each copy registers its OWN go (ga / gb -> gac / gbc, kept,
        // = ga2 / gb2 on every edge), so the go reaches 37 local loads; the select copies are not reset (as q / oh).
        wire gq_a, gq_b;
        if (RF >= 1) begin : g_gc
            (* keep = "true" *) reg gac, gbc;
            always @(posedge clk) begin gac <= ga; gbc <= gb; end
`ifdef OT_RFD_MUT_L0R3   // bench mutant: the copy uses the undelayed go (read select one edge early)
            assign gq_a = ga; assign gq_b = gb;
`else
            assign gq_a = gac; assign gq_b = gbc;
`endif
        end else begin : g_gn
            assign gq_a = ga_s; assign gq_b = gb_s;
        end
        wire [4:0] qn = gq_a ? {gq_b, 4'd0} : {q[4], q[3:0] + 4'd1};
        always @(posedge clk) begin q <= qn; oh <= 32'd1 << qn; end
        assign ohs[32 * c +: 32] = oh;
    end endgenerate
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin a_on <= 1'b0; a_i <= 4'd0; r_v <= 1'b0; r_f <= 1'b0; fault_hold <= 1'b0; end
        else begin
            if (ga_s) begin a_on <= 1'b1; a_i <= 4'd0; a_acc <= gacc_s; if (a_on && a_i != 4'd15) fault_hold <= 1'b1; end
            else if (a_on) begin a_i <= a_i + 4'd1; if (a_i == 4'd15) a_on <= 1'b0; end
            r_f <= fault_hold || (ga_s && a_on && a_i != 4'd15);
            r_v <= a_on;
        end
    // word w of group i = {b, i}: slice 4m + ws(w), half k >> 1, word (k & 1) * 3 + wo(w)   (m = i[1:0], k = i[3:2])
    // store index = 192 b + 12 (4 m + ws) + 6 i[3] + 3 i[2] + wo  (a constant per (w, e) term)
    wire [319:0] rdn;
    genvar gw, gk;
    generate for (gw = 0; gw < 10; gw = gw + 1) begin : g_rw
        localparam integer WS = (gw < 2) ? 0 : (gw < 5) ? 1 : (gw < 8) ? 2 : 3;
        localparam integer WO = (gw == 1 || gw == 6 || gw == 9) ? 1 : (gw == 3) ? ((MUT == 6) ? 2 : 1) :
                                (gw == 4) ? ((MUT == 6) ? 1 : 2) : (gw == 7) ? 2 : 0;
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_rb
            // R14: AND-OR over the 32 constant-address terms as one combinational loop (unrolled at elaboration: every
            // store index is a constant per term).  R13 built it as a self-referencing packed vector (acc[8(e+1)+:8] =
            // acc[8e+:8] | ...), which Verilator 5.032 flags UNOPTFLAT and then aborts on (V3Ast Rollover, bench build
            // MUT=0); same function, same terms, same OR order.
            reg [7:0] v;
            integer e;
            always @* begin
                v = 8'd0;
                for (e = 0; e < 32; e = e + 1)
                    v = v | ({8{ohs[32 * (4 * gw + gk) + e]}} &
                             rsw[192 * (e / 16) + 12 * (4 * (e % 4) + WS) + 6 * ((e / 8) % 2) + 3 * ((e / 4) % 2) + WO][8 * gk +: 8]);
            end
            assign rdn[32 * gw + 8 * gk +: 8] = v;
        end
    end endgenerate
    always @(posedge clk) begin
        r_i <= a_i; r_acc <= a_acc; r_d <= rdn;
    end
endmodule
