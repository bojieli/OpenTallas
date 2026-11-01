#!/usr/bin/env python3
"""Add the same exact selector substitution at the measured-critical A stage."""
from pathlib import Path
import json
import prepare as P
ROOT=P.ROOT
old_a='''    reg [3:0]    ga;
    reg [XW-1:0] acca;
    always @(*) begin
        ga = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (gea[i]) ga = i[3:0];
        acca = (ga == 4'd15) ? {XW{1'b0}} : s4_r[XW*(ga + 4'd1) +: XW];
    end'''
common='''    reg [3:0] ga;
    wire [XW-1:0] acca;
    always @(*) begin
        ga = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (gea[i]) ga = i[3:0];
    end
'''
head1='''    // A-select R1: top bucket returns ZERO, unlike B's acc_b4 fallback.
    wire [15:0] ah;
    wire az = ~|gea[15:1];
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_highest
        if (ak == 15) begin : g_top
            assign ah[ak] = gea[ak];
        end else begin : g_other
            assign ah[ak] = gea[ak] & ~|gea[15:ak+1];
        end
    end endgenerate
'''
head2='''    // A-select R2: mask and sum capture the SAME compare input edge; no added cycle.
    wire [15:0] gea_nx;
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_compare_next
        assign gea_nx[ak] = s3_r[XW*ak +: XW] >= {{(XW-QW){1'b0}}, q3};
    end endgenerate
    reg [15:0] ah;
    reg az;
    // BEGIN registered A selector -- mutant changes only this block to stale gea
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_highest
        if (ak == 15) begin : g_top
            always @(posedge clk) ah[ak] <= gea_nx[ak];
        end else begin : g_other
            always @(posedge clk) ah[ak] <= gea_nx[ak] & ~|gea_nx[15:ak+1];
        end
    end endgenerate
    always @(posedge clk) az <= ~|gea_nx[15:1];
    // END registered A selector
'''
tree='''    wire [XW-1:0] a_t [0:15];
    generate for (genvar ak = 0; ak < 16; ak = ak + 1) begin : g_a_select_count
        if (ak == 15) begin : g_top
            assign a_t[ak] = {XW{1'b0}};
        end else if (ak == 0) begin : g_zero
            assign a_t[ak] = {XW{az}} & s4_r[XW +: XW];
        end else begin : g_other
            assign a_t[ak] = {XW{ah[ak]}} & s4_r[XW*(ak+1) +: XW];
        end
    end endgenerate
    assign acca = ((a_t[0] | a_t[1]) | (a_t[2] | a_t[3]))
                | ((a_t[4] | a_t[5]) | (a_t[6] | a_t[7]))
                | ((a_t[8] | a_t[9]) | (a_t[10] | a_t[11]))
                | ((a_t[12] | a_t[13]) | (a_t[14] | a_t[15]));'''
assert P.src.count(old_a)==1
recipes=json.loads((ROOT/'recipes.json').read_text())
for n,head in [('r1',head1),('r2',head2)]:
 b=(ROOT/'source'/f'{n}.sv').read_text();assert b.count(old_a)==1
 t=b.replace(old_a,common+head+tree)
 (ROOT/'source'/f'ab_{n}.sv').write_text(t)
 r=dict(recipes['dsdv_bksel_c_pipe_'+n]);r['suffix']='pipe_ab_'+n+'_1131'
 r['rtl_patches']=[dict(r['rtl_patches'][0],why='Actual SEARCH_PIPE1 A+B selectors; unchanged stage/cycle contract',edits=[[old_a,common+head+tree]]+r['rtl_patches'][0]['edits'])]
 r['lec_hints']='tools/s81_ph/bksel_pipe_select_1131/lec_hints_ab_'+n+'.json'
 recipes['dsdv_bksel_c_pipe_ab_'+n]=r
(ROOT/'recipes.json').write_text(json.dumps(recipes,indent=2)+'\n')
print('Prepared A+B companions with distinct zero/acc_b4 top-bucket semantics')
