"""Source-pinned manifest receiver successor of the ONE actual TC/scratch top.

No peer source edits, private clocks, positive grants, inference or full build.
Remote input-bank aggregation/initializer callers remain explicit obligations.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'rtl/model/qwen_hbm_matrix_tc_safety_20261003'
OUT=ROOT/'rtl/model/qwen_hbm_manifest_factory_20261003_r3'
OWNER='rtl/experimental/canonical_qwen_manifest_range_owner_20261003/ot_gpu_qwen_manifest_range_owner.sv'
ABI='results/uarch/canonical_qwen_manifest_range_owner_20261003/ports.json'
MODEL='rtl/model/qwen_hbm_integrated_20261003/issuer/r3/model_r3.json'
ISSUER='rtl/model/qwen_hbm_integrated_20261003/issuer/r3/ot_gpu_qwen_full_issuer_r3.sv'
OLDOWNER='rtl/experimental/canonical_qwen_range_owner_20261003/ot_gpu_qwen_native_range_owner.sv'
OLDISSUER='rtl/model/qwen_hbm_integrated_20261003/issuer/r2/ot_gpu_qwen_full_issuer_r2.sv'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
 if s.count(a)!=1:raise ValueError('pinned receiver anchor changed: '+a[:90])
 return s.replace(a,b)
def generate(out=OUT):
 out=Path(out)
 if out.exists():raise ValueError('fresh additive output directory required')
 model=json.loads((ROOT/MODEL).read_text())
 for p,h in model['source_pins'].items():
  if digest(ROOT/p)!=h:raise ValueError('model input changed: '+p)
 book=json.loads((BASE/'ports.json').read_text());name=book['top']+'.sv'
 sv=(BASE/name).read_text();cpp=(BASE/'pin_driver.cpp').read_text()
 sv=once(sv,'parameter bit ENABLE_TC=0)','parameter bit ENABLE_TC=0,parameter bit ENABLE_MANIFEST=0)')
 sv=once(sv,'ot_gpu_qwen_full_issuer_r2 #(.ENABLE(ENABLE))','ot_gpu_qwen_full_issuer_r3 #(.ENABLE(ENABLE),.ENABLE_TYPED(ENABLE_MANIFEST))')
 sv=once(sv,'ot_gpu_qwen_native_range_owner #(.ENABLE(ENABLE),.SM_INDEX(i))','ot_gpu_qwen_manifest_range_owner #(.ENABLE(ENABLE && ENABLE_MANIFEST),.SM_INDEX(i))')
 additions={};decl=[];assign=[];connections=[]
 spec=json.loads((ROOT/ABI).read_text())
 tapped={'issuer_held_valid':'issuer_busy','issuer_held_fault':'issuer_fault','issuer_held_tuple':'issuer_publish_tuple','issuer_held_owner55':'issuer_publish_owner'}
 for n,p in spec.items():
  if n=='clk':continue
  target='source_owner_'+n
  if target in book['pins']:
   q=book['pins'][target]
   if q['leaf_bits']!=p['width']:raise ValueError('ABI width changed '+n)
   continue
  w=p['width'];direction='output' if n in tapped or n=='workspace_children_drained' else p['direction']
  additions[target]=dict(direction=direction,bits=64*w,count=64,leaf_bits=w,block='source_owner',leaf=n)
  decl.append(f' {direction} wire [{64*w-1}:0] {target}')
  sl=lambda x:x+'[i]' if w==1 else x+f'[i*{w} +: {w}]'
  connections.append(f'.{n}({sl(target)})')
  if n in tapped:assign.append(f' assign {sl(target)}={sl(tapped[n])};')
  if n=='workspace_children_drained':assign.append(f' assign {sl(target)}=scratch_drained[i] && kv_shared_drained;')
 for n,d,w in [('initial_go_valid','output',1),('initial_go_ready','input',1),('initial_go_tuple','output',239),('initial_go_owner','output',55)]:
  target='issuer_'+n;bits=64*w
  # issuer adapter is the existing ONE packed64 wrapper, not a new perSM clock owner.
  additions[target]=dict(direction=d,bits=bits,count=1,leaf_bits=bits,block='issuer',leaf=n)
  decl.append(f' {d} wire [{bits-1}:0] {target}')
 additions['manifest_enabled']=dict(direction='output',bits=1,count=1,leaf_bits=1,block='manifest',leaf='enabled')
 decl.append(' output wire manifest_enabled')
 sv=once(sv,'\n);\nassign assembly_enabled',',\n'+',\n'.join(decl)+'\n);\nassign assembly_enabled')
 sv=once(sv,' u_source_owner(\n',' u_source_owner(\n '+',\n '.join(connections)+',\n')
 sv=once(sv,'begin:g_source_owner\n','begin:g_source_owner\n'+'\n'.join(assign)+'\n')
 sv=once(sv,' u_issuer(\n',' u_issuer(\n .producer_binding_ready(source_owner_producer_visible_ready),\n .required_output_rows(source_owner_required_output_rows),\n .initial_go_valid(issuer_initial_go_valid),.initial_go_ready(issuer_initial_go_ready),\n .initial_go_tuple(issuer_initial_go_tuple),.initial_go_owner(issuer_initial_go_owner),\n')
 sv=once(sv,'assign source_owner_go_accepted[i]=(issuer_backend_go_valid[i] && issuer_backend_go_ready[i]);','assign source_owner_go_accepted[i]=(issuer_backend_go_valid[i] && issuer_backend_go_ready[i]) || (issuer_initial_go_valid[i] && issuer_initial_go_ready[i]);')
 # Both channel aliases carry the unchanged offer tuple. Only the selected real handshake marks GO.
 changed=[]
 for n,w,expr in [('valid',1,'source_owner_workspace_held_valid'),('exclusive',1,'source_owner_workspace_held_valid'),('tuple',239,'source_owner_workspace_held_tuple'),('owner',55,'source_owner_workspace_held_owner55'),('base',10,"'0"),('length',11,"{64{11'd1024}}")]:
  target='scratch_workspace_'+n;bits=64*w
  sv=once(sv,f' input wire [{bits-1}:0] {target}',f' output wire [{bits-1}:0] {target}')
  book['pins'][target]['direction']='output';changed.append(target)
  sv=once(sv,'\nendmodule',f'\nassign {target}={expr};\nendmodule')
 sv=once(sv,'.client_valid(scratch_client_valid[i]),','.client_valid(scratch_client_valid[i] && source_owner_workspace_new_admit[i]),')
 sv=once(sv,'\nendmodule','\nassign manifest_enabled=ENABLE && ENABLE_MANIFEST;\nendmodule')
 cpp='\n'.join(line for line in cpp.splitlines() if not any(f'if(name=="{n}"){{auto v=' in line for n in changed))+'\n'
 get=[];set_=[]
 for n,p in additions.items():
  b=p['bits'];getter=f'word(dut.{n});' if b<=32 else (f'word(uint32_t(dut.{n}>>32));word(uint32_t(dut.{n}));' if b<=64 else f'for(int i={(b+31)//32-1};i>=0;i--)word(dut.{n}[i]);')
  get.append(f' if(name=="{n}"){{{getter}}} else')
  if p['direction']=='input':
   setter=f'dut.{n}=uint64_t(v[0])|(uint64_t(v[1])<<32);' if b<=64 else f'for(unsigned i=0;i<v.size();i++)dut.{n}[i]=v[i];'
   set_.append(f' if(name=="{n}"){{auto v=unpack(value,{b});{setter}std::cout<<"OK";}} else')
 cpp=once(cpp,' throw std::runtime_error("unknown pin");}','\n'.join(get)+'\n throw std::runtime_error("unknown pin");}')
 cpp=once(cpp,' throw std::runtime_error("unknown/output pin");}','\n'.join(set_)+'\n throw std::runtime_error("unknown/output pin");}')
 deps=(BASE/'sources.f').read_text().splitlines();oldtop=deps[-1]
 for old,new in [(OLDOWNER,OWNER),(OLDISSUER,ISSUER)]:
  if deps.count(old)!=1:raise ValueError('source-selection changed '+old)
  deps[deps.index(old)]=new;book['source_sha256'].pop(old,None)
  book['source_sha256'][new]=digest(ROOT/new)
 top=str((out/name).relative_to(ROOT));deps[-1]=top
 book['source_sha256'].pop(oldtop,None);book['source_sha256'][top]=hashlib.sha256(sv.encode()).hexdigest()
 book['pins'].update(additions)
 book['manifest_contract']=dict(owner_module='ot_gpu_qwen_manifest_range_owner',allocator_commit='50a1cbbf502eea9536a020889af7e9b35b0e0ed0',ABI_sha256=digest(ROOT/ABI),issuer_module='ot_gpu_qwen_full_issuer_r3',initial_channel='issuer_initial_go_* separate from native engine GO',workspace='coded issuer held root matched to actual binding',same_clock=True,provider_bank='physicalRF rank/SM kept distinct from execution tuple rank/SM')
 book['receiver_model_sha256']=digest(ROOT/MODEL)
 book['full_build_ready']=False;book['token_qualified']=False;book['physical_qualified']=False
 book['unresolved']+=['Actual manifest component gate pending at source selection','Whole root all remote input-bank GO/terminal/reverse barrier aggregation remains open','Real INITIAL provider caller/full-visible/all-page writes remain open','Genuine native4 handler enrollment and measured token remain open','Conservative global router drain calendar and loaded receiver timing unknown']
 out.mkdir(parents=True);(out/name).write_text(sv);(out/'ports.json').write_text(json.dumps(book,indent=2)+'\n');(out/'sources.f').write_text('\n'.join(deps)+'\n');(out/'pin_driver.cpp').write_text(cpp)
 return out
if __name__=='__main__':print(generate())
