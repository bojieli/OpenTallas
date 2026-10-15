#!/usr/bin/env python3
"""LV6 G3072 core, hierarchical Verilation with the project's RTL FP units.

Same frozen source, top, parameters and unroll limits as
qwen_tp8_fullshape_lv6_build.py (archive 54a3930e lineage), with two changes:
  1. sim_hdc_v41x_fastfp_dpi.sv (C-DPI host-float stand-ins) and its wrapper
     copy sim_qwen_native_current_fastfp_wrap.sv are replaced by
     rtl/hdc/ot_hdc_fastfp.sv: the RTL ot_hdc_fp32_add_fast / mul_fast the
     hardware instantiates (the wrapper qadd/qmul text is identical).
  2. --hierarchical with hier_fp.vlt: each FP unit is its own compiled block,
     so the parent can be compiled optimised (-O<opt>).
"""
import argparse, hashlib, json, subprocess, time, importlib.util
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--opt',default='-O2');p.add_argument('--jobs',default='48');p.add_argument('--G',default='3072')
    p.add_argument('--dpi',action='store_true',help='keep the C-DPI FP stand-ins (speed A/B only)')
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location('frozen_provider',a.source/'tools/qwen_native_fullshape/build_provider.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    src=[Path(s) for s in m.SOURCES]
    if not a.dpi:
        src=[s for s in src if s.name not in('sim_hdc_v41x_fastfp_dpi.sv','sim_qwen_native_current_fastfp_wrap.sv')]
        src.insert(0,a.source/'rtl/hdc/ot_hdc_fastfp.sv')
    vlt=Path(__file__).with_name('hier_fp.vlt')
    a.work.mkdir(parents=True,exist_ok=False)
    pins={str(f):hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in src+[a.source/'rtl/hdc/ot_hdc_isa.svh',vlt,Path(__file__)]}
    cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--build','-j',a.jobs,'--hierarchical','--top-module',m.TOP,
         f'-GG={a.G}','-GW=16','-GIL=8','-GNW=16','-GSU_VEC=1','-GSW=64','-GLV=6',
         '-GHID=4096','-GHALF=64','-GHD=128','-GNATIVE_ATTENTION=1','-GINT8_WEIGHT=1',
         '-GINT8_SCALE_WCS_BASE=1','-GQWEN_FULLSHAPE=1','-GKV_VEC_WRITE_BRIDGE=1',
         '--unroll-count','131072','--unroll-limit','131072','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-TIMESCALEMOD',
         '-I'+str(a.source/'rtl/hdc'),'--Mdir',str(a.work/'obj'),'-CFLAGS',a.opt,'--output-split','20000','--output-split-cfuncs','1000',
         str(vlt),*map(str,src)]
    t=time.monotonic()
    with (a.work/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    (a.work/'receipt.json').write_text(json.dumps({'exit':r.returncode,'seconds':time.monotonic()-t,'command':cmd,'source_sha256':pins,
        'fp_units':'C-DPI stand-ins' if a.dpi else 'RTL rtl/hdc/ot_hdc_fastfp.sv','hierarchical':True,'opt':a.opt},indent=2)+'\n')
    raise SystemExit(r.returncode)
if __name__=='__main__':main()
