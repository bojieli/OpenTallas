#!/usr/bin/env python3
"""Build fresh kit-local FIFO HLAT sources; source/running kit is never modified."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--prev-forward',action='store_true');a=p.parse_args()
if a.out.exists():raise SystemExit('refuse existing output directory')
s=(a.source/'ot_s81ph_hq_parts.sv').read_text(); t=(a.source/'ot_s81ph_hq_slice.sv').read_text()
def replace(s,old,new):
 if s.count(old)!=1:raise SystemExit('expected exactly one source anchor: '+old[:90])
 return s.replace(old,new)
s=replace(s,'parameter integer W=553, AW=3, NS=(W+15)/16, MUT=0','parameter integer W=553, AW=3, NS=(W+15)/16, MUT=0, HLAT=0, HLAT_PREV=0')
s=replace(s,'    always @(posedge clk) begin waddr0 <= wa[0 +: AW]; waddr1 <= wa[AW +: AW]; wdata <= wd; prevdata <= wdata; end','''    // Launch-side negative-level lockup; macro writes keep their original sampled edge.
    // Receiving posedges see the same value; forwarding changes only after fall.
    wire [W-1:0] wdata_l, prevdata_l;
    ot_s81ph_hlk #(.W(W), .EN(HLAT)) u_fl_fq_wdata (.clk(clk), .d(wdata), .q(wdata_l));
    ot_s81ph_hlk #(.W(W), .EN(HLAT_PREV)) u_fl_fq_prev (.clk(clk), .d(prevdata), .q(prevdata_l));
    always @(posedge clk) begin waddr0 <= wa[0 +: AW]; waddr1 <= wa[AW +: AW]; wdata <= wd; prevdata <= wdata_l; end''')
s=replace(s,"    wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata}, raw;","    wire [NB*128-1:0] padded, raw;\n    assign padded={{(NB*128-W){1'b0}},wdata_l};")
s=replace(s,'assign q[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];','assign q[LO+:SW]=cur_q ? wdata_l[LO+:SW] : prev_q ? prevdata_l[LO+:SW] : raw[LO+:SW];')
old='''    ot_sram_showahead_1r1w_h2 #(.W(W*EW), .AW(FW)) u_fq ('''
new='''`ifdef OT_BKQ_FQ_HLAT
    ot_sram_showahead_1r1w_h2 #(.W(W*EW), .AW(FW), .HLAT(HLAT), .HLAT_PREV('''+('HLAT' if a.prev_forward else '0')+''')) u_fq (
`else
'''+old+'''
`endif'''
t=replace(t,old,new)
a.out.mkdir(parents=True);(a.out/'ot_s81ph_hq_parts.sv').write_text(s);(a.out/'ot_s81ph_hq_slice.sv').write_text(t)
(a.out/'FIFO_HLAT_CHANGE.json').write_text(json.dumps({'opt_in':'OT_BKQ_FQ_HLAT','instance':'u_fq only; u_ofq defaults unchanged','cycle_delta':0,'prev_forward':a.prev_forward,'macro_wdata':'wdata_l; same value sampled at original macro write edge','new_hop_names':['u_fl_fq_wdata','u_fl_fq_prev'],'proof_contract':'Receiving-posedge sampling equivalence; high-phase combinational q waveform intentionally changes'},indent=2)+'\n')
