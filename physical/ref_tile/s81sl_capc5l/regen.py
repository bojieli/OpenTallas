#!/usr/bin/env python3
"""s81sl_capc5l: ref_tile gen + GRT dont_touch release (pre_grt) + ck_rt post-CTS region latency balance (pre_cts)."""
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3];kit=Path(__file__).resolve().parent;n=kit.name
rc=subprocess.run(['python3',str(root/'tools/ref_tile/ref_tile.py'),'gen',str(kit/'spec.json')],cwd=root).returncode
p=kit/'pre_grt.tcl';p.write_text(p.read_text()+f'\nsource /src/physical/ref_tile/{n}/grt_dt_release.tcl\n')
p=kit/'pre_cts.tcl';p.write_text(p.read_text()+'\n# DRIVE-S81-CAP: post-CTS region latency balance\nset ::ot_rtb_regions {{ot_entry_0 {{u_rt/clk 266.15 31.85}}} {ot_entry_1 {{u_ld3/clk 112.5 8.4} {u_tw/clk 137.1 12.4}}} {ot_entry_2 {{u_ed/clk 98.65 4.45} {u_te/clk 137.1 12.4}}} {ot_entry_3 {}} {ot_entry_4 {}}}\nsource /src/physical/ref_tile/'+n+'/rt_leaf_balance.tcl\n')

p=kit/'post_cts.tcl';p.write_text(p.read_text()+'\n# DRIVE-S81-CAP: post-CTS refine of hard-child chains to the region soft centre (after DPL + hold repair)\nif {![llength [info procs ot_rtb_refine]]} { set ::ot_rtb_offline 1; source /src/physical/ref_tile/'+n+'/rt_leaf_balance.tcl }\nif {[catch {ot_rtb_refine} ot_rtb_e]} { puts "OT_RTB_REFINE ERROR (db kept): $ot_rtb_e" }\n')
raise SystemExit(rc)
