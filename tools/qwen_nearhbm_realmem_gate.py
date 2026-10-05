#!/usr/bin/env python3
"""Build only the new REAL_MEM component; link the passed nearHBM model archive."""
import argparse, hashlib, json, os, re, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv',
 'rtl/hdc/kv/ot_qwen_hbm_model_ack.sv','rtl/hdc/nearhbm/ot_qwen_nearhbm_row_sectors.sv',
 'rtl/hdc/nearhbm/ot_qwen_nearhbm_realmem_service.sv','rtl/test/qwen_sys/realmem/ot_qwen_nearhbm_realmem_tb.sv',
 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--work',type=Path,required=True);a.add_argument('--reuse',type=Path,required=True);a.add_argument('--vectors',type=Path,required=True);a.add_argument('--verilator',required=True);a.add_argument('--jobs',type=int,default=4);o=a.parse_args()
 w=o.work.resolve();reuse=o.reuse.resolve();v=o.vectors.resolve()
 if w.exists():a.error('immutable work path already exists')
 w.mkdir(parents=True);obj=w/'obj_mem';obj.mkdir();pub=w/'public.vlt'
 pub.write_text('`verilator_config\npublic_flat_rw -module "ot_qwen_hbm_model_ack" -var "mem"\n')
 inputs=[*(ROOT/p for p in FILES),ROOT/'rtl/test/qwen_sys/realmem/qwen_nearhbm_realmem.cpp',ROOT/'tools/runtime/qwen_combined/fullshape_context.hpp',Path(__file__)]
 pinned={str(p.relative_to(ROOT)):sha(p) for p in inputs}
 arch=reuse/'Vot_qwen_nearhbm_sys_tb__ALL.a'
 # The archive is from the actual successful early-replay build, kept intact.
 if not arch.is_file():a.error('passed nearHBM archive required')
 rec={'status':'pending','scope':'HD128 R8 context129/position128 actual memory-connected attention; not fullprogram token/physical adoption','source_sha256':pinned,'reused_archive_sha256':sha(arch),'vector_sha256':{p.name:sha(p) for p in v.iterdir() if p.is_file()},'steps':[]}
 (w/'manifest.json').write_text(json.dumps(rec,indent=2)+'\n')
 def run(name,cmd):
  t=time.monotonic()
  with (w/(name+'.log')).open('w') as log:r=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  rec['steps'].append({'name':name,'returncode':r.returncode,'seconds':time.monotonic()-t});(w/(name+'.exit')).write_text(str(r.returncode)+'\n')
  if r.returncode:raise RuntimeError(name+' failed; original log retained')
 try:
  run('build',[o.verilator,'--cc','--build','-j',o.jobs,'-O2','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-MULTIDRIVEN','-Wno-TIMESCALEMOD','--top-module','ot_qwen_nearhbm_realmem_tb','--prefix','Vmem','--Mdir',obj,pub,*(ROOT/p for p in FILES)])
  # Resolve the real generated public HBM arrays; no guessed fallback memory.
  hdr=(obj/'Vmem___024root.h').read_text();names=[]
  for s in range(4):
   found=re.findall(r'\b(\w*g_hbm__BRA__'+str(s)+r'__KET__\w*__DOT__mem)\b',hdr)
   if len(set(found))!=1:raise RuntimeError('missing or ambiguous actual HBM array '+str(s))
   names.append(found[0])
  access='#pragma once\nstatic uint32_t& mem_word(Vmem& m,int s,int a,int w){switch(s){\n'+''.join(f'case {s}:return m.rootp->{name}[a][w];\n' for s,name in enumerate(names))+'default:std::abort();}}\n'
  (w/'mem_access.hpp').write_text('#include <cstdlib>\n'+access)
  vr=re.search(r'VERILATOR_ROOT\s*=\s*(\S+)',subprocess.check_output([o.verilator,'-V'],text=True)).group(1)
  src=ROOT/'rtl/test/qwen_sys/realmem/qwen_nearhbm_realmem.cpp'
  exe=w/'connected';incs=[f'-I{x}' for x in [obj,reuse,w,ROOT/'tools/runtime/qwen_combined',Path(vr)/'include',Path(vr)/'include/vltstd']]
  run('link',['g++','-std=c++20','-O1','-pthread',*incs,src,'-Wl,--start-group',obj/'Vmem__ALL.a',arch,
   reuse/'sim_nhb_fp_lat_dpi.o',reuse/'sim_hdc_v41x_fastfp_dpi.o','-Wl,--end-group',Path(vr)/'include/verilated.cpp',Path(vr)/'include/verilated_dpi.cpp',Path(vr)/'include/verilated_threads.cpp','-o',exe])
  run('context',[exe,v]);r=json.loads((w/'context.log').read_text().strip().splitlines()[-1]);rec['measurement']=r;rec['status']=r['status'];rec['binary_sha256']=sha(exe)
 except Exception as e:rec['status']='fail';rec['error']=str(e)
 rec['source_stable']=pinned=={str(p.relative_to(ROOT)):sha(p) for p in inputs};rec['reused_archive_stable']=rec['reused_archive_sha256']==sha(arch)
 if not rec['source_stable'] or not rec['reused_archive_stable']:rec['status']='fail'
 (w/'result.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'status':rec['status'],'measurement':rec.get('measurement'),'error':rec.get('error')}),flush=True)
 return 0 if rec['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
