`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// vsw: the SW lane sub-leaf of a beat leaf (x5 per slice, own clock root): ONE hub SwiGLU lane ot_s81_su_swl (unchanged:
// PRE min / clip, ot_dsrom_exp_f12, ot_hdc_qadd_lat (+1), ot_dsrom_fdiv_f12, ot_hdc_qmul_lat x2, g / u / w wait lines
// in SRAM), fed one element a cycle from a 4-element group {u3..u0, g3..g0} (i_d) with its weight and limit, and the
// hub engine's BF16 rounding (ot_dsrom_su_bf16rnd) on the result; 4 BF16 results leave together (o_d, element j at
// [16 j +: 16]).  A group while the previous one is still being fed is a sticky overrun fault.  Pins: input flops,
// output flops, ot_rst_relay.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vsw #(
    parameter integer LM = 5,
    parameter integer LA = 4,
    // S81-CORES2/SW 10-25 (GEOM vsw_c FAIL: v_q, the N-face pin register of i_v, broadcast to 130 lane-input muxes and
    // through the PRE comparators into u_l.p_u 116-120 um away, 40 points, TT -11.44): LR = 1 registers the serialised
    // lane inputs (one flop stage between the pin-register / serialiser band and the lane's PRE), so the cross-core hop
    // carries a mux only.  +1 cycle on o_v / o_d / o_f (every output exactly one edge later; ovr delayed with it).
    // LR = 0 = the previous design (lockstep reference, tb_s81sl_vsw_lr_eq.sv).
    parameter integer LR = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_v,
    input  wire [255:0]  i_d,
    input  wire [31:0]   i_w,
    input  wire [31:0]   i_lim,
    output reg           o_v,
    (* keep *) output reg  [63:0]   o_d,
    output reg           o_f
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_l = rsv[1];
    reg v_q; reg [255:0] d_q; reg [31:0] w_q, l_q;
    always @(posedge clk or negedge rs_c) if (!rs_c) v_q <= 1'b0; else v_q <= i_v;
    always @(posedge clk) begin d_q <= i_d; w_q <= i_w; l_q <= i_lim; end
    // serialiser: element j of the group on the lane in cycle j after the group's pin flop
    reg [95:0] sg, su; reg [31:0] sw, sl; reg [1:0] cnt; reg act, ovr;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin act <= 1'b0; cnt <= 2'd0; ovr <= 1'b0; end
        else begin
            if (v_q) begin act <= 1'b1; cnt <= 2'd0; end
            else if (act) begin cnt <= cnt + 2'd1; if (cnt == 2'd2) act <= 1'b0; end
            if (v_q && act) ovr <= 1'b1;
        end
    always @(posedge clk)
        if (v_q) begin sg <= d_q[127:32]; su <= d_q[255:160]; sw <= w_q; sl <= l_q; end
        else begin sg <= {32'd0, sg[95:32]}; su <= {32'd0, su[95:32]}; end
    wire ln_v0 = v_q || act;
    wire [31:0] ln_g0 = v_q ? d_q[31:0] : sg[31:0], ln_u0 = v_q ? d_q[159:128] : su[31:0];
    wire [31:0] ln_w0 = v_q ? w_q : sw, ln_l0 = v_q ? l_q : sl;
    wire [1:0]  ln_t0 = v_q ? 2'd0 : cnt + 2'd1;
    wire ln_v, ovr_l; wire [31:0] ln_g, ln_u, ln_w, ln_l; wire [1:0] ln_t;
    generate if (LR != 0) begin : g_lr
        reg lv, lo; reg [31:0] lg, lu, lw, ll; reg [1:0] lt;
        always @(posedge clk or negedge rs_c) if (!rs_c) begin lv <= 1'b0; lo <= 1'b0; end else begin lv <= ln_v0; lo <= ovr; end
        always @(posedge clk) begin lg <= ln_g0; lu <= ln_u0; lw <= ln_w0; ll <= ln_l0; lt <= ln_t0; end
        assign ln_v = lv; assign ln_g = lg; assign ln_u = lu; assign ln_w = lw; assign ln_l = ll; assign ln_t = lt;
        assign ovr_l = lo;
    end else begin : g_nlr
        assign ln_v = ln_v0; assign ln_g = ln_g0; assign ln_u = ln_u0; assign ln_w = ln_w0; assign ln_l = ln_l0;
        assign ln_t = ln_t0; assign ovr_l = ovr;
    end endgenerate
    wire [31:0] a, ab; wire [1:0] ta; wire vo, lf;
    ot_s81_su_swl #(.LM(LM), .LA(LA), .TW(2)) u_l (.clk(clk), .rst_n(rs_l), .v(ln_v), .g(ln_g), .u(ln_u), .w(ln_w),
        .lim(ln_l), .t(ln_t), .a(a), .ta(ta), .vo(vo), .fault(lf));
    ot_dsrom_su_bf16rnd u_r (.x(a), .y(ab));
    // deserialiser: element ta -> bits 16 ta; the group leaves with its 4th result
    reg [47:0] ds; reg fs, tbad;
    always @(posedge clk) if (vo) begin
        if (ta == 2'd0) ds[15:0] <= ab[31:16];
        if (ta == 2'd1) ds[31:16] <= ab[31:16];
        if (ta == 2'd2) ds[47:32] <= ab[31:16];
    end
    reg [1:0] texp;
    always @(posedge clk or negedge rs_l)
        if (!rs_l) begin o_v <= 1'b0; o_f <= 1'b0; fs <= 1'b0; texp <= 2'd0; tbad <= 1'b0; end
        else begin
            o_v <= vo && ta == 2'd3;
            if (vo) begin texp <= ta + 2'd1; if (ta != texp) tbad <= 1'b1; end
            fs <= fs | lf | ovr_l | tbad;
            o_f <= fs;
        end
    // S81-KITS-RTLA 10-24 (face_guard: register on every pin, owner rule): o_d was a hold flop (o_d <= ld ? x : o_d),
    // its Q fed its own D mux.  The hold state lives in od_h; o_d is a separate output-only copy loaded with the SAME
    // next-state value every edge (0 cycles, bit / cycle identical).  Both kept so opt_merge cannot fold them.
    (* keep *) reg [63:0] od_h;
    wire [63:0] od_n = (vo && ta == 2'd3) ? {ab[31:16], ds} : od_h;
    always @(posedge clk) begin od_h <= od_n; o_d <= od_n; end
endmodule
