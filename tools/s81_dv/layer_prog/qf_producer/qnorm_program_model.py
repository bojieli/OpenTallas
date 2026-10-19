#!/usr/bin/env python3
"""Private raw-qnorm loader/QB programme model; no fixture g_d stimulus.

Source values are original FP32 state. Quantized outputs are scoreboard only.
Logical dates are explicitly relative to XR CTL pin sampling after reset.
"""
import argparse,hashlib,json,sys,os
from pathlib import Path
os.environ.setdefault('HDC_V41_ARITH','chunk8')
from head_local_contract import ROOT,storage_offset
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
sys.path.insert(0,str(ROOT/'tools/s81_slice'))
from lower_vs import ctl_payload,row_write,vs_imm,vp_cmd
import hc_gate as HG
import hdc_golden_v41 as G
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 d=Path(a.fixture);out=Path(a.out)
 if out.exists():raise SystemExit('REFUSE_EXISTING_RUN_DIR')
 files=json.loads((d/'files.json').read_text());raw=(d/'ops/attn.q_norm.scale.bin').read_bytes()
 assert hashlib.sha256(raw).hexdigest()==files['ops/attn.q_norm.scale.bin']['sha256']
 vals=np.frombuffer(raw,dtype='<f4');bits=vals.view('<u4');assert len(vals)==1280
 # A full source reservation check, not free capacity for other programme phases.
 scratch=set(range(608,928));projection=set()
 for x in range(512):
  e=storage_offset(x);leaf=((e>>6)&15)%5;word=64*(e>>6)//5+(e&63) if False else 64*((e>>6)//5)+(e&63)
  if leaf==2:projection.add(word//4)
 coeff=set(range(17,48,2));qrout=set(range(544,560))
 assert scratch.isdisjoint(projection|coeff|qrout)
 program=[];commits={};reads={};gold=[];epochs=[]
 for row in range(320):
  word=sum(int(bits[4*row+j])<<(32*j) for j in range(4));r=608+row
  program.append(dict(xr_ctl_pin_edge=row,target=5,leaf_mask=4,source_float_first=4*row,
      payload=f'{ctl_payload(1<<6,5,4,row_write(r,15,word)):047x}',raw_state_only=True))
  commits[r]=row+8 # XR pin->input/decode/output2, DL4+VP pin5, SRAM1
 for b in range(20):
  ctl=320+46*b;C=ctl+7 # XR output2 + DL4+VP pin5
  cmd=vp_cmd(9,a0=608+16*b,n=8,imm=vs_imm(umq=1,umi=b))
  program.append(dict(xr_ctl_pin_edge=ctl,target=0,leaf_mask=4,
      payload=f'{ctl_payload(1<<6,0,4,cmd):047x}',source_command='existing QB9'))
  rs=list(range(608+16*b,624+16*b))
  for j,r in enumerate(rs):
   re=C+6+j//2;assert commits[r]<re;reads[r]=re
  q=HG.g_quant(vals[64*b:64*b+64]);assert len(q)==2
  qf,qe=G.quant_fp8(vals[64*b:64*b+64])
  packed=0
  for h,(e,codes) in enumerate(q):
   assert (int(qe[h])&1023)==int(e)
   assert np.array_equal(G.E4M3[np.asarray(codes,np.uint8)],qf[32*h:32*h+32])
   packed|=int.from_bytes(bytes(codes),'little')<<(266*h)
   packed|=int(e)<<(256+266*h)
  gold.append(dict(global_beat=b,payload532=f'{packed:0133x}',scoreboard_only=True))
  epochs.append(dict(beat=b,XR_CTL_pin=ctl,VP_command_pin=C,VS_accept=C+3,
    source_SRAM_reads=[C+6,C+13],VS_u_subbeats=[C+10,C+17],VQ_mode_latch=C+5,
    AQ_samples=[C+16,C+20],AQ_outputs=[C+33,C+37],VQ_run_start=C+38,VQ_run_clear=C+78,
    XQ_fragments=[C+47,C+50],DL4_up_visible=[C+51,C+54],RSTOP_own_assembly=C+56,
    XS_g0_visible=C+57,XS_g_pin=C+58,XS_SRAM_commit=C+59,
    next_mode_earliest=C+51,next_second_AQ_detect_earliest=C+79,
    dates_qualification='STATIC_REGISTER_MODEL; measure all in actual component'))
 for x,y in zip(epochs,epochs[1:]):
  assert y['VQ_mode_latch']>x['XQ_fragments'][1]
  assert y['VQ_run_start']>x['VQ_run_clear']
 assert len(commits)==len(reads)==320
 life=[dict(row=r,write_commit=commits[r],last_read=reads[r],release_after=reads[r]) for r in sorted(scratch)]
 out.mkdir(parents=True)
 (out/'program.json').write_text(json.dumps(program,indent=2)+'\n')
 (out/'quantized_scoreboard.json').write_text(json.dumps(gold,indent=2)+'\n')
 rec=dict(schema='opentallas.s81.raw_qnorm_program_model.v1',source_input_sha256=hashlib.sha256(raw).hexdigest(),
  raw_fp32_values=1280,state_writes=320,commands=20,quantized_codes_expected=1280,block_scales_expected=40,
  new_ff=0,new_macros=0,new_gates=0,source_scratch_bits=40960,
  scratch_rows=[608,927],source_scratch_contexts=1,whole_programme_MU_overlap_proved=False,
  period=46,period_constraints=dict(VS_release=19,mode_after_fourth_fragment=46,second_AQ_after_run_clear=41),
  logical_XS_last_source_commit=epochs[-1]['XS_SRAM_commit'],native_first_reset_ready_date=None,
  absolute_selected_dates=None,source_lifetimes=life,beat_epochs=epochs,
  conflicts_with_other_programme='Existing later SW scratch600+ overlaps; no concurrent FFN/MU owner admitted. Must prove actual release before reuse.',
  causal_model_checks=dict(write_after_read=all(commits[r]<reads[r] for r in reads),mode_stable=True,run_nonoverlap=True,projection_coeff_QR_disjoint=True),
  qualification='PRIVATE_SOURCE_PROGRAMME_MODEL_ONLY; no RTL/quantizer/selected-calendar/deadline/token pass')
 (out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
 print('QNORM_PROGRAM_MODEL_PASS raw1280 writes320 QB20 expectedcodes1280/scales40 period46 lastXScommit',rec['logical_XS_last_source_commit'],'STATIC_ONLY native/deadline/MU UNPROVED')
if __name__=='__main__':main()
