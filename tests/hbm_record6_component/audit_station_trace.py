#!/usr/bin/env python3
"""Adjudicate station supporting logs without upgrading native binding scope."""
import argparse,json,re
from pathlib import Path

NEGATIVE={1:['ADD_INPUT_ID'],2:['ADD_INPUT_ID','GLOBAL_FRAGMENT_CONSUMER_ID'],3:['ADD_INPUT_ID'],4:['EARLY_CAPTURE'],5:['FRAGMENT_OWNERSHIP','GLOBAL_FRAGMENT_CONSUMER_ID'],6:['UNAVAILABLE_FEEDBACK']}

def audit(path,mut):
 text=path.read_text();failures=re.findall(r'Assertion failed[^\n]*|%Error[^\n]*',text)
 if mut:
  matches=[p for p in NEGATIVE[mut]if p in text]
  return dict(verdict='SUPPORT_CAUSAL_FAIL'if matches and 'STATION_CAUSAL_SUPPORT_PASS'not in text else'UNQUALIFIED_NEGATIVE',station_mut=mut,witnesses=matches,failures=failures,native_capture_binding='PENDING')
 def kv(line):return dict(re.findall(r'([A-Za-z_]+)=([^ ]+)',line))
 ins={};outs={};pin={};held={};dupes=[];roots=[]
 for line in text.splitlines():
  if line.startswith('SUPPORT_ROOT '):roots.append(kv(line));continue
  target=None
  if line.startswith('ADD_IN '):target=ins
  elif line.startswith('ADD_OUT '):target=outs
  elif line.startswith('SUPPORT_INPUT '):target=pin
  elif line.startswith('SUPPORT_HELD '):target=held
  if target is None:continue
  f=kv(line)
  key=(int(f['episode']),int(f['id']))if target is ins or target is outs else(int(f['episode']),int(f['group']),int(f['q']),int(f['lane']))
  if key in target:dupes.append(key)
  target[key]=f
 wantadd={(e,i)for e in range(2)for i in range(1281)}
 wantwords={(e,g,q,l)for e in range(2)for g in range(4)for q in range(4)for l in range(128 if q in(0,2)else 32)}
 mismatches=[]
 for key in pin.keys()&held.keys():
  if pin[key]['data'].lower()!=held[key]['value'].lower()or held[key]['valid']!='1':mismatches.append(key)
 ok=('STATION_CAUSAL_SUPPORT_PASS' in text and 'CLOCK_CAUSAL_PASS'in text and not failures and not dupes and set(ins)==wantadd and set(outs)==wantadd and set(pin)==wantwords and set(held)==wantwords and not mismatches and len(roots)==2)
 return dict(verdict='STATION_SUPPORT_PASS'if ok else'FAIL_OR_INCOMPLETE',native_capture_binding='PENDING',scope='41-node station support only; no full native/token/timing/physical claim',add_inputs=len(ins),add_outputs=len(outs),source_pin_words=len(pin),actual_held_words=len(held),pin_held_mismatches=mismatches,duplicates=dupes,roots=roots,failures=failures)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--mut',type=int,default=0);p.add_argument('--output',type=Path);a=p.parse_args();r=audit(a.log,a.mut);s=json.dumps(r,indent=2)+'\n';print(s,end='')
 if a.output:a.output.write_text(s)
 raise SystemExit(0 if r['verdict']in('STATION_SUPPORT_PASS','SUPPORT_CAUSAL_FAIL')else 1)
