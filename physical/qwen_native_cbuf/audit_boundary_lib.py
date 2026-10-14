#!/usr/bin/env python3
"""Exact first Liberty loadpoint boundary costs; no clock-extrema folding."""
import re,json,hashlib,argparse
from pathlib import Path

def groups(text,kind):
 pat=re.compile(r'\b'+re.escape(kind)+r'\s*\(([^)]*)\)\s*\{')
 for m in pat.finditer(text):
  start=m.end();n=1;i=start
  while n and i<len(text):
   if text[i]=='{':n+=1
   elif text[i]=='}':n-=1
   i+=1
  yield m.group(1).strip().strip('"'),text[start:i-1]

def attr(body,key):
 m=re.search(r'\b'+key+r'\s*:\s*([^;]+);',body);return m.group(1).strip().strip('"') if m else None

def table(body,key):
 for name,b in groups(body,key):
  v=re.search(r'values\s*\(\s*"([^"]+)"',b)
  idx=re.search(r'index_1\s*\(\s*"([^"]+)"',b)
  if v:return {'template':name,'first':float(v.group(1).split(',')[0]),'loadpoint':float(idx.group(1).split(',')[0]) if idx else None}
 return None

ap=argparse.ArgumentParser();ap.add_argument('view');ap.add_argument('out');a=ap.parse_args();v=Path(a.view)
ins=json.load(open(v/'insertion.json'));cell=v.name
out={'schema':'ot.qwen.boundary.liberty.firstload.v1','cell':cell,'selected_routed_clock_ref':'corner boundary mean from insertion.json; deliver phi-R, not rawclocktreeglobalmean','definition':{'O_minus_R':'max rising_edge cell_rise/cell_fall atfirst outputloadpoint minuscornerR','S_plus_R':'max setup_rising rise_constraint/fall_constraint pluscornerR','clock_extrema_addends':'separate packet maxima: launch(max-R), capture(R-min). NOT folded intoeach intrinsiccost.','reset':'includedactualexported setup/hold arcs, noasync exemption invented.','Sdc_metrics':'tt_out andtt_i2r are positiveWNSslacks, not interfacecosts.'},'launch_budget_ps':220,'capture_budget_ps':190,'corners':{},'source_sha256':{}}
for corner in ['tt','ff','ss']:
 f=v/(cell+'_'+corner+'.lib');t=f.read_text();assert attr(t,'time_unit')=='1ps'
 R=ins[corner]['boundary']['mean'];p={};bad=[]
 for name,b in groups(t,'pin'):
  direction=attr(b,'direction');arcs=[]
  for _,tb in groups(b,'timing'):
   typ=attr(tb,'timing_type');rp=attr(tb,'related_pin');rec={'timing_type':typ,'related_pin':rp}
   for k in ['cell_rise','cell_fall','rise_constraint','fall_constraint']:
    q=table(tb,k)
    if q:rec[k]=q
   if len(rec)>2:arcs.append(rec)
  if not arcs:continue
  q={'direction':direction,'arcs':arcs}
  if direction=='output':
   vals=[z[k]['first'] for z in arcs if z['timing_type']=='rising_edge' for k in ['cell_rise','cell_fall'] if k in z]
   if vals:q['O_minus_R_ps']=round(max(vals)-R,5);q['launch_margin_ps']=round(220-q['O_minus_R_ps'],5)
  if direction=='input':
   vals=[z[k]['first'] for z in arcs if z['timing_type']=='setup_rising' for k in ['rise_constraint','fall_constraint'] if k in z]
   if vals:q['S_plus_R_ps']=round(max(vals)+R,5);q['capture_margin_ps']=round(190-q['S_plus_R_ps'],5)
  if any(q.get(k,0)<0 for k in ['launch_margin_ps','capture_margin_ps']):bad.append(name)
  p[name]=q
 outputs=[(n,q['O_minus_R_ps']) for n,q in p.items() if 'O_minus_R_ps' in q];inputs=[(n,q['S_plus_R_ps']) for n,q in p.items() if 'S_plus_R_ps' in q]
 out['corners'][corner]={'R_ps':R,'boundary':ins[corner]['boundary'],'clock_extrema_packet_ps':{'launch':round(ins[corner]['boundary']['max']-R,5),'capture':round(R-ins[corner]['boundary']['min'],5)},'first_loadpoint_fF':1.44,'pins':p,'over_budget_pins':bad,'worst_launch':max(outputs,key=lambda x:x[1]),'worst_capture':max(inputs,key=lambda x:x[1])}
 out['source_sha256'][str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
 print(corner,'R',R,'launch',out['corners'][corner]['worst_launch'],'capture',out['corners'][corner]['worst_capture'],'bad',len(bad))
Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
