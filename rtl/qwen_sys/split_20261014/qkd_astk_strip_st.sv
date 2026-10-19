`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KVE-2-ASTK 2026-10-17: wires-only static ASTK strip (credit-free, lane-free successor of qkd_astk_strip_s).
// The topology of the selected static composition qkd_astk_native_stack_cal (rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv)
// without its e-read service (that is KVJ-D's inline qkd_astk_er_tap on the so / si bus) and without the legacy P.V tree:
//   qkd_astk_ctl_s + 8 x qkd_astk_ep_s + 32 x qkd_astk_ex_s + 4 x qkd_astk_zn, registered die relays (qkd_astk_delay) on ck_r.
// No credit, ready or lane: every slot is a fixed age after the command's start edge (cal = {EXP base, Z start, LMAX start},
// held by the compiler from issue through the last slice's start edge); availability / identity / overflow are fault checks.
// Relative to qkd_astk_strip_s: nb* (32 x 1,024 b), ck_v (64), pv_done, si[633] (engine nb_cr) and so[423:412] are gone;
// cal (48 b) is new; ap is the 43-b hub sideband (P.V reaches the hub from the pvw pairs).
// so = 8 x {sf, so[411:0]} (413 b an engine), si = 8 x si[632:0] (633 b an engine).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_astk_strip_st #(
    parameter integer RL = 1,
    parameter integer Z_STRIDE = 4
) (
    input  wire              ck_c,
    input  wire [3:0]        ck_z,
    input  wire [31:0]       ck_x,
    input  wire [7:0]        ck_e,
    input  wire              ck_r,
    input  wire              rst_n,
    input  wire [1:0]        st,
    input  wire [539:0]      aq,
    input  wire [35:0]       am,
    input  wire [47:0]       cal,
    output wire [42:0]       ap,
    output wire              af,
    output wire [20:0]       lt,
    input  wire [413*8-1:0]  so,
    output wire [633*8-1:0]  si
);
    wire [571:0] cq;
    wire [266:0] cx;
    wire [137:0] czi;
    wire [4:0]   zf;
    qkd_astk_ctl_s #(.Z_STRIDE(Z_STRIDE)) u_ctl (.cal(cal[31:0]), .ck(ck_c), .rst_n(rst_n), .st(st), .aq(aq), .lt(lt),
        .am(am), .ap(ap), .af(af), .qo(cq), .xi(cx), .zi(czi), .fz(zf[4]));
    wire [571:0] qi [0:8];
    wire [266:0] xo [0:8];
    wire [650:0] zo [0:8];
    wire [521:0] ro [0:8];
    assign xo[0] = 267'd0; assign zo[0] = 651'd0;
    qkd_astk_delay #(.W(572), .D(RL), .RESET(1)) u_cq (.clk(ck_r), .rst_n(rst_n), .d(cq), .q(qi[8]));
    qkd_astk_delay #(.W(267), .D(RL), .RESET(1)) u_cx (.clk(ck_r), .rst_n(rst_n), .d(xo[8]), .q(cx));
    assign ro[8] = {zo[8][650:139], zo[8][10:7], zo[8][6:3], zo[8][2], zo[8][0]};
    genvar e, h, z;
    generate for (e = 0; e < 8; e = e + 1) begin : g_ep
        wire [266:0] xi;
        wire [650:0] zi;
        wire [263:0] xa;
        wire [135:0] xe;
        qkd_astk_delay #(.W(267), .D(RL), .RESET(1)) u_x (.clk(ck_r), .rst_n(rst_n), .d(xo[e]), .q(xi));
        qkd_astk_delay #(.W(651), .D((e % 2) ? 0 : RL), .RESET(1)) u_z (.clk(ck_r), .rst_n(rst_n), .d(zo[e]), .q(zi));
        qkd_astk_delay #(.W(572), .D(RL), .RESET(1)) u_q (.clk(ck_r), .rst_n(rst_n), .d(qi[e+1]), .q(qi[e]));
        qkd_astk_delay #(.W(522), .D(RL), .RESET(1)) u_r (.clk(ck_r), .rst_n(rst_n), .d(ro[e+1]), .q(ro[e]));
        // the slice's EXP offset: the chunk chain's 9-edge join plus the command-bus relay skew (qkd_astk_native_stack_cal)
        qkd_astk_ep_s u_ep (.cal_exp(cal[47:32]), .eo(8'(9*e + RL*(e + e/2))), .ck(ck_e[e]), .rst_n(rst_n), .sq({st, 3'(e)}),
            .so(so[413*e +: 412]), .sf(so[413*e + 412]), .si(si[633*e +: 633]), .qi(qi[e]), .xi(xi), .xo(xo[e+1]),
            .zi(zi), .zo(zo[e+1]), .ri(ro[e]), .xa(xa), .xe(xe));
        for (h = 0; h < 4; h = h + 1) begin : g_ex
            qkd_astk_ex_s u_ex (.ck(ck_x[4*e+h]), .rst_n(rst_n), .xa(xa[66*h +: 66]), .xe(xe[34*h +: 34]));
        end
    end endgenerate
    wire [137:0] zn [0:4];
    assign zf[0] = 1'b0;
    assign zn[0] = {zo[8][138:11], zo[8][10:7], zo[8][6:3], zo[8][2], zo[8][0]};
    generate for (z = 0; z < 4; z = z + 1) begin : g_zn
        qkd_astk_zn u_zn (.ck(ck_z[z]), .rst_n(rst_n), .zc({2'(z), st}), .tc(cq[14:0]), .zi(zn[z]), .zo(zn[z+1]),
            .fi(zf[z]), .fo(zf[z+1]));
    end endgenerate
    assign czi = zn[4];
endmodule
