"""Finish the existing canonical assembly with Pauli's actual sources.
No new engine/ABI; all authority inputs become physical outputs of this top.
"""
import json,hashlib
from pathlib import Path
from tools.gpu_sys.canonical_qwen_native_aperture_cluster import ports
from tools.gpu_sys.canonical_qwen_manifest_install import once
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'rtl/model/qwen_hbm_native_aperture_factory_20261003_r6_bound_final'
CTRL='rtl/gpu/native/ot_gpu_native_primitive_controller_authority.sv'
ROM='rtl/gpu/native/ot_gpu_native_shape_authority.sv'
DEST=ROOT/'rtl/model/qwen_hbm_native_final_join_20261003'

def generate():
 b=json.loads((BASE/'ports.json').read_text());sv=(BASE/(b['top']+'.sv')).read_text();cpp=(BASE/'pin_driver.cpp').read_text();extra=[];decl=[];added={}
 def sl(n,w):return n+'[i]' if w==1 else n+f'[i*{w}+:{w}]'
 def physical(n):
  p=b['pins'][n];assert p['direction']=='input' and not p.get('host_writable'),n
  svline=f" input wire [{p['bits']-1}:0] {n}"
  nonlocal sv
  sv=once(sv,svline,svline.replace(' input',' output',1));p['direction']='output'
 for n,p in list(b['pins'].items()):
  if n.startswith('native_aperture_') and p['direction']=='input' and not p.get('host_writable'):physical(n)
 # EXACT one serialized source-only ROM, fed retained cursor keys.
 rm={n:'native_aperture_'+n for n in ports(ROOT/ROM)}
 rm.update(source_valid='native_aperture_source_cursor_valid',source_tuple='native_aperture_authority_tuple',source_sequence='native_aperture_authority_sequence')
 extra.append('ot_gpu_native_shape_authority #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER && ENABLE_NATIVE_APERTURES),.BASE_FILE("results/uarch/qwen_native_shape_authority_20261003/shape_base.mem"),.PROFILE_FILE("results/uarch/qwen_native_shape_authority_20261003/shape_profile.mem"),.DESCRIPTOR_FILE("results/uarch/qwen_native_primitive_control_20261003/descriptor.mem"),.PC_TEMPLATE_FILE("results/uarch/qwen_native_primitive_control_20261003/pc_templates.mem")) u_native_source_ROM(\n '+',\n '.join('.'+n+'('+rm[n]+')' for n in ports(ROOT/ROM))+'\n);')
 # Actual controller authority/RF observations: no host authority write.
 m={'clk':'stream_clk','power_on_reset_n':'source_owner_por_n[i]','warm_reset':'source_owner_warm_reset[i]'}
 for n in ['authority_valid','authority_tuple','authority_owner','authority_PC','authority_shape_sha','authority_source_slots','authority_source_owners','authority_result_slots','authority_result_owner','source_owner_held','result_owner_held','output_visible']:
  alias=n.replace('authority_shape_sha','authority_shape_sha')
  m[n]=sl('native_aperture_'+alias,ports(ROOT/CTRL)[n]['bits'])
 for n,v in {'authority_descriptor':'source_descriptor','authority_source_types':'source_types','authority_operands':'source_operands','authority_signed_i8_mask':'source_signed_i8_mask','authority_source_vector_mask':'source_vector_mask','authority_source_counts':'source_counts','visible_tuple':'authority_tuple','visible_owner':'authority_owner'}.items():m[n]=sl('native_aperture_'+v,ports(ROOT/CTRL)[n]['bits'])
 for n,v in {'busy':'actor_busy','fault':'actor_fault','host_rd_valid':'actor_rd_valid','host_rd_ready':'actor_rd_ready','host_a':'actor_a','host_b':'actor_b','host_wr_valid':'actor_wr_valid','host_wr_ready':'actor_wr_ready','host_dst':'actor_dst','host_wdata':'actor_wdata','host_owner':'actor_wowner','host_rsp_valid':'actor_rsp_valid','host_rsp_ready':'actor_rsp_ready','host_rsp_a':'actor_rsp_a','host_rsp_b':'actor_rsp_b','host_ack_valid':'actor_ack_valid','host_ack_ready':'actor_ack_ready','host_ack_slot':'actor_ack_slot','host_ack_owner':'actor_ack_owner'}.items():m[n]=sl('native_aperture_rfroute_'+v,ports(ROOT/CTRL)[n]['bits'])
 for n in ['host_read_operand','host_read_page','host_write_page']:m[n]=sl('native_aperture_controller_'+n.removeprefix('host_'),ports(ROOT/CTRL)[n]['bits'])
 for n,p in ports(ROOT/CTRL).items():
  if n in m:continue
  # EXTERNAL_OPCODE_MASK=0 and installed mask 0..37 covers local/fp branches;
  # external service is not selected and cannot grant any command.
  if n.startswith('external_') and p['direction']=='input':m[n]="'0";continue
  target='native_controller_'+n;w=p['bits'];decl.append(f" {p['direction']} wire [{64*w-1}:0] {target}")
  added[target]=dict(direction=p['direction'],bits=64*w,count=64,leaf_bits=w,leaf=n,block='native_controller',host_writable=p['direction']=='input')
  m[n]=sl(target,w)
 extra+=['for(genvar i=0;i<64;i=i+1)begin:actual_native_controllers','ot_gpu_native_primitive_controller_authority #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER && ENABLE_NATIVE_APERTURES),.EXTERNAL_OPCODE_MASK(0),.DESCRIPTOR_FILE("results/uarch/qwen_native_primitive_control_20261003/descriptor.mem"),.PC_TEMPLATE_FILE("results/uarch/qwen_native_primitive_control_20261003/pc_templates.mem")) u_controller(\n '+',\n '.join('.'+n+'('+m[n]+')' for n in ports(ROOT/CTRL))+'\n);']
 for role,prefix in [('terminal','result'),('reverse','reverse')]:
  extra.append('assign native_aperture_'+role+'_accept[i]=native_controller_'+prefix+'_valid[i] && native_controller_'+prefix+'_ready[i];')
  for field,w in [('tuple',239),('owner',55),('sequence',64)]:extra.append('assign '+sl('native_aperture_'+role+'_'+field,w)+'='+sl('native_controller_'+prefix+'_'+field,w)+';')
 # Visibility is local private RF, not root publication: both actual W4 mirror
 # ACKs are retained in the collector's coded state, and physical child/read
 # debt must drain while the captured result lease remains held.
 extra+=['wire [5:0] result_bank=native_aperture_authority_result_bank[i*6+:6];',
 'wire local_result_written=u_actual_native_apertures.actual_collectors[i].u_collector.clean && u_actual_native_apertures.actual_collectors[i].u_collector.c[1060] && (!u_actual_native_apertures.actual_collectors[i].u_collector.c[636] || u_actual_native_apertures.actual_collectors[i].u_collector.c[1061]);',
 'assign native_aperture_visibility_valid[i]=native_aperture_authority_valid[i] && native_aperture_result_owner_held[i] && local_result_written && native_aperture_rfroute_bank_routes_drained[result_bank] && rfdrain_w6_local_RF_empty[result_bank] && !tc_busy[result_bank] && !tc_fault[result_bank] && !sm_identity_fault[result_bank];']
 for field,w in [('tuple',239),('owner',55),('sequence',64)]:extra.append('assign '+sl('native_aperture_visibility_'+field,w)+'='+sl('native_aperture_authority_'+field,w)+';')
 extra.append('end')
 sv=once(sv,'\n);\nassign assembly_enabled',',\n'+',\n'.join(decl)+'\n);\nassign assembly_enabled');sv=once(sv,'\nendmodule','\n'+'\n'.join(extra)+'\nendmodule')
 # Same existing RPC driver syntax: expose actual command/accept pins only.
 gets=[];sets=[]
 for n,p in added.items():
  w=p['bits'];get=f'word(dut.{n});' if w<=32 else f'word(uint32_t(dut.{n}>>32));word(uint32_t(dut.{n}));' if w<=64 else f'for(int i={(w+31)//32-1};i>=0;i--)word(dut.{n}[i]);'
  gets.append(f' if(name=="{n}"){{{get}}} else')
  if p['host_writable']:
   setv=f'dut.{n}=v[0];' if w<=32 else f'dut.{n}=uint64_t(v[0])|(uint64_t(v[1])<<32);' if w<=64 else f'for(unsigned i=0;i<v.size();i++)dut.{n}[i]=v[i];'
   sets.append(f' if(name=="{n}"){{auto v=unpack(value,{w});{setv}std::cout<<"OK";}} else')
 cpp=once(cpp,' throw std::runtime_error("unknown pin");}','\n'.join(gets)+'\n throw std::runtime_error("unknown pin");}');cpp=once(cpp,' throw std::runtime_error("unknown/output pin");}','\n'.join(sets)+'\n throw std::runtime_error("unknown/output pin");}')
 deps=(BASE/'sources.f').read_text().splitlines();oldtop=deps.pop();more=(ROOT/'results/uarch/qwen_native_primitive_control_20261003/sources.f').read_text().splitlines();more=[p for p in more if p!='rtl/gpu/native/ot_gpu_native_primitive_controller.sv'];more +=['rtl/gpu/native/ot_gpu_native_conversion_i8.sv',CTRL,ROM]
 for p in more:
  if p not in deps:deps.append(p)
 top=str((DEST/(b['top']+'.sv')).relative_to(ROOT));deps.append(top)
 b['source_sha256'].pop(oldtop);b['source_sha256'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in deps if p!=top});b['source_sha256'][top]=hashlib.sha256(sv.encode()).hexdigest();b['pins'].update(added)
 for p in ['rtl/gpu/native/ot_gpu_native_shape_authority_abi.svh','results/uarch/qwen_native_shape_authority_20261003/shape_base.mem','results/uarch/qwen_native_shape_authority_20261003/shape_profile.mem','results/uarch/qwen_native_shape_authority_20261003/model.json','results/uarch/qwen_native_primitive_control_20261003/descriptor.mem','results/uarch/qwen_native_primitive_control_20261003/pc_templates.mem']:
  b['source_sha256'][p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
 b['native_aperture_contract']['physical_profile_and_controller_installed']=True
 b['native_controller_contract']=dict(actual_module='ot_gpu_native_primitive_controller_authority',count=64,profile_module='ot_gpu_native_shape_authority',profile_services=1,external_opcode_mask=0,PROGRAM_SHA='ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354',private_visibility='actual coded per-page common ACKs + real RF/route drain + captured result lease; not whole output publication')
 b['unresolved']=[x for x in b['unresolved'] if not x.startswith('Physical producer input native_aperture_')]
 b['full_build_ready']=True # source-selected assembly only; numerical qualification remains runtime
 b['native_aperture_contract']['full_build_ready']=True
 b['native_aperture_contract']['missing']=''
 b['native_aperture_contract']['runtime_qualified']=False
 DEST.mkdir(exist_ok=True);(DEST/(b['top']+'.sv')).write_text(sv);(DEST/'ports.json').write_text(json.dumps(b,indent=2)+'\n');(DEST/'sources.f').write_text('\n'.join(deps)+'\n');(DEST/'pin_driver.cpp').write_text(cpp)
 return DEST
if __name__=='__main__':print(generate())
