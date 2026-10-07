#!/usr/bin/env python3
"""Fresh SS/FF parasitic timing; preserve clock ownership and full path reports."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/w18'))
import corner_sta as C
p=argparse.ArgumentParser();p.add_argument('--orfs-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
original=C.script
def script(corner,base,macros,post_sdc=()):
 s=original(corner,base,macros,post_sdc)
 extra='''
if {[llength [all_clocks]]!=6} {error "actual forwarded clocks lost"}
source /src/physical/qwen_link_forwarded_tmr_pair/reset_inventory.tcl
report_clock_properties [all_clocks]
foreach c {ab_hop1 ba_hop1} {
 report_checks -to [all_registers -clock $c -data_pins] -path_delay min_max -group_path_count 8 -format full_clock_expanded
}
check_setup -verbose
puts "FORWARDED_SIGNOFF_CLOCKS_OK"
'''
 return s.rsplit('exit\n',1)[0]+extra+'exit\n'
C.script=script
r=dict(schema='opentallas.qwen_forwarded_pair.ssff.v1',setup_ss=C.run(a.orfs_dir,'ss',[]),hold_ff=C.run(a.orfs_dir,'ff',[]),adoption=False,remaining=['die endpoint budgets','control/link protection','cold reset physical binding','warm drain and epoch','postroute clockbuffer and placement inventory','DRC0'])
for corner in ['ss','ff']:
 log=(a.orfs_dir/f'w18_sta_{corner}.log').read_text()
 if 'FORWARDED_SIGNOFF_CLOCKS_OK' not in log or 'Error:' in log:
  r['setup_ss' if corner=='ss' else 'hold_ff']['errors'].append('Fresh timing script failed clock/path qualification')
r['margin_pass']=all(x['worst_slack_ps'] is not None and x['worst_slack_ps']>=15 and not x['errors'] for x in [r['setup_ss'],r['hold_ff']])
a.output.write_text(json.dumps(r,indent=2)+'\n')
