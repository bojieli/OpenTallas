`timescale 1ns/1ps
// Native full BF-capable S81 pair. This is NOT the current dsfd_bf pin contract:
// the die must carry the native BF stream and go_bf to use this block.
// Compile with ot_v41_rom_elem_w10_rne_wake_prepare.sv (same legacy module
// name), ot_v41_bf16_lanes2_rne_prepare.sv, and the shared RNE multiplier
// companions. The exact runner packages their pinned arithmetic dependencies.
// Zero additional wrapper cycles. Original prepared element remains byte-identical.
module ot_s81_bf_native #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 8,
    parameter integer LV = 5,
    parameter integer BF16 = 1,       // 1: the 16-lane BF16 path (ot_v41_bf16_lanes) and its x port
    parameter integer NCHB = 8,
    parameter integer NB = 2,
    parameter integer MTP = 1,        // 1: up to 6 positions time-multiplexed position-outer (2 tree banks by parity)
    parameter integer EARLY = 1,      // 1: segment tree early exit (fill cut)
    parameter integer CG = 1,         // 1: one integrated clock gate for the element (pair): clocked only from go
                                      //    until DRAIN cycles after its last word issued
    parameter integer DRAIN = 127,
    // 1.2 GHz at SS (W10, 2026-09-30): FAST = 1 builds the lanes, chains, pair adder and segment tree on the re-cut
    // modules (ot_v41_bterm2_w10, ot_v41_fadd with stage mask CUT); PP = 1 replaces each macro with two
    // ot_rom_4096x274_m8 read alternately (ping-pong), each a 2-cycle path, addressed in issue order
    parameter integer FAST = 1,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer PP = 1,
    // W10 SS frontend: remove class selection from the address carry/compare
    // cone. Opt-in, no added cycles or changes to capture/walker sequencing.
    parameter integer FRONT_PAR = 0,
    // Necessary baseline correction, opt-in until exact and SS/FF gates pass.
    parameter integer WAKE_REG = 1,
    parameter integer HITFIX = 0,     // element x-need match from registered class offsets (default off)
    // BF16_PAIR (root decision 2026-09-30, option iii): BF16 rows on the standard pair.  A BF16 word (16 weights,
    // lane l = element b of golden chunk 16u + l) is held 4 cycles; 4 multipliers per macro take lanes 4k..4k+3 in
    // cycle k into 4 chunk chains (NCH >= 24 slots: slot = 4 x word-in-round + k); at the round b = 7 the 4 chunk
    // sums of a cycle meet in 2 pair adds and 1 add (golden levels 1-2) and the 4-chunk node is the segment tree's
    // base node.  A BF16 sub-block is 2 units.  Requires FAST = 1.
    parameter integer BP = 0,
    parameter integer FIX_SECOND_ROW_INDEX = 1, // mandatory row decoder repair, opt-in preparation
    parameter integer GRADUAL_RNE = 1, // shared reviewed multiplier repair
    // PINREG (margin-first 2026-10-06, default 0): every input pin captured in a flop at the pin (+1 cycle on all inputs
    // uniformly, so cfg/go/stream alignment is unchanged) and busy/fault launched from a flop (+1); pv..ppos are
    // already element output flops. Block boundary is then register-to-register for the die IO budget.
    parameter integer PINREG = 0,
    // Default-off physical noninverting HB2 seats before existing pin capture.
    // No new edge, cycle or throughput change. Requires measured delay/fit.
    parameter integer INPUT_HOLD_SEATS = 0,
    // HALF (BF SAFE variant B, 2026-10-07, default 0; requires PINREG): the UNCHANGED element runs at half rate on
    // hclk = clk gated every other cycle (ot_hdc_cg latch + AND, enable = ph toggling on clk), so every element flop and
    // every pin-capture flop launches and captures only on gated edges: element-internal paths get two clk periods
    // (multicycle setup 2 / hold 1, physical/s81_native_bf/margin/signoff_half.sdc).  Protocol: hph (a clk flop, pin) is
    // 1 in the clk cycle that ends on a gated edge; the inputs are sampled only at gated edges, so the driver holds
    // every input (cfg, go, x beats) for the slow cycle; pv..ppos are re-launched from clk flops at the pins for
    // exactly one clk cycle per slow cycle (the cycle after the gated edge), busy/fault every clk cycle.  Crossings
    // (pin regs -> element, element -> output regs) are register to register.  Throughput: one element cycle per two
    // clk cycles (BF column time x2); exact at transaction level (tools/s81/run_bf_half_exact.py).
    parameter integer HALF = 0,
    // RECUT (BF re-cut A, 2026-10-07, default 0): the element is the DS q-element ot_v41_rom_elem_qx_w10 (its closed
    // walker / x-need / issue / segment-tree / chain / per-macro re-cuts: QTIMING_FIX QPIPE QZ QY QX 10, as routed for
    // the S81 q pairs) with BF16 = 1 under QBF (RECUT: 1 = as is, 2 = + BF lanes re-cut: 8-stage multiplier, chain4
    // kept forward copies, fully cut tree adders; 3 = 2 + the BF lane chunk chains unrolled by 2 on a half-rate gated
    // clock, ot_v41_chain2u2, multicycle 2/1 u2_mc.sdc), GRADUAL_RNE and the second-row decoder fix (built in).  Latency
    // changes (QPIPE boundary, split lanes, tree), values and per-lane order do not: exact at transaction level
    // (tools/s81/bf_txn_bench.py --variant recut).  Requires FAST = 1, PP = 1, BP = 0, HALF = 0.
    parameter integer RECUT = 0,
    // QZE (RECUT only, 2026-10-08, default 0): the q-element's ICG enable retimed onto a register beside the ICG
    // (ot_v41_rom_elem_qx_w10 QZE); zero added cycles.
    parameter integer QZE = 0,
    parameter integer RDRAIN = 200,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         go_bf,        // the phase's family: 0 = FP8/FP4 (shared FP8 x stream), 1 = BF16
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,       // MTP position of the beat
    input  wire [2:0]   xb_pos,
    // BF16 x stream beat: 4 lane-group slices {unit, 16 BF16} for block b
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault,
    output wire         hph           // HALF: 1 in the clk cycle that ends on a gated (element) edge; 1 when HALF = 0
);
    // HALF: element / pin-capture clock
    wire eclk, pclk;
    wire [NB-1:0] pv_e; wire [32*NB-1:0] pval_e; wire [16*NB-1:0] prow_e; wire [5*NB-1:0] pseg_e, pnseg_e;
    wire [NB-1:0] perr_e; wire [3*NB-1:0] ppos_e;
    if (HALF != 0) begin : g_half
        reg ph;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) ph <= 1'b0;
            else ph <= ~ph;
        // !rst_n in the enable: the gated flops are clocked during reset (ot_hdc_cg contract)
        ot_hdc_cg u_hcg (.clk(clk), .en(ph | !rst_n), .gclk(eclk));
        assign pclk = eclk;
        assign hph = ph;
        // outputs: one clk cycle per slow cycle (the cycle after the gated edge, ph = 0 before the capturing edge)
        reg [NB-1:0] o_pv; reg [32*NB-1:0] o_pval; reg [16*NB-1:0] o_prow; reg [5*NB-1:0] o_pseg, o_pnseg;
        reg [NB-1:0] o_perr; reg [3*NB-1:0] o_ppos;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) o_pv <= {NB{1'b0}};
`ifdef BF_HALF_MUTANT_PV
            else o_pv <= pv_e;                      // negative control: pv not qualified to the slow cycle
`else
            else o_pv <= pv_e & {NB{~ph}};
`endif
        always @(posedge clk) if (!ph) begin
            o_pval <= pval_e; o_prow <= prow_e; o_pseg <= pseg_e; o_pnseg <= pnseg_e; o_perr <= perr_e; o_ppos <= ppos_e;
        end
        assign pv = o_pv; assign pval = o_pval; assign prow = o_prow; assign pseg = o_pseg; assign pnseg = o_pnseg;
        assign perr = o_perr; assign ppos = o_ppos;
`ifndef SYNTHESIS
        initial if (PINREG == 0) $fatal(1, "HALF requires PINREG");
`endif
    end else begin : g_full
        assign eclk = clk; assign pclk = clk; assign hph = 1'b1;
        assign pv = pv_e; assign pval = pval_e; assign prow = prow_e; assign pseg = pseg_e; assign pnseg = pnseg_e;
        assign perr = perr_e; assign ppos = ppos_e;
    end
    // pin-captured inputs (PINREG) or pass-through
    wire cfg_v_i;
    wire [4:0] cfg_a_i;
    wire [47:0] cfg_d_i;
    wire go_i;
    wire go_bf_i;
    wire xs_v_i;
    wire [7:0] xs_p_i;
    wire [2:0] xs_b_i;
    wire [1:0] xs_sv_i;
    wire [255:0] xs_q0_i;
    wire [9:0] xs_e0_i;
    wire [255:0] xs_q1_i;
    wire [9:0] xs_e1_i;
    wire [2:0] xs_pos_i;
    wire [2:0] xb_pos_i;
    wire xb_v_i;
    wire [2:0] xb_b_i;
    wire [3:0] xb_sv_i;
    wire [31:0] xb_u_i;
    wire [1023:0] xb_d_i;
    wire busy_e, fault_e;
    if (PINREG != 0) begin : g_pin
        wire [3:0] hs_control;
        wire [1667:0] hs_data;
        ot_s81_bf_input_holdseat #(.W(4), .SEATS(INPUT_HOLD_SEATS)) u_hs_control (
            .a({cfg_v, go, xs_v, xb_v}), .y(hs_control));
        ot_s81_bf_input_holdseat #(.W(1668), .SEATS(INPUT_HOLD_SEATS)) u_hs_data (
            .a({cfg_a, cfg_d, go_bf, xs_p, xs_b, xs_sv, xs_q0, xs_e0,
                xs_q1, xs_e1, xs_pos, xb_pos, xb_b, xb_sv, xb_u, xb_d}), .y(hs_data));
        reg r_cfg_v, r_go, r_xs_v, r_xb_v, r_busy, r_fault;
        reg [4:0] r_cfg_a;
        reg [47:0] r_cfg_d;
        reg r_go_bf;
        reg [7:0] r_xs_p;
        reg [2:0] r_xs_b;
        reg [1:0] r_xs_sv;
        reg [255:0] r_xs_q0;
        reg [9:0] r_xs_e0;
        reg [255:0] r_xs_q1;
        reg [9:0] r_xs_e1;
        reg [2:0] r_xs_pos;
        reg [2:0] r_xb_pos;
        reg [2:0] r_xb_b;
        reg [3:0] r_xb_sv;
        reg [31:0] r_xb_u;
        reg [1023:0] r_xb_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin r_busy <= 1'b0; r_fault <= 1'b0; end
            else begin r_busy <= busy_e; r_fault <= fault_e; end
        always @(posedge pclk or negedge rst_n)
            if (!rst_n) begin r_cfg_v <= 1'b0; r_go <= 1'b0; r_xs_v <= 1'b0; r_xb_v <= 1'b0; end
            else {r_cfg_v, r_go, r_xs_v, r_xb_v} <= hs_control;
        always @(posedge pclk) begin
            {r_cfg_a, r_cfg_d, r_go_bf, r_xs_p, r_xs_b, r_xs_sv,
             r_xs_q0, r_xs_e0, r_xs_q1, r_xs_e1, r_xs_pos, r_xb_pos,
             r_xb_b, r_xb_sv, r_xb_u, r_xb_d} <= hs_data;
        end
        assign cfg_v_i = r_cfg_v;
        assign cfg_a_i = r_cfg_a;
        assign cfg_d_i = r_cfg_d;
        assign go_i = r_go;
        assign go_bf_i = r_go_bf;
        assign xs_v_i = r_xs_v;
        assign xs_p_i = r_xs_p;
        assign xs_b_i = r_xs_b;
        assign xs_sv_i = r_xs_sv;
        assign xs_q0_i = r_xs_q0;
        assign xs_e0_i = r_xs_e0;
        assign xs_q1_i = r_xs_q1;
        assign xs_e1_i = r_xs_e1;
        assign xs_pos_i = r_xs_pos;
        assign xb_pos_i = r_xb_pos;
        assign xb_v_i = r_xb_v;
        assign xb_b_i = r_xb_b;
        assign xb_sv_i = r_xb_sv;
        assign xb_u_i = r_xb_u;
        assign xb_d_i = r_xb_d;
        assign busy = r_busy; assign fault = r_fault;
    end else begin : g_nopin
        assign cfg_v_i = cfg_v;
        assign cfg_a_i = cfg_a;
        assign cfg_d_i = cfg_d;
        assign go_i = go;
        assign go_bf_i = go_bf;
        assign xs_v_i = xs_v;
        assign xs_p_i = xs_p;
        assign xs_b_i = xs_b;
        assign xs_sv_i = xs_sv;
        assign xs_q0_i = xs_q0;
        assign xs_e0_i = xs_e0;
        assign xs_q1_i = xs_q1;
        assign xs_e1_i = xs_e1;
        assign xs_pos_i = xs_pos;
        assign xb_pos_i = xb_pos;
        assign xb_v_i = xb_v;
        assign xb_b_i = xb_b;
        assign xb_sv_i = xb_sv;
        assign xb_u_i = xb_u;
        assign xb_d_i = xb_d;
        assign busy = busy_e; assign fault = fault_e;
    end
    if (RECUT != 0) begin : g_rc
        ot_v41_rom_elem_qx_w10 #(.NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NCHB(NCHB), .NB(NB), .MTP(MTP),
            .EARLY(EARLY), .CG(CG), .DRAIN(RDRAIN), .FAST(FAST), .CUT(CUT), .PP(PP), .FRONT_PAR(FRONT_PAR), .BP(BP),
            .QTIMING_FIX(1), .QPIPE(1), .QP_XS(1), .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .QZ(1), .QZ_NS(8), .QZ_NE(4),
            .QY(1), .QX(10), .QBF(RECUT), .QZE(QZE), .GRADUAL_RNE(GRADUAL_RNE), .INSTANCE(INSTANCE)) u_elem (
            .clk(eclk), .rst_n_pin(rst_n), .cfg_v_pin(cfg_v_i), .cfg_a_pin(cfg_a_i), .cfg_d_pin(cfg_d_i), .go_pin(go_i),
            .go_bf_pin(go_bf_i), .xs_v_pin(xs_v_i), .xs_p_pin(xs_p_i), .xs_b_pin(xs_b_i), .xs_sv_pin(xs_sv_i),
            .xs_q0_pin(xs_q0_i), .xs_e0_pin(xs_e0_i), .xs_q1_pin(xs_q1_i), .xs_e1_pin(xs_e1_i), .xs_pos_pin(xs_pos_i),
            .xb_pos_pin(xb_pos_i), .xb_v_pin(xb_v_i), .xb_b_pin(xb_b_i), .xb_sv_pin(xb_sv_i), .xb_u_pin(xb_u_i),
            .xb_d_pin(xb_d_i), .pv(pv_e), .pval(pval_e), .prow(prow_e), .pseg(pseg_e), .pnseg(pnseg_e), .perr(perr_e),
            .ppos(ppos_e), .busy(busy_e), .fault(fault_e));
`ifndef SYNTHESIS
        initial if (FAST == 0 || PP == 0 || BP != 0 || HALF != 0) $fatal(1, "RECUT requires FAST = 1, PP = 1, BP = 0, HALF = 0");
`endif
    end else begin : g_orig
        ot_v41_rom_elem_w10 #(
            .NSEG(NSEG),
            .NCH(NCH),
            .XF(XF),
            .LV(LV),
            .BF16(BF16),
            .NCHB(NCHB),
            .NB(NB),
            .MTP(MTP),
            .EARLY(EARLY),
            .CG(CG),
            .DRAIN(DRAIN),
            .FAST(FAST),
            .CUT(CUT),
            .PP(PP),
            .FRONT_PAR(FRONT_PAR),
            .WAKE_REG(WAKE_REG),
            .HITFIX(HITFIX),
            .BP(BP),
            .FIX_SECOND_ROW_INDEX(FIX_SECOND_ROW_INDEX),
            .GRADUAL_RNE(GRADUAL_RNE),
            .INSTANCE(INSTANCE)
        ) u_elem (
            .clk(eclk),
            .rst_n(rst_n),
            .cfg_v(cfg_v_i),
            .cfg_a(cfg_a_i),
            .cfg_d(cfg_d_i),
            .go(go_i),
            .go_bf(go_bf_i),
            .xs_v(xs_v_i),
            .xs_p(xs_p_i),
            .xs_b(xs_b_i),
            .xs_sv(xs_sv_i),
            .xs_q0(xs_q0_i),
            .xs_e0(xs_e0_i),
            .xs_q1(xs_q1_i),
            .xs_e1(xs_e1_i),
            .xs_pos(xs_pos_i),
            .xb_pos(xb_pos_i),
            .xb_v(xb_v_i),
            .xb_b(xb_b_i),
            .xb_sv(xb_sv_i),
            .xb_u(xb_u_i),
            .xb_d(xb_d_i),
            .pv(pv_e),
            .pval(pval_e),
            .prow(prow_e),
            .pseg(pseg_e),
            .pnseg(pnseg_e),
            .perr(perr_e),
            .ppos(ppos_e),
            .busy(busy_e),
            .fault(fault_e)
        );
    end
endmodule

// Technology binding is explicit so synthesis cannot erase the hold seats.
// The simulation contract is bit identity; delay is measured with real liberty.
module ot_s81_bf_input_holdseat #(
    parameter integer W = 1,
    parameter integer SEATS = 0
) (input wire [W-1:0] a, output wire [W-1:0] y);
    wire [W-1:0] seat [0:SEATS];
    assign seat[0] = a;
    for (genvar s = 0; s < SEATS; s = s + 1) begin : g_seat
        for (genvar b = 0; b < W; b = b + 1) begin : g_bit
`ifdef SYNTHESIS
            (* keep = 1, dont_touch = 1 *)
            HB2xp67_ASAP7_75t_R u_hb (.A(seat[s][b]), .Y(seat[s+1][b]));
`else
            assign seat[s+1][b] = seat[s][b];
`endif
        end
    end
`ifdef BF_INPUT_SEAT_MUTANT
    if (SEATS > 0 && W > 16) begin : g_mutant
        // Stuck-low first BF16 lane sign: the enabled seat path must be observed.
        assign y = seat[SEATS] & ~({{(W-16){1'b0}}, 16'h8000});
    end else begin : g_mutant_bypass
        assign y = seat[SEATS];
    end
`else
    assign y = seat[SEATS];
`endif
endmodule
