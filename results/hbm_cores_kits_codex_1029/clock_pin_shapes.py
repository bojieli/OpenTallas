#!/usr/bin/env python3
"""Opt-in C25c GEOM-21 repair. New pin tables, same RTL/body/cycles."""
import copy, hashlib, json, os, re, shutil, sys
from pathlib import Path
base,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
d=json.load(open(base/'die_plan.json')); shapes={};changed={};rows=[]
entries=json.load(open(base/'clock_entries.json')); roots={}
for tn,t in d['partition_types'].items():
 for c in t.get('hard_cores',[]):
  e=entries.get(tn,{}).get(c['inst'],{})
  if e.get('xy_um'):
   for n in ([e['port']] if e.get('port') else list(e.get('merged_clock_ports') or [])[:1]):roots[(c.get('pins_file'),n)]=e['xy_um']
ck=re.compile(r'^(clk|clk_\w+|\w+_clk|ck|ck_\w+|\w*clk_\w+)(\[\d+\])?$')
for t in d['partition_types'].values():
 for c in t.get('hard_cores',[]):
  f=c.get('pins_file')
  if f and f not in shapes:shapes[f]=tuple(c['outline_um'])
for f,(W,H) in shapes.items():
 pins=json.load(open(base/f)); moves=[]
 if not isinstance(pins,list):continue
 for p in pins:
  if not ck.fullmatch(p.get('name','')):continue
  if (f,p['name']) in roots:continue  # declared slice entries already get full M5 geometry
  if p.get('layer')=='M5' and p.get('w',0)>=.048 and p.get('h',0)>=.48 and min(p['x'],W-p['x'])>=min(p['y'],H-p['y']):continue
  # All clock pins need full vertical-M5 access; master-slice consumes declared
  # centre entries after gen, while unmerged secondary pins keep NS-face access.
  old=copy.deepcopy(p)
  p['layer']='M5';p['w']=.048;p['h']=.48
  x=min(max(p['x'],1.008),W-1.008)
  p['x']=round(.024+round((x-.024)/.048)*.048,4)
  p['y']=.24 if p['y']<H/2 else round(H-.24,4)
  root=roots.get((f,p['name']))
  if root:
   p['x']=round(.024+round((root[0]-.024)/.048)*.048,4);p['y']=root[1]
  # Pin overlaps judged with actual 0.048x0.48 shapes on the same layer.
  step=.096 if p['x']<W/2 else -.096
  while any(q is not p and q.get('layer')=='M5' and abs(q['x']-p['x'])<.096-1e-6 and abs(q['y']-p['y'])<.552-1e-6 for q in pins):
   p['x']=round(p['x']+step,4)
  if p!=old:moves.append({'pin':p['name'],'old':old,'new':copy.deepcopy(p)})
 if moves:
  nf=f[:-5]+'__codex_g21.json';changed[f]=nf;rows.append({'old_file':f,'new_file':nf,'pins':moves})
  dst=out/nf;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(pins,indent=1))
for t in d['partition_types'].values():
 for c in t.get('hard_cores',[]):
  if c.get('pins_file') in changed:c['pins_file']=changed[c['pins_file']]
for f in base.rglob('*'):
 r=f.relative_to(base);p=out/r
 if p.exists() or r==Path('die_plan.json'):continue
 if f.is_dir():p.mkdir(parents=True,exist_ok=True)
 elif f.is_file():
  p.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(f,p)
  except OSError:shutil.copy2(f,p)
d['die']['label']='C25c clock-pin access shape repair | '+d['die']['label']
(out/'die_plan.json').write_text(json.dumps(d,indent=1))
report={'schema':'opentallas.codex.hbm.clock_pin_shapes.v1','base_sha256':hashlib.sha256((base/'die_plan.json').read_bytes()).hexdigest(),'tables':len(rows),'pins':sum(len(x['pins']) for x in rows),'body_moves':0,'added_cycles':0,'changes':rows}
(out/'clock_pin_shapes_report.json').write_text(json.dumps(report,indent=1))
print('tables',report['tables'],'pins',report['pins'],'body_moves 0 added_cycles 0')
