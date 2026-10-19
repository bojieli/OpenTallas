from pathlib import Path
import json,subprocess,shutil,hashlib
p=Path(__file__).resolve().parent;root=p.parents[1];kit=root/'physical/ref_tile/pg_xor16_canonical_1019'
s=json.loads((p/'spec.json').read_text());s['orfs_vars']={'PRE_TAPCELL_TCL':'/src/tests/pg_canonical_coupon_1019/band_rows.tcl'}
for mode in ['default','strict']:
 c=dict(s);c['pg_strict']=mode=='strict'
 spec=p/('spec_'+mode+'.json');spec.write_text(json.dumps(c,indent=2)+'\n')
 subprocess.run(['python3',str(root/'tools/ref_tile/ref_tile.py'),'gen',str(spec)],check=True)
 for name in ['clock.sdc','signoff.sdc']:(kit/name).write_bytes((p/'component.sdc').read_bytes())
 for name in ['pre_cts.tcl','post_cts.tcl','pre_grt.tcl','post_grt.tcl','pre_drt.tcl','post_drt.tcl','pre_fill.tcl','post_fill.tcl']:
  (kit/name).write_text('# Private sourceowned component boundary; canonical ORFS stage is unchanged.\nsource /src/tests/pg_canonical_coupon_1019/component_boundary.tcl\n')
 snapshot=p/'profiles'/mode
 if snapshot.exists():shutil.rmtree(snapshot)
 shutil.copytree(kit,snapshot)
print('KIT_GENERATION_ONLY_NO_PHYSICAL_ENGINE')
