#!/usr/bin/env python3
"""Package real retained views and fixed-shape H17 declarations; never synthesize timing."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
RESULT=ROOT/'results/physical/hbm_die_abstracts_20261006/memory_control'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def package(src,name,signoff):
 dst=OUT/name;dst.mkdir(exist_ok=True)
 paths=[src/f'{name}.lef',src/f'{name}_ss.lib',src/f'{name}_ff.lib']
 hashes={p.name:sha(p) for p in paths}
 abstract=json.loads((src/'abstract.json').read_text())
 assert abstract['ok'] and hashes==abstract['files'], 'Retained export hash mismatch'
 lef=paths[0].read_text();size=[float(v) for v in re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups()]
 pins=[]
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',lef,re.M|re.S):
  body=m[2];rect=[]
  for r in re.finditer(r'LAYER\s+(\S+)\s*;\s*RECT\s+([^;]+);',body):
   rect.append({'layer':r[1],'rect_um':[float(v) for v in r[2].split()]})
  pins.append({'name':m[1],'direction':re.search(r'DIRECTION\s+(\S+)',body)[1],'geometry':rect})
 pinset={p['name'] for p in pins};clocks={};arcs={}
 for corner,p in zip(('ss','ff'),paths[1:]):
  text=p.read_text();libpins=set(re.findall(r'\bpin\s*\(\s*"?([^"\s)]+)"?\s*\)',text))
  assert libpins==pinset, (corner,'LEF/LIB ABI mismatch',len(libpins),len(pinset))
  assert re.search(r'cell\s*\(\s*"?'+name,text)
  clocks[corner]=re.findall(r'pin\s*\("?([^"\s)]+)"?\)\s*\{[^{}]*clock\s*:\s*true',text)
  assert clocks[corner]==['clk']
  arcs[corner]={'rising_edge_count':len(re.findall(r'timing_type\s*:\s*rising_edge',text)),
   'setup_rising_count':len(re.findall(r'timing_type\s*:\s*setup_rising',text)),
   'hold_rising_count':len(re.findall(r'timing_type\s*:\s*hold_rising',text))}
  assert arcs[corner]['rising_edge_count']>0, 'Missing real output clock arcs'
 for p in paths:shutil.copyfile(p,dst/p.name)
 for f in ('abstract.json','interface.sdc','export_ss.tcl','export_ff.tcl','export_ss.log','export_ff.log'):
  if (src/f).exists():shutil.copyfile(src/f,dst/f)
 write(dst/'pins.json',{'macro':name,'size_um':size,'pins':pins,'clock_pins':clocks,'timing_arcs':arcs})
 write(dst/'clock_contract.json',{'macro':name,'leaf_signoff':signoff,'clock_pins':clocks,
  'period_ps':833,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,
  'parent_closed':False,'parent_clock_credit':False,'interface_sdc_sha256':sha(dst/'interface.sdc'),
  'retained_leaf_io_exceptions_do_not_qualify_parent':True})
 return {'macro':name,'path':str(dst.relative_to(ROOT)),'files':hashes,'signal_and_power_pins':len(pins),
  'size_um':size,'leaf_closed':True,'parent_closed':False,'timing_arcs':arcs}
def compatibility():
 dst=OUT/'sm_compat';dst.mkdir(exist_ok=True);rec=[]
 for name,params in [('ot_hbm_accel_bd_col',{'LB':2,'IL':8,'TAGW':16}),('ot_hbm_accel_tc16',{'IL':8,'TAGW':16})]:
  src=ROOT/'physical/hbm_accel_sm_views'/name/f'{name}_bb.v';text=src.read_text()
  header='module '+name+' #(\n'+',\n'.join(f'    parameter integer {k} = {v}' for k,v in params.items())+'\n) ('
  text=text.replace('module '+name+' (',header)
  # Port widths deliberately remain the actual fixed macro ABI.
  conditions=' || '.join(f'{k} != {v}' for k,v in params.items())
  text=text.replace('endmodule',f'`ifndef SYNTHESIS\ninitial if ({conditions}) $fatal(1, "unsupported fixed hardened macro shape");\n`endif\nendmodule')
  target=dst/src.name;target.write_text(text)
  rec.append({'macro':name,'supported_parameters':params,'original_declaration':str(src.relative_to(ROOT)),
   'original_sha256':sha(src),'compat_sha256':sha(target),'replacement_only':True,
   'port_widths_fixed':True,'parent_closed':False})
 write(dst/'supported_shapes.json',{'records':rec,'unsupported_shapes':'reject before synthesis; never use fixed macro timing for another shape'})
 return rec
def main():
 RESULT.mkdir(parents=True,exist_ok=True)
 original=ROOT/'physical/hbm_fmax_attn/ot_attn_hgrp_m6h1/retained_export.json'
 signoff=json.loads(original.read_text())
 attention=package(ROOT/'physical/hbm_fmax_attn_context/ot_attn_hgrp_m6h1','ot_attn_hgrp_m6h1',signoff)
 comp=compatibility()
 write(RESULT/'prepared_views.json',{'schema':'opentallas.hbm.memory-control-real-views.v1',
  'attention':attention,'sm_compat':comp,'retained_signoff_sha256':sha(original),
  'jobs_rebuilt':0,'passing_gates_repeated':0,'whole_sm_closed':False,'attention_tile_parent_closed':False})
 print(json.dumps({'attention':attention,'compatibility_macros':len(comp)}))
if __name__=='__main__':main()
