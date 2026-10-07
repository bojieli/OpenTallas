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
    output wire         fault
);
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
            if (!rst_n) begin r_cfg_v <= 1'b0; r_go <= 1'b0; r_xs_v <= 1'b0; r_xb_v <= 1'b0; r_busy <= 1'b0; r_fault <= 1'b0; end
            else begin r_cfg_v <= cfg_v; r_go <= go; r_xs_v <= xs_v; r_xb_v <= xb_v; r_busy <= busy_e; r_fault <= fault_e; end
        always @(posedge clk) begin
            r_cfg_a <= cfg_a;
            r_cfg_d <= cfg_d;
            r_go_bf <= go_bf;
            r_xs_p <= xs_p;
            r_xs_b <= xs_b;
            r_xs_sv <= xs_sv;
            r_xs_q0 <= xs_q0;
            r_xs_e0 <= xs_e0;
            r_xs_q1 <= xs_q1;
            r_xs_e1 <= xs_e1;
            r_xs_pos <= xs_pos;
            r_xb_pos <= xb_pos;
            r_xb_b <= xb_b;
            r_xb_sv <= xb_sv;
            r_xb_u <= xb_u;
            r_xb_d <= xb_d;
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
        .BP(BP),
        .FIX_SECOND_ROW_INDEX(FIX_SECOND_ROW_INDEX),
        .GRADUAL_RNE(GRADUAL_RNE),
        .INSTANCE(INSTANCE)
    ) u_elem (
        .clk(clk),
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
        .pv(pv),
        .pval(pval),
        .prow(prow),
        .pseg(pseg),
        .pnseg(pnseg),
        .perr(perr),
        .ppos(ppos),
        .busy(busy_e),
        .fault(fault_e)
    );
endmodule
