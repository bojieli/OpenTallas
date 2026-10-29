# DIE-QC-24 (copy of DIE-QC-21 overlay21, copy of DIE-QC-20 overlay20): apply clock_body_bays base sites (no pads) to trial13 tree.json + ctree.tcl (as Codex overlay_body5.py)
import json,re,shutil,hashlib,sys
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude/die-qc24-1028")
p=Q/'trial24/clock/tree.json';T=json.load(open(p))
B=json.load(open(Q/'bays24/base_body_sites.json'))['sites']
assert set(B)==set(T['sites']),(len(B),len(T['sites']))
shutil.copyfile(p,p.with_name('tree_GENERATED.json'))
ct=p.with_name('ctree.tcl');shutil.copyfile(ct,ct.with_name('ctree_GENERATED.tcl'))
for n,xy in B.items():T['sites'][n]=xy
for i,n in T['node_buf'].items():
  if n in B: T['nodes'][str(i)]['x'],T['nodes'][str(i)]['y']=B[n]
T['meta']['body_overlay']=dict(source='tools/die_plan/clock_body_bays.py (main 4d4c968ee0)',report=json.load(open(Q/'bays24/bay_report.json')),scope='Prebuild frozen row/body layout; no route or timing result',explicit_pad_sites_matched=0)
s=ct.read_text();found=set()
pat=re.compile(r'^(place_inst -name (\S+) -location \{)[^}]+(\} -status[^\n]*)$',re.M)
def sub(m):
  n=m[2]
  if n not in T['sites']:return m[0]
  found.add(n);x,y=T['sites'][n];return m[1]+f'{x:.6f} {y:.6f}'+m[3]
s=pat.sub(sub,s)
assert found==set(T['sites']),(len(found),len(T['sites']))
ct.write_text(s);p.write_text(json.dumps(T,indent=1)+'\n')
rep=dict(clock_cells=len(found),base_cells=len(B),explicit_pads=0,tree_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ctree_tcl_sha256=hashlib.sha256(ct.read_bytes()).hexdigest())
(Q/'trial24/body_overlay.json').write_text(json.dumps(rep,indent=2)+'\n');print(rep)
