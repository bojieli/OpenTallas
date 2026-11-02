import importlib.util,json,os,pathlib,time
os.environ['OT_LEC_RESET_CYCLES']='64'
s=importlib.util.spec_from_file_location('L','/subject/lec.py');F=importlib.util.module_from_spec(s);s.loader.exec_module(F)
r=pathlib.Path('/subject/lec');w=pathlib.Path('/out');logs=[];t=time.time()
L=F.Lec(F.read_aig(r/'gold.aig'),F.read_map(r/'gold.map'),F.read_aig(r/'gate.aig'),F.read_map(r/'gate.map'))
prefixes=['ff:u_dut.u_bound.u_d2d_rom.u_core.u_rec.st','ff:u_dut.u_bound.u_sys_face.u_ot_pr_core.st']
h={};cs=[]
for prefix,codebook in zip(prefixes,[{0:0,1:1,2:2,5:3},{0:0,1:3,2:2,3:4,4:1}]):
 keys=[prefix+'['+str(i)+']' for i in range(3)]
 for code,bit in codebook.items():h[('gate',prefix+'#t['+str(bit)+']')]=('cube','gold',keys,[(code>>i)&1 for i in range(3)])
 cs.append(('gold',keys,[[(code>>i)&1 for i in range(3)] for code in sorted(codebook)]))
(w/'EXPLICIT_ORIGINAL.json').write_text(json.dumps({'classification':'UNTRUSTED_LEMMA_ONLY','basis':'exact retained lec.log lines88/89, not newly inferred heuristic','hypotheses':[[list(k),v] for k,v in h.items()],'constraints':cs},indent=1))
results=[]
for mode in ['original','rec_reachable']:
 L.hyp=dict(h);L.cons=list(cs)
 if mode=='rec_reachable':
  L.cons=[(sd,ks,[[0,0,0],[1,0,1]]) if ks[0].startswith(prefixes[0]+'[') else (sd,ks,a) for sd,ks,a in cs]
 m,_=L.build(with_compare=False,with_hyp=True)
 statuses=F.prove(m,w,1000,logs,tag='explicit_'+mode,single_cap=1000)
 results.append({'mode':mode,'statuses':statuses,'n_outputs':len(m.outs),'n_inputs':m.ni,'n_ands':len(m.ands)//2})
 (w/'EXPLICIT_RESULT.json').write_text(json.dumps({'classification':'UNTRUSTED_LEMMA_ONLY','original_verdict_unchanged':True,'reset_cycles':64,'accepted_hints':False,'full_compare_rerun':False,'results':results,'elapsed_s':time.time()-t},indent=1))
 (w/'EXPLICIT_LEMMA.log').write_text('\n'.join(logs))
 print(mode,statuses,flush=True)
