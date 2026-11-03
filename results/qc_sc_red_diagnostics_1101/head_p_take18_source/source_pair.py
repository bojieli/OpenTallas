from pathlib import Path
import json,re,hashlib
P=Path(__file__).parent;T=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248');S=Path('/srv/opentallas-scratch/claude/head-ld-source-1102');m=json.load(open(T/'subject/lec/gold.aliases.json'))['modules']['lec_top'];p=json.load(open(T/'subject/lec/hyp.json'));pd={(a,b):c for a,b,c in p};s=(S/'1_2_yosys.v').read_text();dr={}
for n,c in m['cells'].items():
 for port,bs in c['connections'].items():
  if c.get('port_directions',{}).get(port)=='output':
   for i,b in enumerate(bs):dr[b]=(n,c,i)
lanes=[];points=[]
for lane in ['a','b']:
 e=f'ff:u_dut.u_core.u_l{lane}.u_ln.u.u_ep.';g=e.removeprefix('ff:');a=e+'ok_f';b=e+'g_fcopy.u_k_ok_f3.q';assert ('both',a)not in pd and ('both',b)not in pd
 assert pd['gold',e+'s2v']==['eq','gold',b,0]
 fs=[]
 for field in ['s2v','ok_f','g_fcopy.u_k_ok_f3.q','u_k_ok_f2.q']:
  Q=m['netnames'][g+field]['bits'][0];n,c,i=dr[Q];D=c['connections']['D'][i];assert c['connections']['CLK']==[2]and c['connections']['AD']==['0'];fs.append({'field':field,'Qbit':Q,'Dbit':D,'CLK':c['connections']['CLK'],'async_reset':c['connections']['ALOAD'],'reset_value':0,'state_enable':None,'state_age':'sameedge currentp_take'})
 assert len({x['Dbit']for x in fs})==1
 mapped=[]
 for tail in ['ok_f$_DFF_PN0_','g_fcopy.u_k_ok_f3','u_k_ok_f2']:
  name=f'u_core.u_l{lane}.u_ln.u.u_ep.'+tail;x=re.search(r'^\s*(\w+)\s+\\'+re.escape(name)+r'\s*\((.*?)\n\s*\);',s,re.M|re.S);assert x
  ports={p:v.strip()for p,v in re.findall(r'\.(\w+)\((.*?)\)',x[2])};assert ports.get('CLK',ports.get('clk'))=='clk';assert ports.get('D',ports.get('d'))==f'\\u_core.u_l{lane}.u_ln.u.u_ep.p_take';mapped.append({'instance':name,'master':x[1],'ports':ports})
 chains=[]
 for leaf in [8,23,24]:
  k=f'ff:u_dut.u_core.u_l{lane}.u_ln.u.u_rr.g_local[{leaf}].local_r';chain=[]
  while('both',k)in pd:
   h=pd['both',k];assert h[0]=='eq'and h[3]==0;chain.append(['both',k,h]);k=h[2]
  assert k=='ff:u_dut.u_core.u_la.u_ln.u.u_rr.g_local[0].local_r';chains.append(chain)
 nine=[e+x for x in ['g_fcopy.u_k_ok_f3.q','ok_f','u_k_ok_f2.q','u_k_ok_o.q','u_k_ok_o2.q','u_k_ok_ready.q','u_k_okc.q','u_k_oku.q','u_k_okv.q']];points+=nine
 lanes.append({'lane':lane,'gold':fs,'mapped':mapped,'retained_gold_s2v_mapping':['gold',e+'s2v',pd['gold',e+'s2v']],'retained_reset_alias_chains':chains,'source_correspondence_to_qualify':{'left_side':'both','left':a,'right_side':'gold','right':b,'xor':0,'existing_target_tuple':None,'applied':False},'nine_fields':nine})
r={'scope':'TWO_FIELD_SOURCE_RELATION_RECORD_ONLY_NO_HINT_APPLIED_NO_JOB','prior_unchanged':12732,'matched':58437,'reset64_retained':True,'new_reset_assumption':False,'lanes':lanes,'source_expected18_points':points,'actual_terminal_result_join':None,'not_dispatchable_until_exact_terminal_join_and_caller_review':True,'source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in [T/'subject/lec/gold.aliases.json',T/'subject/lec/hyp.json',S/'1_2_yosys.v']},'no_LB_replica_cycle':'Separatep_takecohort; existingLBrep_ra/rep_o canonicaltuples untouched.'}
actual=P/'LA_REPLICA_RESULT.json'
if actual.is_file():
 result=json.load(open(actual));remaining=sorted(k for k,v in result['statuses'].items()if k.startswith('ff:')and v=='differs')
 assert remaining==sorted(points) and result['prior_count']==12732 and result['matched']==58437
 assert result['prior_preserved'] and result['new_relations_all_proved'] and result['all_auxiliary_proved']
 assert result['matched_residual_counts']=={'proved':238,'differs':18}
 assert all(x['covered']for x in result['native_BASE64']) and len(result['native_BASE64'])==4
 r['actual_terminal_result_join']={'runtime':'intel1:/srv/opentallas-scratch2/claude/codex-head-la2-0940/LA_REPLICA_RESULT.json','sha256':hashlib.sha256(actual.read_bytes()).hexdigest(),'remaining18_exact_match':True,'matched_residual_counts':result['matched_residual_counts'],'source_credit':False}
(P/'P_TAKE18_SOURCE.json').write_text(json.dumps(r,indent=1)+'\n');print('two sourcefields,18 expectedpoints; nohyp applied; actualterminaljoinrecorded_ifavailable')
