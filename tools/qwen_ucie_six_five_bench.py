#!/usr/bin/env python3
"""Actual fixed-slot1.2GHzcore:1GHzFDI storage/4FDI PHY component proof; not parentphysical qualification."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''#include "Vtb_qfd_ucie_six_five.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <initializer_list>
uint32_t word(int c,int j){return uint32_t(c*0x9e3779b9u)^uint32_t(j*0x85ebca6bu)^0xdeadbeefu;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);int bad=0,checks=0,faults=0;
 for(int base: {0,5})for(int phi=0;phi<6;phi++){auto*t=new Vtb_qfd_ucie_six_five;t->rst_n=0;t->core_ck=0;t->fdi_ck=0;t->eval();
 t->core_ck=1;t->fdi_ck=1;t->eval();t->core_ck=0;t->fdi_ck=0;t->eval();t->rst_n=1;t->eval();int c=0,local=0;
 for(int tick=0;tick<6000;tick++){bool ce=tick%5==0 && tick>=base,fe=tick%6==phi;
 if(ce){t->tx_valid=(c%11<8);for(int j=0;j<19;j++)t->tx_frame[j]=word(c,j);t->tx_frame[18]&=0x1fffff;}
 t->core_ck=ce;t->fdi_ck=fe;t->eval();
 if(ce){if(c>=24){int x=c-24;checks++;if(t->rx_valid!=(x%11<8))local++;
 for(int j=0;j<19;j++){uint32_t w=word(x,j);if(j==18)w&=0x1fffff;if(t->rx_frame[j]!=w)local++;}}
 else if(t->rx_valid)local++;c++;}
 t->core_ck=0;t->fdi_ck=0;t->eval();}
 int fault=t->core_fault||t->fdi_fault;faults+=fault;bad+=local;
 printf("base=%d phase=%d corecycles=%d mismatches=%d corefault=%d fdifault=%d\n",base,phi,c,local,int(t->core_fault),int(t->fdi_fault));delete t;}
 printf("checks=%d mismatches=%d faults=%d\n",checks,bad,faults);return (bad||faults)?1:0;}
'''
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);x=a.parse_args();out=x.out.resolve();out.mkdir(parents=True,exist_ok=True)
 src=[ROOT/'rtl/physical/ot_qfd_ucie_six_five.sv',ROOT/'rtl/test/tb_qfd_ucie_six_five.sv'];h=out/'harness.cpp';h.write_text(CPP);rows=[]
 for mut in [0,1,2,3]:
  obj=out/f'obj{mut}';cmd=['verilator','--cc','--exe','--build','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-Wno-MULTIDRIVEN','--top-module','tb_qfd_ucie_six_five',f'-GMUT={mut}','--Mdir',str(obj),*[str(p) for p in src],str(h),'-j','4']
  b=subprocess.run(cmd,capture_output=True,text=True);(out/f'mut{mut}.build.log').write_text(b.stdout+b.stderr)
  if b.returncode:raise SystemExit('buildFAIL '+str(mut))
  r=subprocess.run([str(obj/'Vtb_qfd_ucie_six_five')],capture_output=True,text=True);(out/f'mut{mut}.run.log').write_text(r.stdout+r.stderr)
  good=(r.returncode==0)==(mut==0);rows.append({'mutant':mut,'expected_positive':mut==0,'passed_expectation':good,'exit':r.returncode,'output':r.stdout});print(mut,good,r.stdout,flush=True)
  if not good:raise SystemExit('expectationFAIL '+str(mut))
 (out/'record.json').write_text(json.dumps({'schema':'opentallas.qwen.ucie.six_five_component.v1','core_period_ps':833.3333333333334,'FDI_period_ps':1000,'PHY_FDI_cycles':4,'core_transport_edges':24,'core_slots_per_block':6,'FDI_beats_per5cycles':4,'FDI_word_bits':1043,'logical_frame_bits':597,'slot_bits':598,'cases':rows,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src+[Path(__file__).resolve()]},'parent_join_qualified':False,'physical_qualified':False},indent=2)+'\n')
if __name__=='__main__':main()
