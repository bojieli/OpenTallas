"""Install atomic physical-bank receiver links on parent-selected manifest r4.

Requires Nash's actual frozen immutable profile module, source hashes and model.
Missing profile refuses generation; there is no zero mask, host map or READY
fallback. No initializer payload/terminal/reverse is fabricated by this join.
"""
import hashlib,json
from pathlib import Path
from tools.gpu_sys.canonical_qwen_manifest_install import once
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'rtl/model/qwen_hbm_manifest_factory_20261003_r4'
JOIN='rtl/model/qwen_input_bank_barrier_20261003/ot_gpu_qwen_input_bank_barrier.sv'
MODEL='rtl/model/qwen_input_bank_barrier_20261003/model_r2.json'
# One actual packed64 bank/actor interface; no mutable copy of root identity.
LINKS={
 'root_offer_tuple':'issuer_issue_tuple','root_held_tuple':'issuer_publish_tuple','root_held_owner':'issuer_publish_owner',
 'root_busy':'issuer_busy','root_fault':'issuer_fault','root_go_accepted':'actual_root_go_accepted',
 'root_input_terminal_valid':'issuer_input_terminal_valid','root_input_reverse_valid':'issuer_input_reverse_valid','root_frame_retire_valid':'issuer_frame_retire_valid',
 'root_input_terminal_tuple':'issuer_input_terminal_tuple','root_input_reverse_tuple':'issuer_input_reverse_tuple','root_frame_retire_tuple':'issuer_frame_retire_tuple',
 'bank_bound_valid':'source_owner_inputs_bound_valid','bank_live':'source_owner_issued_input_live','bank_started':'source_owner_issued_input_started',
 'bank_fault':'source_owner_fault','bank_barrier_ready':'source_owner_row_barrier_ready','bank_tuple':'source_owner_inputs_bound_tuple','bank_mask':'source_owner_inputs_bound_mask',
 'bank_input_terminal_ready':'source_owner_input_terminal_ready','bank_input_reverse_ready':'source_owner_input_reverse_ready','bank_frame_retire_ready':'source_owner_frame_retire_ready',
 'root_inputs_bound_valid':'issuer_inputs_bound_valid','root_inputs_bound_tuple':'issuer_inputs_bound_tuple','root_inputs_bound_mask':'issuer_inputs_bound_mask','root_row_barrier_ready':'issuer_row_barrier_ready',
 'root_input_terminal_ready':'issuer_input_terminal_ready','root_input_reverse_ready':'issuer_input_reverse_ready','root_frame_retire_ready':'issuer_frame_retire_ready',
 'bank_inputs_bound_ready':'source_owner_inputs_bound_ready','bank_go_accepted':'source_owner_go_accepted','bank_go_tuple':'source_owner_go_tuple',
 'bank_input_terminal_valid':'source_owner_input_terminal_valid','bank_input_reverse_valid':'source_owner_input_reverse_valid','bank_frame_retire_valid':'source_owner_frame_retire_valid',
 'bank_input_terminal_tuple':'source_owner_input_terminal_tuple','bank_input_reverse_tuple':'source_owner_input_reverse_tuple','bank_frame_retire_tuple':'source_owner_frame_retire_tuple',
 'bank_input_terminal_mask':'source_owner_input_terminal_mask','bank_input_reverse_mask':'source_owner_input_reverse_mask',
 'bank_issuer_held_valid':'source_owner_issuer_held_valid','bank_issuer_held_fault':'source_owner_issuer_held_fault','bank_issuer_held_tuple':'source_owner_issuer_held_tuple','bank_issuer_held_owner':'source_owner_issuer_held_owner55','bank_frame_retire_owner':'source_owner_frame_retire_owner',
}
def generate(profile_contract,out):
 """profile_contract is frozen hardware provenance, never runtime ownership.

 Required producer ABI: root_tuple[15295:0] input, profile_valid[63:0] and
 required_banks[4095:0] outputs; ENABLE defaultoff. Nash owns this source.
 """
 c=json.loads(Path(profile_contract).read_text());out=Path(out)
 if out.exists():raise ValueError('fresh additive output required')
 if c.get('source_complete') is not True or c.get('mutable_state_bits')!=0:
  raise ValueError('actual complete immutable source profile required')
 required={'root_tuple':('input',15296),'profile_valid':('output',64),'required_banks':('output',4096)}
 if any((c.get('ports',{}).get(n,{}).get('direction'),c.get('ports',{}).get(n,{}).get('bits'))!=v for n,v in required.items()):
  raise ValueError('source profile actual hardware ABI mismatch')
 if not c.get('source_sha256') or not c.get('model_path'):
  raise ValueError('source-bound profile/model missing')
 for p,h in c['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('profile source changed '+p)
 if hashlib.sha256((ROOT/c['model_path']).read_bytes()).hexdigest()!=c['model_sha256']:
  raise ValueError('priced profile source changed')
 b=json.loads((BASE/'ports.json').read_text());name=b['top']+'.sv';s=(BASE/name).read_text()
 s=once(s,'parameter bit ENABLE_MANIFEST=0)','parameter bit ENABLE_MANIFEST=0,parameter bit ENABLE_BANK_BARRIER=0)')
 # Replace only bank binding/accepted events. ACK/pub stays the actual grouped manifest receiver.
 driven=set(LINKS[n] for n in ['root_inputs_bound_valid','root_inputs_bound_tuple','root_inputs_bound_mask','root_row_barrier_ready','root_input_terminal_ready','root_input_reverse_ready','root_frame_retire_ready','bank_inputs_bound_ready','bank_go_accepted','bank_go_tuple','bank_input_terminal_valid','bank_input_reverse_valid','bank_frame_retire_valid','bank_input_terminal_tuple','bank_input_reverse_tuple','bank_frame_retire_tuple','bank_input_terminal_mask','bank_input_reverse_mask','bank_issuer_held_valid','bank_issuer_held_fault','bank_issuer_held_tuple','bank_issuer_held_owner','bank_frame_retire_owner'])
 lines=s.splitlines()
 for target in driven:
  matches=[i for i,l in enumerate(lines) if l.strip().startswith('assign '+target+'[')]
  if len(matches)!=1:raise ValueError('actual receiver driver changed '+target)
  lines[matches[0]]=''
 s='\n'.join(lines)+'\n'
 # Foreign source-bank frontier uses actual binding offer/current coded holder PC,
 # never the source bank's unrelated execution issuer or a relabelled SM tuple.
 s=once(s,'assign source_owner_next_source_PC[i*11 +: 11]=issuer_issue_tuple[i*239+164 +: 11];',
 'assign source_owner_next_source_PC[i*11 +: 11]=(source_owner_issued_input_live[i] ? source_owner_inputs_bound_tuple[i*239+164 +: 11] : source_owner_bind_tuple[i*239+164 +: 11])==11\'d2047 ? 11\'d0 : (source_owner_issued_input_live[i] ? source_owner_inputs_bound_tuple[i*239+164 +: 11] : source_owner_bind_tuple[i*239+164 +: 11]);')
 extra='''\nwire [63:0] source_profile_valid;wire [4095:0] source_profile_required_banks;
wire [15295:0] source_profile_root_tuple;
wire [63:0] actual_root_go_accepted=(issuer_backend_go_valid & issuer_backend_go_ready) | (issuer_initial_go_valid & issuer_initial_go_ready);
for(genvar p=0;p<64;p=p+1)begin:g_actual_profile_root
 assign source_profile_root_tuple[p*239+:239]=issuer_busy[p] ? issuer_publish_tuple[p*239+:239] : issuer_issue_tuple[p*239+:239];
end
'''
 extra+=c['module']+' #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER)) u_actual_source_profile(\n .root_tuple(source_profile_root_tuple),.profile_valid(source_profile_valid),.required_banks(source_profile_required_banks));\n'
 extra+='ot_gpu_qwen_input_bank_barrier #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER)) u_actual_bank_join(\n .profile_valid(source_profile_valid),.required_banks(source_profile_required_banks),\n '+',\n '.join('.'+p+'('+n+')' for p,n in LINKS.items())+'\n);\n'
 s=once(s,'\nendmodule',extra+'\nendmodule')
 deps=(BASE/'sources.f').read_text().splitlines();oldtop=deps.pop();newtop=str((out/name).relative_to(ROOT));deps.extend([JOIN,*c['source_sha256'],newtop])
 b['source_sha256'].pop(oldtop,None);b['source_sha256'].update(c['source_sha256']);b['source_sha256'][JOIN]=hashlib.sha256((ROOT/JOIN).read_bytes()).hexdigest();b['source_sha256'][newtop]=hashlib.sha256(s.encode()).hexdigest()
 b['atomic_bank_join']=dict(source_profile_module=c['module'],profile_contract_sha256=hashlib.sha256(Path(profile_contract).read_bytes()).hexdigest(),model_sha256=hashlib.sha256((ROOT/MODEL).read_bytes()).hexdigest(),atomic_events=['GO','input terminal','input reverse','frame retirement'],source_release='unchanged dedicated actual native source-retirement path',INITIAL='real caller/payload/terminal/reverse remains mandatory, no generated positive readiness')
 b['full_build_ready']=False;b['unresolved']+=['Actual allbank/profile and initializer native4 connected gates still required; leaf fixture is not fullprogram proof']
 out.mkdir(parents=True);(out/name).write_text(s);(out/'ports.json').write_text(json.dumps(b,indent=2)+'\n');(out/'sources.f').write_text('\n'.join(deps)+'\n');(out/'pin_driver.cpp').write_bytes((BASE/'pin_driver.cpp').read_bytes())
 return out
