#!/usr/bin/env python3
"""Remote-admitted one-link TT mapped inventory; no place/route or headline fit."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path.cwd()
OUT=ROOT/'map_r1';OUT.mkdir(exist_ok=False)
libs=sorted((Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM').glob('*_RVT_TT_*.lib'))
if len(libs)!=5:raise RuntimeError('Expected five real TT RVT groups')
combined=OUT/'combined.lib'
combined.write_text('library (hub_sram_inventory_tt) {\n'+'\n'.join(p.read_text().split('{',1)[1].rsplit('}',1)[0] for p in libs)+'\n}\n')
sources=['rtl/lib/ot_reset_sync.sv','rtl/lib/ot_async_fifo.sv',
 'rtl/qwen_sys/emb_hbm_20261008/ot_qfd_hub_sram_ingress.sv',
 'rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_cdc_ch_sram.sv',
 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v']
record={'scope':'TT one full128x523 ingress plus unchanged AD8 async and OD8 output. Standard-cell area only; macros separate. Identical ABC/liberty settings for baseline and candidate. No CTS/wires/physical closure or KVdiefit.',
 'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in sources},
 'libraries':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in libs},'cases':{}}
for enabled in [0,1]:
 name=f'sram{enabled}';case=OUT/name;case.mkdir()
 ys=case/'synth.ys'
 ys.write_text('\n'.join([
  'read_verilog -sv -D SYNTHESIS '+' '.join(sources),
  f'hierarchy -check -top ot_qwen_die_cdc_ch_sram -chparam SRAM {enabled} -chparam W 523 -chparam IBUF 128 -chparam OCRED 8 -chparam AD 8',
  'synth -top ot_qwen_die_cdc_ch_sram -flatten',
  f'dfflibmap -liberty {combined}',f'abc -liberty {combined}',
  'clean',f'stat -liberty {combined}',f'write_json {case}/mapped.json',
  f'write_verilog -noattr {case}/mapped.v'])+'\n')
 with(case/'synth.log').open('w')as f:
  cp=subprocess.run(['/usr/bin/time','-v',str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(ys)],stdout=f,stderr=subprocess.STDOUT)
 text=(case/'synth.log').read_text()
 area=re.findall(r"Chip area for module '\\?ot_qwen_die_cdc_ch_sram':\s*([\d.]+)",text)
 mapped=json.loads((case/'mapped.json').read_text())if cp.returncode==0 else{}
 cells=mapped.get('modules',{}).get('ot_qwen_die_cdc_ch_sram',{}).get('cells',{})
 counts={}
 for c in cells.values():counts[c['type']]=counts.get(c['type'],0)+1
 record['cases'][name]={'returncode':cp.returncode,'mapped_stdcell_um2':float(area[-1])if area else None,
  'cell_inventory':counts,'memories':len(mapped.get('modules',{}).get('ot_qwen_die_cdc_ch_sram',{}).get('memories',{})),
  'peak_RSS_kB':re.findall(r'Maximum resident set size \(kbytes\):\s*(\d+)',text),
  'log_sha256':hashlib.sha256(text.encode()).hexdigest()}
 (OUT/'record.json').write_text(json.dumps(record,indent=2)+'\n')
 if cp.returncode:raise SystemExit(cp.returncode)
base=record['cases']['sram0']['mapped_stdcell_um2'];candidate=record['cases']['sram1']['mapped_stdcell_um2']
if base is not None and candidate is not None:
 saving=(base-candidate)*4
 record['composed_four_link_stdcell_saving_um2']=saving
 record['original_72p5k_component_savings_gate']='PASS'if saving>=72525.907936 else'FAIL'
 record['macro_count_per_link']=record['cases']['sram1']['cell_inventory'].get('ot_sram_1r1w_128x256_m1_r2c2',0)
 (OUT/'record.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
