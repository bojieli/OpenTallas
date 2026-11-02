#!/usr/bin/env python3
"""Declare actual saved-route/SDC input AFTER the own-container fill wrapper.

Preserve every stock byte except the one input loader; preserve the driver.
Old input is mounted read-only at /work, new finish capsule beside it at /finish.
This prepares source only and grants no native dispatch/qualification credit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

ANCHOR=b'load_design 5_2_route.odb 5_1_grt.sdc\n'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def quote(value):
    value=str(value)
    if any(c in value for c in '{}\\\r\n'):raise ValueError('unsupported Tcl input path')
    return '{'+value+'}'


def loader(results_dir,odb_name,sdc):
    relative=os.path.relpath(sdc,results_dir)
    return ('''# Declared genuine saved-route input; actual SDC, no 5_1 alias.
if {[info exists ::ot_pg_fill_declared_results]} {error OT_PG_FILL_INPUT_REENTRY}
set ::ot_pg_fill_declared_results $::env(RESULTS_DIR)
try {
  set ::env(RESULTS_DIR) '''+quote(results_dir)+'''
  load_design '''+quote(odb_name)+' '+quote(relative)+'''
} finally {
  set ::env(RESULTS_DIR) $::ot_pg_fill_declared_results
  unset ::ot_pg_fill_declared_results
}
''').encode()


def patch(scripts,results_dir,odb_name,sdc,expected_odb,expected_sdc,receipt):
    scripts,results_dir,sdc=map(lambda p:Path(p).resolve(),(scripts,results_dir,sdc))
    receipt=Path(receipt)
    if Path(odb_name).name!=odb_name or not odb_name.endswith('.odb'):raise ValueError('ODB basename required')
    odb=results_dir/odb_name
    if not odb.is_file() or not sdc.is_file():raise ValueError('actual input missing')
    if sha(odb)!=expected_odb or sha(sdc)!=expected_sdc:raise ValueError('declared input hash mismatch')
    if receipt.exists():raise ValueError('new receipt required')
    entry=scripts/'fillcell.tcl';original=scripts/'fillcell.native_pg_original.tcl'
    driver=entry.read_bytes();before=original.read_bytes()
    if driver.count(b'source $::env(SCRIPTS_DIR)/fillcell.native_pg_original.tcl')!=1 or b'ot_pg_native_birth_end' not in driver:
        raise ValueError('canonical whole-body wrapper must run first')
    if before.count(ANCHOR)!=1:raise ValueError('exact preserved stock loader must occur once')
    declared=loader(results_dir,odb_name,sdc)
    after=before.replace(ANCHOR,declared,1)
    record=dict(schema='opentallas.declared-fill-input.v1',status='PREPARED_NOT_RUN',dispatch_ready=False,
        INPUT_STAGE='genuine_saved5_2_route',actual_odb=str(odb),actual_sdc=str(sdc),
        odb_sha256=expected_odb,sdc_sha256=expected_sdc,
        native_body_before_sha256=hashlib.sha256(before).hexdigest(),
        native_body_after_sha256=hashlib.sha256(after).hexdigest(),driver_sha256=sha(entry),
        source_input_mutated=False,sdc_alias_created=False,other_native_body_changes=False,
        results_dir_restored_before_pre_fillcell=True)
    original.write_bytes(after)
    if entry.read_bytes()!=driver:raise RuntimeError('driver changed unexpectedly')
    with receipt.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scripts',type=Path)
    p.add_argument('--source-results',type=Path,required=True)
    p.add_argument('--odb',required=True)
    p.add_argument('--actual-sdc',type=Path,required=True)
    p.add_argument('--expected-odb-sha256',required=True)
    p.add_argument('--expected-sdc-sha256',required=True)
    p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args();print(json.dumps(patch(a.scripts,a.source_results,a.odb,a.actual_sdc,
        a.expected_odb_sha256,a.expected_sdc_sha256,a.receipt),indent=2))
