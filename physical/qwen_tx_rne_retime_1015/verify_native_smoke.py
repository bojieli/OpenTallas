#!/usr/bin/env python3
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[2]
d=root/'results/rtl/qwen_compute_native_glue_1014/tx_rne207_1015/native_smoke'
for name,want in json.loads((d/'ARTIFACT_HASHES.json').read_text()).items():
 assert hashlib.sha256((d/name).read_bytes()).hexdigest()==want,name
r=json.loads((d/'receipt.json').read_text())
assert hashlib.sha256((root/'rtl/qwen_sys/tx_rne_retime_20261015/qwen_tx_rne.sv').read_bytes()).hexdigest()==r['rtl_sha256']
pins=json.loads((d/'actual_pin_comparison.json').read_text())
for item,probe in zip(r['masters'],pins):
 name=item['name'];assert item['harness_exit']==0 and not item['cts'] and not item['route']
 assert probe['status']=='PASS'and not probe['missing']and not probe['extra']and not probe['mismatches']
 gate=json.loads((root/f'physical/ref_tile/{name}/gate_result.json').read_text())
 assert gate['source_binding']['archive_sha256']==item['source_archive_sha256']
 source=next(x for x in gate['source_binding']['files']if x['path']=='rtl/qwen_sys/tx_rne_retime_20261015/qwen_tx_rne.sv')
 assert source['sha256']==r['rtl_sha256']
 count=0
 for port,v in json.loads((root/f'physical/ref_tile/{name}/assigned_pins.json').read_text())['positions'].items():
  for i,xy in enumerate(v['xy_um']):
   p=port if len(v['xy_um'])==1 else f'{port}[{i}]';actual=probe['actual_pins'][p]
   assert actual['layer']==v['layer']and all(abs(x-y)<=.001 for x,y in zip(xy,actual['xy'])),p
   count+=1
 assert count==probe['actual_signal_pin_count']
print('PASS source-bound native synthesis/pin smoke: R0 106.5069um2/211FF/476pins; R1 125.6796um2/202FF/407pins; WARN retained; CTS/route/native timingOPEN')
