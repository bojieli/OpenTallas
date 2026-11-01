"""Decode actual CALR masks and report base-calendar SU instruction coverage."""
import argparse,collections,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',type=Path,required=True);p.add_argument('--dw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
paths=[a.image/f'calendar_m{i}.viamap.hex' for i in range(2)]
rows=[[int(s,16) for s in f.read_text().split()] for f in paths]
def macro(m,addr):
    return sum(((rows[m][addr//8]>>(8*b+addr%8))&1)<<b for b in range(266))
words=[macro(0,r)|(macro(1,r)<<266) for r in range(256)]
dw=[int(s,16) for s in a.dw.read_text().split()];assert len(dw)==8
assert dw[0]>>32==0x43414c52
nent=dw[0]&1023;segments=[]
for name,d in zip(('stage0','decode','HEAD37','BOOT'),dw[1:5]):
    first=(d>>16)&65535;count=d&65535;assert first%4==0 and first+count<=nent
    kinds=collections.Counter();su=collections.Counter();entries=[]
    for idx in range(first,first+count):
        entry=(words[idx//4]>>(128*(idx%4)))&((1<<128)-1)
        cmd=entry&((1<<116)-1);kind=(cmd>>1)&7;kinds[kind]+=1
        if cmd&1 and kind==1:
            pc=(cmd>>4)&511;su[pc]+=1;entries.append(dict(entry=idx,pidx=pc))
    segments.append(dict(name=name,first=first,count=count,command_kinds=dict(kinds),base_su_pidx_counts=dict(sorted(su.items())),su_entries=entries,
                         missing_from_six_pairs=sorted(set(su)-set(range(12)))))
result=dict(scope='Physical CALR image/base instruction join only. Runtime user relocation, current source timing, transformer arithmetic and HEAD assets are separate gates.',
            images_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths+[a.dw]},nent=nent,segments=segments,
            monitored_copies_12_to_15_issued=any(set(s['base_su_pidx_counts'])&set(range(12,16)) for s in segments),
            HEAD_native_finalnorm_SU_issued=bool(segments[2]['su_entries']))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
print('CALR_BASE_PROG_JOIN', 'missing', [s['missing_from_six_pairs'] for s in segments], 'HEAD_SU',result['HEAD_native_finalnorm_SU_issued'])
