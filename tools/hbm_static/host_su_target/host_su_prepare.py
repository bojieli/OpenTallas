#!/usr/bin/env python3
"""Bind a real SU compiler image to the heterogeneous host target ABI."""
import argparse, hashlib, importlib.util, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path);p.add_argument('--extra-mem',type=Path);p.add_argument('--extra-bits',type=int,default=0);p.add_argument('--lowerer',type=Path,default=ROOT/'tools/hbm_static/su_programme_compile.py');p.add_argument('--lowerer-root',type=Path);p.add_argument('--line-bits',type=int,default=9688);a=p.parse_args()
spec=importlib.util.spec_from_file_location('lower',a.lowerer)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if a.lowerer_root:m.ROOT=a.lowerer_root
kw={'line_bits':a.line_bits} if a.line_bits!=9688 else {}
r=m.lower(a.source,a.out,a.extra_mem,a.extra_bits,**kw)
if r.get('index_pack',1)!=1:raise ValueError('host_su_target supports INDEX_PACK=1 only; packed layout requires a new readiness validator')
r['source_pins']['tools/hbm_static/su_programme_compile.py']=hashlib.sha256(a.lowerer.read_bytes()).hexdigest()
(a.out/'manifest.json').write_text(json.dumps(r,indent=2)+'\n')
entries="'{"+','.join(map(str,r['dictionary_entries']))+"}"
banks="'{"+','.join(map(str,r['dictionary_banks']))+"}"
tb=(ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_tb.sv').read_text()
for k,v in {'BITS':r['line_bits'],'EDGES':r['edges'],'WRITES':r['config_transactions'],'MACROS':r['total_macros'],'ENTRIES':entries,'BANKS':banks,'DICT':r['first_dictionary_bank']}.items():tb=tb.replace('@'+k+'@',str(v))
(a.out/'host_su_tb.sv').write_text(tb)
axi=(ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_axi_tb.sv').read_text()
for k,v in {'BITS':r['line_bits'],'EDGES':r['edges'],'WRITES':r['config_transactions'],'MACROS':r['total_macros'],'ENTRIES':entries,'BANKS':banks}.items():axi=axi.replace('@'+k+'@',str(v))
(a.out/'host_su_axi_tb.sv').write_text(axi)
lef=ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
width,height=map(float,re.search(r'SIZE ([0-9.]+) BY ([0-9.]+)',lef.read_text()).groups())
model=dict(schema='opentallas.host_su_target.model.v1',qualified=False,
 scope='actual SRAM programme + installation readiness component; no whole-SU or physical claim',
 cfg_abi={'bank_bits':16,'row_bits':7,'payload_bits':256,'packed_config_row_bit7':'must be zero'},
 edges=r['edges'],line_bits=r['line_bits'],macros=r['total_macros'],
 sram_allocated_bits=r['allocated_bits'],loaded_bitmap_ff_bits=r['total_macros']*128,
 config_transactions=r['config_transactions'],validation_scan_edges=r['config_transactions'],
 commit_guard_edges=2,start_to_present_edges=3,start_to_consumer_edges=4,
 steady_command_interval_edges=1,supported_index_pack=1,unsupported_layout_action='refuse compiler/model preparation; packed macro capacity fails native elaboration',axi_boundary_ff_bits=387,axi_words_per_config=9,axi_min_write_interval_edges=3,
 macro_outline_um=[width,height],macro_area_sum_mm2=width*height*r['total_macros']/1e6,
 area='macro outline sum only; control FF/mux, placement whitespace and clocks unmeasured',
 physical_clock_limit=('loaded bitmap alone exceeds 15000 sinks on controller clk; requires partition or measured CTS before physical acceptance' if r['total_macros']*128>15000 else 'loaded bitmap below 15000; actual total sink count and physical CTS unmeasured'),
 lowerer_sha256=hashlib.sha256(a.lowerer.read_bytes()).hexdigest(),image_sha256=r['source_sha256'],extra_sha256=r['extra_sha256'],dictionary_entries=r['dictionary_entries'],
 source_hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [
 ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_target.sv',
 ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_tb.sv',
 ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_axi_install.sv',
 ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_axi_tb.sv',
 ROOT/'rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv',
 ROOT/r['memory_model'],lef]})
(a.out/'host_su_model.json').write_text(json.dumps(model,indent=2)+'\n')
print(json.dumps(model,indent=2))
