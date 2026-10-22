#!/usr/bin/env python3
"""Read-only actual native/LP clock evidence; no new functional/GEN experiment."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p='rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_native32.sv';nb=(ROOT/p).read_bytes();assert sha(nb)=='66cd44bf35e5bbb8a3f2cf9bf0698ca9c75f7e2f676dcf4ee2727c46627eb9da';n=nb.decode()
 alias=json.loads((HERE/'actual_frontend_aliases.json').read_text());assert alias['source_sha256']=='883eaeacdd8485ff16ebd1de5a9d8ee2888da260241c2b9b2bbdc816e67e06ce'
 fs={}
 for m in re.finditer(r'(qfd_bmath_dff_\w+) #\(\.ID\(0\)\) (u_\d+)\(([^;]+)\);',n):
  ps=dict(re.findall(r'\.(\w+)\(([^()]+)\)',m[3]));fs[ps['Q']]={'master':m[1],'instance':m[2],**ps}
 assert 'assign n_3159 = ck_core;'in n and 'assign n_3160 = ck_hr;'in n
 groups={};source={};banks={};calendar={}
 for port,width in [('emb_start',1),('emb_token',18),('emb_position',18),('emb_user',2)]:
  exp=re.search(r'^assign '+port+r' = ([^;]+);',n,re.M)[1];bits=exp.strip('{}').split(',');assert len(bits)==width
  rows=[]
  for b,net in enumerate(reversed(bits)):
   row=dict(bit=b,net=net,**fs[net]);assert row['C']=='n_3160';rows.append(row)
  groups[port]={'width':width,'clock':'ck_hr','bit_rows':rows}
  sr=[]
  for b,net in enumerate(alias['netnames']['g_'+port]):
   row=dict(bit=b,net='n_'+str(net),**fs['n_'+str(net)]);assert row['C']=='n_3159';sr.append(row)
  source['u_gi.'+port]={'width':width,'clock':'ck_core','bit_rows':sr}
 for key,bits in alias['netnames'].items():
  if key.startswith(('u_gi.tok_b[','u_gi.pos_b['))or key in ('u_gi.c_emb','u_gi.c_user'):
   rows=[dict(bit=b,net='n_'+str(net),**fs['n_'+str(net)])for b,net in enumerate(bits)]
   assert all(row['C']=='n_3159'for row in rows)
   (calendar if key in ('u_gi.c_emb','u_gi.c_user')else banks)[key]={'clock':'ck_core','bit_rows':rows}
 assert sum(x['width']for x in groups.values())==sum(x['width']for x in source.values())==39
 assert sum(len(x['bit_rows'])for x in banks.values())==144
 assert fs['n_18730']['D']=='n_17398'and fs['n_18731']['D']=='n_5936'and fs['n_18732']['D']=='n_5938'
 lpfile=HERE/'source_lp.sv';lpb=lpfile.read_bytes();assert sha(lpb)=='0f86c241395c56cdccdc683c57444538d88c96c6850a9ae34b7437b25b26cff1';lptext=lpb.decode();landings=[]
 record_path='results/arch/qw_headprep_1021/tt_lp_recipe/generated/qfd_tt_ctlm_dv_lpf_hp13_lp_record.json';rb=(ROOT/record_path).read_bytes();assert sha(rb)=='468a9704f3fb5f0df53e8a4e7d0d89e860fdee6597d5b052f2f800ec67f9807f';rec=json.loads(rb)
 for no,port in zip(range(29,33),groups):
  row=next(r for r in rec['landings']if r['name']==str(no));assert row['net']=='g_'+port and row['src_region']=='core'and row['dst_region']=='hr'
  for suffix,clock in [('w','ck_core'),('r','ck_hr')]:assert re.search(r'u_lpl_'+str(no)+'_'+suffix+r'\s*\(\.ck\('+clock+r'\)',lptext)
  landings.append(row)
 fixture_path='results/arch/qw_headprep_1021/rrloc_projection/realcalendar_native/tb_hp13_native.sv';fixture=(ROOT/fixture_path).read_bytes();line=next(i for i,l in enumerate(fixture.decode().splitlines(),1)if '.ck_core(clk), .ck_hr(clk)'in l);assert line==105
 oldpath='results/arch/qw_headprep_1021/rrloc_projection/realcalendar_native/tt_source_local.json';old=(ROOT/oldpath).read_bytes()
 evidence={'status':'EXACT_CLOCK_SOURCE_EVIDENCE_NO_NEW_EXPERIMENT','native_source':{'path':p,'sha256':sha(nb)},'frontend_aliases':{'path':alias['source_path'],'sha256':alias['source_sha256']},'LP_record':{'path':record_path,'sha256':sha(rb)},'source_LP_sha256':sha(lpb),'calendar_sample':{'clock':'ck_core','source_ff_groups':source,'calendar_predicate_and_user':calendar,'token_position_bank_groups':banks,'sample_intrinsic_edges':1,'unit':'ck_core rising edge; pre-edge same c_emb/tok_b/pos_b/c_user, no RESULT/NEXT token'},'landing_path':{'source_clock':'ck_core','destination_clock':'ck_hr','record_added_edges_reference':3,'offsets_reference':{'producer_u_gi':3,'output':6},'landings':landings,'unit':'LP/compiler common-clock-reference offset/index count; physical clock ratio/phase/time conversion not established'},'final_outputs':groups,'fixture':{'path':fixture_path,'sha256':sha(fixture),'line':line,'connection':'.ck_core(clk), .ck_hr(clk)','scope':'Existing realcalendar/native component comparison only; no independent clock relation/physical GEN proof'},'historical_receipt':{'path':oldpath,'sha256':sha(old),'bytes_preserved':True}}
 (HERE/'EMB_CLOCK_EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
 canonical={'schema':'opentallas.qwen.tt_emb_source_clock_canonical.v1','status':'COMMON_CLOCK_REFERENCE_ONLY_NOT_ACTUAL_AVAILABILITY','master':'qfd_tt_ctlm_dv_hp13_rrloc_native32','rtl':p,'rtl_sha256':sha(nb),'lp_record':record_path,'lp_record_sha256':sha(rb),'supersedes_for_actual_availability':{'path':oldpath,'sha256':sha(old),'raw_bytes_preserved':True,'old_status_is_historical_component_scope_only':True},'reference_source_local_edges':4,'reference_formula':'1 ck_core sample + LP common-clock-reference offset(6-3) =4 reference edges','source_local_edges':None,'actual_availability_edges':None,'clock_domain':'MIXED_ck_core_TO_ck_hr','clock_unit':'COMMON_CLOCK_REFERENCE_INDEX_ONLY','source_segments':[{'segment':'calendar bank/user sample into u_gi.emb_*','clock':'ck_core','edges':1,'knownness':'EXACT_SOURCE_CORE_CAPTURE'},{'segment':'u_gi emb_* to outer emb_* through LP29..32','source_clock':'ck_core','destination_clock':'ck_hr','reference_added_edges':3,'physical_elapsed_edges':None,'knownness':'CROSS_DOMAIN_REFERENCE_ONLY_RATIO_PHASE_UNMEASURED'},{'segment':'39 final output QFFs','clock':'ck_hr','count':39,'knownness':'ALL39_ACTUAL_NATIVE_CLOCK_PINS_VERIFIED'}],'reference_fixture':evidence['fixture'],'evidence':'results/arch/qw_headprep_1021/coherent73_assembly/clock_units/EMB_CLOCK_EVIDENCE.json','actual_GEN_clock_relation':None,'actual_GEN_TT_to_native_transport':None,'native_prepare_assembled_age':None,'face_held_bank_assembled_age':None,'actual_GEN_native_to_face_transport':None,'compiler_law':'This is the current canonical override. It is NOT status QUALIFIED_SOURCE_LOCAL_EDGES and provides no source_local_edges integer. Existing source-status guard must reject as actual availability; do not ingest historical numeric4/status without this mixed-clock override. Final source-clock law and selectedGEN proof remain required.','HR_separate':{'arm_local_candidate_edges':1,'clock':'ck_hr','unit':'ck_hr rising edges local to scheduler-sourceQ->HRcaptureQ; no core/ns/physicaltransport conversion','head380_post_source_edges':0,'head380_clock':'ck_hr hardchild rom_cmd output to exact same native nets at outerHR','valid_startup_edges':2,'guard482':'UNCHANGED_REFUSAL'},'no_new_work':'Read existing native/LP/frontend-alias/fixture source only. No bench/build/GEN/phase fix/compensating delay or programme/image.'}
 (HERE/'TT_SOURCE_CLOCK_CANONICAL.json').write_text(json.dumps(canonical,indent=2)+'\n')
 assembly_path=HERE.parent/'ASSEMBLY.json';assembly=json.loads(assembly_path.read_text());assembly['previous_assembly_sha256']=sha(assembly_path.read_bytes());assembly['canonical_clock_override']='results/arch/qw_headprep_1021/coherent73_assembly/clock_units/TT_SOURCE_CLOCK_CANONICAL.json';assembly['ages']['TT_source_local']={'status':canonical['status'],'reference_edges':4,'actual_availability_edges':None,'clock_domain':canonical['clock_domain'],'clock_unit':canonical['clock_unit'],'source':'1 ck_core sample plus3 mixed-domain LP reference offsets; both fixture clocks tied clk, no physical ratio/phase law'};assembly['ages']['HR_arm_source_local']={'candidate_edges':1,'clock':'ck_hr','unit':'ck_hr rising edges','actual_GEN_transport_edges':None};assembly['blockers'].insert(0,'Canonical EMBclock override: historical4 is common-clock fixture/index ONLY, actual availability unqualified until selected clock relation; compiler must reject canonicalstatus')
 (HERE/'ASSEMBLY_CANONICAL.json').write_text(json.dumps(assembly,indent=2)+'\n')
 print('SOURCE_CLOCK_EVIDENCE all39producer/core+39final/hr+144bank/core+3calendar/core; mixed clock canonical reference4 only; old receipt bytes preserved')
if __name__=='__main__':main()
