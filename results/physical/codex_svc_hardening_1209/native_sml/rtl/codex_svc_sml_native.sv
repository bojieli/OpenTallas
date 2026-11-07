module codex_svc_sml_native #(parameter integer MUT=0) (
    input wire ck,
    input wire rst,
    input wire sk_en,
    input wire i_cv,
    input wire [6:0] i_nv,
    input wire [31:0] i_scale,
    input wire [31:0] i_sink,
    input wire i_sv,
    input wire [31:0] i_s,
    input wire i_mv,
    input wire [31:0] i_nmb,
    output wire o_mxv,
    output wire [31:0] o_mx,
    output wire o_ev,
    output wire o_es,
    output wire o_el,
    output wire [31:0] o_e
);
    dsfd_su_t_sml u_native (
        .ck(ck),
        .rst(rst),
        .sk_en(sk_en),
        .i_cv(i_cv),
        .i_nv(i_nv),
        .i_scale(i_scale),
        .i_sink(i_sink),
        .i_sv((MUT ? 1'b0 : i_sv)),
        .i_s(i_s),
        .i_mv(i_mv),
        .i_nmb(i_nmb),
        .o_mxv(o_mxv),
        .o_mx(o_mx),
        .o_ev(o_ev),
        .o_es(o_es),
        .o_el(o_el),
        .o_e(o_e)
    );
endmodule
