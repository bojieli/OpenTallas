from pathlib import Path
import re,json,hashlib
P=Path(__file__).parent;S=Path('/srv/opentallas-scratch/claude/head-ld-source-1102');T=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248')
gold=T/'subject/lec/gold.aliases.json';assert hashlib.sha256(gold.read_bytes()).hexdigest()=='4335dbca42fd196d3a31e13457b05db653b2a0386a4c82d43ca7372f170d9cfb'
m=json.load(open(gold))['modules']['lec_top'];s=(S/'1_2_yosys.v').read_text();prior=json.load(open(T/'subject/lec/hyp.json'));pd={(a,b):tuple(c)for a,b,c in prior}
driver={}
for n,c in m['cells'].items():
 for port,bs in c['connections'].items():
  if c.get('port_directions',{}).get(port)=='output':
   for i,b in enumerate(bs):driver[b]=(n,c,i)
def mapped(name):
 x=re.search(r'^\s*(\w+)\s+\\'+re.escape(name)+r'\s*\((.*?)\n\s*\);',s,re.M|re.S);assert x,name
 return {'instance':name,'master':x[1],'ports':{p:v.strip()for p,v in re.findall(r'\.(\w+)\((.*?)\)',x[2])}}
lanes=[];new=[]
for lane in ['a','b']:
 e=f'u_dut.u_core.u_l{lane}.u_ln.u.u_ep.';rr=f'u_dut.u_core.u_l{lane}.u_ln.u.u_rr.';native=[]
 for nm in ['rep_r','rep_ra','u_k_rep_o.q','g_arep[0].a_rep_c']:
  out=[]
  for bit in m['netnames'][e+nm]['bits']:
   dn,c,i=driver[bit];D=c['connections']['D'][i];_,dc,_=driver.get(D,(None,{},None));out.append({'Q_bit':bit,'cell':dn,'type':c['type'],'CLK':c['connections'].get('CLK'),'async_reset':c['connections'].get('ALOAD'),'reset_value':c['connections'].get('AD'),'enable':None,'D_bit':D,'D_operator':dc.get('type'),'D_connections':dc.get('connections')})
  native.append({'field':e+nm,'primitive':out})
 roots=[native[j]['primitive'][0]for j in [0,1,2]];args=[{p:v for p,v in q['D_connections'].items()if p!='Y'}for q in roots];assert args[0]==args[1]==args[2]
 assert all(q['CLK']==[2]for q in roots)
 rootpriors=[x for x in prior if x[1]in ['ff:'+rr+'g_local[10].local_r','ff:'+rr+'g_local[22].local_r']]
 assert len(rootpriors)==2 and all(x[2]==['eq','gold','ff:'+rr+'g_local[0].local_r',0]for x in rootpriors)
 gate={q:mapped(f'u_core.u_l{lane}.u_ln.u.'+q)for q in ['u_ep.rep_ra[0]$_DFF_PN0_','u_ep.rep_ra[1]$_DFF_PN0_','u_ep.u_k_rep_o','u_rr.g_local[10].local_r$_DFF_PN0_','u_rr.g_local[22].local_r$_DFF_PN0_']}
 assert gate['u_ep.rep_ra[0]$_DFF_PN0_']['ports']['D']==gate['u_ep.rep_ra[1]$_DFF_PN0_']['ports']['D']==gate['u_ep.u_k_rep_o']['ports']['d']
 existing=[x for x in prior if e+'rep_ra' in str(x)or e+'u_k_rep_o.q'in str(x)]
 if lane=='a':
  for bit in [0,1]:
   k='ff:'+e+f'rep_ra[{bit}]';assert ('both',k)not in pd
   new.append(['both',k,['eq','gold','ff:'+e+'u_k_rep_o.q',0]])
 else:
  assert list(pd['both','ff:'+e+'u_k_rep_o.q'])==['eq','gold','ff:'+e+'rep_ra[0]',0]
 lanes.append({'lane':lane,'gold':native,'mapped':gate,'retained_reset_priors':rootpriors,'retained_replica_priors':existing,'source_data_equation':'accept_a ? rep_1 : rep_0','source_clock':'posedge clk','replica_enable':'unconditional; no state enable','replica_reset':'async active-low reset to0; rst_v2=local10, rst_v14=local22; bothalreadycanonicalizedtolocal0','state_age':'rep_r/rep_ra0/rep_ra1/rep_o allcapture sameD on sameedge; g_arep0.a_rep_c samples previousrep_ra0 and isoneedgeolder','candidate_status':'TWO_NEW_RELATIONS'if lane=='a'else'ALREADY_RETAINED_DO_NOT_ADD_REVERSE_CYCLE'})
negative=[{'name':'wrong_polarity_BASE_control','proposal':['both',new[0][1],['eq','gold',new[0][2][2],1]],'expect':'NativeBASE64mustreject sincebothresetto0; no accepted prior mutation.'},{'name':'wrong_state_age_NEXT_control','proposal':['both',new[0][1],['eq','gold','ff:u_dut.u_core.u_la.u_ln.u.u_ep.g_arep[0].a_rep_c',0]],'source_clock':'posedge clk onboth','wrong_partner_type':'unreset dff, D=currentrep_ra0 vs currentreplicaD=accept_a?rep_1:rep_0','expect':'Do not assumeBASE; nativeBASE64mustmeasurewhetherunresetdelayflushed. IfBASEcovered, NEXTmustDIFFER with anactualcounterexample; no init/age mask or exception.'}]
packet={'scope':'SOURCE_ONLY_UNTRUSTED_NEXT_BOUNDED_NATIVE_LEMMA_PREP_NO_HINT_ADOPTION','current_counts':{'residual_proved':172,'residual_differs':297,'matched_only_differs':256,'matched_only_LA':247,'matched_only_LB':9,'gold_X':27,'padding':14,'aux_proved':82},'immutable_context':{'prior':12732,'matched':58437,'reset_used':64,'preserve_typed70_hunt_KEEP_context':True,'reset_new_relation_needed':False},'source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in [gold,T/'subject/lec/hyp.json',S/'1_2_yosys.v',S/'rtl/ot_s81ph_link_ep_safe4.sv',S/'rtl/ot_s81ph_coll_lane_safe4.sv',S/'rtl/ot_rst_relay_tree3.sv']},'new_candidate_mappings':new,'negative_controls':negative,'lanes':lanes,'native_cut_witness':'native_cut_witness.json','diagnosis':'ActualnativecutmismatchiscausedbyindependentLAreplica/rep_o coordinates permittedinthecurrentcut. SourceandmappedCLK/D/enable/stateage match; existingprioralreadycoversresetleafequality. This supportsmissingrelation diagnosis, notareachableDUTcounterexample; onlysoleFLOWnativeBASE64+jointNEXTcanqualifyit. LBcanonicalrelationsalreadyexist, soits9failuresremainseparate.','next_scope':'SoleFLOWproducer mayprepareonejointBASE64/NEXTfortwoLANEWrelationsandaffected256originaloutputsplusalreadyprovedauxcontext. No repeatedhunt/ld/wholeLEC, no newresetassumption, no edits/constraints/masks/sourcecredit.'}
(P/'REPLICA_CANDIDATE.json').write_text(json.dumps(packet,indent=1)+'\n');print('new',new,'LBretain',lanes[1]['retained_replica_priors'])
