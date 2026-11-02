#!/usr/bin/env python3
"""Wrap a reviewed stock stage only in an OWN new container, after normal MM.

No host/live runtime is an admitted target. The owner's launcher must be
reviewed before dispatch. This changes no tool executable, stage body or RTL.
"""
import argparse
from pathlib import Path


def wrap(scripts, driver, stage='global_route'):
    scripts, driver=Path(scripts).resolve(),Path(driver).resolve()
    target=scripts/(stage+'.tcl')
    original=scripts/(stage+'.native_pg_original.tcl')
    anchor={'global_route':'load_design 4_cts.odb 4_cts.sdc\n',
            'cts':'load_design 3_place.odb 3_place.sdc\n',
            'fillcell':'load_design 5_2_route.odb 5_1_grt.sdc\n'}[stage]
    before=target.read_bytes();body=driver.read_bytes()
    if original.exists():raise ValueError('refuse existing native PG runtime wrapper')
    if before.count(anchor.encode())!=1:raise ValueError('stock loaded-design anchor must occur once')
    required=('source $::env(SCRIPTS_DIR)/'+original.name).encode()
    if body.count(required)!=1:raise ValueError('driver must source preserved original stage exactly once')
    if b'ot_pg_native_birth_end' not in body:raise ValueError('driver lacks native cleanup')
    original.write_bytes(before)
    target.write_bytes(body)
    return original


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scripts',type=Path)
    p.add_argument('--driver',type=Path,required=True)
    p.add_argument('--stage',choices=('global_route','cts','fillcell'),default='global_route')
    a=p.parse_args();print('OWN_CONTAINER_PG_WRAPPER',wrap(a.scripts,a.driver,a.stage))
