#!/usr/bin/env python3
"""Cheap source-exact controller preflight alongside, never replacing full arithmetic proof."""
import argparse,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
s=(ROOT/'rtl/hdc/v41x/static/ot_hdc_v41x_attn_calendar.sv').read_text();prefix=s.split('    // ================= staging buffer =================')[0]
prefix=prefix.replace('ot_hdc_v41x_attn_calendar #(', 'ot_attn_control_preflight #(')
prefix+='''
// The exact real-staging control pipeline: tags captured at read issue;
// rd_fill is the one-edge macro response tag, independent of payload data.
always @(posedge clk or negedge rst_n) if(!rst_n)begin rd_fill<=0;rd_qk<=0;end else begin rd_fill<=fl_go;rd_qk<=qk_go;end
always @(posedge clk)begin fill_blk_d<=fl_blk;fill_cnt_d<=fl_cnt;end
endmodule
`default_nettype wire
'''
(a.out/'controller.sv').write_text(prefix)
(a.out/'sha.txt').write_text(hashlib.sha256(s.encode()).hexdigest()+'\n')
