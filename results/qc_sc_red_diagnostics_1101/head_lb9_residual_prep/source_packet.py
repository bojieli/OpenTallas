from pathlib import Path
import json,re,hashlib
P=Path(__file__).parent;T=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248');S=Path('/srv/opentallas-scratch/claude/head-ld-source-1102')
f=T/'subject/lec/gold.aliases.json';assert hashlib.sha256(f.read_bytes()).hexdigest()=='4335dbca42fd196d3a31e13457b05db653b2a0386a4c82d43ca7372f170d9cfb'
m=json.load(open(f))['modules']['lec_top'];h=json.load(open(T/'subject/lec/hyp.json'));pd={(a,b):c for a,b,c in h};s=(S/'1_2_yosys.v').read_text();driver={}
for n,c in m['cells'].items():
 for port,bs in c['connections'].items():
  if c.get('port_directions',{}).get(port)=='output':
   for i,b in enumerate(bs):driver[b]=(n,c,i)
e='u_dut.u_core.u_lb.u_ln.u.u_ep.';rr='ff:u_dut.u_core.u_lb.u_ln.u.u_rr.'
fields=['s2v','ok_f','g_fcopy.u_k_ok_f3.q','u_k_ok_f2.q','u_k_ok_o.q','u_k_ok_o2.q','u_k_ok_ready.q','u_k_okc.q','u_k_oku.q','u_k_okv.q'];gold=[]
for name in fields:
 bit=m['netnames'][e+name]['bits'][0];cell,c,i=driver[bit];D=c['connections']['D'][i]
 gold.append({'field':e+name,'Q_bit':bit,'cell':cell,'type':c['type'],'CLK':c['connections'].get('CLK'),'reset_active_low_bit':c['connections'].get('ALOAD'),'reset_value':c['connections'].get('AD'),'D_bit':D,'enable':None,'state_age':'sameposedge sample of current p_take or currentok_d; no added stage'})
assert len({x['D_bit']for x in gold[:4]})==1 and gold[0]['D_bit']==130458
assert len({x['D_bit']for x in gold[4:]})==1 and gold[4]['D_bit']==130501
assert all(x['CLK']==[2]and x['reset_value']==['0']for x in gold)
def mapped(name):
 v=re.search(r'^\s*(\w+)\s+\\'+re.escape(name)+r'\s*\((.*?)\n\s*\);',s,re.M|re.S);assert v,name
 return {'instance':name,'master':v[1],'ports':{p:x.strip()for p,x in re.findall(r'\.(\w+)\((.*?)\)',v[2])}}
native=[mapped('u_core.u_lb.u_ln.u.u_ep.'+x)for x in ['ok_f$_DFF_PN0_','g_fcopy.u_k_ok_f3','u_k_ok_f2','u_k_ok_o','u_k_ok_o2','u_k_ok_ready','u_k_okc','u_k_oku','u_k_okv']]
assert all(x['ports'].get('CLK',x['ports'].get('clk'))=='clk'for x in native)
chains={}
for q in [8,23,24]:
 key=rr+f'g_local[{q}].local_r';chain=[];seen=set()
 while ('both',key)in pd:
  assert key not in seen;seen.add(key);v=pd['both',key];chain.append(['both',key,v]);assert v[0]=='eq'and v[3]==0;key=v[2]
 assert key=='ff:u_dut.u_core.u_la.u_ln.u.u_rr.g_local[0].local_r'
 chains[q]=chain
a='ff:'+e+'ok_f';b='ff:'+e+'g_fcopy.u_k_ok_f3.q';assert('both',a)not in pd and('both',b)not in pd
assert pd['gold','ff:'+e+'s2v']==['eq','gold',b,0]
out={'scope':'UNTRUSTED_SOURCE_ONLY_LB9_DIAGNOSIS_NO_PROOF_HINT_OR_JOB','current9verdict':'DIFFERS_UNCHANGED','separate_from_LA_replica_producer':True,'existing_context':{'prior_count':12732,'matched':58437,'reset_cycles':64,'LBreplica_relations_already_retained':True,'new_reset_relation':False,'retain_gold_s2v_tuple':['gold','ff:'+e+'s2v',pd['gold','ff:'+e+'s2v']]},'points':[x['point']for x in json.load(open(P/'native_cut_witnesses.json'))['witnesses']],'gold_primitives':gold,'mapped_primitives':native,'retained_reset_alias_chains':chains,'source_equations':{'p_take':'pv && !s2v','ok_d':'p_take && !p_bad','p_bad':'(pack-una_s) > (nxt_rw-una_s)','p_take_copy_next':'s2v,ok_f,ok_f2,ok_f3 allcapturecurrentp_take on sameposedge, reset0','ok_d_copy_next':'ok_u/ok_v/ok_c/ok_o/ok_o2/ok_ready allcapturecurrentok_d on sameposedge, reset0'},'actual_gate_feedback':{'pv_QN':'_000733_','pv_logical':'INV_175258_.Y=_081753_','ok_f_QN':'_037578_','buffered_ok_f_QN':'BUFx2_104800_.Y=_100997_','p_take_driver':'AND2_175259_(_081753_,_100997_)','meaning':'pv && !ok_f; s2v merged into same physicalstatecohort'},'cause':'Originalgold-onlys2v mapping choosesfcopy3 whilegatep_take choosesok_f. Bothmatchedstatesremainindependentinthecurrentcut. Shared source/mapped CLK,D,resetvalue,enable,stateage andretainedresetaliases supportmissingcohortcorrespondence; actualnativeBooleanwitnessesforall9 verifycausality. No reachableDUTsequence inferred.','candidate_only':['both',a,['eq','gold',b,0]],'negative_controls':[{'name':'wrong_polarity_BASE','candidate':['both',a,['eq','gold',b,1]],'expected':'NativeBASE64rejects0vs1; do not assumeorpatchinitialstate.'},{'name':'wrong_ok_d_cohort_NEXT','candidate':['both',a,['eq','gold','ff:'+e+'u_k_ok_o.q',0]],'expected':'NativeBASE64mustmeasure0/0. NEXTmustDIFFER: p_take1,p_bad1 yieldsDp_take1vsDok_d0. Sameclock/resetage doesnotmakeaccept-validityfilterequivalent.','concrete_source_values':{'pv':1,'s2v':0,'pack':1,'una_s':0,'nxt_rw':0},'no_new_assumption':True}],'source_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [f,T/'subject/lec/hyp.json',S/'1_2_yosys.v',S/'rtl/ot_s81ph_link_ep_safe4.sv']},'native_witnesses':'native_cut_witnesses.json','limits':'No actual counts updated, no modifications to oldhyp/source/constraints/masks or LAjob scope. SoleFLOWmaypreparea separate futureboundednativeBASE/NEXTafterparent review.'}
(P/'LB9_CANDIDATE.json').write_text(json.dumps(out,indent=1)+'\n');print('candidate',out['candidate_only'],'goldD130458/130501; existingresetaliases',list(chains))
