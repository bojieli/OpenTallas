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
L.hyp=dict(h);L.cons=[(sd,ks,[[0,0,0],[1,0,1]]) if ks[0].startswith(prefixes[0]+'[') else (sd,ks,a) for sd,ks,a in cs]
m,kind=L.build(with_compare=False,with_hyp=True)
val,mask=m.simulate(32,seed=2238)
witness=[]
for i,name in enumerate(m.onames):
 if prefixes[0] not in name or not any('#t['+str(j)+']' in name for j in [0,3]):continue
 bad=F.lit_val(val,mask,m.outs[i])
 if not bad:continue
 bit=(bad&-bad).bit_length()-1
 inputs={str(v):dict(kind=kind.get(v),name=m.inames[v-1],value=(val[v]>>bit)&1) for v in sorted(m.cone_inputs(m.outs[i]))}
 nexts={str((sd,k)): (F.lit_val(val,mask,l)>>bit)&1 for (sd,k),l in L.dlit.items() if any(k.startswith(p+'[') or k.startswith(p+'#t[') for p in prefixes)}
 witness.append(dict(output=name,simulation_lane=bit,inputs=inputs,next_states=nexts))
(w/'COUNTEREXAMPLES.json').write_text(json.dumps(dict(classification='UNTRUSTED_ABSTRACT_NATIVE_STEP_WITNESS',basis='explicit original codebook plus proposed rec reachable domain, all other unmatched states free; no original accepted hints',witnesses=witness,elapsed_s=time.time()-t),indent=1))
print('WITNESSES',len(witness),flush=True)
