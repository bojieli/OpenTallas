import json,hashlib
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-hbm-token-1028/profile_elab')
g=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-1028/elab_sourcefix/asbuilt.json')
def zero(v):return isinstance(v,str) and v and set(v)=={'0'}
def normalize(path):
 mods=json.load(open(path))['modules']
 def pname(n):
  m=mods.get(n,{})
  if not m:return n
  ps={k:v for k,v in m.get('parameter_default_values',{}).items() if k!='WCOPY' or not zero(v)}
  return m.get('attributes',{}).get('hdlname',n)+'::'+json.dumps(ps,sort_keys=True)
 def clean(o):
  if isinstance(o,list):return [clean(x) for x in o]
  if not isinstance(o,dict):return o
  return {k:clean(v) for k,v in o.items() if k not in ('src','hdlname') and not(k=='WCOPY' and zero(v))}
 out={}
 for name,m in mods.items():
  m=clean(m)
  for cell in m.get('cells',{}).values():cell['type']=pname(cell['type'])
  m['cells']=sorted(m.get('cells',{}).values(),key=lambda c:json.dumps(c,sort_keys=True))
  m['netnames']={k:v for k,v in m.get('netnames',{}).items() if not k.startswith('$')}
  key=pname(name)
  if key in out and out[key]!=m:raise ValueError('ambiguous normalized module '+key)
  out[key]=m
 return out
old=normalize(g);new=normalize(r/'default.json')
missing=sorted(set(old)^set(new));different=[n for n in old.keys()&new.keys() if old[n]!=new[n]]
def propagation(path):
 mods=json.load(open(path))['modules'];rows=[]
 for n,m in mods.items():
  if m.get('attributes',{}).get('hdlname')!='ot_hbm_su_static_pgslice_s':continue
  p=m['parameter_default_values']; banks=[]
  for cn,c in m.get('cells',{}).items():
   child=mods.get(c['type'],{})
   if child.get('attributes',{}).get('hdlname',c['type'])=='ot_hbm_su_static_pinned_bank':
    v=c.get('parameters',{}).get('WCOPY',child.get('parameter_default_values',{}).get('WCOPY','0'))
    banks.append(int(v,2))
  rows.append(dict(MLAT=int(p['MLAT'],2),ALAT=int(p['ALAT'],2),WCOPY=int(p.get('WCOPY','0'),2),banks=len(banks),bank_values=sorted(set(banks))))
 return rows
profile=propagation(r/'profile.json');mutant=propagation(r/'mutant.json')
report=dict(default_structural_identity=not missing and not different,missing=missing,differing_modules=different,
 profile=profile,mutant=mutant,
 optin_propagated=bool(profile) and all(x['MLAT']==5 and x['ALAT']==4 and x['WCOPY']==1 and x['banks'] and x['bank_values']==[1] for x in profile),
 mutant_caught=bool(mutant) and all(x['bank_values']==[0] for x in mutant),
 scope='Actual selected-source structural default identity plus enabled parameter propagation; underlying WCOPY numeric bank mechanism has existing REBAL gate, no new whole-token claim')
(r/'profile_proof_v2.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('profile','mutant','differing_modules','missing')}), 'different_count',len(different),'missing_count',len(missing))
if different:
 for n in different[:3]:print('DIFF',n,[(k,old[n].get(k)==new[n].get(k)) for k in set(old[n])|set(new[n])])
raise SystemExit(not (report['default_structural_identity'] and report['optin_propagated'] and report['mutant_caught']))
