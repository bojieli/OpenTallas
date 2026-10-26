#!/usr/bin/env python3
"""Materialize bounded source/port manifest, not a die/netlist/physical result."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_split import headprep_source as H
from qwen_split.source_pin_plan import rtl_ports
Q='3fcc9f094';S='c5105665874bd54e2b3704cb08a1a70df7d9f871';K='d0d585b182605a9ebacbc4b3b41aafbfb15adb67'
def blob(rev,path):return subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 if any(out.iterdir()):raise SystemExit('fresh source assembly directory required')
 records={}
 def stage(ns,rev,path):
  key=ns+'/'+path
  if key not in records:
   data=blob(rev,path);dst=out/key;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data);records[key]={'revision':rev,'path':path,'sha256':sha(data)}
  return out/key
 masters={
 'Q.tt_ctlm':(Q,H.MASTER,H.SOURCE,{}),
 'Q.native59':(Q,'qfd_native59_dv_headprep_obs1','rtl/qwen_split/qfd_native59_dv_headprep_obs1.sv',{'HEAD_PREP':1,'NU':4,'ROPE':1,'USER_BIND':1,'MCTX':1,'EMB_RELAY':1}),
 'Q.sys_face':(Q,'qfd_sys_face_ovl_fault1','rtl/qwen_split/qfd_sys_face_ovl_fault1.sv',{'MU':1,'MU_HEAD':1,'ROPE':1}),
 'Q.d2d_rom':(Q,'qfd_d2d_static_ovl_sf7_obs1','rtl/qwen_sys/d2d_static_20261015/ot_qwen_status_observers_v1.sv',{'TXDP':'HELD_ACTUAL_FINAL_IMAGE','PR':'SELECTED_RECIPE_REQUIRED'}),
 'Q.mu_ctxrx':(Q,'qfd_mu_ctx_rx_die_obs1','rtl/qwen_split/mu/qfd_mu_ctx_rx_obs1.sv',{'NU':4}),
 'Q.mu_dhobs':(Q,'qfd_sys_face_mu_dhobs_obs1','rtl/qwen_split/mu/qfd_sys_face_mu_dhobs_obs1.sv',{'NU':4}),
 'Q.embed_prov':(Q,'qfd_embedding_word_provider','rtl/qwen_split/qfd_embedding_word_provider.sv',{'ROPE':1}),
 'Q.S8_D4':(S,'qfd_dv_s8_lp','rtl/qwen_dv/s5/s8/lp/qfd_dv_s8_lp.sv',{}),
 'Q.S8_D8':(S,'qfd_dv_s8b_lp','rtl/qwen_dv/s5/s8/lp/qfd_dv_s8b_lp.sv',{}),
 'K.d2d_kv':(K,'qkd_d2d_static_ovl_sfm3_obs1','rtl/qwen_sys/d2d_static_20261015/ot_qwen_k_status_obs1.sv',{'TXDP':'HELD_ACTUAL_FINAL_IMAGE','PR':'SELECTED_RECIPE_REQUIRED'}),
 'K.kvnc':(K,'qkd_kvn_ctx_ovl_rope','rtl/qwen_sys/d2d_static_20261015/qkd_kvn_ctx_ovl_rope.sv',{'MUT_USER':0,'MUT_STALE':0,'MUT_BOOT':0}),
 'K.kvs_emb':(K,'qkd_kvs_emb_ctx','rtl/qwen_sys/static_embedding_20261014/qkd_kvs_emb_ctx.sv',{'NATIVE32':1,'PIPE_JOIN':1,'ROPE':1,'ROPE_DELAY':1024,'OVL':1}),
 'K.host':(K,'qkd_host_root_admission_status_obs1','rtl/qwen_sys/kv_status_obs_20261021/qkd_host_root_admission_status_obs1.sv',{'MU':1}),
 'K.reader':(K,'qkd_host_status_obs','rtl/qwen_sys/kv_status_obs_20261021/qkd_host_status_obs.sv',{}),
 }
 table={};ports={};errors={}
 for inst,(rev,master,path,params)in masters.items():
  f=stage(inst[0],rev,path)
  try:pr=rtl_ports(f,master)
  except ValueError as e:errors[inst]=str(e);continue
  ports[inst]=pr;table[inst]={'master':master,'source':str(f.relative_to(out)),'sha256':sha(f.read_bytes()),'parameters':params,'ports':pr,'physical_adoption':'NOT_EVALUATED_NO_OLD_VIEW_ALIAS'}
 # Exact frozen source recipes/dependencies, not a blanket all-RTL compilation.
 dependencies={}
 for name in ['qfd_dv_s8','qfd_dv_s8b']:
  sp='tools/landed_parent/specs/'+name+'.json';spec=json.loads(stage('Q',S,sp).read_text());fs=spec['sources']+spec['child_sources'];dependencies[name]={'spec':sp,'defines':spec.get('defines',[]),'sources':fs}
  for f in fs:stage('Q',S,f)
 for f,digest in H.SOURCES.items():assert sha(stage('Q',Q,f).read_bytes())==digest
 for f in ['rtl/qwen_dv/headprep13/qfd_tt_ctlm_dv_lpf_hp13.sv','rtl/qwen_dv/headprep13/qfd_tt_ctlm_dv_lpf_hp13_parts.sv','rtl/qwen_split/qfd_native59_qbank.sv','rtl/qwen_split/qfd_native59_svc_obs1.sv','rtl/qwen_split/qfd_native59_static_service_obs1.sv','rtl/qwen_split/mu/qfd_mu_head_context_tx.sv','rtl/qwen_sys/d2d_static_20261015/qfd_d2d_cal_seq_ovl_rope.sv','tools/qwen_split/dv_case.py','tools/qwen_split/die_params.py','tools/qwen_split/record_bundles.py','tools/qwen_split/headprep_source.py','tools/qwen_split/fault_face_bind.py']:
  stage('Q',Q,f)
 qstatus=stage('Q',Q,'rtl/qwen_sys/d2d_static_20261015/ot_qwen_status_observers_v1.sv').read_bytes();kstatus=stage('K',K,'rtl/qwen_sys/d2d_static_20261015/ot_qwen_status_observers_v1.sv').read_bytes()
 marker=b'module ot_qwen_status_obs_rx_body';common_end=qstatus.index(b'module ot_qwen_status_obs_rx_chunk')
 # K only adds RX support before the old RX chunk. Compare complete pre-RX prefix.
 qprefix=qstatus[:qstatus.rfind(b'(* keep_hierarchy',0,common_end)];kprefix=kstatus[:kstatus.rfind(b'(* keep_hierarchy',0,kstatus.index(marker))]
 assert qprefix==kprefix
 joins=[]
 def join(si,sp,di,dp,w):
  assert ports[si].get(sp)==(w,'output'),(si,sp,ports[si].get(sp));assert ports[di].get(dp)==(w,'input'),(di,dp,ports[di].get(dp));joins.append({'source':[si,sp],'sink':[di,dp],'bits':w,'status':'EXACT_SOURCE_PORT_COMPATIBILITY_ONLY','GEN_transport_edges':None})
 for _,_,w,eps in H.prepare_joins(H.MASTER,ports['Q.tt_ctlm'],ports['Q.native59']):join('Q.'+eps[0][0],eps[0][1],'Q.'+eps[1][0],eps[1][1],w)
 for p,w in [('head_descriptor_v',1),('head_descriptor_tag',59),('head_descriptor_generation',2)]:join('Q.native59',p,'Q.sys_face',p,w)
 for p in ['tx_user','rx_user']:join('Q.d2d_rom',p,'Q.native59',p,2)
 for si,p,w in [('Q.mu_ctxrx','obs_ctx',62),('Q.mu_dhobs','obs_res',47),('Q.native59','obs_native',60)]:join(si,p,'Q.d2d_rom',p,w)
 for p,w in [('status_obs_v',1),('status_obs_epoch16',16),('status_obs_payload',208)]:
  join('K.d2d_kv',p,'K.host',p,w);join('K.d2d_kv',p,'K.reader',p,w)
 assert ports['K.kvnc']['head_record']==(552,'input') and ports['K.kvnc']['ovl_users']==(4,'input')
 assert all(ports['K.d2d_kv'][p]==(2,'output')for p in ['tx_user','rx_user'])
 assert ports['K.kvs_emb']['head_rx_user']==(2,'input')and ports['K.kvs_emb']['emb_tx_user']==(2,'input')
 for p,w in [('record_rx',548),('record_rx_v',1),('record_witness_slot',1),('record_send_kind',2)]:assert ports['K.d2d_kv'][p]==(w,'output')
 kd=stage('K',K,'tools/qwen_kv_die/kv_die.py').read_text();ks=stage('K',K,'tools/qwen_kv_die/kv_static_die.py').read_text()
 assert "D2DS_REC_RX = ['record_send_kind', 'record_witness_slot', 'record_rx_v', 'record_rx']" in kd
 assert "b['ports']['ovu']=['tx_user','rx_user']" in kd
 assert ".head_rx_user(i_ovl_users[3:2]), .emb_tx_user(i_ovl_users[1:0])" in ks
 assert ".i_ctx({i_head_record[3],i_head_record[3],i_head_record[551:516],i_head_record[64:4]})" in ks
 reader=(out/'K/rtl/qwen_sys/kv_status_obs_20261021/qkd_host_status_obs.sv').read_text()
 assert 'NB=293' in reader and '{seen,errors,delta,seq_hi,seq_lo,receipt_epoch,status_obs_payload}' in reader
 qinventory=json.loads(stage('Q',Q,'results/arch/qw_fault_face1_1021/coherent_source_inventory.json').read_text())
 kinventory=json.loads(stage('K','1e1a5851e','results/rtl/codex_kv_die_1340/coherent73_source_ledger.json').read_text())
 for f in ['results/arch/qw_headprep_1021/rrloc_projection/realcalendar_native/tt_source_local.json','results/arch/qw_headprep_1021/tt_lp_recipe/generated/qfd_tt_ctlm_dv_lpf_hp13_lp_record.json','results/arch/qw_headprep_1021/rrloc_projection/closed_h16za/selected_hp13_recipe.json']:stage('Q',Q,f)
 result={'status':'BOUNDED_COHERENT73_SOURCE_ASSEMBLY_PORT_CHECKS_ONLY','selected_source_flags':{'Q':dict(qinventory['flags'],OT_QWEN_MU_NU=4),'K':kinventory['flags']},'S8_slot_um':[2462.376,4319.976],'source_only_guard':'No final calendar image or fourROM artifact selected/materialized. S8 newhardstation source qualification pending. Captured595 readset untouched/diagnostic only.','source_revisions':{'Q':Q,'S8':S,'K':K},'masters':table,'parse_errors':errors,'joins':joins,'files':records,'explicit_dependency_recipes':dependencies,'dependency_scope':'Selected source boundaries and declared S8 child-source readset. NOT a complete die synthesis/elaboration filelist; parent source dependencies/view matching remain owed. Q/K namespaces intentionally distinct.','status_shared_source':{'Q_sha256':sha(qstatus),'K_sha256':sha(kstatus),'QTX_and_grammar_prefix_byteidentical':True,'prefix_sha256':sha(qprefix),'difference':'K-only RX structural epoch/body grouping, not silent Q source replacement'},'owner_encoding':{'users':4,'user_bits':2,'Q_tx_rx_user_bits_each':2,'K_tx_rx_user_bits_each':2,'K_kvnc_ovl_users':{'bits':4,'packing_msb_to_lsb':['rx_user[1:0]','tx_user[1:0]']},'K_head_record':{'bits':552,'packing_msb_to_lsb':['record_rx[547:0]','record_rx_v','record_witness_slot','record_send_kind[1:0]'],'O61':'head_record[64:4], user=O61[44:43]'},'K_emb_i_ctx99':'{head_record[3],head_record[3],head_record[551:516],head_record[64:4]}','K_emb_users':'head_rx_user=ovl_users[3:2],emb_tx_user=ovl_users[1:0]'},'status_mapping':{'wire_schema':'kind15 version1 extension208 at[511:304], gap148zero, lower156unchanged','K_internal225':['status_obs_v1','status_obs_epoch16','status_obs_payload208'],'host_atomic293_msb_to_lsb':['seen1','errors4','delta32','seq_hi16','seq_lo16','receipt_epoch16','payload208'],'epoch_law':'Operation TAG epoch independent of outer STATUS receipt epoch; same-receipt-epoch starts do not clear nativecount; delta first/new=count, sameepoch=count-prior; regression/overflow/schema/seqfull sticky faults','CSR':'0x1800-0x19ff, actual qkd_host_status_obs reader, not transport age'},'ages':{'TT_source_local':{'qualified_compositional_edges':4,'basis':'1+(output6-u_gi3), source/native proof only; not direct timestamp trace'},'construction_XPF':21,'actual_GEN_TT_to_native':None,'native_prepare_descriptor_assembled_age':None,'actual_GEN_native_to_face':None,'face_heldbank_assembled_age':None,'K_HEAD_to_full_header':None,'K_KVN_expected':None,'K_STATUS225_transport':None},'blockers':['SOURCE_SELECTOR482 passes bounded source/port tests only; no actual full GEN install model ran','Fixednative no params: HR source/output-age and fixedXPF21 route law failclosed in gen_params','S8 LP D4/D8 to actual whole-die face adapter/master/source binding unresolved; no old monolithicface alias','S8 newpfx hardstation/native qualification pending; SOFTred transport unchanged','New native HEAD_PREP/STATUS/SFfault1 parentviews absent; oldsvc4 CLOSED not sameABI','cf exactHR owner needs unpublished cd8 endpointclock API and actual crossrootlandings; no firstclock fallback','RRroleSIDE not adopted; no newsource actualplacement/RRloc; no oldXY','Sole73 image/ROMplayback held until actualselected Q+K source ages/transport receipts; captured595 is diagnostic only']}
 (out/'ASSEMBLY.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(table),'masters',len(joins),'joins',len(records),'sourcefiles','parse_errors',errors)
if __name__=='__main__':main()
