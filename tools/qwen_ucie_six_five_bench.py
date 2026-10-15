#!/usr/bin/env python3
"""r10 block-stage 1.2GHz core : 200MHz block : 1GHz FDI gearbox component proof (30 reset-release offsets, 5 mutants); not parent physical qualification."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''#include "Vtb_qfd_ucie_six_five.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
// tick = 5 ns / 30: core every 5 ticks, FDI every 6 (+FPHI), block every 30.
// rst_n releases at tick REL (between edges); words are offered from core
// edge N0 after release; output must equal input 19 core edges later.
uint32_t word(int c,int j){return uint32_t(c*0x9e3779b9u)^uint32_t(j*0x85ebca6bu)^0xdeadbeefu;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);int bad=0,checks=0,faults=0,cases=0;
 int fphi=0;const char*e=getenv("FPHI");if(e)fphi=atoi(e);const int N0=24,LAT=19;
 for(int rel=0;rel<30;rel++){auto*t=new Vtb_qfd_ucie_six_five;t->rst_n=0;t->core_ck=0;t->fdi_ck=0;t->blk_ck=0;t->tx_valid=0;t->eval();
 int c=-1,local=0,validseen=0;
 for(int tick=0;tick<30*1200;tick++){
  if(tick==60+rel){t->rst_n=1;t->eval();c=0;}
  bool ce=tick%5==0,fe=(tick+30-fphi)%6==0,be=tick%30==0;
  if(ce&&c>=0){t->tx_valid=(c>=N0)&&(c%11<8);for(int j=0;j<19;j++)t->tx_frame[j]=word(c,j);t->tx_frame[18]&=0x1fffff;}
  t->core_ck=ce;t->fdi_ck=fe;t->blk_ck=be;t->eval();
  if(ce&&c>=0){int x=c-LAT;bool ev=(x>=N0)&&(x%11<8);checks++;
   if(t->rx_valid!=ev)local++;
   if(ev){validseen++;for(int j=0;j<19;j++){uint32_t w=word(x,j);if(j==18)w&=0x1fffff;if(t->rx_frame[j]!=w)local++;}}
   c++;}
  t->core_ck=0;t->fdi_ck=0;t->blk_ck=0;t->eval();}
 int fault=t->core_fault||t->fdi_fault;faults+=fault;bad+=local;cases++;
 printf("release_tick=%d corecycles=%d validwords=%d mismatches=%d corefault=%d fdifault=%d\n",rel,c,validseen,local,int(t->core_fault),int(t->fdi_fault));delete t;}
 printf("cases=%d checks=%d mismatches=%d faults=%d\n",cases,checks,bad,faults);return (bad||faults)?1:0;}
'''
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);x=a.parse_args();out=x.out.resolve();out.mkdir(parents=True,exist_ok=True)
 src=[ROOT/'rtl/physical/ot_qfd_ucie_six_five.sv',ROOT/'rtl/test/tb_qfd_ucie_six_five.sv'];h=out/'harness.cpp';h.write_text(CPP);rows=[]
 for mut,fphi in [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(1,0),(2,0),(3,0),(4,0)]:
  obj=out/f'obj{mut}';cmd=['verilator','--cc','--exe','--build','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-Wno-MULTIDRIVEN','--top-module','tb_qfd_ucie_six_five',f'-GMUT={mut}','--Mdir',str(obj),*[str(p) for p in src],str(h),'-j','4']
  b=subprocess.run(cmd,capture_output=True,text=True) if not (obj/'Vtb_qfd_ucie_six_five').exists() else subprocess.CompletedProcess(cmd,0,'reused same-run build\n','');(out/f'mut{mut}_fphi{fphi}.build.log').write_text(b.stdout+b.stderr)
  if b.returncode:raise SystemExit('buildFAIL '+str(mut))
  import os;env=dict(os.environ,FPHI=str(fphi));r=subprocess.run([str(obj/'Vtb_qfd_ucie_six_five')],capture_output=True,text=True,env=env);(out/f'mut{mut}_fphi{fphi}.run.log').write_text(r.stdout+r.stderr)
  good=(r.returncode==0)==(mut==0);rows.append({'mutant':mut,'fdi_phase_ticks':fphi,'sta_qualifiable_phase':fphi==0,'expected_positive':mut==0,'passed_expectation':good,'exit':r.returncode,'output':r.stdout});print(mut,fphi,good,r.stdout,flush=True)
  if not good:raise SystemExit('expectationFAIL '+str(mut))
 (out/'record.json').write_text(json.dumps({'schema':'opentallas.qwen.ucie.six_five_component.v1','core_period_ps':833.3333333333334,'FDI_period_ps':1000,'PHY_FDI_cycles':4,'core_transport_edges':19,'block_stage_period_ps':5000,'mutants':{'1':'padding bit','2':'wrong output word','3':'PHY 5 FDI edges','4':'core frame misaligned'},'fdi_phase_note':'RTL is functionally tolerant of FDI phase offsets 0..5 ticks (166.7 ps steps); only phase 0 (aligned 5 ns frame) has ordinary STA relations >=833 ps; offsets are an STA/clock-tree matter, not an RTL negative control','core_slots_per_block':6,'FDI_beats_per5cycles':4,'FDI_word_bits':1043,'logical_frame_bits':597,'slot_bits':598,'cases':rows,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src+[Path(__file__).resolve()]},'parent_join_qualified':False,'physical_qualified':False},indent=2)+'\n')
if __name__=='__main__':
 main();print('PASS qfd_ucie_six_five r10 block-stage component: 180 positive cases, 4 mutants rejected')
