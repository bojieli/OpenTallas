#!/usr/bin/env python3
"""s81sl_capc5i: ref_tile gen + GRT dont_touch release (pre_grt) + ck_rt post-CTS region latency balance (pre_cts)."""
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3];kit=Path(__file__).resolve().parent;n=kit.name
rc=subprocess.run(['python3',str(root/'tools/ref_tile/ref_tile.py'),'gen',str(kit/'spec.json')],cwd=root).returncode
p=kit/'pre_grt.tcl';p.write_text(p.read_text()+f'\nsource /src/physical/ref_tile/{n}/grt_dt_release.tcl\n')
p=kit/'pre_cts.tcl';p.write_text(p.read_text()+'\n# DRIVE-S81-CAP: post-CTS region latency balance\nset ::ot_rtb_regions {{ot_entry_0 {{u_rt/clk 266.15 31.85}}}}\nsource /src/physical/ref_tile/'+n+'/rt_leaf_balance.tcl\n')
raise SystemExit(rc)
