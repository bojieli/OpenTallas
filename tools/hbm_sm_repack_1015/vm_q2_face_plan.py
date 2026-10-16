#!/usr/bin/env python3
"""Exact additive q2 face-clock source/geometry candidate; no physical adoption."""
from pathlib import Path
import json,sys,subprocess,math,hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
from spread_face_pins import port_widths
old=json.loads(subprocess.check_output(['git','show','ee83da123:physical/ref_tile/vm_native_q2_ref/spec.json'],cwd=ROOT))
s=old.copy();s.update(name='vm_native_q2_faces',top='hfd_vms_bank_native_q2_faces')
s['sources']=['rtl/hbm_accel/generic/vm/static/faces_q2/'+x for x in ['hfd_vms_bank_native_q2_faces.sv','ot_vms_bank_q2_faces_core.sv','ot_vms_bank_q2_faces_body.sv']]+['rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v']
s['clock']='multiple_cts_roots'
s['clock_data_paths']='related_same_frequency'
s['clock_relationship']={'kind':'same_pll_fixed_phase','ratio':[1,1],'phase_ps':0}
s['clock_ports']=['clk','clk_n','clk_s','clk_e','clk_w']
s['pin_regs']={'enable':False,'reason':'Actual source wrapper explicitly preserves exact recipe3 input registers; no additional automatic stage.'}
s['pins']={f:[p for p in ps if p!='clk'] for f,ps in old['pins'].items()}
clocks={'clk':('N',134.988),'clk_n':('N',137.964),'clk_s':('S',134.988),'clk_e':('E',134.988),'clk_w':('W',134.988)}
for p,(f,pos) in clocks.items():s['pins'][f].append(p)
widths=port_widths(s,ROOT);pins={};metrics=[];lines=['# Actual-layer phase .012 from current-generator ODB; new-master candidate only.']
for face,ps in s['pins'].items():
 data=[]
 for p in ps:
  if p in clocks:continue
  n,vec=widths[p];data.extend([f'{p}[{i}]' if vec else p for i in range(n)])
 cs=[x for f,x in clocks.values() if f==face]
 tracks=[round(.012+.048*k,3) for k in range(math.ceil((5.4-.012)/.048),math.floor((264.6-.012)/.048)+1) if all(abs(.012+.048*k-c)>=1.08-1e-8 for c in cs)]
 usable=259.2-2.16*len(cs);cut=len(data)*.096/usable;assert cut<=.60
 selected=[tracks[round(i*(len(tracks)-1)/(len(data)-1))] for i in range(len(data))]
 assert len(set(selected))==len(data);assert min(b-a for a,b in zip(selected,selected[1:]))>=.096-1e-7
 for p,x in zip(data,selected):pins[p]={'face':face,'layer':'M4' if face in ['W','E'] else 'M5','position_um':x,'clock':False}
 metrics.append({'face':face,'bits':len(data),'usable_um':usable,'cut':cut,'minimum_pitch_um':round(min(b-a for a,b in zip(selected,selected[1:])),6)})
for p,(f,x) in clocks.items():pins[p]={'face':f,'layer':'M4' if f in ['W','E'] else 'M5','position_um':x,'clock':True}
assert len(pins)==sum(x[0] for x in widths.values())
# Exact constructor avoids pin-place rounding and enforces actual layer grid.
lines+=['source /src/physical/common_flow/assigned_pin_exact.tcl','set vm_expected {']
for p,v in pins.items():lines.append(' {'+p+' '+v['face']+' '+v['layer']+f" {v['position_um']:.3f}"+'}')
lines+=['}','foreach vm_item $vm_expected {lassign $vm_item vm_p vm_f vm_l vm_x;ot_assigned_pin_exact $vm_p $vm_l $vm_f $vm_x}']
pf=ROOT/'physical/ref_tile_specs/smh/vm_q2_faces_pins.tcl';pf.write_text('\n'.join(lines)+'\n')
s['io_tcl']=str(pf.relative_to(ROOT));s['orfs_vars']['POST_IO_PLACEMENT_TCL']='physical/ref_tile_specs/smh/vm_q2_faces_post_iop.tcl'
s['clock_entry_domains']={}
for face in ['N','S','E','W']:
 c='clk_'+face.lower();ports=[p for p in old['pins'][face] if p not in ['clk','rst_n']];ins=[p for p in ports if p in ['rq2','rq1','rq2','rq3','rq4','wq2','wq1','dq','kq','xq','xq2','pq','bid','sid','rslot_v','rslot','wslot_v','wslot']]
 s['clock_entry_domains'][face.lower()]={'ratio':[1,1],'ports':[c],'inputs':ins,'outputs':[p for p in ports if p not in ins]}
s['clock_entry_domains']['core']={'ratio':[1,1],'ports':['clk'],'inputs':['rst_n'],'outputs':[]}
s['job'].update(tag='faces0',purpose='Additive q2 face-local clocks: existing recipe3 input state and existing response state, no new edges. Physical grant/native proof required.',views_to='physical/ref_tile/vm_native_q2_faces/views',record_to='results/rtl/ref_tile/vm_native_q2_faces')
s['job']['benches']=[{'name':'exact_real_memory','cmd':'bash rtl/hbm_accel/generic/vm/static/faces_q2/run.sh {RUN}/bench/q2_faces','expect':'pass','threads':1,'peak_ram_gb':4,'pass_regex':'Q0_FACE_CLOCKS BENCH PASS'}]
s.pop('contract',None) # No grant exists; attach actual H-DIE contract only after review.
s['structural_change']='Native q2 failed L250.8/C194.4/spread46.9 despite routed timing. New master uses four literal face-local related roots plus core/SRAM root; existing boundary stages only, return7/writeDone4 preserved. Same270square/3 actual SRAMs. No default/compiler adoption.'
p=ROOT/'physical/ref_tile/vm_native_q2_faces';p.mkdir(exist_ok=True);(p/'spec.json').write_text(json.dumps(s,indent=2)+'\n')
r={'status':'UNGRANTED_SOURCE_EXACT_CANDIDATE','top':s['top'],'source_commit':'7de433f3c','outline_um':[270,270],'clock_entries':clocks,'normal_edges_added':0,'return_edges':7,'write_done_edges':4,'windows':metrics,'pins':pins,'pinfile_sha256':hashlib.sha256(pf.read_bytes()).hexdigest()}
(ROOT/'results/physical/hsm_takeover_0825/q2_faces_pins.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='pins'},indent=2))
