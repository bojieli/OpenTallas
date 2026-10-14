#!/usr/bin/env python3
"""Frozen full-G3072 provider successor with real 4096-element reduction capacity."""
import argparse, importlib.util, hashlib, json, subprocess, time
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    spec=importlib.util.spec_from_file_location('frozen_provider',a.source/'tools/qwen_native_fullshape/build_provider.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    a.work.mkdir(parents=True,exist_ok=False)
    sources=m.SOURCES+[a.source/'rtl/hdc/ot_hdc_isa.svh',Path(__file__)]
    pins={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}
    (a.work/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--build','-j','8','--top-module',m.TOP,
         '-GG=3072','-GW=16','-GIL=8','-GNW=16','-GSU_VEC=1','-GSW=64','-GLV=6',
         '-GHID=4096','-GHALF=64','-GHD=128','-GNATIVE_ATTENTION=1','-GINT8_WEIGHT=1',
         '-GINT8_SCALE_WCS_BASE=1','-GQWEN_FULLSHAPE=1','-GKV_VEC_WRITE_BRIDGE=1',
         '--unroll-count','131072','--unroll-limit','131072','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-TIMESCALEMOD',
         '-I'+str(a.source/'rtl/hdc'),'--Mdir',str(a.work/'obj'),'-CFLAGS','-O0','--output-split','20000','--output-split-cfuncs','1000',*map(str,m.SOURCES)]
    t=time.monotonic()
    with (a.work/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    (a.work/'receipt.json').write_text(json.dumps({'exit':r.returncode,'seconds':time.monotonic()-t,'command':cmd,
        'source_sha256':pins,'parameters':{'G':3072,'SW':64,'LV':6,'NW':16,'INT8_EMBED':0},
        'benched_by':'actual composed layer/head gate; identical core+SU embedding gate proves LV4 fault/LV6 4096 reduction',
        'scope':'Functional local layer/head provider; actual NW18 embedding and tagged controller are separate stages'},indent=2)+'\n')
    raise SystemExit(r.returncode)
if __name__=='__main__':main()
