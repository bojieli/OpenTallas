#!/usr/bin/env python3
"""Prepare the actual GQ issue/RING/land caller with explicit external partners.

qids2/3 are the two physical north cuts. qids0/1 are real source components
at the external boundary; this is not a claim of four locally bound NTOP cuts.
"""
from pathlib import Path
import re, argparse
ROOT=Path(__file__).resolve().parents[3]
def prepare(out, warm=False):
    s=(ROOT/'rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_gq.sv').read_text()
    s=s.replace('parameter integer MUT = 0, KQMUT = 0;', 'parameter integer MUT = 0, KQMUT = 0;\n    parameter integer OUTER_PROFILE=0, RING_FACES=0;\n    localparam integer PAIR_PERIOD=OUTER_PROFILE ? 5 : 3;')
    s=s.replace('reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;', 'reg clk=0, rst_n=0; always begin #0.416 clk=1; #0.417 clk=0; end')
    s=s.replace('ot_hgi_coll_gq #(.MUT(MUT), .VM_RT(VM_RT))', 'ot_hgi_coll_gq #(.MUT(MUT), .VM_RT(VM_RT), .OUTER_FACE_B2(OUTER_PROFILE))')
    a=s.index('        ot_hgi_coll_ring_ag #(.SPLIT_CLOCKS(1), .AG(1)) ra(')
    b=s.index('        ot_hgi_coll_ring_b_stop rb(', a)
    old=s[a:b]
    s=s[:a]+('''        if(q>=2) begin:g_native_north
            if(RING_FACES) begin:g_face
'''+old.replace('ot_hgi_coll_ring_ag #','source_ring_cut_api #')+'''            end else begin:g_bare
'''+old.replace('ot_hgi_coll_ring_ag #','native_ring_cut_api #')+'''            end
        end else begin:g_external_partners
'''+old+'''        end
''')+s[b:]
    s=s.replace('localparam integer NR = 6,', 'localparam integer NR = 2,')
    vals={'r_qbg':'0,0','r_r2':'1,0','r_self':'0,0','r_t':'0,300+VM_RT','r_f':'72,19','r_bs':'0,0','r_src':"'h1000,'h1100",'r_dst':"'h0000,'h0200",'r_str':'72,24','r_vec':'"",""'}
    for name,v in vals.items():
        pat=rf'({name}\s*\[0:NR-1\]\s*=\s*)\x27\{{[^}}]*\}};'
        s,n=re.subn(pat,lambda m:m[1]+"'{"+v+'};',s);assert n==1,name
    s=s.replace('3 * (k / 2)', 'PAIR_PERIOD * (k / 2)')
    s=s.replace('wres[q][a%8][ie+32+KS+2*h+VM_RT]','wres[q][a%8][ie+32+KS+2*h+VM_RT+face_extra(q,d,h,r)]')
    s=s.replace('wsec[q][a%8][ie+32+KS+2*h+VM_RT]','wsec[q][a%8][ie+32+KS+2*h+VM_RT+face_extra(q,d,h,r)]')
    fn='''    function automatic integer face_extra(input integer q,d,h,r);
        integer atq,extra; atq=q;extra=(q>=2)?2:0;
        for(integer j=0;j<h;j=j+1)begin atq=d?nextq(atq):prevq(atq);if(atq>=2)extra+=2;end
        return OUTER_PROFILE && r==0 ? extra : 0;
    endfunction
'''
    s=s.replace('    // ---------------------------------------------------------------- host frame',fn+'    // ---------------------------------------------------------------- host frame',1)
    s=s.replace('COLLQ PASS ', 'COLLQ_FACE_CALLER_PASS ')
    s=s.replace('gather_edges_F72R2=%0d', 'compiled_span_F72R2=%0d')
    s=s.replace('1 + 3 * ((36 - 1) / 2) + ((36 - 1) % 2) + 38', '1 + PAIR_PERIOD * ((36 - 1) / 2) + ((36 - 1) % 2) + 40 + VM_RT + (OUTER_PROFILE?4:0)')
    s=s.replace('repeat (5) @(negedge clk); rst_n = 1; repeat (6)', 'repeat (66) @(negedge clk); rst_n = 1; repeat (66)')
    if warm:
        s=s.replace('parameter integer OUTER_PROFILE=0, RING_FACES=0;', 'parameter integer OUTER_PROFILE=0, RING_FACES=0, VM_WARM_MUT=0;')
        s=s.replace('    integer cyc = 0;', '    wire warm_reset,warm_done; wire whole_rst_n=rst_n&&!warm_reset;\n    integer cyc = 0;',1)
        s=s.replace('.rst_n(rst_n)', '.rst_n(whole_rst_n)')
        s=s.replace('if (rst_n &&', 'if (whole_rst_n &&')
        coupon="""    native_vm_warm_coupon #(.MUT_RESET(VM_WARM_MUT)) warm_coupon(.clk(clk),.cold_rst_n(rst_n),.enable(1'b1),
        .queued_valid(|g_q[3].pa_v),.kq(v_kq[3][0+:281]),.warm_reset(warm_reset),.done(warm_done));
    initial begin wait(warm_done); $display("COLLQ_QUEUED_WARM_PASS");$finish;end
"""
        s=s.replace('    // ---------------------------------------------------------------- VM model',coupon+'    // ---------------------------------------------------------------- VM model',1)
    # Preserve the existing independently checked source words and all reservations.
    out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'tb.sv').write_text(s)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('out');a.add_argument('--warm',action='store_true');v=a.parse_args();prepare(v.out,v.warm)
