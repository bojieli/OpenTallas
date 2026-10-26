#!/usr/bin/env python3
"""Smallest S81 service attention engine: actual H16/D32/NL4 production configuration, isolated from 16-slice fabric."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import rtl_hdc_v41x_attn_campaign as C
SOURCES=['rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv','rtl/hdc/v41x/ot_hdc_v41x_kreg.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv','rtl/hdc/v41x/ot_hdc_v41x_attn.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv','physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/v41x/ot_dsrom_su_add6.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/v41x/ot_s81c_attn_hcore.sv']
TB='rtl/test/tb_hdc_v41x_attn_s.sv';HARNESS='rtl/test/hdc_v41_harness.cpp'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--profile',choices=['fg3','closing'],required=True);ap.add_argument('--jobs',type=int,default=8);a=ap.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
 rng=np.random.default_rng(20261025);js=[C.random_job(rng,16,32,t,min(t,64),'coarse') for t in (32,128)]
 counts,stats=C.write_jobs(o/'vectors',js,16,32,32)
 params=dict(H=16,D=32,TD=32,NL=4,TROWS=640,SRAM_MACRO=0,PWORDS=2,ILV=1,REPL=2,NSTAGE=2,SC_CRED=0,PV_CRED=0)
 params.update({('NJOBMAX' if k=='NJOB' else k):1<<max(4,int(v-1).bit_length()) for k,v in counts.items()})
 closing=a.profile=='closing';params.update(FPL=4 if closing else 3,FML=6 if closing else 3,TILE_S=int(closing),NARROW=int(closing),MFAN=int(closing),TRX=int(closing),F12=int(closing),FPLX=5 if closing else 0)
 defs=['OT_ATTN_HCORE','OT_S81C_HCORE_CTLA','OT_S81C_HCORE_RST_TIMED'] if closing else []
 if closing:
  m=json.loads((ROOT/'physical/die_plan/s81/bind/asbuilt_b178_coll.json').read_text());assert not 'SVCQ_ENG_FG3' in m['defines'];assert all(d in m['defines'] for d in defs)
 sources=SOURCES if closing else [s for s in SOURCES if not s.endswith('ot_s81c_attn_hcore.sv')]
 hier=o/'hier.vlt';hier.write_text('`verilator_config\nhier_block -module "ot_s81c_attn_hcore"\n' if closing else '`verilator_config\nhier_block -module "ot_hdc_v41x_attn_tile_l"\n')
 v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
 cmd=[v,'--cc','--exe','--build','--hierarchical','--top-module','tb_hdc_v41x_attn','--prefix','Vtb','-Mdir',str(o/'obj'),'-j',str(a.jobs),'-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','--output-split','20000','--output-split-cfuncs','2000','--unroll-count','16','--unroll-limit','131072','-MAKEFLAGS','OPT_SLOW=-O0','-CFLAGS','-O1',*[f'-G{k}={v}' for k,v in params.items()],*[f'-D{d}' for d in defs],str(hier),*[str(ROOT/s) for s in sources],str(ROOT/TB),str(ROOT/HARNESS)]
 rec=dict(profile=a.profile,params=params,defines=defs,source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),source_sha256={s:sha(ROOT/s) for s in sources+[TB,HARNESS]},scope='actual production engine shape; isolated arithmetic/cycle qualification, not a full service or die token gate',counts=counts)
 (o/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 with (o/'build.log').open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 exe=o/'obj/Vtb'
 with (o/'run.log').open('w') as f:r=subprocess.run([str(exe),f'+dir={o/"vectors"}','+seed=1','+njob=2'],stdout=f,stderr=subprocess.STDOUT)
 text=(o/'run.log').read_text();m=C.ENG_RE.search(text)
 rec['returncode']=r.returncode;rec['summary']=m.group(0) if m else None;rec['jobs']=[dict(zip(('job','T','qk_first','qk_last','qk_beats','pv_first','pv_last','pv_beats','last_score','last_p','last_pv'),map(int,x.groups()))) for x in C.JOB_RE.finditer(text)]
 rec['pass']=bool(m and int(m.group(3))==0 and int(m.group(5))==0 and int(m.group(11))==0 and int(m.group(1))==2)
 (o/'record.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec['summary']));raise SystemExit(0 if rec['pass'] else 1)
if __name__=='__main__':main()
