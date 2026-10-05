#!/usr/bin/env python3
"""Deterministic added-source join; no compiler, simulation or physical launch."""
from pathlib import Path
import json,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1]
ARCH=ROOT/'results/rtl/dsrom_xneed_rtl_join_20261003'
QP=ARCH
def original(record,suffix):
    manifest=json.loads((record/'source_inputs.json').read_text())
    entries=manifest if isinstance(manifest,list) else manifest['origins']
    hits=[e for e in entries if e['path'].endswith(suffix)]
    if len(hits)!=1:raise ValueError('one exact source required: '+suffix)
    e=hits[0];data=(record/e['archive']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=e['sha256']:raise ValueError('source pin changed')
    return data.decode()
def once(s,a,b):
    if s.count(a)!=1:raise ValueError('source substitution not unique: '+a[:70])
    return s.replace(a,b,1)
def generated():
    core=original(QP,'rtl/v41rom/ot_v41_rom_elem_qp_w10.sv')
    core=once(core,'module ot_v41_rom_elem_qp_w10 #(','module ot_v41_rom_elem_qp_xneed_w10 #(')
    core=once(core,'    parameter integer HC = 3,','    parameter integer QP_NEED_LOOKAHEAD = 0, // existing model: zero added cycles, II1\n    parameter integer HC = 3,')
    # Mandatory legal second-row mapping, including delayed output table.
    core=once(core,'s_row[NSEG + cfg_a_e[SW-1:0] - 1]','s_row[NSEG + (32\'(cfg_a_e) - (2*NSEG+1))]')
    core=once(core,'so_row[NSEG + qa_[SW-1:0] - 1]','so_row[NSEG + (32\'(qa_) - (2*NSEG+1))]')
    core=core.replace('end else begin                          // 2NSEG+1+s:', 'end else if (32\'(cfg_a_e) <= 3*NSEG) begin // 2NSEG+1+s:')
    core=once(core,"end else if ({27'd0, qa_} > 2 * NSEG)","end else if ({27'd0, qa_} > 2 * NSEG && 32'(qa_) <= 3*NSEG)")
    start=core.index('    if (FAST != 0) begin : g_nw2')
    end=core.index('    wire pair_match;',start)
    old=core[start:end]
    new='''    wire [UW-1:0] need_local [0:HC-1];
    if (QP_NEED_LOOKAHEAD != 0 && FAST != 0) begin : g_need
        // Three local copies, exact source-sized 84FF each at NSEG8.
        for(genvar h=0;h<HC;h=h+1) begin : g_copy
            wire [2:0] dq,db,dj,dp;wire [SW-1:0] dc;
            if(QTIMING_FIX != 0) begin : g_shadow
                assign dq=g_qt_hit.g_hc[h].d_q;assign db=g_qt_hit.g_hc[h].d_b;
                assign dj=g_qt_hit.g_hc[h].d_j;assign dp=g_qt_hit.g_hc[h].d_pos;
                assign dc=g_qt_hit.g_hc[h].d_c;
            end else begin : g_canonical
                assign dq=n_q;assign db=n_b;assign dj=n_j;assign dp=n_pos;assign dc=n_c;
            end
            ot_v41_need_lookahead #(.N(NSEG)) u_need(.clk(gclk),.rst_n(rst_n),.go(go_e),.go_bf(go_bf_e),
                .accept(hit_k[h]),.q(dq),.b(db),.j(dj),.c(dc),.pos(dp),.qlast(qlast),.plast(plast),
                .current_desc(nA),.next_desc(nB),.q2_desc(nQ2),
                .seed0(sbf(4'd0,2'd3,nu_p,base_go)),.seed1(sbf(4'd1,2'd3,nu_p,base_go)),
                .restart0(sbf(4'd0,2'd3,nu_p,base_live)),.restart1(sbf(4'd1,2'd3,nu_p,base_live)),.nx(need_local[h]));
        end
        assign n_nx=need_local[0];
    end else begin : g_original_need
'''+old+'''        for(genvar h=0;h<HC;h=h+1) assign need_local[h]=n_nx;
    end
    initial if(QP_NEED_LOOKAHEAD != 0 && (FAST==0 || BF16!=0 || BP!=0 || QTIMING_FIX==0 || HC!=3 || NSEG!=8 || NB!=2 || NCH!=16 || XF!=4))
        $fatal(1,"XNEED selected full q geometry/source contract required");
'''
    core=core[:start]+new+core[end:]
    # Local successor clocks disjoint state/descriptor enable groups; don't
    # distribute canonical high-fanout n_nx across all three copies.
    a=core.index('        for (genvar hc = 0; hc < HC; hc = hc + 1) begin : g_hc')
    b=core.index('        assign hit_q = hit_k[0];',a)
    core=core[:a]+core[a:b].replace('n_nx','need_local[hc]')+core[b:]
    for h in (1,2):
        lines=core.splitlines(keepends=True)
        core=''.join(line.replace('n_nx',f'need_local[{h} % HC]') if f'hit_k[{h} % HC]' in line else line for line in lines)
    pair=original(ARCH,'rtl/v41die/ot_v41_pair_w17w10.sv')
    pair=once(pair,'module ot_v41_pair_w17w10 #(','module ot_v41_pair_w17w10_xneed #(')
    pair=once(pair,'    parameter integer FAST = 0,','    parameter integer QP_NEED_LOOKAHEAD = 0,\n    parameter integer QPIPE = 0, QP_CAP = 0, QP_P1 = 1,\n    parameter integer FAST = 0,')
    a=pair.index('    ot_v41_rom_elem_w10 #(');b=pair.index('\nendmodule',a)
    instance=pair[a:b]
    qinst=instance.replace('ot_v41_rom_elem_w10 #(','ot_v41_rom_elem_qp_xneed_w10 #(').replace('.FAST(FAST),','.QP_NEED_LOOKAHEAD(1), .QTIMING_FIX(1), .QPIPE(QPIPE), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .FAST(FAST),')
    # New core uses boundary pin names; outputs keep existing pair contract.
    for port in ('rst_n','cfg_v','cfg_a','cfg_d','go','go_bf','xb_v','xb_b','xb_sv','xb_u','xb_d','xs_v','xs_p','xs_b','xs_sv','xs_q0','xs_e0','xs_q1','xs_e1','xs_pos','xb_pos'):
        qinst=qinst.replace('.'+port+'(','.'+port+'_pin(')
    pair=pair[:a]+'    generate if (QP_NEED_LOOKAHEAD != 0 && BF16 == 0) begin : g_q_need\n'+qinst+'\n    end else begin : g_retained\n'+instance+'\n    end endgenerate'+pair[b:]
    field=original(ARCH,'rtl/dsrom_sys/ot_v41_field_w17w10_sys.sv')
    field=once(field,'module ot_v41_field_w17w10_sys #(','module ot_v41_field_w17w10_xneed_sys #(')
    field=once(field,'    parameter integer FAST = 0,','    parameter integer QP_NEED_LOOKAHEAD = 0,\n    parameter integer QPIPE = 0, QP_CAP = 0, QP_P1 = 1,\n    parameter integer FAST = 0,')
    field=once(field,'        ot_v41_pair_w17w10 #(','        ot_v41_pair_w17w10_xneed #(.QP_NEED_LOOKAHEAD(is_bf(g) ? 0 : QP_NEED_LOOKAHEAD), .QPIPE(QPIPE), .QP_CAP(QP_CAP), .QP_P1(QP_P1), ')
    return {'rtl/v41rom/xneed_lookahead/ot_v41_rom_elem_qp_xneed_w10.sv':core,
        'rtl/v41die/ot_v41_pair_w17w10_xneed.sv':pair,'rtl/dsrom_sys/ot_v41_field_w17w10_xneed_sys.sv':field}
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    for path,text in generated().items():
        out=ROOT/path
        if a.check:
            if out.read_text()!=text:raise ValueError('generated source changed: '+path)
        else:out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text)
if __name__=='__main__':main()
