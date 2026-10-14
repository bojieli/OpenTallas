#!/usr/bin/env python3
"""Distinct exact selector clock-owned successors; coherent common phase only."""
import re,hashlib,json
from pathlib import Path
root=Path('rtl/hbm_accel/index')
src=['rtl/hdc/v41x/ot_hdc_v41x_sel.sv','rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv']
s=Path(src[0]).read_text().replace('ot_hdc_v41x_sel_ctl','ot_hbm_idx_sel_ctl_owned_native').replace('module ot_hdc_v41x_sel #','module ot_hbm_idx_sel_owned_native #').replace('ot_hdc_v41x_sel_slice','ot_hbm_idx_sel_slice_owned_native')
a=s.index('module ot_hbm_idx_sel_owned_native');b=s.index('module ot_hbm_idx_sel_ctl_owned_native');top=s[a:b];ctl=s[b:]
top=top.replace('input  wire                     clk,','input wire clk,clk_ctl,\n    input wire [Q-1:0] clk_slice,\n    input wire [Q*2-1:0] clk_hist,clk_pack,\n    input wire [1:0] clk_search,',1).replace('.clk(clk), .rst_n(rst_n),','.clk(clk_slice[gq]), .clk_hist(clk_hist[gq*2+:2]), .clk_pack(clk_pack[gq*2+:2]), .rst_n(rst_n),',1)
# Control boundary, not slice replacement.
needle='ot_hbm_idx_sel_ctl_owned_native #'
pos=top.index(needle);top=top[:pos]+top[pos:].replace('.clk(clk), .rst_n(rst_n),','.clk(clk_ctl), .clk_search(clk_search), .rst_n(rst_n),',1)
ctl=ctl.replace('input  wire                    clk,','input wire clk,\n    input wire [1:0] clk_search,',1)
for i,inst in enumerate(['u_cs','u_fs']):
 ctl=re.sub(r'('+inst+r'\s*\(\s*)\.clk\(clk\)',r'\1.clk(clk_search['+str(i)+'])',ctl)
sl=Path(src[1]).read_text().replace('module ot_hdc_v41x_sel_slice #','module ot_hbm_idx_sel_slice_owned_native #').replace('input  wire                  clk,','input wire clk,\n    input wire [1:0] clk_hist,clk_pack,',1)
for family,insts in [('hist',['u_hc','u_hf']),('pack',['u_pi','u_ps'])]:
 for i,inst in enumerate(insts):
  sl=re.sub(r'('+inst+r'\s*\(\s*)\.clk\(clk\)',r'\1.clk(clk_'+family+'['+str(i)+'])',sl)
(root/'ot_hbm_idx_selector_owned_native.sv').write_text('// Distinct functional source. No old physical view alias.\n'+top+ctl+'\n'+sl)
(root/'ot_hbm_idx_selector_owned_lineage.json').write_text(json.dumps({'source_sha256':{f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in src},'clock_entries':'top1+control1+search2+4slice+8histogram+8pack=24 coherent entries for Q4 topK. Original helper bodies unchanged, every used child has distinct externally owned clock pins.','physical_qualified':False},indent=2)+'\n')
