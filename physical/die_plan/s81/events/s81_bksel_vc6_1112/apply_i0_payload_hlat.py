#!/usr/bin/env python3
"""Fresh-source-only opt-in BKSEL i0 payload forwarding lockup; zero cycles."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
if a.out.exists():raise SystemExit('refuse existing output directory')
s=(a.source/'ot_s81ph_hq_slice.sv').read_text()
def once(old,new):
 global s
 if s.count(old)!=1:raise SystemExit('expected one exact consumer anchor: '+old[:100])
 s=s.replace(old,new)
anchor='''    // -- ingest: filter (CMP_RETIME, H8) ----------------------------------------------------------------------------'''
new='''    // Optional zero-cycle forwarding of the complete registered i0 payload.
    // Data consumers sample the same value on each receiving posedge; raw
    // in_val/in_sg H8 compare inputs and every i0 control edge stay unchanged.
    wire [W-1:0] i0_lv_f;
    wire [W*16-1:0] i0_val_f;
    wire [W*IW-1:0] i0_idx_f;
`ifdef OT_BKQ_I0_OUT_HLAT
    ot_s81ph_hlk #(.W(W*(17+IW)), .EN(HLAT)) u_fl_i0out (
        .clk(clk), .d({i0_lv, i0_val, i0_idx}), .q({i0_lv_f, i0_val_f, i0_idx_f}));
`else
    assign {i0_lv_f, i0_val_f, i0_idx_f} = {i0_lv, i0_val, i0_idx};
`endif

'''+anchor
once(anchor,new)
once('wire [15:0] v0  = i0_val[16*gl +: 16];','wire [15:0] v0  = i0_val_f[16*gl +: 16];')
once('assign i1_s_d[gl] = i0_lv[gl] && ge;','assign i1_s_d[gl] = i0_lv_f[gl] && ge;')
once('assign i1_fm_d[gl] = i0_lv[gl] && ge && hi_match;','assign i1_fm_d[gl] = i0_lv_f[gl] && ge && hi_match;')
once('assign i0_lane[EW*gl +: EW] = {i0_lv[gl], i0_val[16*gl +: 16], i0_idx[IW*gl +: IW]};','assign i0_lane[EW*gl +: EW] = {i0_lv_f[gl], i0_val_f[16*gl +: 16], i0_idx_f[IW*gl +: IW]};')
# Explicitly preserve the direct H8 compare inputs and input/control registers.
for required in ['wire [15:0] vx  = in_val[16*gl +: 16];','assign ik[15]   = ~in_sg[4*gl + 3];','i0_last <= in_last_l; i0_lv <= in_lv_l; i0_val <= in_val_l; i0_idx <= in_idx_l; i0_rp <= rp_acc;']:
 if s.count(required)!=1:raise SystemExit('required untouched source anchor absent')
a.out.mkdir(parents=True);(a.out/'ot_s81ph_hq_slice.sv').write_text(s)
(a.out/'I0_PAYLOAD_HLAT_CHANGE.json').write_text(json.dumps({'opt_in':'OT_BKQ_I0_OUT_HLAT','default':'off; existing HLAT parameter controls latch enable when selected','new_hop':'u_fl_i0out','payload_bits':592,'cycle_delta':0,'consumers':['i0_lane (P input, replay mux, sign copies)','g_i1.v0/fkey -> i1_k','i1_s_d/i1_fm_d LV mask'],'untouched':['in_val/in_sg direct H8 compare','i0_v/i0_rp/i0_last controls','register and macro write edges'],'status':'conditional backup; not selected'},indent=2)+'\n')
