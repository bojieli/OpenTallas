#!/usr/bin/env python3
"""PREP ONLY: whole-body PG wrapper with honest fixed-clock PLACE/GRT input.

Run only inside a root-reviewed OWN new container, after normal MM patch.
No fake CTS input filenames, no CTS/GPL operation or credit.
"""
import argparse,hashlib,json
from pathlib import Path

def wrap(scripts,driver):
 scripts=Path(scripts).resolve();driver=Path(driver).resolve()
 target=scripts/'global_route.tcl';original=scripts/'global_route.native_pg_original.tcl'
 if original.exists():raise ValueError('Existing native PG wrapper preserved; refuse overwrite')
 before=target.read_bytes();body=driver.read_bytes()
 old=b'load_design 4_cts.odb 4_cts.sdc\n'
 new=b'load_design fixed_clock_PLACE_input.odb fixed_clock_PLACE_input.sdc\n'
 if before.count(old)!=1:raise ValueError('Expected exact stock GRT load anchor once')
 if body.count(b'source $::env(SCRIPTS_DIR)/global_route.native_pg_original.tcl')!=1:raise ValueError('Whole-body driver must source preserved stage once')
 if b'ot_pg_native_birth_end' not in body:raise ValueError('Whole-body PG cleanup missing')
 honest=before.replace(old,new,1)
 original.write_bytes(honest);target.write_bytes(body)
 receipt={'scope':'PRIVATE_HONEST_FIXED_CLOCK_PLACE_INPUT_PLUS_WHOLE_BODY_PG_WRAPPER','INPUT_STAGE':'fixed_clock_PLACE','cts_credit':False,'rtl_changed':False,'other_native_body_changes':False,'stock_after_mm_sha256':hashlib.sha256(before).hexdigest(),'honest_body_sha256':hashlib.sha256(honest).hexdigest(),'driver_sha256':hashlib.sha256(body).hexdigest(),'load_design':new.decode().strip()}
 print(json.dumps(receipt,indent=2));return receipt

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('scripts',type=Path);p.add_argument('--driver',type=Path,required=True);a=p.parse_args();wrap(a.scripts,a.driver)
