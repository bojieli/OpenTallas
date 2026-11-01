#!/usr/bin/env python3
"""Build opt-in actual-pipeline candidates and the stale-selector mutant, without touching defaults."""
from pathlib import Path
import hashlib, json, re
ROOT=Path(__file__).resolve().parent
src=(ROOT/'source/original.sv').read_text()
old='''    reg [XW-1:0] aboveb;
    always @(*) begin
        bb = 4'd0; okb = 1'b0;
        for (i = 0; i < 16; i = i + 1)
            if (geb[i]) begin bb = i[3:0]; okb = 1'b1; end
        aboveb = (bb == 4'd15) ? acc_b4 : u4_r[XW*(bb + 4'd1) +: XW];
    end'''
assert src.count(old)==1
base='''    wire [XW-1:0] aboveb;
    always @(*) begin
        bb = 4'd0; okb = 1'b0;
        for (i = 0; i < 16; i = i + 1)
            if (geb[i]) begin bb = i[3:0]; okb = 1'b1; end
    end
'''
r1head='''    // Opt-in R1: constant-index highest-one mask, balanced returning-count select.
    wire [15:0] gh;
    wire gz = ~|geb[15:1];
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_highest
        if (bk == 15) begin : g_top
            assign gh[bk] = geb[bk];
        end else begin : g_other
            assign gh[bk] = geb[bk] & ~|geb[15:bk+1];
        end
    end endgenerate
'''
r2head='''    // Opt-in R2: register the NEXT compare mask on the same edge as geb.
    wire [15:0] geb_nx;
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_compare_next
        assign geb_nx[bk] = u3_r[XW*bk +: XW] >= {{(XW-QW){1'b0}}, q_b3};
    end endgenerate
    reg [15:0] gh;
    reg gz;
    // BEGIN registered selector -- mutant changes only this block to stale geb
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_highest
        if (bk == 15) begin : g_top
            always @(posedge clk) gh[bk] <= geb_nx[bk];
        end else begin : g_other
            always @(posedge clk) gh[bk] <= geb_nx[bk] & ~|geb_nx[15:bk+1];
        end
    end endgenerate
    always @(posedge clk) gz <= ~|geb_nx[15:1];
    // END registered selector
'''
select='''    wire [XW-1:0] ab_t [0:15];
    generate for (genvar bk = 0; bk < 16; bk = bk + 1) begin : g_select_above
        if (bk == 15) begin : g_top
            assign ab_t[bk] = {XW{gh[bk]}} & acc_b4;
        end else if (bk == 0) begin : g_zero
            assign ab_t[bk] = {XW{gz}} & u4_r[XW +: XW];
        end else begin : g_other
            assign ab_t[bk] = {XW{gh[bk]}} & u4_r[XW*(bk+1) +: XW];
        end
    end endgenerate
    assign aboveb = ((ab_t[0] | ab_t[1]) | (ab_t[2] | ab_t[3]))
                  | ((ab_t[4] | ab_t[5]) | (ab_t[6] | ab_t[7]))
                  | ((ab_t[8] | ab_t[9]) | (ab_t[10] | ab_t[11]))
                  | ((ab_t[12] | ab_t[13]) | (ab_t[14] | ab_t[15]));'''
for name,head in [('r1',r1head),('r2',r2head)]:
 (ROOT/'source'/f'{name}.sv').write_text(src.replace(old,base+head+select))
print('Prepared actual ot_s81ph_sel_su_pipe R1/R2 full-file opt-in copies')
# The canonical generator already supports exact-anchor kit-local rtl_patches.
# These NEW recipe keys preserve its current plan pin/outline contract; no default recipe is edited.
recipes={}
for name,head in [('r1',r1head),('r2',r2head)]:
 recipes['dsdv_bksel_c_pipe_'+name]={'ref_tile':'physical/ref_tile/s81dvbk_selc2','plan_module':'dsdv_bksel_c','suffix':'pipe_'+name+'_1131','two_mode':True,'setup_margin':70,'rtl_patches':[{'file':'rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv','why':'Actual SEARCH_PIPE1 vehicle: cycle-exact constant B-select'+(' with compare-NEXT registered selector' if name=='r2' else ''),'edits':[[old,base+head+select]]}]}
(ROOT/'recipes.json').write_text(json.dumps(recipes,indent=2)+'\n')
