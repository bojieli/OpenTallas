"""ONE banked successor of the parent r4 top; no old leaf, host mask or fake ACK.

The standalone immutable profile contract is mandatory, source/hash/model bound.
Generation does not compile or qualify the enclosing engine or INITIAL caller.
"""
import hashlib,json,tempfile
from pathlib import Path
from tools.gpu_sys import canonical_qwen_input_bank_install as B
from tools.gpu_sys.canonical_qwen_manifest_install import once
ROOT=B.ROOT
OLD='rtl/experimental/canonical_qwen_manifest_range_owner_20261003/ot_gpu_qwen_manifest_range_owner.sv'
OWNER='rtl/experimental/canonical_qwen_banked_manifest_owner_20261003/ot_gpu_qwen_banked_manifest_range_owner.sv'
ABI='results/uarch/canonical_qwen_banked_manifest_owner_20261003/ports.json'
JOIN='rtl/model/qwen_banked_atomic_receiver_20261003/ot_gpu_qwen_banked_output_join.sv'
MODEL='rtl/model/qwen_banked_atomic_receiver_20261003/model_r2.json'
OWNER_SHA='eb8a74eb0386fdecf5b3c2b5dc904536e1a2f8d3f7da32a415d823ea5e927f58'
LINKS={
 'profile_valid':'source_profile_valid','required_banks':'source_profile_required_banks',
 'root_busy':'issuer_busy','root_fault':'issuer_fault','root_held_tuple':'issuer_publish_tuple','root_held_owner':'issuer_publish_owner',
 'root_visible_tuple':'issuer_producer_visible_tuple','root_visible_valid':'issuer_producer_visible_valid','root_publish_tuple':'issuer_publish_tuple','root_publish_owner':'issuer_publish_owner','root_publish_mask':'issuer_publish_page_mask','root_publish_valid':'issuer_publish_valid','root_ack_ready':'issuer_rf_range_ack_ready',
 'bank_live':'source_owner_issued_input_live','bank_started':'source_owner_issued_input_started','bank_fault':'source_owner_fault','bank_tuple':'source_owner_inputs_bound_tuple',
 'bank_ack_valid':'source_owner_rf_range_ack_valid','bank_ack_tuple':'source_owner_rf_range_ack_tuple','bank_ack_owner':'source_owner_rf_range_ack_owner','bank_ack_mask':'source_owner_rf_range_ack_page_mask',
 'bank_required_union':'source_owner_required_bank_mask64','bank_required_input':'source_owner_required_input_bank_mask64','bank_required_output':'source_owner_required_output_bank_mask64',
 'bank_visible_ready':'source_owner_producer_visible_ready','bank_publish_ready':'source_owner_publish_ready',
 'root_ack_valid':'issuer_rf_range_ack_valid','root_ack_tuple':'issuer_rf_range_ack_tuple','root_ack_owner':'issuer_rf_range_ack_owner','root_ack_mask':'issuer_rf_range_ack_page_mask',
 'root_visible_ready':'actual_allbank_visible_ready','root_publish_ready':'issuer_publish_ready','root_output_presence':'actual_whole_output_presence',
 'bank_ack_ready':'source_owner_rf_range_ack_ready','bank_visible_valid':'source_owner_producer_visible_valid','bank_visible_tuple':'source_owner_producer_visible_tuple',
 'bank_publish_valid':'source_owner_publish_valid','bank_publish_tuple':'source_owner_publish_tuple','bank_publish_owner':'source_owner_publish_owner','bank_publish_mask':'source_owner_publish_page_mask'}
OUTPUTS=['root_ack_valid','root_ack_tuple','root_ack_owner','root_ack_mask','root_publish_ready','bank_ack_ready','bank_visible_valid','bank_visible_tuple','bank_publish_valid','bank_publish_tuple','bank_publish_owner','bank_publish_mask']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate(profile_contract,out):
 out=Path(out).resolve()
 if digest(ROOT/OWNER)!=OWNER_SHA:raise ValueError('frozen045 banked owner changed')
 model=json.loads((ROOT/MODEL).read_text())
 for p,h in model['source_sha256'].items():
  if digest(ROOT/p)!=h:raise ValueError('priced source changed '+p)
 # Validates actual immutable hardware, including hash/ABI/model; no fallback.
 c=json.loads(Path(profile_contract).read_text())
 if c.get('whole_operation_scope') is not True or c.get('additional_mutable_FF')!=0 or c.get('grants') is not False or c.get('parameter')!={'ENABLE':0}:
  raise ValueError('actual immutable wholeoperation producer required')
 if not isinstance(c.get('source_path'),str) or not isinstance(c.get('source_sha256'),str):raise ValueError('frozen producer source missing')
 normalized=dict(c,source_complete=True,mutable_state_bits=0,source_sha256={c['source_path']:c['source_sha256']})
 with tempfile.TemporaryDirectory(prefix='euclid-exact-profile-') as d:
  adapter=Path(d)/'contract.json';adapter.write_text(json.dumps(normalized))
  B.generate(adapter,out)
 b=json.loads((out/'ports.json').read_text());name=b['top']+'.sv';sv=(out/name).read_text();cpp=(out/'pin_driver.cpp').read_text()
 sv=once(sv,'ot_gpu_qwen_manifest_range_owner #(.ENABLE(ENABLE && ENABLE_MANIFEST),.SM_INDEX(i))','ot_gpu_qwen_banked_manifest_range_owner #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER),.SM_INDEX(i))')
 # The mask ROM is indexed by EXISTING protected B while live, not a changing
 # external bind offer. Before bind, the genuine caller offer is its source.
 sv=once(sv,'.bind_tuple(source_owner_bind_tuple[i*239 +: 239]),',
 '.bind_tuple(source_owner_issued_input_live[i] ? source_owner_inputs_bound_tuple[i*239 +: 239] : source_owner_bind_tuple[i*239 +: 239]),')
 masknames=['required_bank_mask64','required_input_bank_mask64','required_output_bank_mask64']
 spec=json.loads((ROOT/ABI).read_text());decl=[];get=[];con=[]
 for leaf in masknames:
  if spec.get(leaf)!=['output','63:0']:raise ValueError('actual banked ABI changed '+leaf)
  n='source_owner_'+leaf
  b['pins'][n]=dict(direction='output',bits=4096,count=64,leaf_bits=64,block='source_owner',leaf=leaf)
  decl.append(' output wire [4095:0] '+n)
  con.append('.'+leaf+'('+n+'[i*64+:64])')
  get.append(' if(name=="'+n+'") {for(int i=127;i>=0;i--)word(dut.'+n+'[i]);} else')
 sv=once(sv,'\n);\nassign assembly_enabled',',\n'+',\n'.join(decl)+'\n);\nassign assembly_enabled')
 sv=once(sv,' u_source_owner(\n',' u_source_owner(\n '+',\n '.join(con)+',\n')
 lines=sv.splitlines()
 for p in OUTPUTS:
  n=LINKS[p];indices=[i for i,l in enumerate(lines) if l.strip().startswith('assign '+n+'[')]
  if len(indices)!=1:raise ValueError('original local receiver driver changed '+n)
  lines[indices[0]]=''
 sv='\n'.join(lines)+'\n'
 sv=once(sv,'.producer_binding_ready(source_owner_producer_visible_ready),','.producer_binding_ready(actual_allbank_visible_ready),')
 # Issuer uses only ZERO/NONZERO output presence for typed dispatch; each bank
 # retains its exact count and all child bitmaps. No truncation of a global sum.
 sv=once(sv,'.required_output_rows(source_owner_required_output_rows),','.required_output_rows(actual_whole_output_presence),')
 extra='\nwire [63:0] actual_allbank_visible_ready;wire [255:0] actual_whole_output_presence;\n'
 extra+='ot_gpu_qwen_banked_output_join #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER)) u_actual_banked_output_join(\n '+',\n '.join('.'+p+'('+n+')' for p,n in LINKS.items())+'\n);\n'
 sv=once(sv,'\nendmodule',extra+'\nendmodule')
 cpp=once(cpp,' throw std::runtime_error("unknown pin");}','\n'.join(get)+'\n throw std::runtime_error("unknown pin");}')
 deps=(out/'sources.f').read_text().splitlines()
 if deps.count(OLD)!=1:raise ValueError('old leaf source-selection anchor changed')
 deps[deps.index(OLD)]=OWNER;deps.insert(len(deps)-1,JOIN)
 b['source_sha256'].pop(OLD);b['source_sha256'][OWNER]=digest(ROOT/OWNER);b['source_sha256'][JOIN]=digest(ROOT/JOIN)
 top=str((out/name).relative_to(ROOT));b['source_sha256'][top]=hashlib.sha256(sv.encode()).hexdigest()
 b['manifest_contract'].update(owner_module='ot_gpu_qwen_banked_manifest_range_owner',allocator_commit='0455075096f39068260b9acdbd0f3d19ab55ce73',ABI_sha256=digest(ROOT/ABI))
 b['atomic_bank_join'].update(original_profile_contract_sha256=digest(Path(profile_contract)),producer_commit='4c4adbcd7e4345a5852e9379c0e7c297f6449166',output_join_sha256=digest(ROOT/JOIN),complete_receiver_model_sha256=digest(ROOT/MODEL),atomic_events=['GO','ALL banks aggregate RF ACK','ALL banks producer visibility','ALL banks publication','input terminal','input reverse','frame retirement'],immutable_masks=masknames,mask_index='existing coded B full239 while live, genuine offer before bind',output_count='issuer typed ZERO/NONZERO presence only; exact local counts and ALL child page bitmaps remain in each bank',physical_bank='SM_INDEX distinct from full239 executionactor; no tuple relabel')
 b['unresolved']=[x for x in b['unresolved'] if 'remote input-bank' not in x and 'manifest component gate pending' not in x]
 b['unresolved']+=['New combined allbank receiver directed runtime and enclosing actual native/INITIAL acceptance still required; no token/SSFF claim']
 (out/name).write_text(sv);(out/'ports.json').write_text(json.dumps(b,indent=2)+'\n');(out/'sources.f').write_text('\n'.join(deps)+'\n');(out/'pin_driver.cpp').write_text(cpp)
 return out
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--profile-contract',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(generate(a.profile_contract,a.out))
