#!/usr/bin/env python3
"""Join selected valid-bit paths, actual HEAD descriptors and tail counter evidence."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for x in ['paths','counters','calendar','IB','out']:p.add_argument('--'+x,type=Path,required=True)
a=p.parse_args();j=json.loads(a.paths.read_text());valid=[x for x in j['rows']if x.get('semantic')=='valid'];assert len(valid)==128
assert {x['slice']for x in valid}=={'E2','E3','E4','E5'}
assert all(x['root_bit'][2]==512 for x in valid)
for sl in ['E2','E3','E4','E5']:assert {x['station_region']for x in valid if x['slice']==sl}==set(range(8))
die=Path('/home/ubuntu/coord/tmp/codex-native-head-post-reference-prep/die_r56.v');dt=die.read_text();cluster_map=[]
for sl in ['E2','E3','E4','E5']:
 for i,quad in enumerate(['bf','bn','tn','tf']):
  mm=re.search(r'qfd_c_b16_dv\s+c16_'+sl+'_'+str(i)+r'\s*\((.*?)\);',dt,re.S);assert mm
  cid=int(re.search(r"\.cid\(12'h([0-9a-f]+)\)",mm[1])[1],16)
  q=cid//8;assert q==(4 if sl in ['E2','E3']else 5)
  cluster_map.append(dict(part='c_'+sl+'_'+quad+'_00',original_instance='c16_'+sl+'_'+str(i),cid=cid,global_group_interval=[64*cid,64*(cid+1)],q=q))
assert {x['root_bit'][0]for x in valid}=={x['part']for x in cluster_map}
root=Path('/home/ubuntu/OpenTallas');files={'part':root/'rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv','nk':root/'rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_45.sv','nl':root/'rtl/physical/a0_rc14_selected_2000/qfd_tile_nl_rp2_45.sv','logic':root/'rtl/physical/a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv','node':root/'rtl/physical/ot_qwen_tile_node.sv'}
texts={k:v.read_text()for k,v in files.items()}
guards={'part':['wire             j_last = (j == IL - 1);','wrom_re <= !wsrc_r;','else e_v <= acc[4];','else begin s1_v <= m_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end','assign t_vout = vline[SD + OD + XTD];','if (PORTS) begin : g_atag','assign a_tag = {TW{1\'b0}};'], 'nk':['.n_va(n_a_q[512])','t_out_q[513:512]<=reset_q ? {tf,tv} : 2\'d0;','mis_q <= mis_q | (n_a_q[512] ^ n_b_q[512]);','n_y_q[513:512]<=reset_q ? {fy_q,nvy} : 2\'d0;'], 'nl':['t_out_q[513:512]<=reset_q ? {tf,tv} : 2\'d0;'],'logic':['assign t_vout = t_vout_nd;','.va(n_va)'],'node':['.d(va), .q(vd)','.D(8), .RESET(1)) u_vy']}
evidence={}
for k,patterns in guards.items():
 evidence[k]=[]
 for needle in patterns:
  assert needle in texts[k],(k,needle)
  lines=[dict(line=i+1,source=s.strip())for i,s in enumerate(texts[k].splitlines())if needle in s]
  evidence[k].extend(lines)
fields=[('nout',18),('tiles',18),('k',18),('wsrc',1),('wbase',24),('ts',24),('ks',24),('js',24),('xbase',24),('xks',24),('xjs',24),('xcs',24),('jsh',3),('split',4),('wcs',24),('round',1),('obase',24),('ots',24),('ojs',24),('mmode',1),('oen',1),('amax',1),('rmax',1),('mbase',24)];ibs=[]
for line in a.IB.read_text().splitlines():
 v=int(line,16);d={}
 for k,w in reversed(fields):d[k]=v&((1<<w)-1);v>>=w
 assert d['split']==9 and d['mmode']==0 and d['k']==8 and d['ts']==64 and d['ks']==8 and d['js']==1 and d['jsh']==0
 ibs.append(d)
assert [(x['nout'],x['tiles'],x['wbase'])for x in ibs]==[(6144,8,18432),(6144,8,18944),(6144,8,19456),(560,1,19968)]
cal=json.loads(a.calendar.read_text());cmd=[]
for x in cal['retained_head_commands']:
 v=int(x['cmd'],16)
 if (v>>1)&7!=2:continue
 cmd.append(dict(source_index=x['old_index'],dst=(v>>112)&15,mode=(v>>4)&3,nwords=(v>>7)&255,dbase=(v>>26)&0xffffff,kc=((v>>59)&255)+1))
receivers=[x for x in cmd if x['mode']==2];assert len(cmd)==298 and len(receivers)==149
assert [x for x in receivers if x['nwords']==3]==[dict(source_index=779,dst=8,mode=2,nwords=3,dbase=18944,kc=8)]
assert not any(x['dbase']==19072 for x in receivers)
rows=[]
for q in range(6):
 kept=[i for i in range(64)if (q*128+(i%8)*16)<560]
 assert len(kept)==(64 if q<4 else 24 if q==4 else 0)
 rows.append(dict(q=q,nout=560,t=0,perK_slot_row0=[q*128+16*slot for slot in range(8)],candidate_visible_raw_ordinals=kept,native_raw_valid_count=64,candidate_visible_count=len(kept)))
compact=[];operation_catalog=[];operation_ids={}
for x in valid:
 path_ids=[]
 for y in x['path']:
  op=dict(part=y['evidence'].get('part'),instance=y['evidence'].get('instance'),primitive=y['evidence'].get('primitive'),line=y['evidence'].get('line'),ledger_cycles=y['ledger_cycles'])
  key=json.dumps(op,sort_keys=True)
  if key not in operation_ids:operation_ids[key]=len(operation_catalog);operation_catalog.append(op)
  path_ids.append(operation_ids[key])
 compact.append(dict(slice=x['slice'],region=x['station_region'],station_port=x['station_port'],control_bit=x['control_bit'],root=x['root_bit'],operation_ids=path_ids))
result=dict(status='SELECTED_SOURCE_TAIL_VALIDITY_CONTRACT_MISMATCH_UNDER_LEGAL_STEADY_FRAMES',scope='source proof only; no globalexecution/providerphase/datequalification; passed24wordpostboundarycomponent retained',source_chain='nativePART1active64→e_v/S1/S3valid→t_vout→NK/NLfacebit512→15nativepurevalidnodes→rootn_y512→allselectedCA/fullwordregister/frontendbitprojections→STNrs_c valid; no nout-aware thinning on selectedpaths',transport_operation_catalog=operation_catalog,valid_paths=compact,original_cluster_identity=cluster_map,original_die_source_sha256=hashlib.sha256(die.read_bytes()).hexdigest(),control_path_count=256,valid_path_count=len(valid),native_source_evidence=evidence,HEAD_IBs=ibs,HEAD_STNs=dict(count=298,receiver_count=149,q4tail_sender=next(x for x in cmd if x['source_index']==778),q4tail_receiver=next(x for x in cmd if x['source_index']==779),q5last_reserved_rowblock_base=max(x['dbase']for x in receivers if x['dst']==10),absent_rowblock149_base=19072),last_instruction_row_decisions=rows,current_station_counter_source=json.loads(a.counters.read_text()),candidate=dict(status='PROPOSAL_ONLY_NO_IMPLEMENTATION_OR_ADOPTION',event='explicitdefaultOFF nativeHEADpublisherrowvalidcontract; preserve oldrawPART1ABI bydefault',predicate='row0 = t*768 + (gb>>9)*128 + j*16; visible = row0<nout_r; full18bitt and28bitrowarithmetic, no truncation',guard='authenticatedcurrentHEADlease exact4IB forms,split9/GT3072/mmode0/k8,ts64/ks8/js1/jsh0,noutWaligned; onlyHEADcur resident18432..20031, BASE outsidelease remainsoldvalid',placement='computeonebit besidee_v, carry inparallelwithoriginalvalid, ANDonlypublisher t_vout; doNOTgateMACe_v/s3_v or alter64ROM/accumupdates',existing_tag_caution='PORTSfalse makesa_tagzero; raw_nb/raw_nout are NOT usable outputtags in selectedPART1. Usealreadylivefullwidtht/j, restoreonlynout_r ifpruned, carrypredicatebit.',alignment='REGROOT3: e_pred1 +MEM_EXTRA8 +S1/S1b/S2/S3four +SD15/OD16/XTX2(33)=46FF predicatepipeline; zeroextraarithmeticcycles; exact sourcecut/TTFFreview required',analytic_state_price='up to46predicateFF+18nout_r+1mmode_r=65FFperTG4,49920perrank768tiles beforeactualsynthesis; no nb/nb_t restore;28bitconstantadds/compare/matcherlogic andfanoutmustbepriced, notmeasuredhere',q4_output='24sparsevalids at everyKslots0..2; unchangedtail1KC8/nwords3 then selectsraw56,57,58',q5_output='zero validpublications, covering missingrowblock149; stationonly3wordrepair cannot handle absentq5consumer',lease_event='publish actualgapped24pattern over64rawslots; compact24wordfixture lastselectedordinal23→realraw58 is35inputedge difference, projectednominalcomponentage only, no globaldate adoption',required_gate='default0historicalbehavior, enabledq0..3unchanged64/q4gapped24/q5zero; actualcounter/nativepaircontrols+genuinecaptureddata withexplicitnumericboundary; comparator/tagalignmentmutants; modelprice+physicalTT/FF beforeactivation'),readset={str(v):hashlib.sha256(v.read_bytes()).hexdigest()for v in files.values()},input_sha256={str(v):hashlib.sha256(v.read_bytes()).hexdigest()for v in [a.paths,a.counters,a.calendar,a.IB]},selected_transport_readset=j['readset'])
a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],'valid_paths',len(valid),'q4published24 q5published0 candidateonly')
