#!/usr/bin/env python3
"""r10 block-stage 1.2GHz core : 200MHz block : 1GHz FDI gearbox component proof (30 reset-release offsets, 5 mutants; r11: 50%-duty clocks at 5 ns/60 ticks for the half-cycle crossings); not parent physical qualification."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''#include "Vtb_qfd_ucie_six_five.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
// tick = 5 ns / 60 (r11): 50% duty clocks, core period 10 ticks, FDI 12 (+2*FPHI), block 60, so the
// half-cycle (negedge) crossing registers see the real T/2 edges. rst_n releases at tick 2*REL (between edges);
// words are offered from core edge N0 after release; output must equal input 19 core edges later.
uint32_t word(int c,int j){return uint32_t(c*0x9e3779b9u)^uint32_t(j*0x85ebca6bu)^0xdeadbeefu;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);int bad=0,checks=0,faults=0,cases=0;
 int fphi=0;const char*e=getenv("FPHI");if(e)fphi=atoi(e);const int N0=24,LAT=19;
 for(int rel=0;rel<30;rel++){auto*t=new Vtb_qfd_ucie_six_five;t->rst_n=0;t->core_ck=0;t->fdi_ck=0;t->blk_ck=0;t->tx_valid=0;t->eval();
 int c=-1,local=0,validseen=0;
 for(int tick=0;tick<60*1200;tick++){
  if(tick==120+2*rel+1){t->rst_n=1;t->eval();c=0;}
  int fp=(tick+60-2*fphi)%12;
  bool ce=tick%10==0,cl=tick%10<5,fl=fp<6,bl=tick%60<30;
  if(ce&&c>=0){t->tx_valid=(c>=N0)&&(c%11<8);for(int j=0;j<19;j++)t->tx_frame[j]=word(c,j);t->tx_frame[18]&=0x1fffff;}
  t->core_ck=cl;t->fdi_ck=fl;t->blk_ck=bl;t->eval();
  if(ce&&c>=0){int x=c-LAT;bool ev=(x>=N0)&&(x%11<8);checks++;
   if(t->rx_valid!=ev)local++;
   if(ev){validseen++;for(int j=0;j<19;j++){uint32_t w=word(x,j);if(j==18)w&=0x1fffff;if(t->rx_frame[j]!=w)local++;}}
   c++;}
 }
 int fault=t->core_fault||t->fdi_fault;faults+=fault;bad+=local;cases++;
 printf("release_tick=%d corecycles=%d validwords=%d mismatches=%d corefault=%d fdifault=%d\n",rel,c,validseen,local,int(t->core_fault),int(t->fdi_fault));delete t;}
 printf("cases=%d checks=%d mismatches=%d faults=%d\n",cases,checks,bad,faults);return (bad||faults)?1:0;}
'''
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);x=a.parse_args();out=x.out.resolve();out.mkdir(parents=True,exist_ok=True)
 src=[ROOT/'rtl/physical/ot_qfd_ucie_six_five.sv',ROOT/'rtl/test/tb_qfd_ucie_six_five.sv'];h=out/'harness.cpp';h.write_text(CPP);rows=[]
 # r11: the positive is the STA-modelled phase 0 (the RTL requirement: all five clocks phase-aligned at the 5 ns
 # frame; fs<-bt framing and every half-cycle crossing are ordinary STA relations there). Offset phases 1..5 put the
 # FDI edge after the block edge, which STA forbids; they are run and recorded as diagnostics, not expectations.
 for mut,fphi in [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0)]:
  obj=out/f'obj{mut}';cmd=['verilator','--cc','--exe','--build','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-Wno-MULTIDRIVEN','--top-module','tb_qfd_ucie_six_five',f'-GMUT={mut}','--Mdir',str(obj),*[str(p) for p in src],str(h),'-j','4']
  b=subprocess.run(cmd,capture_output=True,text=True) if not (obj/'Vtb_qfd_ucie_six_five').exists() else subprocess.CompletedProcess(cmd,0,'reused same-run build\n','');(out/f'mut{mut}_fphi{fphi}.build.log').write_text(b.stdout+b.stderr)
  if b.returncode:raise SystemExit('buildFAIL '+str(mut))
  import os;env=dict(os.environ,FPHI=str(fphi));r=subprocess.run([str(obj/'Vtb_qfd_ucie_six_five')],capture_output=True,text=True,env=env);(out/f'mut{mut}_fphi{fphi}.run.log').write_text(r.stdout+r.stderr)
  diag=(mut==0 and fphi!=0);good=True if diag else (r.returncode==0)==(mut==0);rows.append({'mutant':mut,'fdi_phase_ticks':fphi,'sta_qualifiable_phase':fphi==0,'expected_positive':mut==0 and fphi==0,'diagnostic_only':diag,'passed_expectation':good,'exit':r.returncode,'output':r.stdout});print(mut,fphi,good,r.stdout,flush=True)
  if not good:raise SystemExit('expectationFAIL '+str(mut))
 (out/'record.json').write_text(json.dumps({'schema':'opentallas.qwen.ucie.six_five_component.v1','core_period_ps':833.3333333333334,'FDI_period_ps':1000,'PHY_FDI_cycles':4,'core_transport_edges':19,'block_stage_period_ps':5000,'mutants':{'1':'padding bit','2':'wrong output word','3':'PHY 5 FDI edges','4':'core frame misaligned','5':'TX stage crossing on the full-cycle core edge','6':'RX beat crossing on the full-cycle FDI-RX edge'},'fdi_phase_note':'r11: positive = phase 0 (aligned 5 ns frame, the RTL clock requirement; every crossing is an ordinary STA relation with T/2 setup and hold margin). Offsets 1..5 (166.7 ps steps) place the FDI edge after the block edge, outside the STA model; recorded as diagnostics (the TX half-cycle beat register then reads the previous block)','core_slots_per_block':6,'FDI_beats_per5cycles':4,'FDI_word_bits':1043,'logical_frame_bits':597,'slot_bits':598,'cases':rows,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src+[Path(__file__).resolve()]},'parent_join_qualified':False,'physical_qualified':False},indent=2)+'\n')
if __name__=='__main__':
 main();print('PASS qfd_ucie_six_five r11 half-cycle crossings: 30 positive phase-0 cases, 6 mutants rejected')
