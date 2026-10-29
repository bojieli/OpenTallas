"""Freeze the actual bind3 source cohort, then apply approved coherent profile."""
import json,shutil,hashlib,subprocess
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-qc-profile-fold-1029')
GOLD=Path('/srv/opentallas-scratch2/claude/wt/tok-qc-1-1028')
CFGBASE=Path('/srv/opentallas-scratch2/claude/wt/codex-qwen-token-1028')
CFG=CFGBASE/'physical/die_plan/qwen_compute/bind/asbuilt_tokqc4_ca.json'
SRC=R/'source';SRC.mkdir(exist_ok=True);inputs=R/'inputs';inputs.mkdir(exist_ok=True)
a=json.load(open(CFG));src_record=json.load(open(CFGBASE.parent.parent/'codex-qwen-token-1028/qc_bind3/asbuilt_sources.json'))
for rel in ['rtl','physical/asap7_memory_macros_v2','physical/asap7_memory_macros']:
 dest=SRC/rel
 if dest.exists():raise ValueError('immutable source snapshot already exists '+str(dest))
 dest.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(['cp','-a','--reflink=auto',str(GOLD/rel),str(dest)],check=True)
for rel in a.get('netlist',[])+a.get('files',[]):
 dest=SRC/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 origin=GOLD/rel
 if not origin.is_file():origin=CFGBASE/rel
 shutil.copy2(origin,dest)
# Tables and map use the actual current bind manifest, not an older source tree.
map_src=CFG.parent/a['map_file'];map_dst=inputs/map_src.name;shutil.copy2(map_src,map_dst);a['map_file']=str(map_dst)
for key in ['land_r8','clock_landing_table']:
 origin=CFGBASE/a[key];dest=SRC/a[key];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin,dest)
for rel in a.get('land_r8_extra',[]):
 dest=SRC/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(CFGBASE/rel,dest)
if a.get('rewires',{}).get('file'):
 rel=a['rewires']['file'];dest=SRC/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(CFGBASE/rel,dest)
rel=a['param_regen']['file'];dest=SRC/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'coll_regen_current.py',dest)
a['base']=str(SRC);a.setdefault('defines',[]).append('OT_S8_CROM_ALIGN')
assert len(a['defines'])==len(set(a['defines']))
a.update(json.load(open(R/'candidate_profile.json')))
inner=json.load(open(R/'candidate_inner.json'));candidate_path=SRC/'profile/head_witness_inner.json';candidate_path.parent.mkdir(exist_ok=True)
candidate_path.write_text(json.dumps(inner,indent=1));a.setdefault('land_r8_extra',[]).append(str(candidate_path))
a['note'] += ' | CODEX ONE-QC candidate: restore documented d58 CROM_ALIGNMENT3, coherent HEAD/ROPE/L1 + aligned witness8/TXDP18; no cached param0 qualification.'
(R/'asbuilt_profile3.json').write_text(json.dumps(a,indent=1))
# Pin only the actually selected old RTL cohort; no exhaustive repository census.
selected=[]
for f in src_record['full']+src_record['lib']:
 origin=Path(f)
 if origin.is_relative_to(GOLD):
  dst=SRC/origin.relative_to(GOLD);assert dst.read_bytes()==origin.read_bytes()
  selected.append(dict(path=str(dst),sha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
(R/'source_cohort.json').write_text(json.dumps(dict(source='actual qc_bind3 selected cohort; original param0 retained as history',selected=selected,define='OT_S8_CROM_ALIGN',profile='HEAD_CONTEXT=ROPE=L_CONTEXTS=1; witness4->8; TXDP derived18'),indent=1))
print('PREPARED',len(selected),'selected source files; explicit CROM3 + HEAD profile + witness8',flush=True)
