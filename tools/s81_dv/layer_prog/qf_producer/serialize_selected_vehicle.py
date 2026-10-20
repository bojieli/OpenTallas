#!/usr/bin/env python3
"""Private six-frame serialization from frozen actual plans; no re-legalisation.

Produces original checkpoint weights/static cfg only. No g/return/Q stimulus.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from head_local_contract import ROOT,storage_offset
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
import xs_place as XP
import frame_bench as B
import v41_die_images_w17w10 as I
from field_cfg7_image import encode_bank,decode_bank
from pq_calendar import viamap

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--model',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=Path(a.out)
 if out.exists():raise SystemExit('REFUSE_EXISTING_RUN_DIR')
 md=Path(a.model);rec=json.loads((md/'contract.json').read_text());assert len(rec['plans'])==90
 fx=XP.Fix(a.fixture)
 for name in ['weights/wq_b.bin','weights/wq_b.scale.bin']:
  assert hashlib.sha256((Path(a.fixture)/name).read_bytes()).hexdigest()==fx.files[name]['sha256']
 frames={};seen=set();retags=0
 for pl in rec['plans']:
  name=pl['frame'];base=pl['master'].replace('_MX','').removesuffix('_l4');q,bf=B.frame_pairs(base)
  npq=len(pl['pairs']);assert npq in (9,12)  # 12 = TOK.DS.BENCH.1 CAP-ED global placement (12 physical Q pairs)
  f=frames.setdefault(name,dict(field=I.Field(16,1,0,depth=8192,active=10 if npq==9 else 12,pp=True,fast=True),q=q,bf=bf,pairs=pl['pairs'],master=pl['master']))
  assert f['pairs']==pl['pairs']
  mat=XP.FMat('wq_b','fp8',fx.w('wq_b'),fx.sc('wq_b'),pl['rows'],'attn.wq_b')
  plan=dict(assign_slots=[(p['field_slot'],p['super_row'],p['seg']) for p in pl['placement']])
  orig=I._place;I._place=__import__('frame_return_plan').place_fn(plan['assign_slots'],3)
  try:ph=I.add_phase(f['field'],[mat])
  finally:I._place=orig
  assert ph==pl['phase'],('frozen writer metadata changed',name,pl['epoch'])
  for slot in range(npq):
   cfg=f['field'].cfg[-1][slot]
   for wi in list(range(8))+list(range(17,25)):
    v=cfg[wi]
    if not v:continue
    tag=v&65535
    if tag&0x8000:continue
    assert tag<len(pl['rows'])
    dim=pl['rows'][tag]-3072;assert 0<=dim<512
    # Actual frame go_tag must supply the original row flag at runtime.
    newtag=(tag&0xc000)|6144|storage_offset(dim)
    cfg[wi]=(v&~65535)|newtag;seen.add(dim);retags+=1
 assert len(frames)==6 and seen==set(range(512)) and retags==1536
 out.mkdir(parents=True);images=out/'images';images.mkdir();blank=out/'blank_weight.hex'
 I.viamap({},blank);blank.write_text(''.join(blank.read_text().splitlines(keepends=True)[:512]))
 summary=[]
 for name,f in frames.items():
  field=f['field'];tmp=out/(name+'_field');I.write_field(field,tmp,10,flat_viamaps=True)
  # Required source stream must match the existing admitted reader ROMs byte-for-byte.
  words=field.stream+[0]*(16384-len(field.stream))
  for bank in range(4):assert viamap(words[4096*bank:4096*(bank+1)])==(md/f'pq_stream{bank}.viamap.hex').read_text()
  smap={k:i for i,k in enumerate(f['pairs'])}
  for k in f['q']:
   for mb in ('','b'):
    for par in (0,1):
     src=tmp/f'e{smap[k]}{mb}_{par}.viamap.hex' if k in smap else blank
     shutil.copyfile(src,images/f'{name}_e{k}{mb}_{par}.viamap.hex')
  for k in f['bf']:
   for side in ('e','w'):
    for par in (0,1):shutil.copyfile(blank,images/f'{name}_e{k}{side}_{par}.viamap.hex')
  for k in f['q']+f['bf']:
   banks=[[0]*4096 for _ in range(7)]
   for ph in range(15):
    ws=field.cfg[ph][smap[k]] if k in smap else [0]*25
    for wi,v in enumerate(ws):banks[wi%7][4*ph+wi//7]=v
   for bank in range(7):
    enc=encode_bank(banks[bank]);assert decode_bank(enc)==banks[bank]
    (images/f'{name}_c{k}_{bank}.viamap.hex').write_text(''.join(f'{w:0144x}\n' for w in enc))
  summary.append(dict(frame=name,master=f['master'],physical_q=f['q'],physical_BF=f['bf'],populated_q=f['pairs'],
   max_logical_ROM_fill=int(field.fill.max()),phases=15))
 ps=sorted(images.glob('*'));assert len(ps)==1012,len(ps)
 result=dict(scope='PRIVATE whole-six actual image serialization only; no runtime/native/calendar PASS',
  original_rows=512,original_row_tag_instances=retags,epochs=15,frames=summary,
  frozen_source_stream_byte_identity=True,original_row_flag_runtime='UNPROVED; go_tag/PV/RET must be measured',
  CAP_rbase_expected_if_original_flag1=0x5800,CAP_rcnt=828,new_datapath_RTL=False,
  fixtures={n:fx.files[n]['sha256'] for n in ['weights/wq_b.bin','weights/wq_b.scale.bin']},
  files=[dict(path=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in ps])
 (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
 print('SELECTED_SERIALIZATION_ONLY originalrows512 tagcopies1536 phases15 actualROMimages1012 streambytesIDENTICAL; flags/ARR/CW/native OPEN')
if __name__=='__main__':main()
