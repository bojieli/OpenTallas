"""Emit genuine TC instances into the actual scratch+range-owner assembly.

No engine leaf or peer mux modification, arithmetic, reset, build or simulation.
The selected source operator model is a prerequisite; this is an additive
connection of the already sized full SM engine, not another optional topology.
"""
import argparse,hashlib,json,re
from pathlib import Path
from tools.gpu_sys.canonical_qwen_matrix_tc_pins import FIELDS,PARAMS,SOURCE,select_engine_sources
from tools.hbm_accel_epilogue_ha8 import ENGINE_DEPENDENCIES

DEFAULT_BASE='rtl/model/qwen_hbm_connected_factory_20261003'
DEFAULT_OUT='rtl/model/qwen_hbm_matrix_tc_factory_20261003'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(s,old,new):
 if s.count(old)!=1:raise ValueError('actual source join anchor changed: '+old[:80])
 return s.replace(old,new)

def generate(root,base,out):
 root=Path(root).resolve();base=Path(base).resolve();out=Path(out)
 out=(out if out.is_absolute() else root/out).resolve()
 if out.exists():raise ValueError('new additive output directory required')
 book=json.loads((base/'ports.json').read_text());topname=book['top']+'.sv'
 source=(base/topname).read_text();cpp=(base/'pin_driver.cpp').read_text()
 model=root/'results/uarch/qwen_matrix_scratch_adapter_20261003/tc_model_ready.json'
 priced=json.loads(model.read_text())
 if priced['parameters']!=PARAMS or sha(root/SOURCE)!=priced['source_pins'][SOURCE]:
  raise ValueError('model before source install: actual TC source/parameters changed')
 if book['inventory'].get('source_owner_count')!=64 or book['inventory'].get('scratch_client_mux_count')!=64:
  raise ValueError('actual64 source owners and sole64 scratch mux prerequisite')
 if 'matrix_TC_contract' in book or any(n.startswith('tc_') for n in book['pins']):
  raise ValueError('TC already installed, no duplicate emitter')
 selected=select_engine_sources(root)
 if selected['module']!='ot_gpu_sm_q' or selected['parameters']!={}:raise ValueError('baseline engine selection')
 source=once(source,'parameter bit ENABLE_SCRATCH_CLIENT=0)',
                     'parameter bit ENABLE_SCRATCH_CLIENT=0,parameter bit ENABLE_TC=0)')
 declarations=[' output wire tc_enabled']
 newpins={}
 for n,(direction,w) in FIELDS.items():
  target='tc_'+n;declarations.append(f' {direction} wire [{64*w-1}:0] {target}')
  newpins[target]=dict(direction=direction,bits=64*w,count=64,leaf_bits=w,block='tc',leaf=n)
 newpins['tc_enabled']=dict(direction='output',bits=1,count=1,leaf_bits=1,block='tc',leaf='enabled')
 source=once(source,'\n);\nassign assembly_enabled',',\n'+',\n'.join(declarations)+'\n);\nassign assembly_enabled')
 connections=['.clk(stream_clk)', '.rst_n(sm_rst_n[i])']
 for n,(direction,w) in FIELDS.items():
  if n=='consume_valid':continue
  connections.append(f'.{n}(tc_{n}'+('[i]' if w==1 else f'[i*{w} +: {w}]')+')')
 params=','.join(f'.{n}({v})' for n,v in PARAMS.items())
 instances='\nassign tc_enabled=ENABLE && ENABLE_TC;\n'
 instances+='for(genvar i=0;i<64;i=i+1)begin:g_actual_tc\n if(ENABLE && ENABLE_TC)begin:g_enabled\n'
 instances+=f' ot_gpu_sm_q #({params}) u_sm(\n '+',\n '.join(connections)+'\n );\n'
 instances+=' assign tc_consume_valid[i]=u_sm.w_valid && u_sm.w_ready;\n end else begin:g_disabled\n'
 for n,(d,w) in FIELDS.items():
  if d=='output':instances+=f" assign tc_{n}"+('[i]' if w==1 else f'[i*{w} +: {w}]')+"='0;\n"
 instances+=' end\nend\n'
 source=once(source,'\nendmodule',instances+'\nendmodule')
 # Preserve existing HELLO and clock owner; constructor checks actual tc_enabled.
 get=[];set_=[]
 for n,p in newpins.items():
  b=p['bits'];getter=f'word(dut.{n});' if b<=32 else (f'word(uint32_t(dut.{n}>>32));word(uint32_t(dut.{n}));' if b<=64 else f'for(int i={(b+31)//32-1};i>=0;i--)word(dut.{n}[i]);')
  get.append(f' if(name=="{n}"){{{getter}}} else')
  if p['direction']=='input':
   setter=f'dut.{n}=uint64_t(v[0])|(uint64_t(v[1])<<32);' if b<=64 else f'for(unsigned i=0;i<v.size();i++)dut.{n}[i]=v[i];'
   set_.append(f' if(name=="{n}"){{auto v=unpack(value,{b});{setter}std::cout<<"OK";}} else')
 cpp=once(cpp,' throw std::runtime_error("unknown pin");}','\n'.join(get)+'\n throw std::runtime_error("unknown pin");}')
 cpp=once(cpp,' throw std::runtime_error("unknown/output pin");}','\n'.join(set_)+'\n throw std::runtime_error("unknown/output pin");}')
 deps=(base/'sources.f').read_text().splitlines();oldtop=deps[-1]
 if book['source_sha256'].get(oldtop)!=sha(base/topname):raise ValueError('actual base top source pin changed')
 if Path(oldtop).name!=topname:raise ValueError('actual source list top ordering')
 deps=deps[:-1]
 # Reuse byte-identical installed definitions, refuse a second differing FPU/SRAM.
 for dep in [*ENGINE_DEPENDENCIES,SOURCE]:
  aliases=[p for p in deps if Path(p).name==Path(dep).name]
  if len(aliases)>1:raise ValueError('ambiguous engine dependency '+dep)
  if aliases:
   if (root/aliases[0]).read_bytes()!=(root/dep).read_bytes():raise ValueError('shared engine definition differs '+dep)
  else:
   if not (root/dep).is_file():raise ValueError('actual engine dependency missing '+dep)
   deps.append(dep)
 top=str((out/topname).relative_to(root));deps.append(top)
 for dep in deps[:-1]:
  expected=book['source_sha256'].get(dep)
  if expected is not None and sha(root/dep)!=expected:raise ValueError('actual installed source pin changed '+dep)
  book['source_sha256'][dep]=sha(root/dep)
 book['source_sha256'].pop(oldtop,None)
 book['source_sha256'][top]=hashlib.sha256(source.encode()).hexdigest()
 book['pins'].update(newpins)
 book['matrix_TC_contract']=dict(module='ot_gpu_sm_q',parameters=PARAMS,
  source_sha256=sha(root/SOURCE),consume_tap='u_sm.w_valid && u_sm.w_ready')
 book['inventory'].update(native_TC_count=64,native_TC_memory_macros=64*21,
                          duplicate_scratch_macros=0)
 book['matrix_TC_model_sha256']=sha(model)
 book['physical_qualified']=False;book['token_qualified']=False;book['full_build_ready']=False
 book['unresolved']+=['Nash complete input census, grouped outputs, typed zero RF output and actual workspace grants',
  'Native4 provider/dispatcher enrollment and whole saved-GO visibility/terminal/reverse',
  'TC memory/capture protection and loaded clock/setup/hold/route remain unqualified']
 out.mkdir(parents=True)
 (out/topname).write_text(source);(out/'pin_driver.cpp').write_text(cpp)
 (out/'ports.json').write_text(json.dumps(book,indent=2)+'\n');(out/'sources.f').write_text('\n'.join(deps)+'\n')
 return out

def main():
 a=argparse.ArgumentParser();a.add_argument('--base',type=Path,default=Path(DEFAULT_BASE));a.add_argument('--out',type=Path,default=Path(DEFAULT_OUT));args=a.parse_args()
 root=Path(__file__).resolve().parents[2]
 print(generate(root,root/args.base,args.out))
if __name__=='__main__':main()
