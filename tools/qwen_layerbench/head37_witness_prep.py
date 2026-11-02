#!/usr/bin/env python3
"""Pack real CALR BASE witnesses and a TEST-ONLY HEAD37 dispatch fixture.

No production HEAD dates, activation, rate or physical qualification is implied.
BASE dates and ordering come directly from the selected corrected CALR image.
"""
import argparse, hashlib, json
from pathlib import Path
import residual2_calendar_candidate as R
import typed_witness_control_vectors as V


def pack(records):
    words=[0]*1024
    header=0x57544e3101640000 | (len(records)<<6)
    for i,r in enumerate(records):
        events=r['events'];base=min(x[0] for x in events);pc=r['pc']
        assert 0<=base<8192 and 0<=pc<128 and len({s for _,s,_ in events})==len(events)
        mask=sum(1<<s for _,s,_ in events)
        rw=base | pc<<13 | mask<<22 | i<<130
        for due,s,p in events:
            assert p==pc and 0<=due-base<=255
            rw|=(due-base)<<(34+8*s)
        words[400+3*i:403+3*i]=[rw&((1<<64)-1),(rw>>64)&((1<<64)-1),(rw>>128)|((header & ~63) if i==0 else 0)]
    return words


def prepare(calendar,head):
    words,dw=R.decode_image(calendar)
    events=[(e['edge'],e['decoded']['dst'],e['decoded']['pidx']) for e in R.entries(words,dw[2]) if e['decoded']['kind']==1]
    groups=[]
    for due,s,pc in events:
        eligible=[r for r in groups if r['pc']==pc and due-min(x[0]for x in r['events'])<=255 and s not in {x[1]for x in r['events']}]
        if eligible:r=eligible[-1]
        else:r=dict(pc=pc,events=[]);groups.append(r)
        r['events'].append((due,s,pc))
    assert len(groups)==13 and sum(len(r['events'])for r in groups)==114
    assert groups[11]['pc']==2, 'canonical RES2 caller fix required'
    join=[]
    assert head['stage']==37 and head['native_head_monitor']==dict(slice=0,apply_pidx=16,monitor_pidx=17,extra_pairs=0,extra_cycles=0)
    for sl in head['slices']:
        s=sl['slice'];assert len(sl['prog_users'])==4
        for u,rows in enumerate(sl['prog_users']):
            assert len(rows)==1 and rows[0]['addr']==8
            pair=int(rows[0]['payload_hex'],16);lo=pair&((1<<512)-1);hi=pair>>512
            assert lo!=0 and ((s==0 and hi==lo) or (s!=0 and hi==0))
            join.append(dict(slice=s,user=u,primary_local_pc=16,witness_local_pc=17 if s==0 else 16,primary_word_sha256=hashlib.sha256(lo.to_bytes(64,'big')).hexdigest()))
    assert len(join)==48 and {r['slice']for r in join}==set(range(12))
    # Observer issue -> registered observation; fixture dates are not relocations.
    hg=[dict(pc=17,events=[(129,0,17)]),dict(pc=16,events=[(129+2*s,s,16)for s in range(1,12)])]
    masks=[sum(1<<s for _,s,_ in r['events'])for r in hg]
    assert masks[0]&masks[1]==0 and masks[0]|masks[1]==0xfff
    return groups,hg,join


def write_stim(path,lines):
    seen=set()
    for row in lines:
        if row[1]==4:
            assert row[0] not in seen, f"one-port SU collision at {row[0]}"
            seen.add(row[0])
    lines.sort(key=lambda x:(x[0],x[1]==9))
    path.write_text("".join("%d %d %x %x %x %x %x\n"%tuple(row)for row in lines))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--calendar',type=Path,required=True);ap.add_argument('--head',type=Path,required=True);ap.add_argument('--legacy-pw',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);base,hg,join=prepare(a.calendar,json.loads(a.head.read_text()))
    old=[int(x,16)for x in a.legacy_pw.read_text().split()];legacy=V.decode(old)
    # Corrected BASE differs only in group11's local pc; dates/masks stay exact.
    corrected=V.decode(pack(base))
    for i,(l,r)in enumerate(zip(legacy,corrected)):
        assert l['base']==r['base'] and l['mask']==r['mask'] and [x[:2]for x in l['events']]==[x[:2]for x in r['events']]
        assert r['pc']==(2 if i==11 else l['pc'])
    profiles={}
    for name,recs in [('legacy',legacy),('base',base),('head37',base+hg)]:
        pw=old if name=='legacy' else pack(recs)
        (a.out/f'{name}_pw.hex').write_text(''.join(f'{x:016x}\n'for x in pw))
        profiles[name]=dict(records=len(recs),template_bits=len(recs)*134,sha256=hashlib.sha256((a.out/f'{name}_pw.hex').read_bytes()).hexdigest())
    # Content-addressed new test profile identity (not the production auth path).
    identity=json.dumps(dict(base=base,head_fixture=hg,kernel_join=join),sort_keys=True).encode()
    dig=int.from_bytes(hashlib.sha256(identity).digest()[:8],'big');assert dig not in (0,V.DIGEST)
    meta=dict(scope='SOURCE PREP / TEST ONLY; production HEAD dates unresolved',profiles=profiles,digest=f'{dig:016x}',epoch=8,head_groups=hg,kernel_join=join,base_records=base,source_sha256={str(p):R.sha(p)for p in [a.head,a.legacy_pw,*[a.calendar/f for f in ('calendar_m0.viamap.hex','calendar_m1.viamap.hex','dw.hex')]]})
    # Existing BASE vector ABI preserves its exact historical observer timing.
    for mode,recs,pw,dd,ep in [('legacy',legacy,old,V.DIGEST,7),('enabled_base',base,pack(base+hg),dig,8)]:
        V.DIGEST,V.EPOCH=dd,ep
        for mut in [None,'missing','late','duplicate','wrong_pidx','bad_stage','digest']:
            lines,_=V.build(pw,recs,mut)
            if mode=='enabled_base' and mut=='bad_stage':
                for row in lines:
                    if row[1]==3 and row[3]==37:row[3]=38
            write_stim(a.out/f'{mode}_{mut or "nominal"}.txt',lines)
    for mut in [None,'wrong_pc','missing','late','duplicate','old_digest','stage']:
        lines=[]
        def add(t,k,*v):lines.append([t,k,*v,*([0]*(5-len(v)))])
        dd=0x198f7708b478a667 if mut=='old_digest' else dig
        add(2,2,dd>>32,dd&0xffffffff,8,1)
        for i,w in enumerate(pack(base+hg)):add(10+i,0,i,w>>32,w&0xffffffff)
        add(1040,1,1)
        # Disjoint starts keep all four contexts live while using one observer port.
        for u in range(4):
            start=1100+32*u
            add(start,3,u,38 if mut=='stage' and u==1 else 37,0x100+u)
            for sl in range(12):
                # Stored counter due129 corresponds to command at start+129:
                # counter starts at0 and compares its pre-edge value after observer.
                t=start+129+2*sl;pc=17 if sl==0 else 16
                if u==1 and sl==0:
                    if mut=='missing':continue
                    if mut=='wrong_pc':pc=16
                    if mut=='late':t+=1
                    if mut=='duplicate':add(t+25,4,u,sl,(u<<7)|pc,37,0x100+u)
                add(t,4,u,sl,(u<<7)|pc,37,0x100+u)
            add(start+180,5,u,1)
        add(1500,9)
        write_stim(a.out/f'head_{mut or "nominal"}.txt',lines)
    (a.out/'profile.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(dict(digest=meta['digest'],profiles=profiles)))
if __name__=='__main__':main()
