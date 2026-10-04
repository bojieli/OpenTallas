"""Source-owned HE/SSX native leaf archive; incremental, no wall/file caps."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/test/s81_native_he_bootstrap/native_leaves.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv','rtl/hdc/v41x/ot_hdc_v41x_hcp.sv',
 'rtl/hdc/ot_hdc_vreduce.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_delay.sv',
 'rtl/hdc/ot_hdc_sfu.sv',
 'rtl/hdc/v41/ot_hdc_fdiv.sv',
 'tools/runtime/dsrom/s81_native_he_bootstrap.cpp',
 'tools/runtime/dsrom/s81_native_he_bootstrap_abi.h',
 'tools/runtime/dsrom/s81_native_he_bootstrap.hpp',
 'tools/runtime/dsrom/s81_minimum_prefix.hpp','tools/runtime/dsrom/s81_minimum_prefix.cpp',
 'tools/runtime/dsrom/s81_minimum_embedding.hpp','tools/runtime/dsrom/s81_minimum_runtime.hpp',
 'tools/runtime/dsrom/s81_embedding_abi.h', 'tools/uarch_model.py',
 'tools/hdc_isa_v41.py','tools/hdc_golden_v41.py',
 'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv',
 'tools/dsrom_s81_native_he_bootstrap_build.py',
 'tools/dsrom_s81_native_he_bootstrap_test.py',
 'results/uarch/dsrom_s81_native_he_bootstrap_20261004/model.json']


def pin(root=ROOT):
 return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in SOURCES}


def build(out,workers):
 out=out.resolve();out.mkdir(parents=True,exist_ok=True)
 pins=pin();obj=out/'obj';obj.mkdir(exist_ok=True)
 model=json.loads((ROOT/'results/uarch/dsrom_s81_native_he_bootstrap_20261004/model.json').read_text())
 record=dict(status='IN_PROGRESS_NATIVE_SOURCE_LEAF_BUILD',source_sha256=pins,model=model,
             output=str(out),workers=workers,wall_limit=None,file_size_limit=None,
             source_scope='HE HW8 fullshapeKCMAX2560 plus actual SUN256 chunk8 reducer; no fullcore or different arithmetic')
 def save(): (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
 save()
 def run(name,cmd):
  record['phase']=name;save()
  with (out/(name+'.log')).open('w') as f:
   result=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  record[name+'_exit_code']=result.returncode;save()
  if result.returncode: raise RuntimeError(name+' failed; retained outputs')
 try:
  run('compiler_version',['verilator','--version'])
  run('generate',['verilator','--cc','--top-module','s81_native_he_bootstrap',
      '--Mdir',str(obj),'--output-split','20000','--output-split-cfuncs','500',
      '-Wno-fatal','-CFLAGS','-fPIC -O1']+[str(ROOT/p) for p in SOURCES if p.endswith('.sv') and 'fastpp_pc21' not in p])
  run('CXX',['make','-C',str(obj),'-f','Vs81_native_he_bootstrap.mk','-j'+str(workers),
             'OPT_FAST=-O1','OPT_SLOW=-O1','OPT_GLOBAL=-O1'])
  env=subprocess.check_output(['verilator','-V'],text=True)
  import re
  home=Path(re.search(r'VERILATOR_ROOT\s*=\s*(\S+)',env)[1])/'include'
  lib=out/'libs81_native_he_bootstrap.so'
  run('link',['g++','-shared','-fPIC','-O1','-std=c++17','-pthread',
      '-I'+str(home),'-I'+str(home/'vltstd'),'-I'+str(obj),
      str(ROOT/'tools/runtime/dsrom/s81_native_he_bootstrap.cpp'),
      str(obj/'Vs81_native_he_bootstrap__ALL.a'),str(home/'verilated.cpp'),
      str(home/'verilated_threads.cpp'),'-o',str(lib)])
  record['library_sha256']=hashlib.sha256(lib.read_bytes()).hexdigest()
  run('native_fullshape_component_test',['python3',str(ROOT/'tools/dsrom_s81_native_he_bootstrap_test.py'),'--library',str(lib),'--out',str(out/'native_test.json')])
  if pins!=pin(): raise ValueError('source changed during native build')
  record['status']='PASS_NATIVE_HE_SSX_COMPONENT_ONLY_NOT_JOINED_PROVIDER'
 except BaseException as error:
  record['status']='FAIL_PRESERVED';record['error']=repr(error);save();raise
 save()


if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True)
 a.add_argument('--workers',type=int,default=2);a.add_argument('--prepare',action='store_true')
 v=a.parse_args()
 if not 1<=v.workers<=2: raise ValueError('reviewed two-worker source leaf allocation')
 if v.prepare:
  v.out.mkdir(parents=True,exist_ok=True)
  (v.out/'source_manifest.json').write_text(json.dumps(pin(),indent=2,sort_keys=True)+'\n')
 else: build(v.out,v.workers)
