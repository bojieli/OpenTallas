#!/usr/bin/env python3
"""Decode real KVWB scalar rows; unknown positions remain unknown, never rectangles."""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path


def inspect(repo, image, manifest, positions=None):
    sys.path.insert(0, str(repo/'tools/hbm_next'))
    from isa_loader import load_isa
    IR, IC = load_isa()
    raw=image.read_bytes(); meta=json.loads(manifest.read_text()); records=IC.decode_all(raw)
    assert len(records)==len(meta['records'])
    rows=[]; command_count=0; envelopes=set()
    for i, ((offset, rec, rx, encoded), source) in enumerate(zip(records, meta['records'])):
        assert source['offset']==offset and source['bytes']==len(encoded)
        if (rec.unit, rec.op)!=('DMA','KVWB_DS'):
            continue
        command_count+=1
        for bank, scalar in IR.expand(rec, rx):
            a,o=scalar.desc['A'],scalar.desc['O']
            assert a.space=='VM' and o.space=='HBM' and a.fmt==o.fmt=='FP32'
            assert a.m==1 and a.n==o.n and o.m and not(o.m&(o.m-1))
            assert not any([a.indexed,o.indexed,a.dyn_mul,o.dyn_mul,a.lstride,o.lstride,a.l1stride,o.l1stride])
            assert a.istride in (0,1) and o.istride in (0,1)
            last=o.base+(o.m-1)*o.stride+o.n*4
            envelopes.add((o.base,last))
            row=dict(resident_command=i,source_record=source['source_record'],DYN_bank=bank,
                     VM_source_word=a.base,words=a.n,ring_base_byte=o.base,
                     ring_slots=o.m,slot_stride_bytes=o.stride,scalar_write_bytes=a.n*4,
                     possible_logical_envelope=[o.base,last],position=None,logical_write_interval=None)
            if positions is not None:
                pos=positions[str(bank)]
                base=o.base+(pos&(o.m-1))*o.stride
                row.update(position=pos,logical_write_interval=[base,base+a.n*4])
            rows.append(row)
    return dict(status='SOURCE_SEMANTICS_AND_MISSING_NATIVE_JOIN; NO_CACHE_ADOPTION',
        image=dict(path=str(image),sha256=hashlib.sha256(raw).hexdigest(),commands=len(records)),
        KVWB_commands=command_count,scalar_rows=len(rows),
        scalar_payload_bytes=sum(x['scalar_write_bytes']for x in rows),
        possible_logical_envelopes=sorted(envelopes),
        semantics='O.m is ring capacity, not rows written. One scalar writes n FP32 words at O.base+(POS & (O.m-1))*O.stride.',
        positions='Explicit supplied bank positions' if positions is not None else 'UNKNOWN: require actual doorbell/CTL.USERS/ROWX bank-position lowering; do not infer from record number',
        normative_evidence=['rtl/hbm_accel/generic/adapters/ot_hgi_dma_record.sv:15-18,130,145-147,158-170',
            'tools/hbm_next/isa_v1r_20261019/hbm_next/isa_rows.py:379-399,526-535'],
        actual_native_path=dict(command='ot_hgi_dma_back_cp_collar CW308={epoch16,bank1,move227,drain32,issue32}',
            selected_wrapper='ot_hgi_dma_back_static_vp4_banks_cp; no position/ring decode inputs',
            write_partner='ot_hbm_svc_wb_kport_q -> ot_hbm_svc_vm_kshare -> PC controller -> external PHY',
            address='Write partner accepts quadrant ordinal o, real sector={o[28:6],q^o[10]^o[15],o[5:0]}; logical byte addresses require inverse fold/partition lowering first',
            completion='Controller mv_src is source consumed; mv_done waits pending sector ACK count to zero. Partner wa counts true PC write completions, not request readiness.',
            missing=['Actual HGI-1R bank position -> resolved227 source command producer',
                     'Logical real-sector -> per-quadrant ordinal + actual VM-source partitioning',
                     'Native fixed issue/drain dates, WB bank/epoch reservations and global drain fence',
                     'Actual SOURCE0 current instance/route closure; endpoint tests do not substitute it']),
        conservative_fence=['Invalidate any retained SOURCE0 window whose true source sectors intersect each resolved write; if position/fold mapping unknown, invalidate all SOURCE0 retained windows at KVWB.',
            'Stop using affected old owned epoch; retire all prior consumers before release/reuse.',
            'Do not issue replacement fill at mv_src/posted retirement: wait actual write completion/ACK drain (mv_done/quiet plus complete global fence).',
            'Refill from updated external memory, then acquire a new owned epoch; current models do not establish cache snooping.'],
        ring_hazard=dict(status='SOURCE_LEVEL_CONDITIONAL_COUNTEREXAMPLE; NO_IMAGE_PATCH',
            selected_ring_slots=128,selected_rows=6,window=128,
            example='If six positions127..132 append before row0 attention, slots0..4 of its [0..127] window are overwritten by128..132.',
            required_join='Confirm actual MTP position/cohort order and ATT/KVUNION mapping; never silently enlarge ring to256 or relocate allocations.'),
        rows=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True);p.add_argument('--image',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--positions',type=Path)
    p.add_argument('--native-roster',type=Path)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('Fresh output required')
    result=inspect(a.repo,a.image,a.manifest,None if a.positions is None else json.loads(a.positions.read_text()))
    if a.native_roster is not None:
        result['actual_native_path']['frozen_native_roster']=json.loads(a.native_roster.read_text())
        result['actual_native_path']['missing'][3]='SOURCE0 DMA writeback producer absent from frozen469cell C11E top: onlyNE/NW bothstk2; require real new source/plan, never0→2 alias'
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['status','KVWB_commands','scalar_rows','scalar_payload_bytes','possible_logical_envelopes']}))
