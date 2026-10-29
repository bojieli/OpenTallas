import json,pickle,sys,collections
from pathlib import Path
kit=Path(sys.argv[1]);sys.path.insert(0,str(kit));import lec
src=kit/'lec_helpers';out=kit/'lec_nkprofile';out.mkdir(exist_ok=False);L=pickle.loads((src/'model.pkl').read_bytes());log=[];n=0
for sd,k,h in json.loads(Path('/profile.json').read_text()):
 if (sd,k) in L.hyp:continue
 valid=(k in L.gp and k in L.tp) if sd=='both' else k in (L.gp if sd=='gold' else L.tp)
 if h[0]=='eq':valid=valid and h[2] in (L.gp if h[1]=='gold' else L.tp)
 if h[0]=='loaded':valid=valid and all(key in L.gp or key in L.tp for cube in h[2] for key,v in cube)
 if valid:L.hyp[sd,k]=tuple(h);n+=1
for k in L.gp:
 import re
 mm=re.search(r'\.osh\[(10|11)\]\[(\d+)\]$',k)
 if mm:
  target=re.sub(r'\.osh\[\d+\]\[\d+\]$', '.osh#t[5]['+str((int(mm[1])-10)*37+int(mm[2]))+']',k)
  if target in L.tp:L.hyp['gold',k]=('eq','gate',target,0)
 if '.u_mt.g_line.line[' in k:
  target=k.replace('.line[','.line#t[')
  if target in L.tp:L.hyp['gold',k]=('eq','gate',target,0)
print('RESTORED_UNTRUSTED' ,n,flush=True)
for it in range(16):
 m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag='joint'+str(it),single_cap=200);print('JOINT',it,collections.Counter(st.values()),flush=True)
 (out/('joint'+str(it)+'.json')).write_text(json.dumps(st));bad=[k for k,v in st.items() if v!='proved']
 if not bad:break
 lec.drop_failed(L,bad)
(out/'model.pkl').write_bytes(pickle.dumps(L));(out/'native_profile.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())],indent=1))
m,_=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=200);print('COMPARE',collections.Counter(st.values()),flush=True)
(out/'compare.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log));_,missing,constants=lec.kept_registers(L,kit/'lec_profile/gold.keep');print('KEPT',len(missing),len(constants),flush=True)
raise SystemExit(0 if all(v=='proved' for v in st.values()) and not missing and not constants else 1)
