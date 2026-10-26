#!/usr/bin/env python3
"""Canonical dispatch -> affine full-N512 raw control lowering, fail explicit.

Arithmetic lowering only. Memory-bank service calendars, scalar/reducer/SFU
joins and final producer commits remain separately required before execution.
No unknown class is silently treated as BYP or excluded from the census.
"""
import argparse
from collections import Counter
import hashlib
import gzip
import json
from pathlib import Path
from su_program_inventory import decode
from su_arith_compile import pack


def stride(md,half=False):
    return 0 if md.ibcast else (md.istride or 1)


def lower(raw):
    dispatch,unit,sut,desc=decode(raw)
    why=[]
    if unit!=2:why.append('native_SFU128_lane_selection_and_variable_depth_calendar')
    if sut['sfu']:why.append('native_SFU_or_scalar_side_control_calendar')
    if sut['m1'] in (4,5):why.append('native_M128_divider_lane_selection_calendar')
    if sut['a_ind']:why.append('indexed_address_value_calendar')
    if sut['dst'] not in (0,1):why.append('native_KV_destination_calendar')
    for role,md in desc.items():
        if md.space!='VM':why.append('native_'+md.space+'_'+role+'_source_calendar')
        if md.indexed:why.append('MDESC_indexed_scalar_runtime_address_calendar')
    if why:return dict(supported=False,reasons=sorted(set(why)),sut=sut),[]
    no,ni=desc['A'].m,dispatch['n'][0]
    if not no or not ni:return dict(supported=True,empty=True,words=0,sut=sut),[]
    # A physical issue is at most512 elements. Long rows advance i_v/vb
    # directly; padding a 20480-column row to32768 would add24 empty issues.
    slot=min(512,1<<(max(ni,8 if sut['red']else 1)-1).bit_length());ls=slot.bit_length()-1
    ctl=dict(no=no,ni=ni,ls=ls,lvw=7,srcs=0,dst=sut['dst'],co_dst=sut['dst'],
             aind=0,cpair=sut['c_pair'],cx_arnd=sut['a_rnd'],cx_arelu=sut['a_relu'],
             cx_amin=sut['a_min'],cx_cclip=sut['c_clip'],cx_imm3=sut['imm3'],
             cp_m1=sut['m1'],cp_imm1=sut['imm1'],cm_m1=sut['m1'],cm_m2=sut['m2'],
             cm_qm=sut['qm'],cm_imm1=sut['imm1'],ca_ad=sut['ad'],ca_imm2=sut['imm2'],
             ci_sfu=0,cs_sfu=0,cs_e1=sut['e1'],cs_imm2=sut['imm2'],ce_e2=sut['e2'],
             ce_imm1=sut['imm1'],co_rnd=sut['rnd'])
    terms=0
    for s,role in enumerate('ABCDO'):
        if role not in desc:continue
        md=desc[role];si=stride(md)
        for k in range(7):
            do=(1<<k)//slot;di=(1<<k)%slot
            if role in 'BD' and sut['b_half']:di//=2
            term=(md.stride*do+si*di)&0xffffff
            terms|=term<<(24*(s*10+k))
    ctl['ld_c']=terms
    schedule=[];checked=0
    positions=([(o,0)for o in range(0,no,512//slot)]if ni<=512 else
               [(o,i)for o in range(no)for i in range(0,ni,512)])
    for outer,inner in positions:
        words=[]
        for q in range(4):
            base=q*128;qo,qi=divmod(base,slot);ov,iv=outer+qo,inner+qi
            vb=0
            for s,role in enumerate('ABCDO'):
                if role not in desc:continue
                md=desc[role];ii=iv//2 if role in 'BD' and sut['b_half'] else iv
                addr=(md.base+ov*md.stride+ii*stride(md))&0xffffff
                vb|=addr<<(24*s)
                # Independent enumerated-address check, all active native lane identities.
                for lane in range(128):
                    oo=ov+(lane>>ls);ii0=iv+(lane&(slot-1))
                    if oo>=no or ii0>=ni:continue
                    want=(md.base+oo*md.stride+(ii0//2 if role in 'BD'and sut['b_half']else ii0)*stride(md))&0xffffff
                    got=addr+sum((terms>>(24*(s*10+k)))&0xffffff for k in range(7)if lane>>k&1)
                    assert got&0xffffff==want,(role,base,lane,got,want)
                    checked+=1
            words.append(pack(dict(ctl,emit=1,o_v=ov,i_v=iv,vb=vb)))
        schedule.append(words)
    return dict(supported=True,empty=False,words=no*ni,sut=sut,
                address_checks=checked,issue_groups=len(schedule),
                needs_reducer=bool(sut['red']),
                execution_qualified=False,
                open=['actual_3072_SRAM_bank_calendar','scalar_reducer_external_joins',
                      'native_global_numerical_proof','production_timing_price']),schedule


def main():
    ap=argparse.ArgumentParser();ap.add_argument('inputs',type=Path);ap.add_argument('out',type=Path)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    counts=Counter();rows=[]
    images=gzip.open(args.out/'raw_control_candidates.jsonl.gz','wt')
    for path in sorted(args.inputs.glob('*/su_rec.mem')):
        manifest=json.loads((path.parent/'su_prod.json').read_text())
        raw=[int(v,16)for v in path.read_text().split()]
        assert len(raw)==len(manifest['cases'])
        for i,value in enumerate(raw):
            row,programme=lower(value)
            row.update(design=path.parent.name,record=i,case=manifest['cases'][i],
                       raw_sha256=hashlib.sha256(value.to_bytes(275,'little')).hexdigest())
            for why in row.get('reasons',[]):counts[why]+=1
            if programme:
                # Candidate raw stage controls really exist. They require the
                # explicitly listed bank/physical calendar joins before issue.
                images.write(json.dumps(dict(design=path.parent.name,record=i,
                    qualified=False,setup=[f'{((v&~(1<<539))|(1<<1741)):0436x}'for v in programme[0]],
                    issue=[[f'{v:0436x}'for v in q]for q in programme]))+'\n')
            rows.append(row)
    images.close()
    report=dict(qualified=False,records=len(rows),supported=sum(r['supported']for r in rows),
                unsupported_reasons=dict(counts),rows=rows)
    (args.out/'canonical_lowering.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='rows'}))


if __name__=='__main__':main()
