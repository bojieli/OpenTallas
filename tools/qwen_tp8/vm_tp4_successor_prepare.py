#!/usr/bin/env python3
"""Freeze original TP4 group and distinct region leaf for exact functional miter.
No historical physical requirement retirement or TP8 parameter alias.
"""
import argparse,hashlib,json,pathlib,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
old='da28dc03eb72c086612503f5a30affa8995f6da2'
base=['rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv','rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv','rtl/hdc/ot_hdc_delay.sv']
macros=['physical/asap7_memory_macros/ot_sram_1r1w_'+s+'_m2_r2c2/ot_sram_1r1w_'+s+'_m2_r2c2.v' for s in ['256x256','1024x256']]
extras=['rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_region_leaf.sv','rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_answer_tiles.sv','rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_xfifo8_t.sv']
def read(commit,f):return subprocess.check_output(['git','show',commit+':'+f])
original={f:read(old,f).decode() for f in base+macros}
names=set(re.findall(r'^module\s+(\w+)', '\n'.join(original.values()), re.M));mapping={n:n+'_tp4_da28' for n in names}
pat=re.compile(r'\b('+'|'.join(sorted(names,key=len,reverse=True))+r')\b')
records={};sources=[]
for i,(f,s) in enumerate(original.items()):
 transformed=pat.sub(lambda m:mapping[m.group()],s);q=a.out/f'original_{i}.sv';q.write_text(transformed);sources.append(q.name)
 records['original:'+f]={'sha256':hashlib.sha256(s.encode()).hexdigest(),'transformed_sha256':hashlib.sha256(transformed.encode()).hexdigest(),'local':q.name}
for i,f in enumerate(base+macros+extras):
 s=read(a.candidate,f);q=a.out/f'candidate_{i}.sv';q.write_bytes(s);sources.append(q.name);records['candidate:'+f]={'sha256':hashlib.sha256(s).hexdigest(),'local':q.name}
b=read(a.candidate,'rtl/qwen_sys/vm_plane_20261013/tb_qfd_vm_region_leaf.sv').decode()
b=b.replace('tb_qfd_vm_region_leaf','tb_qfd_vm_tp4_successor').replace('ot_qfd_vm_region_quarter','ot_qfd_vm_grp_tp4_da28').replace('.USE_MACRO(0)','.USE_MACRO(1)')
q=a.out/'bench.sv';q.write_text(b);sources.append(q.name)
manifest={'original_commit':old,'candidate_commit':a.candidate,'params':{'NBK':8,'NSB':2,'NSU':3,'DEPTH':174,'LAW':8,'DEPTHS':695,'LAWS':10,'USE_MACRO':1,'NPP':7,'MEREG':1,'NRI':2,'NRX':2,'NRS':1},'scope':'exact TP4 group vs parameter-bound region leaf; functional macro models, no hard view or TP8 field alias','source_records':records,'renamed_original_modules':mapping,'bench_sha256':hashlib.sha256(b.encode()).hexdigest()}
(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(a.out/'sources.txt').write_text('\n'.join(sources)+'\n')
