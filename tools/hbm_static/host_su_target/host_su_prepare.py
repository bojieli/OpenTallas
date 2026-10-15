#!/usr/bin/env python3
"""Bind a real SU compiler image to the heterogeneous host target ABI."""
import argparse, hashlib, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
spec=importlib.util.spec_from_file_location('lower',ROOT/'tools/hbm_static/su_programme_compile.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
r=m.lower(a.source,a.out)
entries="'{"+','.join(map(str,r['dictionary_entries']))+"}"
banks="'{"+','.join(map(str,r['dictionary_banks']))+"}"
tb=(ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_tb.sv').read_text()
for k,v in {'BITS':r['line_bits'],'EDGES':r['edges'],'WRITES':r['config_transactions'],'MACROS':r['total_macros'],'ENTRIES':entries,'BANKS':banks,'DICT':r['first_dictionary_bank']}.items():tb=tb.replace('@'+k+'@',str(v))
(a.out/'host_su_tb.sv').write_text(tb)
model=dict(schema='opentallas.host_su_target.model.v1',qualified=False,
 scope='actual SRAM programme + installation readiness component; no whole-SU or physical claim',
 cfg_abi={'bank_bits':16,'row_bits':7,'payload_bits':256,'packed_config_row_bit7':'must be zero'},
 edges=r['edges'],line_bits=r['line_bits'],macros=r['total_macros'],
 sram_allocated_bits=r['allocated_bits'],loaded_bitmap_ff_bits=r['total_macros']*128,
 config_transactions=r['config_transactions'],validation_scan_edges=r['config_transactions'],
 commit_guard_edges=2,start_to_present_edges=3,start_to_consumer_edges=4,
 steady_command_interval_edges=1,
 area='unmapped: explicit SRAM count and control FF storage only; no routed area estimate',
 image_sha256=r['source_sha256'],dictionary_entries=r['dictionary_entries'],
 source_hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [
 ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_target.sv',
 ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_tb.sv',
 ROOT/'rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv',
 ROOT/r['memory_model']]})
(a.out/'host_su_model.json').write_text(json.dumps(model,indent=2)+'\n')
print(json.dumps(model,indent=2))
