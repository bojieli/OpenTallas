# hook_cs.py REPO: wrap the S81 svc box modules under `ifdef OT_S81_SVC_CS (default: unchanged)
import sys, pathlib
R = pathlib.Path(sys.argv[1])
NOTE = "// DIE-S81-85 svc census (opt-in -DOT_S81_SVC_CS): the box keeps its name and ports; its body is the census-safe\n// copy in rtl/dsrom_sys/s81_svc (same cycles; lock-step bench tools/s81_dv/svc_cs).  Without the define: unchanged.\n"
W = {
 'ot_s81_su_sml_fold2': ('rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_sml_fold2.sv', """module ot_s81_su_sml_fold2 #(
 parameter integer NVMAX=40, LM=5, LA=4, MUT=0
)(
 input wire clk, rst_in, sk_en, i_cv,
 input wire [6:0] i_nv,
 input wire [31:0] i_scale, i_sink,
 input wire i_sv, input wire [63:0] i_s,
 input wire i_mv, input wire [31:0] i_nmb,
 output wire o_mxv, output wire [63:0] o_mx,
 output wire o_ev, o_es, o_el, output wire [63:0] o_e,
 output wire o_fault
);
 ot_s81_su_sml_fold2_cs #(.NVMAX(NVMAX),.LM(LM),.LA(LA),.MUT(MUT)) u_cs(.clk(clk),.rst_in(rst_in),.sk_en(sk_en),
  .i_cv(i_cv),.i_nv(i_nv),.i_scale(i_scale),.i_sink(i_sink),.i_sv(i_sv),.i_s(i_s),.i_mv(i_mv),.i_nmb(i_nmb),
  .o_mxv(o_mxv),.o_mx(o_mx),.o_ev(o_ev),.o_es(o_es),.o_el(o_el),.o_e(o_e),.o_fault(o_fault));
endmodule
"""),
 'ot_s81_su_smd_fold2': ('rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smd_fold2.sv', """module ot_s81_su_smd_fold2 #(
    parameter integer LPH = 16, TAIL = 64, LM = 5, LA = 4, STALEDEN = 0
) (
    input  wire clk, rst_in, input wire [1:0] cfg_p, input wire i_pv, input wire [127:0] i_pa,
    input  wire i_dv, input wire [31:0] i_den, input wire i_csv, input wire [4:0] i_csi, input wire [63:0] i_csd,
    output wire o_ov, output wire [63:0] o_o, output wire [1:0] o_f
);
    ot_s81_su_smd_fold2_cs #(.LPH(LPH),.TAIL(TAIL),.LM(LM),.LA(LA),.STALEDEN(STALEDEN)) u_cs(.clk(clk),.rst_in(rst_in),
        .cfg_p(cfg_p),.i_pv(i_pv),.i_pa(i_pa),.i_dv(i_dv),.i_den(i_den),.i_csv(i_csv),.i_csi(i_csi),.i_csd(i_csd),
        .o_ov(o_ov),.o_o(o_o),.o_f(o_f));
endmodule
"""),
 'ot_s81_su_smc': ('rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv', """module ot_s81_su_smc #(
    parameter integer LPH = 16, LA = 4
) (
    input  wire clk, rst_in, i_v, i_l, input wire [LPH*32-1:0] i_e,
    output wire o_v, o_l, output wire [31:0] o_s
);
    ot_s81_su_smc_cs #(.LPH(LPH),.LA(LA)) u_cs(.clk(clk),.rst_in(rst_in),.i_v(i_v),.i_l(i_l),.i_e(i_e),.o_v(o_v),.o_l(o_l),
        .o_s(o_s));
endmodule
"""),
 'ot_s81_su_smr': ('rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv', """module ot_s81_su_smr #(
    parameter integer LPH = 16, LA = 4, LTMAX = 6
) (
    input  wire clk, rst_in, i_cv, input wire [2:0] i_lt, input wire i_mxv, input wire [LPH*32-1:0] i_mx,
    input  wire i_skv, input wire [31:0] i_sk, input wire i_vv, i_vl, input wire [31:0] i_vs,
    output wire o_mv, output wire [31:0] o_nmb, output wire o_dv, output wire [31:0] o_den
);
    ot_s81_su_smr_cs #(.LPH(LPH),.LA(LA),.LTMAX(LTMAX)) u_cs(.clk(clk),.rst_in(rst_in),.i_cv(i_cv),.i_lt(i_lt),
        .i_mxv(i_mxv),.i_mx(i_mx),.i_skv(i_skv),.i_sk(i_sk),.i_vv(i_vv),.i_vl(i_vl),.i_vs(i_vs),.o_mv(o_mv),
        .o_nmb(o_nmb),.o_dv(o_dv),.o_den(o_den));
endmodule
"""),
}
for name, (f, wrap) in W.items():
    p = R / f; s = p.read_text()
    if f'`ifdef OT_S81_SVC_CS\n{NOTE}module {name} ' in s: continue
    key = f'\nmodule {name} #('
    i = s.index(key) + 1
    j = s.index('\nendmodule', i) + len('\nendmodule')
    j = s.index('\n', j) + 1 if s.find('\n', j) >= 0 else len(s)
    s = s[:i] + '`ifdef OT_S81_SVC_CS\n' + NOTE + wrap + '`else\n' + s[i:j] + '`endif\n' + s[j:]
    p.write_text(s)
    print('hooked', name, f)
