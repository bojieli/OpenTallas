#!/usr/bin/env python3
"""One real selected six-frame head: fixture ancestry/row/epoch arithmetic only.

Calls original golden segment sums, emits no field images, calendar or RTL.
"""
import argparse,hashlib,json,os,sys
from pathlib import Path
os.environ.setdefault('HDC_V41_ARITH','chunk8')
from head_local_contract import ROOT,storage_offset,retag_return,config
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
from xs_place import Fix,FMat
import frame_return_plan as P
from cap_model import golden_row,decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--placement',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 fx=Fix(a.fixture);fdir=Path(a.fixture);h=next(h for h in json.loads(Path(a.placement).read_text())['head_contracts'] if h['head']==6)
 assert h['frames']==6 and h['selected_wqb_phase_count']==15
 expected_meta='d7f2eb6175bec6a21f2ccede5a103842d7d03e36c54b4859b967a6e04ba44b28'
 assert hashlib.sha256((fdir/'meta.json').read_bytes()).hexdigest()==expected_meta
 ancestry={}
 for n in ['weights/wq_b.bin','weights/wq_b.scale.bin','ops/attn.q_norm.scale.bin','ops/attn.wq_b.bin']:
  actual=hashlib.sha256((fdir/n).read_bytes()).hexdigest();assert actual==fx.files[n]['sha256']
  ancestry[n]=dict(sha256=actual,metadata=fx.files[n])
 assert fx.meta['rank']==0 and fx.w('wq_b').shape==(8192,1280)
 import hdc_golden_v41 as G
 x=fx.op('attn.q_norm.scale');original=fx.op('attn.wq_b').view('uint32')
 epochs=[];seen=set();wrong_owner=0
 for epoch in range(15):
  frames=[]
  for f in h['records']:
   dims=list(range(f['dimension_first'],f['dimension_last']+1))[6*epoch:6*(epoch+1)]
   if not dims:continue
   rankrows=[6*512+d for d in dims]
   m=FMat('wq_b','fp8',fx.w('wq_b'),fx.sc('wq_b'),rankrows,'attn.wq_b')
   vals=P.golden_vals(m,x,3);rows=[]
   for local,d in enumerate(dims):
    acc,err=golden_row(vals[local]);assert not err
    bf=int(G.bits(G.to_bf16(G.from_bits(acc))))
    assert bf==int(original[6*512+d]),(epoch,f['name'],d,hex(bf),hex(int(original[6*512+d])))
    old=(0x4000+6*512+d)<<13
    tag=retag_return(old,head=6,dimension=d);bad,leaf,port,word,rounded=decode(tag,acc,config(6,row_flags=1));assert not bad and rounded==bf
    assert d not in seen;seen.add(d)
    try:retag_return(old,head=7,dimension=d)
    except ValueError:wrong_owner+=1
    else:raise AssertionError('wrong owner accepted')
    rows.append(dict(dimension=d,rank_semantic_row=6*512+d,original_weight_row=6*512+d,
       original_fixture_gold_index=6*512+d,local_phase_row=local,
       original_segment_sums=vals[local],original_accumulator=acc,original_bf16_gold=bf,
       storage_rank_row=0x4000+6*1024+storage_offset(d),leaf=leaf,port=port,word=word,
       actual_producer_arr=None,actual_write_edge=None))
   frames.append(dict(frame=f['name'],master=f['master'],lk=f['lk'],lk_lanes=f['lk_lanes'],
     real_rows=len(rows),unused_six_row_capacity=6-len(rows),
     sent_padding_must_remain_padding=True,actual_emission_calendar=None,rows=rows))
  epochs.append(dict(epoch=epoch,frames=frames,total_rows=sum(f['real_rows'] for f in frames),
      native_start=None,native_finish=None,capture_configuration_release=None))
 assert seen==set(range(512)) and wrong_owner==512
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 rec=dict(schema='opentallas.s81.sid6_selected_fixture_contract.v1',head=6,rank=0,physical_frames=6,epochs=15,
     fixture_meta_sha256=expected_meta,fixture_ancestry=ancestry,
     source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in ['tools/s81_dv/layer_prog/xs_place.py','tools/s81_dv/frame_return_plan.py','tools/s81_slice/cap_model.py','tools/hdc_golden_v41.py','tools/hdc_golden.py','tools/v41_rom_ksplit_bankmap.py']},
     original_checkpoint=fx.meta.get('snapshot',fx.meta.get('checkpoint')),
     rows_tied_to_original_fixture=512,wrong_owner_rejected=512,semantic_coverage_complete=True,
     golden_scope='original three-segment FP8/UE8M0 math equals original BF16 fixture; not a runtime producer',
     phase_contracts=epochs,source_epoch_calendar=None,native_return_phase=None,
     production_images_generated=False,new_hardware=False,
     next_blocker='Actual per-frame element emission plans + selected native return arrival phases, F5-F11 slot/write checks and CAP CFG/VP/QR lifetimes; no imagewriter grant',
     qualification='ONE_HEAD_GENUINE_FIXTURE_ROW_EPOCH_MODEL_ONLY; no physical/native/calendar/token closure')
 (out/'sid6_fixture_contract.json').write_text(json.dumps(rec,indent=2)+'\n')
 print('SID6_FIXTURE_MODEL_PASS original_rows512 epochs15 frames6 source_rows3072..3583 wrong_owner512; ARR/calendar HOLD')
if __name__=='__main__':main()
