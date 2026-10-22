#!/usr/bin/env python3
"""Materialize only the exact pinned real child interfaces used in top elaboration."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
REF='82add93fc'
FILES=['rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv', 'rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv', 'rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional_r3r.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional_r4l.sv', 'rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv', 'rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_lnland.sv', 'rtl/common/landed_parent/ot_pl_land.sv', 'rtl/common/landed_parent/ot_pl_land_field_copies.sv', 'rtl/common/landed_parent/ot_pl_land_kept_enable.sv', 'rtl/common/landed_parent/ot_pl_land_n32.sv', 'rtl/common/landed_parent/ot_pl_land_physical.sv', 'rtl/common/landed_parent/ot_pl_land_reset_forest.sv', 'rtl/common/landed_parent/ot_pl_land_rst_copy.sv', 'rtl/common/landed_parent/ot_pl_stream_land.sv']
out=Path(sys.argv[1] if len(sys.argv)>1 else 'prior');out.mkdir(parents=True,exist_ok=True)
hashes={}
for name in FILES:
 data=subprocess.check_output(['git','-C',str(ROOT),'show',REF+':'+name])
 p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 hashes[name]=hashlib.sha256(data).hexdigest()
(out/'LIBRARIES.txt').write_text('\n'.join(FILES)+'\n')
(out/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(source=REF,sha256=hashes),indent=2)+'\n')
print('Prepared',len(FILES),'real source-pinned child interfaces; no child functional claim')
