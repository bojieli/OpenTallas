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
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--contract',required=True);p.add_argument('--raw-program',required=True);p.add_argument('--out',required=True)
 # TOK.DS.BENCH.1 CAP-ED (LEAD2-S81/TOK2 10-19): global 12-pair placement from the exact root packing (packD_<D>.json)
 p.add_argument('--placements',default=None);p.add_argument('--edly',type=int,default=0);a=p.parse_args()
 glob=json.loads(Path(a.placements).read_text()) if a.placements else None
 if glob:assert glob['complete_search'] and glob['solution'] and a.edly>0
 # frame order of the packing (root_pack.py KIND) and the MEASURED frame-exit offset of each frame's own relative return
 # model (757a340ff diagnostic: every actual return word t - plan rel = 1434 h10 / 1430 h9_MX / 1436 h9, all 624 words)
 ORDER=['L01','L02','L03','R01','R02','R03'];OFFS={'L01':1434,'L02':1430,'L03':1436,'R01':1434,'R02':1430,'R03':1436}
 absedges={}
 out=Path(a.out)
 if out.exists():raise SystemExit('REFUSE_EXISTING_RUN_DIR')
 fx=XP.Fix(a.fixture);meta=json.loads(Path(a.contract).read_text())
 assert meta['head']==6 and meta['rows_tied_to_original_fixture']==512
 x=fx.op('attn.q_norm.scale');common=[];frameplans=[];fields={}
 for epoch in meta['phase_contracts']:
  for f in epoch['frames']:
   name=f['frame'];master=LX.base_master(f['master'])
   q,_=B.frame_pairs(master)
   if glob:
    qa=q[:12];assert len(qa)==12;cand=glob['solution'][str(ORDER.index(name[-3:]))]
    fixed={qa[i]:[tuple(v)] for i,v in enumerate(cand['assign']) if v}
   else:
    qa=q[:9];assert len(qa)==9;fixed=None
   rows=[r['original_weight_row'] for r in f['rows']]
   m=XP.FMat('wq_b','fp8',fx.w('wq_b'),fx.sc('wq_b'),rows,'attn.wq_b')
   plan=XP.phase_plan(f['master'],f['lk'],qa,0,m,x,3,4000,assign=fixed)
   assert plan['faults']==0,(name,epoch['epoch'],plan['faults'])
   if glob:
    assert [int(k) for k in plan['emission']['off']]==qa,('pool pair order != frame q[:12]',name)
    shift=OFFS[name[-3:]]+(a.edly if name[-3]=='R' else 0)
    ab=[w[0]+shift for w in plan['ret']]
    full=sorted(cand['edges'])
    if len(rows)==6:assert sorted(ab)==full,('global calendar edges differ from the packing',name,epoch['epoch'],ab,full)
    else:assert set(ab)<=set(full),('partial epoch leaves the packing',name,epoch['epoch'])
    absedges.setdefault(epoch['epoch'],[]).extend(ab)
   field=fields.setdefault(name,I.Field(16,1,0,depth=8192,active=12 if glob else 10,pp=True,fast=True))
   ph=XP.add_planned(field,plan,m,3)
   words=field.stream[ph['sbase']:ph['sbase']+ph['nbeat']]
   i=epoch['epoch']
   if len(common)<=i:common.append(words)
   assert words==common[i],('required stream differs across selected frames',name,i)
   frameplans.append(dict(epoch=i,frame=name,master=f['master'],lk=f['lk'],rows=rows,pairs=qa,
    phase=ph,placement=plan['placement'],return_model=plan['ret'],emission=plan['emission'],
    calendar='MEASURED_CLASS_MODEL; actual frame/CAP bench still required'))
 if glob:
  for i,ab in absedges.items():assert len(ab)==len(set(ab)),('CAP root edge repeats',i,sorted(ab))
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
  global_calendar=None if not glob else dict(placements=a.placements,edly=a.edly,frame_order=ORDER,measured_frame_offsets=OFFS,
   root_edges_per_epoch={str(i):sorted(v) for i,v in absedges.items()},rule='union of all frames exit edges (R +edly) has no repeat'),
  fixture_raw_sha256=hashlib.sha256((Path(a.fixture)/'ops/attn.q_norm.scale.bin').read_bytes()).hexdigest())
 (out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
 print('RETAINED_XS_PROGRAM_MODEL_PASS frames6 epochs15 rows512 common_streams15 calendarrows',len(cals),'QB20_vs_reload300; ACTUAL_READS_UNPROVED')
if __name__=='__main__':main()
