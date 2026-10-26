#!/usr/bin/env python3
"""QE3-SLICE2 10-21: census-only PROXY hard view for qfd_dv_s8_station_tail1 (slice12_kit --census-hard).
Copies the CLOSED qfd_dv_slice2_stnrgc g3 view (cell qfd_dv_redstn2_region: same 19 ports, same pin regions, same
151.2 x 151.2 outline as station_tail1) and renames the cell. Purpose: the parent's mapped native census sees exactly the
hard-child boundary (one load per pin) it will see with the real CLOSED station view. NEVER used for a gate or a bind:
the gate kits keep refusing until the real station_tail1 view exists (slice11_kit HOLD), and this proxy dir is only
created inside census source snapshots, never committed."""
import shutil,sys
from pathlib import Path
R=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=R/'physical/ref_tile/qfd_dv_slice2_stnrgc/views/qfd_dv_redstn2_region'
dst=R/'physical/ref_tile/qfd_dv_s8_station_tail1/views/qfd_dv_s8_station_tail1'
dst.mkdir(parents=True,exist_ok=True)
for f in src.rglob('*'):
    if f.is_dir():continue
    rel=Path(str(f.relative_to(src)).replace('qfd_dv_redstn2_region','qfd_dv_s8_station_tail1'))
    o=dst/rel;o.parent.mkdir(parents=True,exist_ok=True)
    try:o.write_text(f.read_text().replace('qfd_dv_redstn2_region','qfd_dv_s8_station_tail1'))
    except UnicodeDecodeError:shutil.copy(f,o)
print('STN_CENSUS_PROXY',dst,sum(1 for _ in dst.rglob('*')))
