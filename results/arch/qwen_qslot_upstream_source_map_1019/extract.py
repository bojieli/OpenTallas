#!/usr/bin/env python3
"""Finite read-only extraction. Never invokes a lowerer, compiler or simulator."""
import argparse, collections, csv, gzip, hashlib, json, pathlib, re, subprocess
P=pathlib.Path(__file__).resolve().parent; W=P.parents[2]; S=P/'source'
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(n,x):(P/n).write_text(json.dumps(x,indent=2)+'\n')
files={
'0d4c9808f':['rtl/qwen_dv/qfd_dv_slice2_faces.sv','rtl/qwen_dv/qfd_dv_slice2.sv','rtl/qwen_dv/qfd_dv_su8_entries.sv','rtl/qwen_dv/qfd_dv_stream.sv','rtl/qwen_dv/qfd_dv_vm.sv','rtl/qwen_dv/qfd_dv_hr_pack.sv','rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_hr.sv','rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_static.sv','rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv','rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_pw.sv','rtl/qwen_split/qfd_native59_dv_service.sv','rtl/qwen_dv/qfd_tt_ctlm_dv.sv','rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv','tools/qwen_layerbench/dv_lower.py','tools/qwen_layerbench/ctlm_image.py','results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'],
'7e5150af5':['tools/qwen_layerbench/dv_lower.py','tools/qwen_layerbench/dv_lower_vec.py','tools/qwen_layerbench/dv_lower_mat.py','tools/qwen_layerbench/ctlm_image.py','tools/qwen_layerbench/finite_calendar_body.py','tools/qwen_layerbench/table_user_programme.py','tools/qwen_layerbench/model_programme_integration.py','tools/qwen_layerbench/table_rom_native_fixture.py','results/arch/qwen_calendar_integration_1019/source_body.py','rtl/qwen_dv/qfd_tt_ctlm_dv.sv','rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv','rtl/qwen_dv/qfd_dv_calendar_rom.sv','rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv','results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex','results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/lowering.json','results/arch/qwen_calendar_integration_1019/witness/body.json','results/arch/qwen_calendar_integration_1019/witness/descriptor_cap1.json','results/arch/qwen_calendar_integration_1019/witness/ctlm_metadata_source.json','results/arch/qwen_calendar_integration_1019/witness/pw_metadata.hex','results/arch/qwen_calendar_integration_1019/witness/composition.json','results/arch/qwen_calendar_integration_1019/witness/lowerer_sources.json','results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json']}
manifest=[]
for rev,paths in files.items():
 for path in paths:
  n=rev+'__'+path.replace('/','__'); target=S/n
  b=target.read_bytes() if target.exists() else subprocess.check_output(['git','-C',str(W),'show',rev+':'+path]);target.write_bytes(b)
  manifest.append(dict(rev=rev,path=path,copy=n,sha256=sha(b),bytes=len(b)))
def src(rev,path):return (S/(rev+'__'+path.replace('/','__'))).read_text()
def j(path):return json.loads(src('7e5150af5',path))
root='results/arch/qwen_calendar_integration_1019/witness/'
body=j(root+'body.json');desc=j(root+'descriptor_cap1.json');meta=j(root+'ctlm_metadata_source.json');comp=j(root+'composition.json');receipts=j(root+'lowerer_sources.json')
program=src('7e5150af5','results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex')
assert sha(program.encode())=='cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796'
isa=[int(x,16) for x in program.split()];pw=[int(x,16) for x in src('7e5150af5',root+'pw_metadata.hex').split()]
assert len(isa)==25 and len(pw)==1024
assert all(pw[16*i+b]==(v>>(64*b))&((1<<64)-1) for i,v in enumerate(isa) for b in range(16))
assert all(v==0 for v in pw[400:976])
ctrl=src('0d4c9808f','rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_static.sv')
o={k:int(v) for k,v in re.findall(r'localparam integer O_(\w+) = (\d+);',ctrl)}; widths={k:int(v) for k,v in re.findall(r'localparam integer W_(\w+) = (\d+);',ctrl)}
fields=['UNIT','SU_NOUT','SU_NIN','A_BASE','A_SO','A_SI','B_BASE','C_BASE','DST','D_BASE','D_SO','D_SI','RED','SFU','MA','MB','AD','MC','MD']
ops=[dict(pc=pc,**{k:(v>>o[k])&((1<<widths[k])-1) for k in fields}) for pc,v in enumerate(isa)]
q_isa={}
for pc in [7,9]:
 d=ops[pc];a=[d['D_BASE']+r*d['D_SO']+k*d['D_SI'] for r in range(d['SU_NOUT']) for k in range(d['SU_NIN'])];q_isa[pc]=a
assert len(set(q_isa[7]+q_isa[9]))==512 and sorted(q_isa[7]+q_isa[9])==list(range(13696,14208))
assert all(d['D_BASE']>>22==0 for d in ops if d['UNIT']==2) # Global ISA addresses are not DV Q-window words.
assert [(t,int(c,16)) for t,c in [(e['edge_w5'],e['cmd']) for e in comp['events']]]==[tuple(x) for x in body['segments']['decode']]
assert len(comp['events'])==406
assert desc['entries']==1009 and desc['ranges']['decode']['count']==406 and len(desc['preload_ranges'])==36
assert desc['source']['programme_sha256']==sha(program.encode())
vec=src('7e5150af5','tools/qwen_layerbench/dv_lower_vec.py')
assert sha(vec.encode())==receipts['tools/qwen_layerbench/dv_lower_vec.py']
assert "D.W_D2D | (HD * r['head'])" in vec and "d=d + HD // 2, dsi=1" in vec
assert 'rlo=7, rhi=8' in vec
commands=[]
for seg,events in body['segments'].items():
 for index,(edge,c) in enumerate(events):
  dst=c>>112;kind=(c>>1)&7
  commands.append(dict(segment=seg,index=index,recorded_edge=edge,command=f'{c:029x}',kind=kind,dst=dst,local=dst==14,pidx=(c>>4)&511 if kind==1 and dst!=14 else None))
qcmd=[e for e in comp['events'] if e['label'].startswith('qk: r') and e['label'].endswith('(q)')]
assert len(qcmd)==8
seats=[];words=[]
for e in qcmd:
 c=int(e['cmd'],16);sl=c>>112;pidx=(c>>4)&511;h=sl//2;half=pidx-7
 assert sl in [0,2,4,6] and pidx in [7,8] and (c>>1)&7==1
 for beat in range(8):
  addrs=[128*h+64*half+8*beat+lane for lane in range(8)]
  words.append(dict(slice=sl,head=h,pidx=pidx,half=half,vector_beat=beat,expected_mask=255,dd_kind=0,dv_full_addresses=[(2<<22)|a for a in addrs],dd_addresses=addrs,recorded_command_edge_w5=e['edge_w5'],observed_write_edge=None,token=None,epoch=None))
  for lane,a in enumerate(addrs):
   seats.append(dict(seat=a,source_isa_pc=7 if half==0 else 9,global_isa_element=13696+a,slice_id=sl,head=h,local_pidx=pidx,half=half,vector_beat=beat,lane=lane,dv_full_address=(2<<22)|a,dd_address=a,expected_mask=255,observed_write_edge=None,token=None,epoch=None))
assert sorted(x['seat'] for x in seats)==list(range(512)) and len(words)==64
# Exactly four KV dates change; extraction of Q source is independent, not an execution claim.
frozen=json.loads(src('0d4c9808f','results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'))
selected=json.loads(src('7e5150af5','results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'))
diff=[]
for a,b in zip(frozen['L_compiled'],selected['L_compiled']):
 if a!=b:diff.append(dict(frozen=a,selected=b))
assert len(diff)==4
assert 'L' not in frozen and 'L' not in selected and 'E' not in frozen and 'E' not in selected
# Actual frozen constructor port inventory: no assumptions from XT1 fixtures.
genpath=S/'gen0__die.v.gz';gen=gzip.decompress(genpath.read_bytes());assert sha(gen)=='7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7'
ports=[]
for line in gen.decode().splitlines():
 m=re.match(r'\s*(qfd_dv_slice2_[we]|qfd_native59_dv_service|qfd_tt_ctlm_dv_lpf|qfd_tt_ctlm_dv)\s+(\w+)\s*\((.*)\);',line)
 if m:
  bindings=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3]));ports.append(dict(module=m[1],instance=m[2],bindings=bindings))
assert len([r for r in ports if r['instance'].startswith('dvs_')])==12
(P/'actual_constructor_lines.txt').write_text('\n'.join(line for line in gen.decode().splitlines() if any(' '+r['instance']+' (' in line for r in ports))+'\n')
byname={r['instance']:r for r in ports}
route_names={0:['dvs_W5'],2:['dvs_W3','dvs_W4','dvs_W5'],4:['dvs_W1','dvs_W2','dvs_W3','dvs_W4','dvs_W5'],6:['dvs_E0','dvs_W0','dvs_W1','dvs_W2','dvs_W3','dvs_W4','dvs_W5']}
relay_lines=[];relays={}
for line in gen.decode().splitlines():
 m=re.match(r'\s*(\w+)\s+(rly_dv_x0_dd_dd_0|rly_dvw_dd_wo_\d+)\s*\((.*)\);',line)
 if m:
  r=dict(module=m[1],instance=m[2],bindings=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3])));relays[m[2]]=r;relay_lines.append(line)
assert len(relays)==27
routes=[]
for sid,names in route_names.items():
 steps=[]
 for index,name in enumerate(names):
  r=byname[name];b=r['bindings'];out=b.get('dd_wo',b.get('dd_eo'));inp=b.get('dd_ei',b.get('dd_wi'))
  if index:
   prior=steps[-1]['output_net']
   if name=='dvs_W0':
    land=relays['rly_dv_x0_dd_dd_0'];assert land['bindings']['a']==prior and land['bindings']['b']==inp
    steps.append(dict(landing=land))
   else:assert prior==inp
  steps.append(dict(instance=name,input_net=inp,output_net=out,clock=b['ck'],reset=b['rst_n'],own_source=index==0))
 assert steps[-1]['output_net']=='n_dvw_dd_wo'
 assert relays['rly_dvw_dd_wo_0']['bindings']['a']=='n_dvw_dd_wo'
 for i in range(25):assert relays[f'rly_dvw_dd_wo_{i}']['bindings']['b']==relays[f'rly_dvw_dd_wo_{i+1}']['bindings']['a']
 assert relays['rly_dvw_dd_wo_25']['bindings']['b']==byname['native59']['bindings']['dd_i']
 routes.append(dict(source_slice_id=sid,source_instance=names[0],steps=steps,shared_native_lane=[relays[f'rly_dvw_dd_wo_{i}'] for i in range(26)],destination=byname['native59']))
dump('q_origin_routes.json',routes)
(P/'actual_dd_relay_lines.txt').write_text('\n'.join(relay_lines)+'\n')
cal=src('7e5150af5','rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv')
assert 'parameter integer TABLE_ROM = 0' in cal and 'parameter integer CALENDAR_ROM = 0' in cal
assert 'i_kind == 3\'d4 && TABLE_ROM != 0 && CALENDAR_ROM != 0' in cal
assert 'table_load <= 1; table_stage <= ic[9:4]; table_user <= 2\'(ru);' in cal
assert 'wire          tl_bad = (CALENDAR_ROM != 0)' in cal
for path in ['rtl/qwen_dv/qfd_tt_ctlm_dv.sv','rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv']:
 text=src('7e5150af5',path)
 assert '.TABLE_ROM(' not in text and '.CALENDAR_ROM(' not in text and '.table_load(' not in text
assert not any(c['local'] and c['kind'] in [3,4] for c in commands if c['segment']=='decode')
for n,x in [('sources.json',manifest),('isa_decoded.json',ops),('commands.json',commands),('q_words_contract.json',words),('q_seats_contract.json',seats),('actual_constructor_ports.json',ports)]:dump(n,x)
presence=P/'source_presence.json'
if not presence.exists():
 r=subprocess.run(['git','-C',str(W),'cat-file','-e','7e5150af5:tools/qwen_layerbench/dv_layer.py'],capture_output=True)
 dump('source_presence.json',dict(rev='7e5150af5',path='tools/qwen_layerbench/dv_layer.py',returncode=r.returncode,stderr=r.stderr.decode()))
missing_source=json.loads(presence.read_text())['returncode']!=0
summary=dict(scope='SOURCE_EXTRACTION_ONLY',programme_words=25,pw_isa_beats_checked=400,pw_400_975_zero=True,decode_commands=406,body_command_counts={s:dict(collections.Counter((c>>1)&7 for t,c in es)) for s,es in body['segments'].items()},q_contract_seats=512,q_contract_words=64,q_contract_commands=8,actual_connected_seats_observed=None,source_commands_unchanged=True,body_old_programme_hash=body['source']['programme_sha256'],selected_descriptor_programme_hash=desc['source']['programme_sha256'],vector_lowerer_matches_body_receipt=True,body_dv_layer_source_missing_at_selected_commit=missing_source,profile_differences=diff,old_compiler_todo_scope='dv_lower.py global RMSNorm only; dv_lower_vec.py supplies QK/RoPE arithmetic contract',calr_local4_preload_entries=len(desc['preload_ranges']),table_payload_installation_observed=None,complete_connected_compile_inventory=None,compile_memory_gib=None,new_QSLOT_dates=None,native_phase=None,reset_first_use=None,four_ME_failures_preserved=[[11,543,672],[12,2232,2459],[16,3883,3625],[20,4567,4447]],full_graph='UNRESOLVED')
dump('analysis.json',summary)
print('PASS source extraction: 400 exact ISA PW beats; 406 unchanged decode commands; 8 Q commands / 64 DD-word contracts / 512 distinct seat contracts; no connected execution claimed.')
if not argparse.ArgumentParser().parse_known_args()[1]==['--extraction-only']:
 print('UNRESOLVED: selected table/operand installation, actual Q publications, source phases/reset epochs and QSLOT absent.');raise SystemExit(2)
