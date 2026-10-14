#!/usr/bin/env python3
"""Build real NW18/INT8 embedding-only core, using a frozen provider source."""
import argparse, importlib.util, hashlib, json, subprocess, time
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--bench',type=Path,required=True);a=p.parse_args()
    spec=importlib.util.spec_from_file_location('frozen_provider',a.source/'tools/qwen_native_fullshape/build_provider.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    a.work.mkdir(parents=True,exist_ok=False)
    inputs=module.SOURCES+[a.source/'rtl/hdc/ot_hdc_isa.svh',a.bench,Path(__file__),a.source/'rtl/test/sim_hdc_v41x_fastfp_dpi.cpp']
    pins={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
    (a.work/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--exe','--build','-j','8',
         '--top-module',module.TOP,'--prefix','Vot_qwen_tp8_embedding_core','-GG=1','-GW=16','-GIL=8','-GNW=18',
         '-GSU_VEC=1','-GSW=64','-GLV=6','-GHID=4096','-GHALF=64','-GHD=128','-GINT8_EMBED=1',
         '-GINT8_WEIGHT=1','-GINT8_SCALE_WCS_BASE=1','-GQWEN_FULLSHAPE=1','-GNATIVE_ATTENTION=0',
         '-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-TIMESCALEMOD','-I'+str(a.source/'rtl/hdc'),
         '--Mdir',str(a.work/'obj'),'-CFLAGS','-O1 -std=c++17',
         *map(str,module.SOURCES),str(a.bench),str(a.source/'rtl/test/sim_hdc_v41x_fastfp_dpi.cpp')]
    t=time.monotonic()
    with (a.work/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    (a.work/'build_receipt.json').write_text(json.dumps({'exit':r.returncode,'seconds':time.monotonic()-t,'command':cmd,
            'source_sha256':pins,'scope':'actual NW18 embedding core only; G1 unused ME cannot execute layer/head program'},indent=2)+'\n')
    raise SystemExit(r.returncode)
if __name__=='__main__':main()
