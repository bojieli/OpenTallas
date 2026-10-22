#!/usr/bin/env python3
"""Private same-owner sid6 window programme; genuine rows, stock stream ABI.

No source/gather fixture injection, no production default or datapath changes.
Emits model/ROM/control for a bounded actual XS retained-read component.
"""
import argparse,hashlib,json,sys,os
from pathlib import Path
os.environ.setdefault('HDC_V41_ARITH','chunk8')
from head_local_contract import ROOT
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
import xs_place as XP
import lower_xs as LX
import xs_calendar as XC
import frame_return_plan as P
import frame_bench as B
import v41_die_images_w17w10 as I
from pq_calendar import viamap
from lower_vs import ctl_payload

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--contract',required=True);p.add_argument('--raw-program',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=Path(a.out)
 if out.exists():raise SystemExit('REFUSE_EXISTING_RUN_DIR')
 fx=XP.Fix(a.fixture);meta=json.loads(Path(a.contract).read_text())
 assert meta['head']==6 and meta['rows_tied_to_original_fixture']==512
 x=fx.op('attn.q_norm.scale');common=[];frameplans=[];fields={}
 for epoch in meta['phase_contracts']:
  for f in epoch['frames']:
   name=f['frame'];master=LX.base_master(f['master'])
   q,_=B.frame_pairs(master);qa=q[:9];assert len(qa)==9
   rows=[r['original_weight_row'] for r in f['rows']]
   m=XP.FMat('wq_b','fp8',fx.w('wq_b'),fx.sc('wq_b'),rows,'attn.wq_b')
   plan=XP.phase_plan(f['master'],f['lk'],qa,0,m,x,3,4000)
   assert plan['faults']==0,(name,epoch['epoch'],plan['faults'])
   field=fields.setdefault(name,I.Field(16,1,0,depth=8192,active=10,pp=True,fast=True))
   ph=XP.add_planned(field,plan,m,3)
   words=field.stream[ph['sbase']:ph['sbase']+ph['nbeat']]
   i=epoch['epoch']
   if len(common)<=i:common.append(words)
   assert words==common[i],('required stream differs across selected frames',name,i)
   frameplans.append(dict(epoch=i,frame=name,master=f['master'],lk=f['lk'],rows=rows,pairs=qa,
    phase=ph,placement=plan['placement'],return_model=plan['ret'],emission=plan['emission'],
    calendar='MEASURED_CLASS_MODEL; actual frame/CAP bench still required'))
 # These are actual source programme words from all90 legalised row assignments.
 phase=[];stream=[]
 for i,w in enumerate(common):
  phase.extend([1280<<1|len(w)<<14|len(stream)<<30|6<<46,0]);stream.extend(w)
 # All tags/positions remain0; odd epoch index is NOT a buffer parity change.
 cals=[];issuers={};epochrec=[]
 for i in range(15):
  c=XC.compile_phase(phase,stream,i,6);base=len(cals);cals.extend(c['packed']);shift=1100+600*i
  for t,v in c['iss'].items():
   if t==XC.GW_IT:continue # actual single-owner retained window; never reload-valid by assumption
   if i and t==XC.T_OFFCFG:continue
   if t in (XC.TS-20,XC.TS):
    v=XC.isd(**({'prime':1} if t==XC.TS-20 else {'start':1}),base=base,length=c['cal_rows'])
   issuers[shift+t]=v
  epochrec.append(dict(epoch=i,calendar_base=base,calendar_rows=c['cal_rows'],is_d_shift=shift,
   stock_local_end_model=c['end_iter'],source_parity=0,tag=0,position=0,
   stream_words=c['nb'],data_reads=sum(bool(w&1) for w in common[i]),
   reads_of_beats=sorted(set(g for w in common[i] for g in XC.beats_of(w,0))),
   return_and_native_dates=None))
 assert len(cals)<=4096 and len(stream)<=16384
 raw=json.loads(Path(a.raw_program).read_text());commands={-8:ctl_payload(1<<6,2,0,XC.isd(gw=1,gw_fam=0,gw_par=0))}
 for v in raw:commands[v['xr_ctl_pin_edge']]=int(v['payload'],16)
 for t,v in issuers.items():
  assert t not in commands;commands[t]=ctl_payload(1<<6,2,0,v)
 out.mkdir(parents=True)
 (out/'source_ctl.txt').write_text(''.join(f'{t} {v:047x}\n' for t,v in sorted(commands.items())))
 (out/'pq_calendar_action.viamap.hex').write_text(viamap([w&((1<<72)-1) for w in cals]+[0]*(4096-len(cals))))
 (out/'pq_calendar_time.viamap.hex').write_text(viamap([w>>72 for w in cals]+[0]*(4096-len(cals))))
 (out/'pq_phase0.viamap.hex').write_text(viamap(phase+[0]*(4096-len(phase))))
 stream.extend([0]*(16384-len(stream)))
 for b in range(4):(out/f'pq_stream{b}.viamap.hex').write_text(viamap(stream[b*4096:(b+1)*4096]))
 rec=dict(scope='PRIVATE same-owner retained XS source-reader component; no frame/return/token PASS',
  actual_frames=6,actual_phases=15,semantic_rows=512,plans=frameplans,epochs=epochrec,
  source_window_open_count=1,quantizer_QB_commands=20,raw_writes=320,
  paid_reload_fallback_QB_commands=300,paid_reload_fallback_extra_QB_commands=280,
  fallback_last_source_commit_model=1260+14*20*46,fallback_dates_qualification='SERIAL_SOURCE_MODEL; calendar occupancy/actual source dates require measurement',
  original_deadline_unchanged=True,new_hardware=False,new_ff=0,new_macros=0,
  reservation=dict(raw_scratch=[608,927],bits=40960,XS_source_banks=1,XS_parity=0,
   XS_code_bits=10240,XS_scale_bits=400,XS_valid_entries=20,XS_source_entries=20,
   scope='Exclusive private selected programme only; production/MU overlaps not granted'),
  runtime_checks_required=['all15 actual stream read/valid/source/ex/macros','macro commit dates','g_wpar and selector readback',
   'END retains but no laterGW/overwrite','reset invalidates; reinstall raw path required','mode/slot/port lifetimes'],
  fixture_raw_sha256=hashlib.sha256((Path(a.fixture)/'ops/attn.q_norm.scale.bin').read_bytes()).hexdigest())
 (out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
 print('RETAINED_XS_PROGRAM_MODEL_PASS frames6 epochs15 rows512 common_streams15 calendarrows',len(cals),'QB20_vs_reload300; ACTUAL_READS_UNPROVED')
if __name__=='__main__':main()
