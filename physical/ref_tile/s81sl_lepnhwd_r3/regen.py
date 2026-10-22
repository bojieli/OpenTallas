#!/usr/bin/env python3
"""Regenerate guarded full-row LEP candidate with source-owned stage hooks."""
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3]
kit=Path(__file__).resolve().parent
rc=subprocess.run(['python3',str(root/'tools/ref_tile/ref_tile.py'),'gen',str(kit/'spec.json')],cwd=root).returncode
with (kit/'place.tcl').open('a')as f:f.write('\nsource /src/physical/ref_tile/s81sl_lepnhwd_r3/lep_rows.tcl\n')
for stage in ('pre_cts','pre_grt','pre_drt','pre_fill'):
 p=kit/(stage+'.tcl');p.write_text('source /src/physical/ref_tile/s81sl_lepnhwd_r3/lep_band.tcl\n'+p.read_text())
for stage in ('post_cts','post_grt','post_drt','post_fill'):
 with (kit/(stage+'.tcl')).open('a')as f:f.write('\nsource /src/physical/ref_tile/s81sl_lepnhwd_r3/lep_band.tcl\not_lep_adopt_after_birth '+stage+'\not_lep_band_check '+stage+'\n')
raise SystemExit(rc)
