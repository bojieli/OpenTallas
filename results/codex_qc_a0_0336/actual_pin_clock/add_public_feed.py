"""Preserve frozen E/M4 external ck with explicit real internal feed.
Source-only candidate; external pin restoration is a separate exact-table action.
"""
import json,sys
from pathlib import Path
source,public,out=sys.argv[1:];s=json.load(open(source));t=s['core_tree'];pins=json.load(open(public));ck=next(q for q in pins['pins']if q['name']=='ck');root=next(n for n in t['nodes']if n['parent'].startswith('port:'));oldroot=root['name'];par='port:ck';new=[]
for i,pos in enumerate([[451.8,667.98],[370.8,667.98],[289.8,667.98],[228.96,650.7]]):
 n=dict(name=f'mp_public_e_feed_{i}',parent=par,master='BUFx24_ASAP7_75t_R',xy_um=pos);new.append(n);par=n['name']
root['parent']=par;t['nodes']+=new
parents={n['name']:n['parent']for n in t['nodes']};parents.update({g['inst']:g['parent']for g in t['gates']});depth={'port:ck':0}
def dep(n):
 if n not in depth:depth[n]=dep(parents[n])+1
 return depth[n]
for n in parents:dep(n)
t['nodes'].sort(key=lambda n:(dep(n['name']),n['name']));t.pop('model_qualification',None)
for l in t['leaves']:l.pop('pin_latency_ps',None)
# Compiler M5 clock_entry is an optional interior landing override; remove it
# so it cannot silently override the frozen public M4 port in a future hook.
for i in s.get('islands',[]):
 if 'clock_pin'in i:i.pop('clock_pin');i['note']='internal clock driver island only; public ck is preserved E/M4 with explicit feed'
s['clock_entry_wire']=dict(public_pin=dict(ck),source=str(Path(public).resolve()),first_buffer=new[0]['name'],internal_root=oldroot,planned_layers=['M4','M5'],entry_access_stack=['M4','M3','M2','M1'],note='all public pin centres/layers must be restored exactly; no clock-latency compensation in SDC; source-to-first-buffer passive wire modeled separately')
s['public_pins_source']=str(Path(public).resolve());Path(out).write_text(json.dumps(s,indent=1)+'\n');print(json.dumps(dict(clock_nodes=len(t['nodes']),public_ck=ck,feed_nodes=4,old_internal_root=oldroot)))
