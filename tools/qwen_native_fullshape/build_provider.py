#!/usr/bin/env python3
"""Build fullshape functional candidate library. Run only inside admitted ot-run.

DPI arithmetic preserves latency/order; this library provides no physical proof.
"""
import argparse, hashlib, json, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TOP = 'ot_hdc_core_vector_weight_native_candidate'
NAMES = ('ot_hdc_delay','ot_hdc_fp32_mul_pipe','ot_hdc_fpu','ot_hdc_sfu','ot_hdc_sfu_q',
'ot_hdc_reduce','ot_hdc_reduce_q','ot_hdc_matvec','ot_hdc_stream','ot_hdc_vstream_lane',
'ot_hdc_vreduce','ot_hdc_vstream','ot_hdc_dyn_ttiles','ot_hdc_qwen_int8_arith',
'ot_hdc_qwen_int8_embed_decode','ot_hdc_fp32_add_lat','ot_hdc_fp32_mul_lat','ot_hdc_prefix', TOP)
SOURCES = [*(ROOT/f'rtl/hdc/{n}.sv' for n in NAMES),
ROOT/'rtl/proto/ot_fp32_add_rne_pipe.sv', ROOT/'rtl/proto/ot_fp32_mul_rne_pipe.sv',
ROOT/'rtl/test/sim_hdc_v41x_fastfp_dpi.sv', ROOT/'rtl/test/sim_qwen_native_current_fastfp_wrap.sv',
ROOT/'rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_me_provider_dispatch.sv']
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=8);p.add_argument('--verilator',default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
    p.add_argument('--lint-only',action='store_true');a=p.parse_args()
    a.work.mkdir(parents=True,exist_ok=False)
    pins={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCES+[ROOT/'rtl/hdc/ot_hdc_isa.svh',Path(__file__)]}
    (a.work/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    cmd=[a.verilator, '--lint-only' if a.lint_only else '--cc','--top-module',TOP,
    '-GG=3072','-GW=16','-GIL=8','-GSU_VEC=1','-GSW=64','-GLV=4',
    '-GHID=4096','-GHALF=64','-GHD=128','-GNATIVE_ATTENTION=1',
    '-GINT8_WEIGHT=1','-GINT8_SCALE_WCS_BASE=1','-GQWEN_FULLSHAPE=1','-GKV_VEC_WRITE_BRIDGE=1',
    '--unroll-count','131072','--unroll-limit','131072','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-TIMESCALEMOD',
    '-I'+str(ROOT/'rtl/hdc'),'--Mdir',str(a.work/'obj')]
    if not a.lint_only: cmd+=['--build','-j',str(a.jobs),'-CFLAGS','-O0','--output-split','20000','--output-split-cfuncs','1000']
    cmd+=list(map(str,SOURCES))
    t=time.monotonic()
    with (a.work/'build.log').open('w') as out:r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT)
    record={'scope':'FUNCTIONAL_NOT_PHYSICAL','parameters':{'G':3072,'W':16,'IL':8,'SU_VEC':1,'SW':64,'INT8_WEIGHT':1,'INT8_SCALE_WCS_BASE':1,'NATIVE_ATTENTION':1},
    'command':cmd,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-t,'source_sha256':pins,
    'source_stable':all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==s for f,s in pins.items()),
    'mode':'lint' if a.lint_only else 'library','library':str(a.work/'obj'/('V'+TOP+'__ALL.a')),
    'dpi_link_source':str(ROOT/'rtl/test/sim_hdc_v41x_fastfp_dpi.cpp')}
    (a.work/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    raise SystemExit(r.returncode)
if __name__=='__main__':main()
