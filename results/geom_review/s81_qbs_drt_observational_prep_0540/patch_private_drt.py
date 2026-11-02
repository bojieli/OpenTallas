#!/usr/bin/env python3
"""Source preparation only: own-container normal-MM then this private wrapper."""
from pathlib import Path
import argparse,hashlib,json
p=argparse.ArgumentParser(description=__doc__);p.add_argument('scripts',type=Path);p.add_argument('--packet',type=Path,required=True);a=p.parse_args()
r=a.scripts.resolve();packet=a.packet.resolve();target=r/'detail_route.tcl';original=r/'detail_route.native_pg_original.tcl'
if original.exists():raise ValueError('refuse rewrap')
before=target.read_bytes();driver=(packet/'private_drt_driver.tcl').read_bytes()
load=b'load_design 5_1_grt.odb 5_1_grt.sdc\n';save=b'orfs_write_db $::env(RESULTS_DIR)/5_2_route.odb\n'
if before.count(load)!=1 or before.count(save)!=1:raise ValueError('exact normal input/output anchors required once')
if driver.count(b'source $::env(SCRIPTS_DIR)/detail_route.native_pg_original.tcl')!=1:raise ValueError('wrong driver')
body=before.replace(load,load+b'source /work/pg_drt_diag_init.tcl\n',1).replace(save,b'source /work/pg_drt_diag_before_save.tcl\n'+save,1)
original.write_bytes(body);target.write_bytes(driver)
print(json.dumps(dict(scope='PRIVATE_OBSERVATIONAL_DRT_NOT_ATOMIC_BIRTH_REJECTION',native_run=False,dispatch_ready=False,antenna_policy_changed=False,original_hooks_preserved=True,native_body_before_sha256=hashlib.sha256(before).hexdigest(),native_body_after_sha256=hashlib.sha256(body).hexdigest(),driver_sha256=hashlib.sha256(driver).hexdigest())))
