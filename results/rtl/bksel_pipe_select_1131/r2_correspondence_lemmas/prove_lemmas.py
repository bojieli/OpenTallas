from pathlib import Path
import importlib.util,json,hashlib,random
p=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('LEC',p/'lec.py');le=importlib.util.module_from_spec(spec);spec.loader.exec_module(le)
L=le.Lec(le.read_aig(p/'gold.aig'),le.read_map(p/'gold.map'),le.read_aig(p/'gate.aig'),le.read_map(p/'gate.map'))
log=[]
le.normalize_gold_elements(L,le.slang_elements(p/'gold.aliases.json'),log)
le.json_alias_keys(L,log,work=p);le.slang_element_keys(L,log,work=p);le.alias_arrays(L,log,work=p)
packed=le.slang_packed_vectors(p/'gold.aliases.json');le.relayout(L,log,packed=packed);le.renamed(L,log,packed=packed)
le.fsm_proposals(L,log)
L.hyp={(sd,k):tuple(h) for sd,k,h in json.loads((p/'hyp.json').read_text())}

import os
os.environ['OT_LEC_RESET_CYCLES']='64'
L.kit_reset_ports=['rst']
le.noreset_classify(L)
prefix='ff:u_dut.u_c.'
hints=[['gold',prefix+'g_pipe.u_ctl.c_rep',['eq','gold',prefix+'g_pipe.u_ctl.ovf',0]]]
hints += [['gate',prefix+'t_c['+str(i)+']',['eq','gold',prefix+'g_c[0].cmd[37]',0]] for i in [37,103,169,235]]
results=[]
for j,(side,key,h) in enumerate(hints):
    oside,other=h[1],h[2]
    va=L.rst_val.get((side,key));vb=L.rst_val.get((oside,other))
    base=va is not None and vb is not None and va[0] is not None and va[0]==vb[0]
    if not base:raise SystemExit('reset base not established '+str((key,va,other,vb)))
    L.hyp[(side,key)]=tuple(h)
    m,_=L.build(with_compare=False,with_hyp=True)
    target='hyp:'+side+':'+key
    idx=m.onames.index(target);m.outs=[m.outs[idx]];m.onames=[target]
    sub=p/('lemma_'+str(j));sub.mkdir(exist_ok=True)
    log=[];status=le.prove(m,sub,1000,log,tag='induction')
    (sub/'proof.log').write_text('\n'.join(log))
    ok=status.get(target)=='proved'
    results.append({'hint':[side,key,h],'base64_asserted_reset':{'left':va,'right':vb,'equal':base},'induction':status,'verdict':'PASS' if ok else 'FAIL'})
    if not ok:break
(p/'proven_hints.json').write_text(json.dumps(hints if len(results)==len(hints) and all(x['verdict']=='PASS' for x in results) else [],indent=2)+'\n')
(p/'lemma_receipt.json').write_text(json.dumps({'scope':'Each correspondence added sequentially only after a concrete 64-edge asserted-reset base and its individual exact-AIG induction proof; prior final official hypotheses are already mutually inductive. No wholekit equivalence claimed.','results':results,'verdict':'PASS' if len(results)==len(hints) and all(x['verdict']=='PASS' for x in results) else 'FAIL'},indent=2)+'\n')
print('INDIVIDUAL_CORRESPONDENCE_LEMMAS',len(results),[r['verdict'] for r in results])
