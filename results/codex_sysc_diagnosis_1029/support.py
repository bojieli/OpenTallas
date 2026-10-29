import sys,json,re,pathlib,time
root=pathlib.Path('/srv/opentallas-scratch2/claude/codex-sysc-proof-1028')
sys.path.insert(0,str(root/'src/tools/die_plan'))
import lec
old=pathlib.Path('/srv/opentallas-scratch2/claude/codex-lec-0815/sys_c_directed/out')
t=time.time(); L=lec.Lec(lec.read_aig(old/'gold.aig'),lec.read_map(old/'gold.map'),lec.read_aig(old/'gate.aig'),lec.read_map(old/'gate.map'))
family=['ff:u_dut.u_bound.u_d2d_kv.u_core.u_rec.rc_hi','ff:u_dut.u_bound.u_dcal.u_seq.e','ff:u_dut.u_bound.u_dcal.u_seq.pcnt']
seeds=[(family[0]+'[15]'),(family[1]+'[30]'),(family[2]+'[27]')]
keys=[k for k in L.matched if any(k.startswith(f+'[') for f in family)]
L.hyp={('both',k):('const',0) for k in keys}
# No candidate is accepted: inspect exactly the current engine's raw dependency closure on old frozen AIGs.
sup=lec.raw_support(L,list(L.hyp)); before=len(L.hyp)
for k in seeds:L.hyp.pop(('both',k),None)
dropped=lec.cascade_drop(L,sup,seeds)
rec=dict(scope='raw support diagnostic only, no equivalence verdict',old_frozen_source=str(old),matched_counter_bits=before,seeds=seeds,cascade_dropped=[list(k) for k in dropped],remaining=[list(k) for k in L.hyp],seconds=time.time()-t,support={k[1]:sorted(v) for k,v in sup.items()})
(root/'out/raw_support.json').write_text(json.dumps(rec,indent=1)); print(json.dumps({k:v for k,v in rec.items() if k!='support'}),flush=True)
