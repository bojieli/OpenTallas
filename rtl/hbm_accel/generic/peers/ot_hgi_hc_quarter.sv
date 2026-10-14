// Genuine B2 HC quarter: two bank stages of the original eight-bank SYS chain.
// Both children expose their complete production operands; grouping adds no cycles.
module ot_hgi_hc_quarter #(parameter integer WINPART=0,W=32, RMAX=128, SPL=4, AW=16, HAW=35, RTW=7, TG=11, WMACRO=1, LM=8, LA=7, NVW=$clog2(W)+1, CWW=$clog2(RMAX+1), NXM=W/16) (
    input wire  clk,
    input wire  rst_n,
    input wire  first,
    input wire  d_v,
    input wire  d_ss,
    input wire [NVW-1:0] d_nv,
    input wire [AW-1:0] d_wa,
    input wire [AW-1:0] d_xa,
    output wire  o_v,
    output wire  o_ss,
    output wire [NVW-1:0] o_nv,
    output wire [AW-1:0] o_wa,
    output wire [AW-1:0] o_xa,
    input wire [W*32-1:0] sum_in,
    output wire [W*32-1:0] sum_out,
    input wire  f_in,
    output wire  f_out,
    input wire [1:0] c_start,
    input wire [1:0] c_rel,
    input wire [2*(HAW)-1:0] c_base,
    input wire [2*(SPL*HAW)-1:0] c_soff,
    input wire [2*(SPL*CWW)-1:0] c_nwk,
    input wire [2*(SPL*AW)-1:0] c_bnd,
    input wire [1:0] c_pgo,
    input wire [2*(HAW)-1:0] c_pbase,
    output wire [1:0] t_rdy,
    output wire [1:0] t_flt,
    input wire [2*(2*NXM*150)-1:0] xl_q,
    output wire [2*(2*NXM)-1:0] xl_cr,
    output wire [2*(2*NXM)-1:0] xl_done,
    output wire [2*(SPL)-1:0] hq_v,
    input wire [2*(SPL)-1:0] hq_rdy,
    output wire [2*(SPL*HAW)-1:0] hq_addr,
    output wire [2*(SPL*3)-1:0] hq_len,
    output wire [2*(SPL*TG)-1:0] hq_tag,
    input wire [2*(SPL)-1:0] hr_v,
    input wire [2*(SPL*TG)-1:0] hr_tag,
    input wire [2*(SPL*2)-1:0] hr_beat,
    input wire [2*(SPL*256)-1:0] hr_data
);
    wire v_mid, ss_mid, f_mid;
    wire [NVW-1:0] nv_mid;
    wire [AW-1:0] wa_mid, xa_mid;
    wire [W*32-1:0] sum_mid;
    wire  chain_o_v [0:1];
    assign v_mid = chain_o_v[0];
    assign o_v = chain_o_v[1];
    wire  chain_o_ss [0:1];
    assign ss_mid = chain_o_ss[0];
    assign o_ss = chain_o_ss[1];
    wire [NVW-1:0] chain_o_nv [0:1];
    assign nv_mid = chain_o_nv[0];
    assign o_nv = chain_o_nv[1];
    wire [AW-1:0] chain_o_wa [0:1];
    assign wa_mid = chain_o_wa[0];
    assign o_wa = chain_o_wa[1];
    wire [AW-1:0] chain_o_xa [0:1];
    assign xa_mid = chain_o_xa[0];
    assign o_xa = chain_o_xa[1];
    wire [W*32-1:0] chain_sum_out [0:1];
    assign sum_mid = chain_sum_out[0];
    assign sum_out = chain_sum_out[1];
    wire  chain_f_out [0:1];
    assign f_mid = chain_f_out[0];
    assign f_out = chain_f_out[1];
    for (genvar t=0;t<2;t=t+1) begin : g_tile
        ot_hgi_hc_tile #(.W(W),.RMAX(RMAX),.SPL(SPL),.AW(AW),.HAW(HAW),.RTW(RTW),.TG(TG),.WMACRO(WMACRO),.WINPART(WINPART),.LM(LM),.LA(LA)) u_tile (
            .clk(clk),
            .rst_n(rst_n),
            .first(first && t==0),
            .d_v(t==0 ? d_v : v_mid),
            .d_ss(t==0 ? d_ss : ss_mid),
            .d_nv(t==0 ? d_nv : nv_mid),
            .d_wa(t==0 ? d_wa : wa_mid),
            .d_xa(t==0 ? d_xa : xa_mid),
            .o_v(chain_o_v[t]),
            .o_ss(chain_o_ss[t]),
            .o_nv(chain_o_nv[t]),
            .o_wa(chain_o_wa[t]),
            .o_xa(chain_o_xa[t]),
            .sum_in(t==0 ? sum_in : sum_mid),
            .sum_out(chain_sum_out[t]),
            .f_in(t==0 ? f_in : f_mid),
            .f_out(chain_f_out[t]),
            .c_start(c_start[t]),
            .c_rel(c_rel[t]),
            .c_base(c_base[t*(HAW) +: (HAW)]),
            .c_soff(c_soff[t*(SPL*HAW) +: (SPL*HAW)]),
            .c_nwk(c_nwk[t*(SPL*CWW) +: (SPL*CWW)]),
            .c_bnd(c_bnd[t*(SPL*AW) +: (SPL*AW)]),
            .c_pgo(c_pgo[t]),
            .c_pbase(c_pbase[t*(HAW) +: (HAW)]),
            .t_rdy(t_rdy[t]),
            .t_flt(t_flt[t]),
            .xl_q(xl_q[t*(2*NXM*150) +: (2*NXM*150)]),
            .xl_cr(xl_cr[t*(2*NXM) +: (2*NXM)]),
            .xl_done(xl_done[t*(2*NXM) +: (2*NXM)]),
            .hq_v(hq_v[t*(SPL) +: (SPL)]),
            .hq_rdy(hq_rdy[t*(SPL) +: (SPL)]),
            .hq_addr(hq_addr[t*(SPL*HAW) +: (SPL*HAW)]),
            .hq_len(hq_len[t*(SPL*3) +: (SPL*3)]),
            .hq_tag(hq_tag[t*(SPL*TG) +: (SPL*TG)]),
            .hr_v(hr_v[t*(SPL) +: (SPL)]),
            .hr_tag(hr_tag[t*(SPL*TG) +: (SPL*TG)]),
            .hr_beat(hr_beat[t*(SPL*2) +: (SPL*2)]),
            .hr_data(hr_data[t*(SPL*256) +: (SPL*256)])
        );
    end
endmodule
