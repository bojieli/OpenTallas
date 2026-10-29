import collections,json,re,sys,pickle
from pathlib import Path
kit=Path(sys.argv[1]);sys.path.insert(0,str(kit));import lec
src=kit/'lec_profile';out=kit/'lec_targeted';out.mkdir(exist_ok=False);log=[]
L=lec.Lec(lec.read_aig(src/'gold.aig'),lec.read_map(src/'gold.map'),lec.read_aig(src/'gate.aig'),lec.read_map(src/'gate.map'))
L.kit_reset_ports=lec.kit_reset_ports(kit)
lec.normalize_gold_elements(L,lec.slang_elements(src/'gold.aliases.json'),log)
for fn in (lec.json_alias_keys,lec.slang_element_keys,lec.alias_arrays):fn(L,log,work=src)
for fn in (lec.relayout,lec.renamed,lec.replica_proposals,lec.merged_proposals,lec.register_alias_proposals,lec.fsm_proposals):fn(L,log)
L.hyp.clear()
for sd,k,h in json.loads((src/'proved_profile.json').read_text()):L.hyp[sd,k]=tuple(h)
keys={k for f in json.loads((src/'lec.json').read_text())['failing'] for k in f.get('cone_unmatched_keys',[])}
proposed=[]
for k in sorted(keys):
 if 'g_kv_addr_prep.' not in k:continue
 pat=re.sub(r'(g_off|[qc]_p)\[\d+\]',r'\1[GROUP]',k)
 cs=[c for c in L.matched if re.sub(r'(g_off|[qc]_p)\[\d+\]',r'\1[GROUP]',c)==pat]
 if len(cs)==1:L.hyp['gold',k]=('eq','gold',cs[0],0);proposed.append([k,cs[0]])
for k in sorted(L.gp):
 m=re.search(r'g_icg\.nv_f\[(\d)\]$',k)
 if m:
  i=int(m[1]);target='ff:u_dut.u_g.n_'+('b' if i%2 else 'a')+'_q['+str(512+i//2)+']'
  if target in L.gp:L.hyp['gold',k]=('eq','gold',target,0);proposed.append([k,target])
(out/'proposed.json').write_text(json.dumps(proposed,indent=1));print('PROPOSED',len(proposed),flush=True)
for it in range(32):
 m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag='joint'+str(it),single_cap=200)
 (out/('joint'+str(it)+'.json')).write_text(json.dumps(st));print('JOINT',it,collections.Counter(st.values()),flush=True)
 bad=[k for k,v in st.items() if v!='proved']
 if not bad:break
 before=len(L.hyp);lec.drop_failed(L,bad)
 if len(L.hyp)>=before:raise RuntimeError('no progress')
(out/'model.pkl').write_bytes(pickle.dumps(L));(out/'native_profile.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())],indent=1))
m,_=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=200)
(out/'compare.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log));print('COMPARE',collections.Counter(st.values()),flush=True)
_,missing,constants=lec.kept_registers(L,src/'gold.keep');print('KEPT',len(missing),len(constants),flush=True)
raise SystemExit(0 if all(v=='proved' for v in st.values()) and not missing and not constants else 1)
