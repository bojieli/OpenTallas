#!/usr/bin/env python3
"""Rebuild only actual soft OBS + macro PG pin metal for the type-union holes.
Retain every native signal pin verbatim, including the added START/reset pins.
"""
import argparse,json,re,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--windows',required=True);p.add_argument('--kit',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools);import die_trial as D,schema as S
P=S.Plan(S.load(a.plan),Path(a.plan));win=json.load(open(a.windows))['windows'];mods=D.standin_module_names(P);out=Path(a.out);out.mkdir(parents=True,exist_ok=True);records=[]
obs=re.compile(r'^  OBS\n.*?^  END\n',re.M|re.S)
for tn in sorted(P.types):
 mod=mods[tn];old=(Path(a.kit)/'abstracts'/(mod+'.lef')).read_text();fresh,stats=D.abstract_lef(P,tn,islands=win.get(tn),module_name=mod);mo=obs.search(old);mn=obs.search(fresh);assert mo and mn,tn;new=old[:mo.start()]+mn.group()+old[mo.end():]
 for net in ['VDD','VSS']:
  pat=re.compile(r'^  PIN '+net+r'\n.*?^  END '+net+r'\n',re.M|re.S);mm=pat.search(fresh);assert mm,tn;new,n=pat.subn(lambda _:mm.group(),new);assert n==1,(tn,net,n)
 # Remaining logical/signal pin text must be identical, not regenerated.
 def signal_text(s):
  s=obs.sub('',s)
  for net in ['VDD','VSS']:s=re.sub(r'^  PIN '+net+r'\n.*?^  END '+net+r'\n','',s,flags=re.M|re.S)
  return s
 assert signal_text(new)==signal_text(old),tn;(out/(mod+'.lef')).write_text(new);records.append(dict(type=tn,module=mod,windows=len(win.get(tn,[]))))
(out/'manifest.json').write_text(json.dumps(dict(types=len(records),signal_pins_preserved=True,records=records),indent=1)+'\n');print('REBUILT_NATIVE_ABSTRACTS',len(records))
