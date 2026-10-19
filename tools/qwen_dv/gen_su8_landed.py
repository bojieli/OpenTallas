#!/usr/bin/env python3
"""Experimental SU8 regional cut. Original lane/core sources remain untouched.

All four per-lane payloads cross explicit three-edge transports. The new hard
head identity has ML5/RD2 (inner ML11). Native closure and compiler/golden proof
are required before use. This generator does not authorize a gate.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def generate():
    s = (ROOT/'rtl/qwen_dv/qfd_dv_su8_entries.sv').read_text()
    assert s.count('module qfd_dv_su8_entries') == 1
    s = s.replace('module qfd_dv_su8_entries', 'module qfd_dv_su8_landed')
    start = s.index('        end else if (LTD != 0) begin : g_tile_dv')
    stop = s.index('        end else begin : g_tile\n', start)
    b = s[start:stop]
    b = b.replace('qfd_dv_su_lane u_tile', 'qfd_dv_su_lane_landed u_tile')
    b = b.replace('wire [GBW-1:0] b_d = g_grp[l / 8].g_on.gb;', '''wire [GBW-1:0] b_d = {v, fin_th, rrow, asi, bsi, csi, dsi, asrc, bsrc, csrc, mc, md, redsq,
                    ma, mb, dst, red, ad, cls, i_sfu, imm1, imm2, wrom_q};''')
    b = b.replace('wire [2:0]     b_v = g_grp[l / 8].g_on.gv;', 'wire [2:0] b_v = {emit, accept, v_last_r};')
    a = b.index('`ifdef OT_LOREG_MUT')
    z = b.index('            wire [NW-1:0] t_i;', a)
    b = b[:a] + '''            // Keep the wide slot bank local to its receiver. Only one payload
            // traverses the forwarded half-cycle hops. rst_n has a shared logical
            // epoch contract; rst_l remains the lane hard-child release register.
            ot_pl_stream_land #(.W(GBW-WR*16+3+1+4*AW),.HOPS(3)) u_ctl (
                .ck_src(clk),.ck_dst(ck_lane[l]),.rsi(rst_n),
                .i({b_d[GBW-1:WR*16],b_v,live,tcura,tcurb,tcurc,tcurd}),
                .o({b_q[GBW-1:WR*16],bv_q,lv_q,p_q[PDW-1 -: 4*AW]}));
            ot_pl_stream_land #(.W(WR*16+3*32+64),.HOPS(3)) u_answer (
                .ck_src(clk),.ck_dst(ck_lane[l]),.rsi(rst_n),
                .i({b_d[WR*16-1:0],va_q[32*l +: 32],vb_q[32*l +: 32],vc_q[32*l +: 32],crom_q[64*l +: 64]}),
                .o({b_q[WR*16-1:0],p_q[3*32+64-1:0]}));
''' + b[z:]
    a = b.index('`ifdef OT_LIREG_MUT')
    z = b.index('            qfd_dv_su_lane_landed u_tile', a)
    b = b[:a]+b[z:]
    a = b.index('            ot_hdc_delay #(.W(5),')
    z = b.index('            assign {va_re[l]', a)
    b = b[:a] + '''            ot_pl_stream_land #(.W(5+5*AW),.HOPS(3)) u_request (
                .ck_src(ck_lane[l]),.ck_dst(clk),.rsi(rst_n),
                .i({o_v[10:6],o_d[ODW-1 -: 5*AW]}),
                .o({o_vq[10:6],o_dq[ODW-1 -: 5*AW]}));
            ot_pl_stream_land #(.W(OVW-5+ODW-5*AW),.HOPS(3)) u_result (
                .ck_src(ck_lane[l]),.ck_dst(clk),.rsi(rst_n),
                .i({o_v[5:0],o_d[ODW-5*AW-1:0]}),
                .o({o_vq[5:0],o_dq[ODW-5*AW-1:0]}));
''' + b[z:]
    b = b.replace('the head\'s\n            //: ML + 2 + 2 RD alignment are unchanged by the tile\'s own pin flops.',
                  'the new head has ML5/RD2, inner ML11, to price the longer read loop.')
    b = b.replace('//: group broadcast) and the five read requests take RD - 1 relay stages, so the read round trip and',
                  '//: group broadcast) and requests each take three landed edges;')
    s = s[:start]+b+s[stop:]
    # No unused group-wide kept register remains in this LTD-only candidate.
    s = s.replace('if (LT != 0) begin : g_on', 'if (LT != 0 && LTD == 0) begin : g_on')
    # The other generate paths remain available to parse, but candidate use is
    # explicitly constrained; no alternate shape can silently acquire this model.
    anchor = '    // -- lanes '
    i = s.index(anchor)
    s = s[:i]+'''    generate if (LT!=1 || LTD!=1 || SW!=8 || ML!=1 || RD!=2) begin:g_landed_shape
        QFD_SU8_LANDED_REQUIRES_LT1_LTD1_SW8_ML1_RD2 u_bad_shape();
    end endgenerate
'''+s[i:]
    lane = (ROOT/'rtl/qwen_dv/qfd_dv_su_lane.sv').read_text()
    lane = lane.replace('qfd_dv_lane_h','qfd_dv_lane_h_landed').replace('qfd_dv_su_lane','qfd_dv_su_lane_landed')
    lane = lane.replace('OT_DV_SU_LANE_HARD','OT_DV_SU_LANDED_HARD')
    assert lane.count('.ML(1)') == 1
    lane = lane.replace('.ML(1)', '.ML(5)')
    header = '// GENERATED EXPERIMENT: new ML5/RD2 head identity; native closure pending.\n'
    core = (ROOT/'rtl/qwen_dv/qfd_dv_slice2_rsafe.sv').read_text()
    assert core.count('qfd_dv_su8_entries #') == 1
    core = core.replace('qfd_dv_su8_entries #','qfd_dv_su8_landed #')
    return {'rtl/qwen_dv/qfd_dv_su8_landed.sv':header+s,
            'rtl/qwen_dv/qfd_dv_su_lane_landed.sv':header+lane,
            'rtl/qwen_dv/qfd_dv_slice2_landed_rsafe.sv':
                '// EXPERIMENTAL SAME CLOCK FUNCTIONAL INTEGRATION; region ports not yet exposed.\n'+core}


def main():
    for name,text in generate().items():
        (ROOT/name).write_text(text)
        print(name)


if __name__=='__main__':
    main()
