#!/usr/bin/env python3
"""Source-preserving ten-root BF column successor (opt-in, unqualified).

Copies real reviewed arithmetic unchanged; changes only clock/reset distribution.
All ten clocks must be same-PLL/same-frequency/zero-phase sources with individual
physical phi-R delivery. No asynchronous exception or dynamic scheduling exists.
This is source plumbing for subsequent local physical leaves, not a flat closure.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]


def replace_once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)


def generate():
    path=ROOT/'rtl/v41rom/ot_v41_bf16_lanes3.sv';base=path.read_text()
    s=replace_once(base,'module ot_v41_bf16_lanes3 #(','module ot_v41_bf16_lanes3_roots #(')
    s=replace_once(s,'    input  wire              fclk,','    input wire [5:0] leaf_clk, // lane groups0..3, reduction level0, reduction levels1..3\n    input  wire              fclk,')
    # Lane groups use authentic independent top clock sources; local gates remain.
    s=replace_once(s,'        wire lclk, lrst;',
        '        wire lclk, lrst;\n`ifdef BF_ROOT_MUTANT_STOP\n        wire lane_fclk=l<4 ? 1\'b0 : leaf_clk[l/4];\n`else\n        wire lane_fclk=leaf_clk[l/4];\n`endif')
    s=s.replace('u_tl (.fclk(fclk)', 'u_tl (.fclk(lane_fclk)')
    a='    genvar lv, k;'
    b='''    wire [1:0] tree_clk, tree_rst;
    for (genvar q=0;q<2;q++) begin : g_tree_root
        ot_v41_tile_clk u_tc (.fclk(leaf_clk[4+q]), .rst_pin(rst_pin), .ze_d(ze_d),
                             .gclk(tree_clk[q]), .rst_n(tree_rst[q]));
    end
    genvar lv, k;'''
    s=replace_once(s,a,b)
    a=s.index('    generate for (lv = 0;');tail=s[a:]
    tail=replace_once(tail,'        localparam integer NN =', '        wire lvclk=tree_clk[lv==0?0:1];\n        wire lvrst=tree_rst[lv==0?0:1];\n        localparam integer NN =')
    tail=tail.replace('.clk(clk)', '.clk(lvclk)').replace('.rst_n(rst_n)', '.rst_n(lvrst)').replace('posedge clk','posedge lvclk').replace('negedge rst_n','negedge lvrst').replace('if (!rst_n)','if (!lvrst)')
    s=s[:a]+tail
    lp=ROOT/'rtl/v41rom/ot_v41_bf16_lanes3_roots.sv';lp.write_text(s)
    path=ROOT/'rtl/v41rom/ot_v41_bf_col.sv';base_col=path.read_text()
    s=replace_once(base_col,'module ot_v41_bf_col #(','module ot_v41_bf_col_roots #(')
    # Locate real port declaration without relying on generated text spacing.
    import re
    m=re.search(r'(    input\s+wire\s+clk\s*,)',s);assert m
    s=s[:m.start()]+'    input wire [8:0] leaf_clk, // fp0, fp1, segment, four lane groups, two reduction roots\n'+s[m.start():]
    a='    // QPIPE: this macro\'s own copy'
    pos=s.index(a)
    s=s[:pos]+'''    // Three actual roots for FP4 chains/pair and segment reduction. Same registered
    // enable/reset functions as the original root; arithmetic stages are unchanged.
    wire [2:0] local_gclk,local_rst;
    for (genvar root=0;root<3;root++) begin : g_local_root
        ot_v41_tile_clk u_tc (.fclk(leaf_clk[root]),.rst_pin(b_rst),.ze_d(b_ze),
                             .gclk(local_gclk[root]),.rst_n(local_rst[root]));
    end
'''+s[pos:]
    # Existing arithmetic module boundaries form the FP4 physical leaf cuts.
    for inst,group in [('u_l0',0),('u_l1',1),('u_c0',0),('u_c1',1),('u_pair',0)]:
        pattern=rf'({inst}\s*\(\.clk\()gclk_c(\),\s*\.rst_n\()rst_m[cp]?(\))'
        s,n=re.subn(pattern,rf'\g<1>local_gclk[{group}]\g<2>local_rst[{group}]\g<3>',s)
        assert n>0,inst
    # Shared tag/pass pipelines belong to FP0; their cycle counts remain literal.
    for inst in ['u_pp','u_pt']:
        pattern=rf'({inst}\s*\(\.clk\()gclk_c(\),\s*\.rst_n\()rst_mp(\))'
        s,n=re.subn(pattern,r'\g<1>local_gclk[0]\g<2>local_rst[0]\g<3>',s)
        assert n==1,inst
    # Segment subtree and final registered outputs use root2.
    start=s.index('    if (FAST != 0 && QPIPE != 0 && QX >= 9) begin : g_tr5')
    end=s.index('    if (QY != 0) begin : g_qyb',start)
    seg=s[start:end].replace('.clk(gclk_c)','.clk(local_gclk[2])').replace('posedge gclk_c','posedge local_gclk[2]').replace('rst_mt','local_rst[2]')
    s=s[:start]+seg+s[end:]
    s=replace_once(s,'ot_v41_bf16_lanes3 #(','ot_v41_bf16_lanes3_roots #(')
    # Only BF16 lanes3 has .fclk(clk) at this point (root gate .fclk uses spaces).
    s=replace_once(s,'            .fclk(clk), .rst_pin(b_rst)', '            .leaf_clk(leaf_clk[8:3]), .fclk(clk), .rst_pin(b_rst)')
    cp=ROOT/'rtl/v41rom/ot_v41_bf_col_roots.sv';cp.write_text(s)
    wp=ROOT/'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv';w=wp.read_text();w=w.replace('module dsfd_bf_col #(','module dsfd_bf_col_roots #(')
    w=replace_once(w,'    input  wire [775:0] ci,','    input wire [8:0] leaf_ck,\n    input  wire [775:0] ci,')
    w=replace_once(w,'    ot_v41_bf_col #(','    ot_v41_bf_col_roots #(')
    w=replace_once(w,'.clk(w_clk),','.clk(w_clk), .leaf_clk(leaf_ck),')
    rp=ROOT/'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col_roots.sv';rp.write_text(w)
    rec={'status':'SOURCE_ONLY_NOT_PHYSICAL_CLOSURE','cycles_added':0,'clock_contract':'10 same-PLL833.333ps phase0 roots; physical leaf delivery phi-R individually; ordinary synchronous timing on every cross-root path',
         'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,ROOT/'rtl/v41rom/ot_v41_bf16_lanes3.sv',wp]},
         'outputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [lp,cp,rp]},
         'physical_leaf_status':'Root plumbing complete. Extraction/hardening and boundary channel/capture/launch proof still required. No footprint proposed before measured area/cuts.',
         'roots':['ck: boundary/memory/input relays','leaf_ck[0]: FP4 term0+chain0+pair','leaf_ck[1]: FP4 term1+chain1','leaf_ck[2]: segment reduction/output','leaf_ck[3]: BF16 lanes0..3','leaf_ck[4]: BF16 lanes4..7','leaf_ck[5]: BF16 lanes8..11','leaf_ck[6]: BF16 lanes12..15','leaf_ck[7]: BF16 pairwise level0','leaf_ck[8]: BF16 pairwise levels1..3']}
    out=ROOT/'results/rtl/s81_bf_clock_1015/c10/recovery_0253/root_source.json';out.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))


if __name__=='__main__':generate()
