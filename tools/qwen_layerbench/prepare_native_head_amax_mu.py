#!/usr/bin/env python3
"""Prepare actual NU4 AMAX boundary vectors from qualified native post values."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--post',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
data=(a.post/'checked_scaled_rows.hex').read_bytes();rows=[int(x,16)for x in data.decode().splitlines()if x and not x.startswith('#')];assert len(rows)==11
receipt=json.loads((a.post/'receipt.json').read_text());assert receipt['status']=='PASS_NATIVE_POST_COMPONENT'
(a.out/'checked_scaled_rows.hex').write_bytes(data)
addr=[16*j for j in range(8)]+[18944+16*j for j in range(3)]
plan=[[0,4,8],[1,5,9],[2,6,10],[3,7]]
def key(v):return (~v)&0xffffffff if v>>31 else v|0x80000000
gold=[]
for u,indices in enumerate(plan):
 pairs=[(addr[i]+lane,(rows[i]>>(32*lane))&0xffffffff)for i in indices for lane in range(16)]
 idx,val=max(pairs,key=lambda x:(key(x[1]),-x[0]));gold.append(dict(user=u,vectors=indices,index=idx,value=f'{val:08x}',okey=f'{key(val):08x}'))
assert gold[2]['index']==36 and gold[2]['value']=='4119bef9'
assert len({x['index']for x in gold})==4
(a.out/'expected_candidates.hex').write_text('\n'.join(f'{(1<<56)|(x["index"]<<32)|int(x["value"],16):015x}'for x in gold)+'\n')
result=dict(status='SOURCE_PREP_NOT_RUN',scope='actual qfd_dv_amax_mu NU4 logical numerical component, qualified nativepost176scalars assembled11vectors across8 sequential2lanecontexts; no simultaneousSTN, flattenedhardctl, fullvocab or ROOT/token claim',vectors=11,scalar_values=176,descriptor_legality='elevenonewordAMAXSTNs with originaldbase andr_idx0; finalnonamaxcontext outsideAMAXresults',vector_addresses=addr,user_partition=gold,input_sha256=hashlib.sha256(data).hexdigest(),post_receipt_sha256=hashlib.sha256((a.post/'receipt.json').read_bytes()).hexdigest(),clear_control='clear users2/3 after earlier user candidates merged; nativeMUT3 clear-all must be observable',user_control='new STN on old last result edge is legal per actual ctl am_stn_pend = busy&&!sender&&!(left==1&&r_v); nativeMUT2 currentSTN merge differs from carrieduser',emit_control='finalcurrentSTNuser2 nonamax; emitAMAXuser0 first, nativeMUT4 emitswrongtag',drain='al0..al4 plusrun merge, lastwordE→mergeE+5;6quietedges beforeemit/clear',clock='explicit nominal833ps/1fs component clock; no productionphase claim')
(a.out/'prep_receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(gold))
