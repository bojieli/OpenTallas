#!/usr/bin/env python3
"""Derive a PREP-only HEAD allocation from actual native source footprints.

This does not schedule execution. It avoids reusing live transformer storage:
HEAD gains go after every selected CROM read/write; its pidx goes after every
selected PROG write and the explicitly reserved optional monitor indices.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import dv_lower as D
import programme_store as P
import programme_lower as L


def census(path):
    path=Path(path);m=json.loads(path.read_text())
    if m['parameters'] != P.NATIVE_COMPACT_PARAMETERS or sorted(s['stage'] for s in m['stages']) != list(range(1,37)):
        raise ValueError('actual36-stage native compact source required')
    result=dict(manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source=m['source'],
                crom_write_last=-1,crom_read_last=-1,prog_indices=set(),stored_words=0,live_words=0)
    by_pidx={}
    for st in m['stages']:
        if sorted(s['slice'] for s in st['slices']) != list(range(12)):
            raise ValueError('all12 actual slices required')
        for sl in st['slices']:
            for rec in sl['crom']:
                P.encode(1,rec['addr'],rec['payload_hex'])
                result['crom_write_last']=max(result['crom_write_last'],16*rec['addr']+15)
            if len(sl['prog_users'])!=4:raise ValueError('all4 actual users required')
            for user,records in enumerate(sl['prog_users']):
                if sorted(r['addr'] for r in records)!=list(range(6)):
                    raise ValueError('selected native PROG writes must be the actualsix pairs')
                for rec in records:
                    P.encode(3,rec['addr'],rec['payload_hex'])
                    for half in range(2):
                        pidx=2*rec['addr']+half;result['prog_indices'].add(pidx);result['stored_words']+=1
                        w=(int(rec['payload_hex'],16)>>(512*half))&((1<<457)-1)
                        if not w:continue
                        f=D.su_unpack(w);result['live_words']+=1
                        if f['go'] or not f['nin'] or not f['nout']:
                            raise ValueError('invalid actual native instruction')
                        for field in ('b','c'):
                            if not f[field+'src']:continue
                            lo=f[field]-user*2048
                            hi=lo+(f['nout']-1)*f[field+'so']+(f['nin']-1)*f[field+'si']
                            if not 0<=lo<=hi<2048:raise ValueError('CROM read crosses actual user bank')
                            result['crom_read_last']=max(result['crom_read_last'],hi)
                            by_pidx.setdefault(pidx,set()).add((field,lo,hi))
    result['prog_indices']=sorted(result['prog_indices'])
    result['crom_reads_by_pidx']={str(k):[dict(field=f,first=a,last=b) for f,a,b in sorted(v)] for k,v in sorted(by_pidx.items())}
    return result


def allocation(reports, monitor_indices=(12,13,14,15)):
    if not reports:raise ValueError('actual source census required')
    last=max(max(r['crom_read_last'],r['crom_write_last']) for r in reports)
    gain_base=16*((last+16)//16)
    occupied=set(monitor_indices).union(*(set(r['prog_indices']) for r in reports))
    pidx=next((p for p in range(0,128,2) if p not in occupied and p+1 not in occupied),None)
    if gain_base+384>2048 or pidx is None:raise ValueError('HEAD resident capacity exhausted')
    return dict(gain_base=gain_base,gain_row=gain_base//16,apply_pidx=pidx,
                prior_crom_last=last,selected_prog_indices=sorted(set().union(*(set(r['prog_indices']) for r in reports))),
                optional_monitor_reserved_indices=list(monitor_indices),
                prior_gain_region_access='NONE_IN_SELECTED36_STAGE_READ_OR_WRITE_FOOTPRINT',
                prior_apply_pair_access='NONE_IN_SELECTED36_STAGE_PROG_WRITES_OR_OPTIONAL_MONITOR',
                users=[dict(user=u,crom_first=u*2048+gain_base,crom_end=u*2048+gain_base+384,
                            pidx=u*128+pidx,vm_x_first=u*4096,vm_x_end=u*4096+384,vm_rstd=u*4096+400) for u in range(4)])


def link_stage(obj, btab, alloc):
    """Emit actual stage37 table records; keep every executable date unselected."""
    if obj['status']!='UNLINKED_SOURCE_OBJECT' or obj['gain_elements']!=4096:
        raise ValueError('qualified recovered-gain source object required')
    base,pidx=alloc['gain_base'],alloc['apply_pidx']
    if pidx%2:raise ValueError('native HEAD pair must start at an even pidx')
    slices=[]
    for sl in obj['slices']:
        sid=sl['slice'];w=int(sl['apply_su_template_hex'],16)
        reloc=sl['relocations']
        if len(reloc)!=1 or reloc[0]['field']!='c' or D.su_unpack(w)['c']!=0:
            raise ValueError('native HEAD source relocation differs')
        w|=base<<reloc[0]['bit']
        f=D.su_unpack(w)
        if f['c']+len(sl['blocks'])*128>2048:raise ValueError('HEAD gain crosses user CROM partition')
        prog=L.prog_users([dict(eaddr=pidx//2,payload=f'{w:0256x}')],head=True)
        bt=[]
        for r in btab:
            if r['slice']!=sid:continue
            encoded=P.encode(2,r['addr'],r['payload_hex'],head=True)
            if 'native_word_hex' in r and encoded!=int(r['native_word_hex'],16):
                raise ValueError('recovered HEAD BTAB differs from native record')
            bt.append(dict(addr=r['addr'],payload_hex=r['payload_hex']))
        cr=[dict(addr=alloc['gain_row']+r['relative_crom_row'],payload_hex=r['payload_hex']) for r in sl['gain_payloads']]
        if len(bt)!=P.HEAD_BTAB_COUNTS[sid] or len(cr)!=P.HEAD_CROM_COUNTS[sid]:
            raise ValueError('HEAD genuine BTAB/gain shape differs')
        slices.append(dict(slice=sid,prog_users=prog,btab=bt,crom=cr))
    return dict(stage=37,slices=slices)


def assemble_manifest(base_manifest, stage37, alloc, *, parent_manifest_sha256, lowering_commit):
    """Extend the actual36-stage payload with a distinct, source-only certificate."""
    import copy
    if len(lowering_commit)!=40 or any(c not in '0123456789abcdef' for c in lowering_commit):
        raise ValueError('explicit committed source-event identity required')
    P.logical_images(base_manifest)
    result=copy.deepcopy(base_manifest)
    stage_bytes=(json.dumps(stage37,sort_keys=True,separators=(',',':'))+'\n').encode()
    certificate=dict(schema='opentallas.qwen.native-head-user-relocation.v1',
        qualification='SOURCE_RELOCATION_ONLY_NOT_NATIVE_EXECUTION',
        parent_manifest_sha256=parent_manifest_sha256,
        parent_certificate_sha256=base_manifest['source']['user_relocation_certificate_sha256'],
        stage37_sha256=hashlib.sha256(stage_bytes).hexdigest(),allocation=alloc,
        lowering_commit=lowering_commit)
    raw=(json.dumps(certificate,sort_keys=True,separators=(',',':'))+'\n').encode()
    result['source']['parent_lowering_commit']=result['source']['lowering_commit']
    result['source']['lowering_commit']=lowering_commit
    result['source']['user_relocation_certificate_sha256']=hashlib.sha256(raw).hexdigest()
    result['stages'].append(stage37)
    result['qualification']='PREP_ONLY native HEAD source event; arithmetic, BOOT/calendar and canonical adoption OPEN'
    P.logical_images(result,head_stage37=True)
    return result,certificate


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,action='append',required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();reports=[census(p) for p in a.manifest];alloc=allocation(reports)
    out=dict(schema='opentallas.qwen.native-head-source-lease.v1',status='PREP_ONLY_NOT_ADOPTED',
             allocation=alloc,selected_sources=reports,
             x_lease='existing final residual2 X publication through apply-H last read',
             rstd_lease='existing final fused ROOT publication through apply-H last read',
             h_storage='native W_X BF16 stream, no additional VM region',
             new_first_use='ABSENT_FROM_SELECTED_HEAD_CALENDAR_ZERO_NATIVE_SU_COMMANDS',
             exact_operand_dates='REQUIRES_NATIVE_APPLY_H_WITNESS_AND_PARENT_CALENDAR_JOIN',
             gain_and_prog_region_reuse=False,calendar='NOT_EMITTED',boot='NOT_INSTALLED')
    a.out.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(alloc))

if __name__=='__main__':main()
