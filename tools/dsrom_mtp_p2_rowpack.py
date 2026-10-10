#!/usr/bin/env python3
"""P2 whole-superrow fallback: 1792 pairs, existing eight-segment element interface.

The 1680-pair dense storage record remains historical. Rotation balances region
loads; full-K rows stay on one pair and retain chunk8 reduction order.
"""
import argparse, collections, hashlib, json, math, re, subprocess
from pathlib import Path
import numpy as np
import dsrom_mtp_p2 as P


def schedule(snapshot):
    storage=P.allocate(snapshot)
    fill={s:[[0]*14 for _ in range(128)] for s in ['A','B']}
    stages=collections.defaultdict(list)
    for m in storage['matrices']:
        stages[(m['side'],m['stage'],m['expert'])].append(m)
    phases=[]; maxseg=0; maxread=0
    for (side,stage,expert),ms in stages.items():
        for ops in [('w1','w3'),('w2',)]:
            segs=[]
            for mi,m in enumerate([x for x in ms if x['op'] in ops]):
                nw=math.ceil(m['K']/512)*8
                for sr in range(m['rows']//2):
                    region=(sr+expert*32)%128
                    ff=fill[side][region]
                    pair=next(i for i in range(14) if ff[i]+nw<=8192)
                    base=ff[pair];ff[pair]+=nw
                    segs.append(dict(tensor=m['tensor'],op=m['op'],mi=mi,superrow=sr,
                                     region=region,pair=14*region+pair,base=base,words=nw,
                                     K=m['K'],rank_slices=m['rank_slices']))
            bypair=collections.defaultdict(list)
            for sg in segs:bypair[sg['pair']].append(sg)
            # Configuration hardware order: row first, then matrix. Allocate the
            # SAME reserved interval in that order, so cfg and read image agree.
            for pp,ss in bypair.items():
                pos=min(x['base'] for x in ss)
                for sg in sorted(ss,key=lambda x:(x['superrow'],x['mi'])):
                    sg['base']=pos;pos+=sg['words']
                assert len(ss)<=8
                demand=len(ss)*min(8,math.ceil(ss[0]['K']/512))
            # Emit serial subphases bounded by NCH16; no sum is reordered.
            perphase=16//min(8,math.ceil(segs[0]['K']/512))
            batches=max(math.ceil(len(ss)/perphase) for ss in bypair.values())
            for batch in range(batches):
                subset=[sg for ss in bypair.values() for sg in sorted(ss,key=lambda x:(x['superrow'],x['mi']))[batch*perphase:(batch+1)*perphase]]
                loads=collections.Counter();counts=collections.Counter()
                for sg in subset: loads[sg['pair']]+=sg['words'];counts[sg['pair']]+=1
                maxseg=max(maxseg,max(counts.values()));maxread=max(maxread,max(loads.values()))
                assert max(counts.values())<=perphase
                phases.append(dict(side=side,stage=stage,expert=expert,ops=list(ops),subphase=batch,segments=subset))
    totals={s:[sum(x) for x in rs] for s,rs in fill.items()}
    assert all(set(v)=={107520} for v in totals.values())
    return dict(schema='opentallas.dsrom-mtp-p2-rowpack.v1',source_commit=P.D.git_head(),
                source_sha256=P.digest(__file__),checkpoint=snapshot.name,
                opt_in=True,adopted=False,physical_qualified=False,
                storage_pairs_per_die=1792,dense_predecessor_pairs=1680,pair_delta=112,
                die_delta=0,ROM4096_macros_per_die=7168,
                region_mapping='(superrow + expert*32) mod128; each region has14pairs',
                reduction_order='one full-K segment per superrow; unchanged chunk8 order',
                capacity=dict(max_words=max(v for rs in fill.values() for r in rs for v in r),
                              words_per_region=107520,occupied_pairs={s:sum(v>0 for r in rs for v in r) for s,rs in fill.items()}),
                interface=dict(max_segments_per_phase_pair=maxseg,segment_limit=8,GU_subphases_max=3,W2_subphases_max=2,round_word_limit=16),
                analytical=dict(max_pair_read_words_per_phase=maxread,
                                latency_credit=False,note='New broadcast/read schedules require RTL cycle measurement; no inherited DP1-EP5 timing credit.'),
                phases=phases)


def bench(snapshot,work,build):
    import dsrom_1m_field as FD
    import v41_die_images_w17w10 as I
    import rtl_v41_rom_array as A
    import hdc_golden_v41 as G
    G.set_arith('chunk8')
    work.mkdir(parents=True,exist_ok=True)
    # Full K and maximum two legal GU segments on one pair; one rank0
    # superrows in one region. Other pairs/regions cannot alter this arithmetic.
    ck=A.Ckpt(snapshot);mats=[]
    for op in ['w1','w3']:
        full=A.Mat(ck,f'mtp.0.ffn.experts.0.{op}','fp4',576,5120)
        m=FD.take(full,[0,1])
        m.s81_segments=[[0,5120]]
        m.s81_place=[(j,0,0) for j in range(1)]
        mats.append(m)
    fld=I.Field(2,1,0,pp=True,fast=True)
    meta=I.add_phase(fld,mats,(False,False),0)
    img=work/'img';img.mkdir(exist_ok=True);I.write_field(fld,img,2)
    x=FD.rand_x('p2-worst-gu',5120,False)
    vm=np.zeros(1<<16,dtype=np.uint32);vm[:5120]=x
    (img/'vm.hex').write_text(''.join(f'{int(v):08x}\n' for v in vm))
    ops=work/'ops.txt';ops.write_text(f'0 0 0 5120 32768 {meta["nrows"]}\n')
    if build:
        FD.NP,FD.NR,FD.NBF,FD.BF_SLOTS=2,1,0,[]
        FD.cmd_build(argparse.Namespace(work=work,jobs=2,qelem=0))
    exe=work/'build/tb'
    p=subprocess.run([str(exe),str(img),str(ops)],capture_output=True,text=True)
    (work/'sim.log').write_text(p.stdout+p.stderr)
    writes={int(t[2]):int(t[3],16) for l in p.stdout.splitlines() if (t:=l.split()) and t[0]=='W'}
    expected={32768+i:b<<16 for i,(f,b) in I.golden_phase(mats,G.from_bits(x).astype(G.F)).items()}
    opl=next((l for l in p.stdout.splitlines() if l.startswith('OP ')),'')
    cycles={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',opl)}
    ok=p.returncode==0 and writes==expected and p.stdout.strip().splitlines()[-1].startswith('PASS')
    return dict(pass_=ok,full_K=5120,rows=4,segments_on_one_pair=2,metadata=meta,cycles=cycles,
                golden='linear_q chunk8 on released mtp.0.experts.0.w1/w3 full-K rows',
                executable_sha256=P.digest(exe),checkpoint_header_sha256=ck.pins,
                sim_log_sha256=P.digest(work/'sim.log'),physical_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,default=P.D.SNAP_DEFAULT)
    p.add_argument('--record',type=Path,required=True)
    p.add_argument('--bench-work',type=Path)
    p.add_argument('--build',action='store_true')
    a=p.parse_args();r=schedule(a.snapshot)
    a.record.parent.mkdir(parents=True,exist_ok=True)
    if a.record.exists():raise FileExistsError(a.record)
    a.record.write_text(json.dumps(r,separators=(',',':'))+'\n')
    print(json.dumps({k:r[k] for k in ['capacity','interface','analytical']},indent=1),flush=True)
    if a.bench_work:
        b=bench(a.snapshot,a.bench_work,a.build)
        proof=a.record.with_name(a.record.stem+'_bench.json')
        if proof.exists():raise FileExistsError(proof)
        proof.write_text(json.dumps(b,indent=1)+'\n');print(json.dumps(b,default=str),flush=True)
        if not b['pass_']:raise SystemExit(1)
if __name__=='__main__':main()
