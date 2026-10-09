#!/usr/bin/env python3
"""Minimum full-length whole-row exact gate; no die or physical claim."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import rtl_hdc_v41x_hcp_campaign as hc
dpi='--dpi' in sys.argv
scratch=Path(sys.argv[1]);scratch.mkdir(parents=True,exist_ok=True)
hc.G.set_arith('chunk8');rng=np.random.default_rng(70109)
fn=rng.normal(0,.03,(1,20480)).astype(np.float32)
x=hc.G.to_bf16(rng.normal(0,1,(1,20480)).astype(np.float32))
raw,r,expected=hc.golden_mixes(fn,x.reshape(4,5120),1e-6)
hc.write_vectors(scratch,[{'fn':fn,'x':x,'scale':True,'eps':1e-6,'exp':expected.reshape(1,1)}],32)
(scratch/'expected.mem').write_text(f'{int(hc.bits(expected)[0]):08x}\n')
sources=[ROOT/'rtl/hdc/hbm/ot_hbm_hc_row_projection_sram.sv',ROOT/'rtl/hdc/hbm/ot_hbm_hc_row_operand_sram.sv',ROOT/'rtl/model/ot_hbm_hc_operand_sram_sim.sv',ROOT/'rtl/common/ot_secded.sv',*hc.SOURCES,ROOT/'rtl/test/tb_hbm_hc_row_projection_sram.sv']
if dpi: sources=hc.fp_sources(sources,'dpi')
harness=scratch/'harness.cpp';harness.write_text('#include "Vtb_hbm_hc_row_projection_sram.h"\n#include "verilated.h"\ndouble sc_time_stamp(){return 0;}\nint main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtb_hbm_hc_row_projection_sram t;while(!Verilated::gotFinish()){t.clk=0;t.eval();t.clk=1;t.eval();}t.final();}\n')
obj=scratch/'obj'
cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--exe','--build','-j','2','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-I'+str(ROOT/'rtl/common'),'--output-split','20000','--top-module','tb_hbm_hc_row_projection_sram','-Mdir',str(obj),*map(str,sources),str(harness)]
with (scratch/'build.log').open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
exe=obj/'Vtb_hbm_hc_row_projection_sram';arms={}
for name,plus in [('exact',[]),('negative_sign_flip',['+MUTANT'])]:
 p=subprocess.run([str(exe),*plus],cwd=scratch,capture_output=True,text=True)
 (scratch/(name+'.log')).write_text(p.stdout+p.stderr)
 arms[name]={'returncode':p.returncode,'log':p.stdout[-2000:]}
assert arms['exact']['returncode']==0 and 'HC_ROW_PASS' in arms['exact']['log'],arms
assert arms['negative_sign_flip']['returncode']!=0,arms
out=ROOT/'results/rtl/hbm_hc_row_shard_20261009/sram_exact_dpi.json' if dpi else ROOT/'results/rtl/hbm_hc_row_shard_20261009/sram_exact_real.json';out.parent.mkdir(parents=True,exist_ok=True)
record={'status':'PASS','scope':'one full20480-term F32 row, '+('simulation-only FP DPI' if dpi else 'real FP RTL')+', chunk8 scale, serial256b prefetch with real SRAM interfaces and SECDED, stalled request,response,and consumer; synthetic operands; no die integration or physical qualification','arms':arms,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__)]},'fixture_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in scratch.glob('*.mem')}}
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(arms))
