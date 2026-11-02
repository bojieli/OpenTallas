#!/usr/bin/env python3
"""Prepare a native residual2 caller fix; never activate selected CALR masks.

The selected native store writes instructions0..11. Native cmd[12:4] is the
word pidx: p_idx[8:1] addresses a PROG row and p_idx[0] picks its half. pidx1
therefore selects PS1, while pidx2 selects the otherwise-identical PS2 op.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import dv_lower as D
import programme_store as P


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_native_pair(manifest):
    if manifest.get('parameters') != P.NATIVE_COMPACT_PARAMETERS or sorted(s['stage'] for s in manifest['stages']) != list(range(1,37)):
        raise ValueError('actual36-stage native compact source required')
    checked=0
    for st in manifest['stages']:
        if sorted(s['slice'] for s in st['slices']) != list(range(12)):
            raise ValueError('all12 actual slices required')
        for sl in st['slices']:
            if len(sl['prog_users'])!=4:raise ValueError('all4 actual users required')
            for u,records in enumerate(sl['prog_users']):
                if sorted(r['addr'] for r in records)!=list(range(6)):
                    raise ValueError('actualsix native PROG pairs required')
                for rec in records:P.encode(3,rec['addr'],rec['payload_hex'])
                pair={r['addr']:int(r['payload_hex'],16) for r in records}
                a=D.su_unpack(pair[0]>>512)
                b=D.su_unpack(pair[1]&((1<<457)-1))
                if a['bsrc']!=1 or a['b']!=u*2048 or b['b']!=u*2048+384 or a['ad']!=2 or a['red']!=1 or a['redsq']!=1 or a['d']!=u*4096:
                    raise ValueError('selected residual source layout differs')
                aa=dict(a);bb=dict(b);aa.pop('b');bb.pop('b')
                if aa!=bb:raise ValueError('native residual2 is not the PS2-only operand delta')
                checked+=1
    return checked


def decode_image(base):
    rows=[[int(w,16) for w in (base/f'calendar_m{i}.viamap.hex').read_text().splitlines()] for i in (0,1)]
    if any(len(r)!=256 for r in rows):raise ValueError('selected2048x266 physical CALR masks required')
    words=[sum(sum(((rows[l][a//8]>>(8*b+a%8))&1)<<b for b in range(266))<<(266*l) for l in (0,1)) for a in range(2048)]
    dw=[int(w,16) for w in (base/'dw.hex').read_text().splitlines()]
    return words,dw


def entries(words,descriptor):
    first,count=(descriptor>>16)&65535,descriptor&65535
    out=[];edge=0
    for i in range(first,first+count):
        e=(words[i//4]>>(128*(i%4)))&((1<<128)-1);edge+=e>>116
        cmd=e&((1<<116)-1)
        out.append(dict(index=i,edge=edge,entry=e,cmd=cmd,decoded=D.decode_cmd(cmd)))
    return out


def patch(words,dw):
    base=entries(words,dw[2]);calls=[e for e in base if e['decoded']['kind']==1 and e['decoded']['pidx']==1]
    if len(calls)!=24 or any({e['decoded']['dst'] for e in calls[k:k+12]}!=set(range(12)) for k in (0,12)):
        raise ValueError('selected two-residual caller cohort differs')
    if any(e['decoded']['kind']==1 and e['decoded']['pidx']==2 for e in base):
        raise ValueError('selected source already calls residual2')
    changed=words[:];receipts=[]
    for e in calls[12:]:
        bit=128*(e['index']%4)+4
        changed[e['index']//4]^=3<<bit  # precisely instruction1 -> instruction2, no entry/time changes
        receipts.append(dict(index=e['index'],segment_relative_issue_edge=e['edge'],dst=e['decoded']['dst'],old_pidx=1,new_pidx=2))
    after=entries(changed,dw[2])
    for old,new in zip(base,after):
        delta=old['entry']^new['entry']
        if delta not in (0,3<<4) or old['edge']!=new['edge']:
            raise AssertionError('candidate changed fields beyond the pidx')
    return changed,receipts


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--calendar',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    subject=json.loads(a.manifest.read_text());checked=verify_native_pair(subject)
    before,dw=decode_image(a.calendar);after,sites=patch(before,dw)
    a.out.mkdir(parents=True,exist_ok=False)
    for lane in (0,1):
        (a.out/f'calendar_m{lane}.viamap.hex').write_text(''.join(f'{w:0532x}\n' for w in P.physical_rows(after+[0]*2048,lane)[:256]))
    (a.out/'dw.hex').write_bytes((a.calendar/'dw.hex').read_bytes())
    head=entries(before,dw[3])
    report=dict(status='PREP_ONLY_NOT_ADOPTED',native_pairs_checked=checked,patched_calls=sites,
        native_cmd_field='cmd[12:4] -> su_cmd[8:0] -> p_idx[8:1] row / p_idx[0] half',
        residual1_crom_element_base=0,residual2_crom_element_base=384,
        timing_delta_edges=0,added_issue_slots=0,user_rule='native calendar applies128*user to pidx after this local1->2 fix',
        head_native_su_calls=sum(e['decoded']['kind']==1 for e in head),
        old_calendar_sha256={p.name:sha(p) for p in a.calendar.iterdir() if p.name in ('calendar_m0.viamap.hex','calendar_m1.viamap.hex','dw.hex')},
        candidate_sha256={p.name:sha(p) for p in a.out.iterdir()},manifest_sha256=sha(a.manifest),
        numeric_scope='Corrected source dispatch only; native residual2 arithmetic/current full-layer gate NOT_RUN',
        rstd_source_join='Historical last-residual PSUM/RSTD claims cannot transfer until this native caller/source mismatch is qualified')
    (a.out/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],native_pairs_checked=checked,patched_calls=len(sites),timing_delta_edges=0)))

if __name__=='__main__':main()
