from pathlib import Path
import sys,json,copy,inspect,collections
W=Path(sys.argv[1]);B=Path(sys.argv[2]);sys.path.insert(0,str(W/'tools/die_plan'));import core_family_slice as C
old=json.load(open(B/'plan.json'))[0];fam=json.load(open(B/'families_C.json'))['families'][0];lines=[l.split()for l in(B/'geo.txt').read_text().splitlines()];sinks=[(float(l[1]),float(l[2]),l[4],l[5])for l in lines if l[0]=='SINK'];ent=next(tuple(map(float,l[2:]))for l in lines if l[:2]==['PIN','ck']);core=next(list(map(float,l[1:]))for l in lines if l[0]=='CORE');levels=[[tuple(p)for p in l]for l in fam['lattice']['levels']];P=C.lattice_build(sinks,ent,levels);P['mz']=C._LatticeMaze(core);P['nodes']=[(n[0],n[1],n[2],old['frozen_masters'][n[0]],n[4])for n in P['nodes']];assert len(P['nodes'])==old['n_cells']==2611 and sum(map(len,P['leafsinks'].values()))==30810
libs={co:C.H.lib_cells(str(W.parents[1]/'codex-s81phys-0336/libs'/('asap7sc7p5t_INVBUF_RVT_'+co+'_nldm_220122.lib')),sorted(set(C.ENV+[C.H.REP,C.H.BIG])))for co in ['TT','FF']};kr,kc=map(float,fam.get('rc','0.8,0.9').split(','));r=.5*(1.80365e-2+1.89935e-2)*kr;c=.5*(1.78475e-1+1.64264e-1)*kc;replay,_=C.M7.model_x(P,libs,r,c,{})
for co in ['TT','FF']:
 for k in ['mean','window']:assert abs(replay[co][k]-old[co][k])<.021,(co,k,replay[co],old[co])
# Price the already-declared physical cell centres and actual native entry, not a fictitious centre BPin.
sl=json.load(open(B/'old_master_slice.json'));physical={n['name'].removeprefix('mp_ck_'):n for n in sl['core_tree']['nodes']};assert len(physical)==2611
for n in P['nodes']:assert physical[n[0]]['master']==n[3]
P['nodes']=[(n[0],n[1],tuple(physical[n[0]]['xy_um']),n[3],n[4])for n in P['nodes']];pos={n[0]:n[2]for n in P['nodes']};hub={w['edge']:w['hub']for w in P['wires']}
P['land']={u:(abs(pos[u][0]-hub[h][0])+abs(pos[u][1]-hub[h][1]),h)for u,(seg,h)in P['land'].items()}
entry=(82.092,172.8);root=pos['root'];L=sum(abs(a-b)for a,b in zip(entry,root));ENTRY={co:(r*L*(c*L/2+lib[old['frozen_masters']['root']]['cin']),0)for co,lib in libs.items()};ENTRY={co:(d,2.2*d)for co,(d,_)in ENTRY.items()};ns=dict(C.M7.__dict__);ns['ENTRY']=ENTRY;source=inspect.getsource(C.M7.model_x);needle="arr = {'root': 0.0}; slew = {'root': 0.0}";assert needle in source;exec(source.replace(needle,"arr = {'root': ENTRY[corner][0]}; slew = {'root': ENTRY[corner][1]}"),ns);evaluate=ns['model_x'];baseline,_=evaluate(P,libs,r,c,{})
Q=copy.deepcopy(P);Q['mz'].core=list(Q['mz'].core);Q['mz'].core[2]+=8.64;moved=[];cnt=collections.Counter()
for u,ss in Q['leafsinks'].items():
 for i,s in enumerate(ss):
  name=s[2].replace('\\','');stem=name.split('[')[0].split('$_')[0]
  if stem in ['mhh','mkk','mdd','mv','mpre_q']:
   ss[i]=(s[0]+8.64,s[1],*s[2:]);moved.append(name);cnt[stem]+=1
assert dict(cnt)==dict(mhh=128,mkk=128,mdd=128,mv=1,mpre_q=1),cnt
candidate,stage=evaluate(Q,libs,r,c,{});result=dict(scope='PREBUILD MODEL ONLY, UNCHECKED; actual newG1census must be repriced beforeCTS. No clockgraph/master/home/stage change, only386knownE-pin-registerlocationforecast.',old_nominal_replay=replay,old_nominal_reference={co:old[co]for co in ['TT','FF']},frozen_legalized_existing=baseline,candidate=candidate,entry=dict(native=list(entry),physical_root=list(root),wire_um=L,TTFF_delay_slew_ps=ENTRY,fully_priced=True),moved_capture_count=len(moved),moved_by_stem=dict(cnt),node_count=2611,leaf_count=len(Q['leafsinks']),sink_count=30810,stages=old['stages'],added_cycles=0,gate=dict(window20_all=all(candidate[co]['window']<=20 for co in candidate),slew80_all=all(max(candidate[co]['leaf_slew_in_max'],candidate[co]['leaf_out_slew_max'])<=80 for co in candidate)),stage=stage)
(B/'model.json').write_text(json.dumps(result,indent=2));print('VES_WIDTH_MODEL',result['gate'],{co:candidate[co]for co in candidate},'entry',result['entry'])
