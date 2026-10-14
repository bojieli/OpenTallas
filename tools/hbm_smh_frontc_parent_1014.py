#!/usr/bin/env python3
"""Literal source-pinned front-C parent with real child entry clocks/resets."""
import re,json,hashlib,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/arch/hbm_native_1013/frontc_parent_1014';OUT.mkdir(parents=True,exist_ok=True)
SOURCE='49b00f711';RTL='rtl/hbm_accel/sm/ot_hbm_accel_smh.sv'
def sha(b):return hashlib.sha256(b).hexdigest()
def pinned(p):return subprocess.check_output(['git','show',SOURCE+':'+p],cwd=ROOT)
def clean(s):return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
def header(b):
 b=clean(b);d=0
 for i,c in enumerate(b):
  if c=='(':d+=1
  elif c==')':d-=1
  elif c==';' and d==0:return b[:i+1]
 raise ValueError('header missing')
src=pinned(RTL).decode();bodies={m.group(1):m.group(0) for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',src,re.S)}
top='ot_hbm_accel_smh_front_c';new='ot_smh_frontc_native_parent'
body=bodies[top]
names=['u_bc','u_is','u_xl','u_tw','u_te','u_rw','u_re','u_bw','u_be']
masters={n:'ot_hbm_accel_smh_fc_'+k for n,k in zip(names,['bc','is','xl','t','t','xr','xr','b','b'])}
ports='\n'.join('    input wire raw_'+n+', rst_'+n+',' for n in names)
candidate=body.replace('module '+top+' #(','module '+new+' #(',1)
candidate=re.sub(r'    input\s+wire\s+clk,\s*\n    input\s+wire\s+rst_n,',ports,candidate,count=1)
for n in names:
 p=re.compile(r'('+n+r'\s*\()\.clk\(clk\), \.rst_a\(rst_n\)')
 candidate,nsub=p.subn(r'\1.clk(raw_'+n+'), .rst_a(rst_'+n+')',candidate)
 assert nsub==1,(n,nsub)
pre='`define OT_SMH_FC_HIER\n`define SYNTHESIS\n'
(OUT/'frontc_parent.sv').write_text(pre+candidate+'\n')
(OUT/'source_literal.sv').write_text(src)
(OUT/'frontc_gold.sv').write_text(pre+body+'\n')
(OUT/'frontc_blackboxes.sv').write_text('\n'.join('(* blackbox *) '+header(bodies[m])+'\nendmodule' for m in sorted(set(masters.values())))+'\n')
ys='read_verilog -sv '+str((OUT/'frontc_parent.sv').relative_to(ROOT))+' '+str((OUT/'frontc_blackboxes.sv').relative_to(ROOT))+'\nhierarchy -check -top '+new+'\nproc\nflatten\ncheck\nwrite_json '+str((OUT/'census.json').relative_to(ROOT))+'\n'
(OUT/'census.ys').write_text(ys)
# Actual published views, including the native PG LEF for fc_is. Renaming the file does not alter content.
pubpath=ROOT/'results/arch/hbm_native_1013/sm/publication_evidence.json';pub=json.loads(pubpath.read_text())
view_records={}
for m in sorted(set(masters.values())):
 e=pub[m];d=OUT/'views'/m;d.mkdir(parents=True,exist_ok=True)
 original=ROOT/e['view_lef'];b=original.read_bytes();(d/(m+'.lef')).write_bytes(b)
 hashes={'lef':sha(b)}
 for c,p in e['view_lib'].items():
  b=(ROOT/p).read_bytes();(d/(m+'_'+c+'.lib')).write_bytes(b);hashes[c]=sha(b)
 for f in ['insertion.json','abstract.json','child_lint.json']:
  p=original.parent/f
  if p.exists():shutil.copyfile(p,d/f);hashes[f]=sha(p.read_bytes())
 pg=[]
 for pin in re.findall(r'PIN\s+(?:VDD|VSS)\b(.*?)END\s+(?:VDD|VSS)',original.read_text(),re.S):pg+=re.findall(r'LAYER\s+(M\d+)',pin)
 view_records[m]={**e,'bound_view_dir':str(d.relative_to(ROOT)),'hashes':hashes,'actual_pg_top':max(pg,key=lambda x:int(x[1:]))}
record=dict(schema='opentallas.native_frontc_parent.v1',source_commit=SOURCE,source_file=RTL,source_sha256=sha(src.encode()),source_define=['OT_SMH_FC_HIER','SYNTHESIS'],top=new,original_top=top,parameters='Exact literal parent defaults and SYNTHESIS child-call defaults retained; no guessed override',children=[dict(instance=n,master=masters[n],clock_port='raw_'+n,reset_port='rst_'+n,original_clock_source='clk',original_reset_source='rst_n',reset_active='low',parameters='literal SYNTHESIS call: no overrides',view=view_records[masters[n]]) for n in names],own_state_status='CENSUS_PENDING',semantic_contract='All nine RAW clock/reset entries connect to original parent clk/rst_n in logical composition. Native delivery needs actual childR compensation, source/epoch/hold/recovery proof; no dummy root.',geometry_status='REQUEST_PENDING_DIE_OWNER; actual dimensions only, no obsolete master or placement adoption')
(OUT/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
(OUT/'census_run.sh').write_text('#!/bin/bash\nset -euo pipefail\ncd "$(dirname "$0")/../../../.."\nyosys -Q -s results/arch/hbm_native_1013/frontc_parent_1014/census.ys\n')
print('Generated literal frontC candidate and nine actual CLOSED view bindings')
