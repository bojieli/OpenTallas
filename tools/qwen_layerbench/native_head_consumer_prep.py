#!/usr/bin/env python3
"""Pin genuine selected leaf + four native HEAD descriptors, without dispatch.

The tile0 data is a bounded logical excerpt, not a replacement ROM macro model.
Clocks, descriptor transport, Xfill and full split-tree attachment remain required.
"""
import argparse,hashlib,json,sys
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('root','recovery','object','excerpt','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 sys.path.insert(0,str(a.root/'tools'));import hdc_isa as ISA
 recovery=json.loads(a.recovery.read_text());obj=json.loads(a.object.read_text());ex=json.loads(a.excerpt.read_text())
 selected={}
 for name,r in recovery['initialization_overlay']['selected_source'].items():
  path=Path(r['path'].split('/stage1/')[1]);assert sha(a.root/path)==r['sha256'];selected[name]=dict(path=str(path),sha256=r['sha256'])
 assert ex['groups']==[0,1,2,3] and len(ex['code_words'])==1600 and len(ex['scale_words'])==1200
 rank=obj['ranks'][0];assert ex['code_sha256']==rank['genuine_code_image_sha256'] and ex['scale_sha256']==rank['genuine_scale_image_sha256']
 assert [x['rounds']for x in rank['programme_words'][:4]]==[8,8,8,1]
 ib=[];bounds=[]
 for index,rec in enumerate(rank['programme_words'][:4]):
  f=ISA.decode(int(rec['word_hex'],16));assert f['me_amc']==int(index!=0) and f['me_row0']==index*6144
  code=sorted({f['me_wbase']+r*f['me_ts']+k*f['me_ks']+(j>>f['me_jsh'])*f['me_js']for r in range(f['me_tiles'])for k in range(f['me_k'])for j in range(8)})
  assert code==list(range(*rec['local_code']))
  assert rec['resident_code']==[18432+x for x in rec['local_code']] and rec['resident_scale']==[29376+x for x in rec['local_scale']]
  assert 0<=min(code)<=max(code)<1600 and rec['local_scale'][1]<=1200
  v=int(rec['ib379_hex'],16)
  # HR contract: IB379 wbase[323:300], WCS[124:101].
  assert (v>>300)&0xffffff==f['me_wbase'] and (v>>101)&0xffffff==f['me_wcs']
  v+=18432<<300;v+=29376<<101;ib.append(f'{v:095x}')
  bounds.append(dict(chunk=index,rounds=f['me_tiles'],rows=f['me_nout'],row0=f['me_row0'],amc=f['me_amc'],code=rec['resident_code'],scale=rec['resident_scale'],local_code=rec['local_code'],local_scale=rec['local_scale']))
 assert ISA.decode(int(rank['programme_words'][4]['word_hex'],16))['unit']==0
 (a.out/'resident_ib379.hex').write_text('\n'.join(ib)+'\n')
 (a.out/'tile0_logical_int8.hex').write_text('\n'.join(ex['code_words'])+'\n')
 (a.out/'genuine_scale_bf16.hex').write_text('\n'.join(ex['scale_words'])+'\n')
 result=dict(status='SOURCE_PREP_NOT_EXECUTED',selected_consumer=selected,descriptor_bounds=bounds,groups=3072,tile_groups=4,tile_id=0,source_rank=0,vocabulary_rows=18992,code_words=1600,scale_words=1200,
  genuine_source=ex['source'],genuine_code_sha256=ex['code_sha256'],genuine_scale_sha256=ex['scale_sha256'],
  control_path=['HR cmd380','ot_qwen_tp8_rom_relocate','qfd_dv_hr_pack','actual HR/XPF transports','native NK tap508 {xl128,ib379,go}', 'qfd_tile_nk_rp2_romleaf_rr','qfd_tile_nk_rp2_45','ot_qwen_rom_tile_nk','ot_qwen_rom_tile_logic_w12','ot_qwen_w12_matvec_part PART1'],
  ammax_path='selected collector -> S8 station shared BF16 BTAB post-scale -> peruser AMAX -> scalar root; selected HR AMAX payload tied zero and m_fin outputs unused',
  missing=['frozen821/f79 canonical instance/parameter+clock attachment beyond SHA-matched recovery chain','genuine physical ROMleaf mask extraction for selected tile (logical excerpt is not a macro image)','real Xfill/live-X ownership and perchunk GO/end dates','selected collector/STN298/sharedBF16BTAB/AMAX attachment and simulation; no generic PART2 substitution'],
  readset={str(x):sha(x)for x in (a.recovery,a.object,a.excerpt)},artifacts={n:sha(a.out/n)for n in ('resident_ib379.hex','tile0_logical_int8.hex','genuine_scale_bf16.hex')})
 (a.out/'consumer_prep.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],chunks=4,code=1600,scales=1200,source_entries=len(selected))))
if __name__=='__main__':main()
