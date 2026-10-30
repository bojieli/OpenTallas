#!/usr/bin/env python3
"""Default-OFF local-R14-model 833ps profile and existing byte-layout bootrow.
Sources: tools/qwen_hbm_sustained_bw_model.py PS/ca-contract; base timing
rtl/hdc/kv/ot_hdc_hbm_model.sv; RFCPB rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv.
RREFD8ns, RSP10ns and rowCA1024ps are local MODEL assumptions, not licensedPHY
qualification. Existing controller clock/CDC stays833ps; no DFIclock migration.
"""
import argparse,json,pathlib
CLOCK_PS=833
PS=dict(RCD=19375,RP=16250,RAS=28125,RTP=5625,CCDL=2560,RRDS=2500,RRDL=3125,
        FAW=15000,RFC=350000,RFCPB=200000,RREFD=8000,RCDW=9375,RTW=9948,
        WTR=6250+1024+6250,WRR=6250+1024+20625,CCDS=1024,CL=12500,RSP=10000)
def profile(first_pc=0,npc=16):
 if not(0<=first_pc<32 and 1<=npc<=32-first_pc):raise ValueError('PC range')
 t={k:(v+CLOCK_PS-1)//CLOCK_PS for k,v in PS.items()}
 # Maximum refresh deadlines round DOWN. Four-edge row TDM per PC requires
 # a multiple-of-four period; every initial seed uses that PC row slot.
 period=4*((3900000//32)//CLOCK_PS//4)
 seeds=[]
 for pc in range(first_pc,first_pc+npc):
  r=period+pc*108//32;r+=(2*(pc%2)-r)%4
  assert period<=r<=252 and r%4==2*(pc%2)
  seeds.append(r)
 word=sum(r<<(8*i) for i,r in enumerate(seeds))
 return dict(scope='PREP local-model profile; physical PHY/paired-reset/calendar qualification required',
  clock_ps=CLOCK_PS,h9b_parameters={'TIMING_833':1},timing_ps=PS,timing_cycles=t,
  REFIPB=period,REFI=3900000//CLOCK_PS,ROW_CADENCE=2,COL_TDM=1,
  refresh_cfg={'RMIN':144,'RMAX':252,'REL_HOLD':64,'NPC':npc},first_pc=first_pc,
  reload_bytes=seeds,boot_cfg_addr='0x800',boot_cfg_data_hex=f'{word:064x}',
  external_read_return_edges=t['CL']+t['RSP'],RREG_edges=1,
  local_CL_RET_edges=t['CL']+t['RSP']+1,
  assumptions=['RREFD8ns','RSP10ns','rowCA1024ps','paired PC phase reset alignment'],
  no_claim=['licensed PHY timing','physical route closure','production fixed fill deadline'])
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--first-pc',type=int,default=0);p.add_argument('--npc',type=int,default=16);p.add_argument('--json-out');p.add_argument('--boot-row-out');a=p.parse_args()
 r=profile(a.first_pc,a.npc);s=json.dumps(r,indent=2)+'\n'
 if a.json_out:pathlib.Path(a.json_out).write_text(s)
 if a.boot_row_out:pathlib.Path(a.boot_row_out).write_text(r['boot_cfg_data_hex']+'\n')
 print(s,end='')
