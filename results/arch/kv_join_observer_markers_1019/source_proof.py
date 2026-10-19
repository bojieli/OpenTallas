import pathlib,subprocess,json,hashlib
w=pathlib.Path(__file__).resolve().parents[3]
d=w/'results/arch/kv_native_owner_join_component_1019/private'
b=w/'rtl/qwen_sys/host_integrated_20261014'
checks={}
def check(name,value):
 checks[name]=bool(value)
 assert value,name
def baseline(path):
 return subprocess.check_output(['git','-C',str(w),'show','d93476b97:'+str(path.relative_to(w))],text=True)
s=(d/'ot_host_if_pb2_observed_rc.sv').read_text()
check('scheduler_same_existing_observer_always', 'always @(posedge clk or negedge retained_reset_n)begin' in s)
check('scheduler_retire_marker_exact_source', 'step_retire_native_valid<=ENABLE_NATIVE_OWNER_JOIN && pending_native_valid;' in s)
check('scheduler_cq_marker_exact_saved_source', 'cq_native_valid_observed<=ENABLE_NATIVE_OWNER_JOIN && cq_saved_native_valid;' in s)
t=s.replace(' output reg step_retire_native_valid,cq_native_valid_observed,\n','').replace('step_retire_native_valid<=0;cq_native_valid_observed<=0;','').replace('   // Marker and observer tuple sample identical pre-edge source ownership.\n   cq_native_valid_observed<=ENABLE_NATIVE_OWNER_JOIN && cq_saved_native_valid;\n   step_retire_native_valid<=ENABLE_NATIVE_OWNER_JOIN && pending_native_valid;\n','')
check('scheduler_every_original_byte_reconstructs',t==baseline(d/'ot_host_if_pb2_observed_rc.sv'))
for mod in ['qkd_host_if_pins_observed_rc','qkd_host_tp8_coordinator_rc','qkd_host_coordinator_services_rc']:
 p=d/(mod+'.sv');s=p.read_text()
 t=s.replace(' output wire step_retire_native_valid,cq_native_valid_observed,\n','').replace(' input wire step_retire_native_valid,cq_native_valid_observed,\n','').replace(' wire step_retire_native_valid,cq_native_valid_observed;\n','').replace('.step_retire_native_valid(step_retire_native_valid),.cq_native_valid_observed(cq_native_valid_observed),','')
 t=t.replace('qkd_host_peer_coordinator_codec_rc #(.ENABLE_NATIVE_OWNER_JOIN(ENABLE_NATIVE_OWNER_JOIN))','qkd_host_peer_coordinator_codec').replace('step_retire_v && (!ENABLE_NATIVE_OWNER_JOIN || step_retire_native_valid)','step_retire_v').replace('cq_commit_v && (!ENABLE_NATIVE_OWNER_JOIN || cq_native_valid_observed)','cq_commit_v')
 check(mod+'_only_approved_wiring_delta',t==baseline(p))
s=(d/'qkd_host_peer_rank_codec_rc.sv').read_text()
check('rank_retire_marker_same_packet_capture','retire_word[90]<=step_retire_cq;retire_word[91]<=ENABLE_NATIVE_OWNER_JOIN && step_retire_native_valid;' in s)
check('rank_cq_marker_same_packet_capture','cq_word[89:72]<=cq_token;cq_word[90]<=ENABLE_NATIVE_OWNER_JOIN && cq_native_valid_observed;' in s)
t=s.replace('qkd_host_peer_rank_codec_rc #(parameter[2:0]RANK=0, parameter integer ENABLE_NATIVE_OWNER_JOIN=0)','qkd_host_peer_rank_codec #(parameter[2:0]RANK=0)').replace(' input wire step_retire_native_valid,cq_native_valid_observed,\n','').replace('retire_word[91]<=ENABLE_NATIVE_OWNER_JOIN && step_retire_native_valid;','').replace('cq_word[90]<=ENABLE_NATIVE_OWNER_JOIN && cq_native_valid_observed;','')
check('rank_default_zero_reserved_writes_reconstruct_original',t==(b/'qkd_host_peer_rank_codec.sv').read_text())
s=(d/'qkd_host_peer_coordinator_codec_rc.sv').read_text()
check('coordinator_retire_marker_same_output_capture','else begin step_retire_native_valid<=ENABLE_NATIVE_OWNER_JOIN && d[91];step_retire_v<=1;' in s)
check('coordinator_cq_marker_same_output_capture','else begin cq_native_valid_observed<=ENABLE_NATIVE_OWNER_JOIN && d[90];cq_commit_v<=1;' in s)
t=s.replace('qkd_host_peer_coordinator_codec_rc #(parameter integer ENABLE_NATIVE_OWNER_JOIN=0)','qkd_host_peer_coordinator_codec').replace(' output reg step_retire_native_valid,cq_native_valid_observed,\n','').replace('   step_retire_native_valid<=0;cq_native_valid_observed<=0;\n','').replace('(ENABLE_NATIVE_OWNER_JOIN ? d[511:92]!=0 : d[511:91]!=0)','d[511:91]!=0').replace('(ENABLE_NATIVE_OWNER_JOIN ? d[511:91]!=0 : d[511:90]!=0)','d[511:90]!=0').replace('step_retire_native_valid<=ENABLE_NATIVE_OWNER_JOIN && d[91];','').replace('cq_native_valid_observed<=ENABLE_NATIVE_OWNER_JOIN && d[90];','')
check('coordinator_default_semantics_reconstruct_original',t==(b/'qkd_host_peer_coordinator_codec.sv').read_text())
freeze=json.loads((pathlib.Path(__file__).parent/'pre_edit_freeze.json').read_text())
for path,digest in freeze['source_sha256'].items():
 if path.startswith('rtl/'):
  check('public_unchanged_'+path,hashlib.sha256((w/path).read_bytes()).hexdigest()==digest)
report={'kind':'structural source identities, NOT simulation/equivalence/physical qualification','checks':checks,'private_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob('*.sv'))},'new_declared_bits':4,'new_live_repurposed_selected_rank0_bits':2,'new_live_repurposed_unpruned_eight_rank_bits':16,'event_indexed_bits':2912,'runtime_required':['native marker same source edge and serialized exact payload','raw_unready0 missing binding independently faults join','wrong marker cannot produce native POST/success','NO_NATIVE AXI report drains without native state mutation']}
(pathlib.Path(__file__).parent/'source_proof.json').write_text(json.dumps(report,indent=2)+'\n')
print('SOURCE_IDENTITY_PASS checks='+str(len(checks)))
