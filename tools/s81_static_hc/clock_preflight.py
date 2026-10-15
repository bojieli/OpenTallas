#!/usr/bin/env python3
"""Measure flop counts in actual scalar leaves; this is not physical CTS."""
import collections,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
paths=['rtl/hdc/ot_hdc_prefix.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_fp32_add_rne_preexp.sv',
 'rtl/dsrom_sys/s81_static_hc/s81_static_hc_reduce.sv','rtl/dsrom_sys/s81_static_hc/s81_static_hc_assemble.sv']
result={'scope':'actual source flop partition; physical roots, slots, pin timing and CTS remain unqualified',
 'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'leaves':{}}
with tempfile.TemporaryDirectory(prefix='s81hc-clock-') as tmp:
 for top in ['s81_static_hc_scalar_reduce','s81_static_hc_scalar_assemble']:
  out=pathlib.Path(tmp)/f'{top}.json'
  script=f"read_verilog -sv {' '.join(paths)}; hierarchy -top {top}; proc; flatten; opt; write_json {out}"
  subprocess.run(['yosys','-Q','-T','-p',script],cwd=ROOT,capture_output=True,text=True,check=True)
  m=json.loads(out.read_text())['modules'][top];c=collections.Counter()
  for cell in m['cells'].values():
   if 'dff' in cell['type'].lower():c[cell['type']]+=len(cell['connections']['Q'])
  result['leaves'][top]={'clocked_bits_by_cell_type':dict(c),'clocked_bits_total':sum(c.values())}
result['clocked_bits_per_lane_root']=sum(x['clocked_bits_total'] for x in result['leaves'].values())
result['lane_roots']=16;result['additional_metadata_control_roots']=1
result['clocked_payload_bits_all_16_lanes']=16*result['clocked_bits_per_lane_root']
result['common_epoch_required']=True
result['qualification']='SOURCE_ONLY: single-clock compatibility wrapper does not qualify a whole-tile clock root'
p=ROOT/'results/rtl/s81_static_hc_1014/clock_preflight.json';p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
