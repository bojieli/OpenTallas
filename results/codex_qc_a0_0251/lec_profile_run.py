#!/usr/bin/env python3
"""Candidate-native proof using untrusted existing correspondences, all re-proved.
No source or comparison masking; avoids costly unrestricted correspondence discovery.
Usage inside pinned ORFS image: python3 lec_profile_run.py KIT PROFILE OUT
"""
import collections,json,sys
from pathlib import Path
kit,profile,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(kit));import lec
proposals=json.loads(profile.read_text())
def current_correspond(L,work,conflicts,log,**kw):
 lec.normalize_gold_elements(L,lec.slang_elements(work/'gold.aliases.json'),log)
 for fn in (lec.json_alias_keys,lec.slang_element_keys,lec.alias_arrays):fn(L,log,work=work)
 for fn in (lec.relayout,lec.renamed,lec.replica_proposals,lec.merged_proposals,lec.register_alias_proposals,lec.fsm_proposals):fn(L,log)
 L.hyp.clear();skipped=[]
 for side,key,h in proposals:
  valid=(key in L.gp and key in L.tp) if side=='both' else key in (L.gp if side=='gold' else L.tp)
  if h[0]=='eq':valid=valid and h[2] in (L.gp if h[1]=='gold' else L.tp)
  if h[0]=='loaded':valid=valid and all(k in L.gp or k in L.tp for cube in h[2] for k,v in cube)
  if valid:L.hyp[side,key]=tuple(h)
  else:skipped.append([side,key,h])
 for (side,key),h in L.hyp.items():
  if h[0]=='loaded' and lec.loaded_base(L,h[2]) is not None:raise RuntimeError('unproved reset-false loaded guard '+key)
 (work/'profile_skipped.json').write_text(json.dumps(skipped,indent=1))
 iteration=0
 while True:
  m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,work,conflicts,log,tag='profile_joint'+str(iteration),single_cap=200)
  (work/('profile_joint'+str(iteration)+'.json')).write_text(json.dumps(st))
  print('PROFILE_JOINT',iteration,collections.Counter(st.values()),flush=True)
  bad=[k for k,v in st.items() if v!='proved']
  if not bad:break
  before=len(L.hyp);lec.drop_failed(L,bad)
  if len(L.hyp)>=before:raise RuntimeError('untrusted profile could not be disproved/refreshed')
  iteration+=1
 (work/'proved_profile.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())],indent=1))
lec.correspond=current_correspond
r=lec.check(kit,out=out,gold_frontend='verilog',conflicts=1000)
print('NATIVE_RESULT',r['verdict'],r.get('counts'),r.get('reason'),flush=True)
raise SystemExit(0 if r['verdict']=='EQUIVALENT' else 1)
