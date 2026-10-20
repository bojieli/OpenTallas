#!/usr/bin/env python3
"""s81sl_capc5g: ref_tile gen + landing dont_touch release appended to pre_grt.tcl (S81-TILES-D)."""
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3];kit=Path(__file__).resolve().parent
rc=subprocess.run(['python3',str(root/'tools/ref_tile/ref_tile.py'),'gen',str(kit/'spec.json')],cwd=root).returncode
p=kit/'pre_grt.tcl';p.write_text(p.read_text()+'\nsource /src/physical/ref_tile/s81sl_capc5g/landing_dt.tcl\n')
p=kit/'pre_cts.tcl';p.write_text(p.read_text()+'\n# S81-TILES-D: ck_rt regional roots (k-means clusters) inside the rt region\nsource /src/physical/common_flow/clock_split_km.tcl\n')
raise SystemExit(rc)
