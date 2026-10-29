# Re-derive the transferred QC NL profile on the fresh gate with lec.transfer_profile; no re-synthesis.
import sys,json,pickle,collections,pathlib,time
sys.path.insert(0,'/r/tools/die_plan');import lec
assert lec.__file__.startswith('/r/'), lec.__file__
out=pathlib.Path('/x/out');out.mkdir(exist_ok=True);log=[];t0=time.time()
L=pickle.loads(open('/d/reset_newgate_target/model.pkl','rb').read())   # fresh-gate model after normalization
profile=json.load(open('/d/reset_newgate/hyp.json'))                    # profile transferred from the old gate
p='ff:u_dut.u_g.u_tile.u_tile.u_logic.u_me.';guard=[[(p+'active',1)],[(p+'pend',1)]]
# the predecessor's name-only restore, for the record
naive={}
for sd,k,h in profile:
  valid=(k in L.gp and k in L.tp) if sd=='both' else k in (L.gp if sd=='gold' else L.tp)
  if h[0]=='eq':valid=valid and h[2] in (L.gp if h[1]=='gold' else L.tp)
  if valid:naive[sd,k]=tuple(h)
rec=lec.transfer_profile(L,profile,log)
if lec.loaded_base(L,guard) is not None:raise RuntimeError('guard not reset-false')
for b in range(7):L.hyp['gold',p+f'nb_t[{b}]']=('loaded',0,guard)
nk=set(naive);tk=set(L.hyp)
print('naive kept',len(naive),'transfer kept',rec['kept'],'swapped',len(rec['swapped']),'resided',len(rec['resided']),
      'reanchored',len(rec['reanchored']),'ambiguous',len(rec['ambiguous']),'dropped',len(rec['dropped']),flush=True)
re57={(sd,k):tuple(h) for sd,k,h in json.load(open('/x/re57.json'))}
print('Codex reanchored57 relations reproduced:',sum(L.hyp.get(k)==h for k,h in re57.items()),'of',len(re57),flush=True)
r=lec.prove_profile(L,out,1000,log,single_cap=100)
print('joint',collections.Counter(r['status'].values()),'rounds',r['rounds'],'dropped',len(r['dropped']),r['dropped'][:10],flush=True)
m,_=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=100)
print('compare',collections.Counter(st.values()),flush=True)
# control: invert one swapped relation; the same joint induction must refute it
sd,k,h=rec['swapped'][0]['new'];hk=(sd,k);L.hyp[hk]=('eq',h[1],h[2],h[3]^1)
m,_=L.build(with_compare=False,with_hyp=True);cs=lec.prove(m,out,1000,log,tag='control',single_cap=100)
bad=[n for n,v in cs.items() if v!='proved']
print('control inverted',k,collections.Counter(cs.values()),'CAUGHT' if f'hyp:{sd}:{k}' in bad else 'ESCAPED',flush=True)
json.dump(dict(transfer=rec,joint=dict(collections.Counter(r['status'].values())),joint_dropped=r['dropped'],
  compare=dict(collections.Counter(st.values())),control=dict(relation=[sd,k],counts=dict(collections.Counter(cs.values())),failing=len(bad)),
  seconds=time.time()-t0),open(out/'summary.json','w'),indent=1)
(out/'proof.log').write_text('\n'.join(log));print('seconds',time.time()-t0)
