#!/usr/bin/env python3
"""MODEL ONLY: compare cyclic OVL representation storage; no production word/schema changes.

Uses the existing compiler frame and measured hard-ROM geometry. Inserts the already canonical logical MU
context selector (kind12/beat1, wire beat0) into a private segment compiler instance, so the comparison does not
mistake an omitted receive for a free admission slot. Unified phase eligibility remains calpipe's authority.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from . import mu_d2d_ovl as D

ROOT = Path(__file__).resolve().parents[2]

def words(starts, period):
    """Existing 32-bit list encoding, fixed common phase origin, only final wait entry wraps."""
    out, prev = [], 0
    for t, seg, user in sorted(starts):
        dt = t-prev
        while dt >= 1<<20:
            out.append(((1<<20)-1)<<12)
            dt -= (1<<20)-1
        if dt < 4: raise ValueError(f'list entries {dt} edges apart')
        out.append((dt<<12)|(1<<11)|(seg<<10)|(user<<8));prev=t
    dt=period-prev
    while dt>=1<<20:
        out.append(((1<<20)-1)<<12);dt-=(1<<20)-1
    if dt<4:raise ValueError('wrap too near previous event')
    out.append((dt<<12)|(1<<7))
    return out

def compare(out, frame=16, calpipe_opcal=None):
    overlay_hash = None
    if calpipe_opcal:
        spec=importlib.util.spec_from_file_location("qwen_static_schedule.mu_opcal_model",calpipe_opcal)
        overlay=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay);D.O=overlay
        overlay_hash=hashlib.sha256(calpipe_opcal.read_bytes()).hexdigest()
    old=D.seg_msgs
    def paired(*args,**kwargs):
        seg,law=old(*args,**kwargs)
        # Canonical logical selector. The host opaque payload still carries wire beat0.
        seg['tok_rx'].append(dict(src='K',cyc=2,tx_port=1,rx_port=1,kind=12,beat=1))
        return seg,law
    D.seg_msgs=paired
    try:b=D.build(frame=frame,kv_codec=2,kv_prog=True)
    finally:D.seg_msgs=old
    H=b['cal']['H'];lists=D.start_lists(b)
    leaf_error=None
    try:leaf_entries=len(D.O.leaf_list(b['cal']))
    except D.ScheduleError as exc:
        m=re.search(r'(\d+) leaf entries do not fit',str(exc))
        if not m:raise
        leaf_entries=int(m.group(1));leaf_error=str(exc)
    leaf_capacity=dict(validation_error=leaf_error,base_entries=leaf_entries,base_4096_banks=math.ceil(leaf_entries/4096),
        cohort2H_estimate=leaf_entries+3,qualification='cohort2H count still requires calpipe INIT/RETIRE emission manifest; +3 is three INIT head variants only')
    collisions=D.occupancy_check(lists,b['im'],H)
    if collisions:raise ValueError(collisions[:3])
    encoded,meta=D.encode(lists,H)
    origin=meta['origin'];d0=meta['D0']
    active={c:[] for c in D.CALS}
    spans={}
    for sg, cal in b['im'].items():
        for c,x in cal.items():spans[(c,0 if sg in ('req','rsp') else 1)]=x['occ'][1]-x['occ'][0]
    for c,seq in encoded.items():
        t=0
        for w in seq:
            t+=w>>12
            if w&(1<<11):active[c].append((t,(w>>10)&1,(w>>8)&3))
    occupied=[]
    for c,seq in active.items():
        for t,s,u in seq:occupied.append((t,t+spans[(c,s)]))
    occupied.sort();merged=[]
    for a,z in occupied:
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(z,merged[-1][1]))
        else:merged.append((a,z))
    boundary_gap=(merged[-1][1]-H,merged[0][0])
    rom=json.loads((ROOT/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.json').read_text())
    area=rom['area']['macro_area_um2']; candidates=[]
    for p in (2,4,8,16,32):
        # Exact upper-bound enumeration: every user active every phase. Real INIT/RETIRE masks can only reduce GO
        # words; long disabled gaps can add wait-only words, measured separately once calpipe supplies eligibility.
        sizes={}
        for c,seq in active.items():sizes[c]=len(words([(t+i*H,s,u) for i in range(p) for t,s,u in seq],p*H))
        for packing in (1,2):
            banks={c:math.ceil(math.ceil(n/packing)/4096) for c,n in sizes.items()}
            candidates.append(dict(representation='expanded32',phases=p,packing=packing,entries=sizes,
                logical_period=p*H,fits_current_leaf_22bit_period=(p*H < 1<<22),logical_address_bits=max((n-1).bit_length() for n in sizes.values()),
                physical_banks=banks,macro_area_um2=sum(banks.values())*area,
                mask_or_phase_rtl='none; AW/ROM banking only',
                extra_pipeline_edges=0 if packing==1 else 1,
                minimum_list_dt=min(w>>12 for seq in encoded.values() for w in seq),
                qualification='packing2 needs registered halfword select, MIN_DT>=5; no start edge shift'))
        for width in (32,72):
            if p > width-24:continue
            sizes={c:len(seq) for c,seq in encoded.items()}
            candidates.append(dict(representation=f'mask{width}',phases=p,entries=sizes,
                physical_banks={c:1 for c in D.CALS},macro_area_um2=4*area,
                phase_state_bits_per_player=(p-1).bit_length(),
                new_contract='phase mask for GO words, wrap only for wait words; common phase increments at H boundary',
                qualification='requires new decoder/reserved-bit validation and all wrapper/leaf/context clocks agree'))
    result=dict(schema='opentallas.qwen.ovl-phase-storage-comparison.candidate.v1',model_only=True,
        source=dict(shared='844953bfc',canonical_context='results/rtl/mu_qwen_1018/kvctx/README.md#2',
                    controller_adapter='14114cd77'),
        frame_tokens=frame,calpipe_opcal_sha256=overlay_hash,leaf_capacity=leaf_capacity,H=H,origin=origin,D0=d0,rate=b['cal']['aggregate_tok_s'],
        calendar_entries={sg:{c:len(x['img']) for c,x in cs.items()} for sg,cs in b['im'].items()},
        per_user_go_counts={c:{str(u):sum(v==u for t,s,v in seq) for u in range(4)} for c,seq in active.items()},
        canonical_context=dict(logical_mu=dict(kind=12,beat=1,K_cycle=2),logical_user0=dict(kind=12,beat=0,K_cycle=3),
            wire_beat=0,identity_bits=129,wire_record_bits=548,controller_bank_load_after_rx_slot=3,bank_load_qualification="candidate full-identity validated observer, pending RTL measurement; legacy raw observer2 is unqualified",
            identity_validation='full face context receiver checks digest/image epoch/cap; raw observer alone insufficient'),
        playhead_quiet_boundary=dict(last_busy_offset=boundary_gap[0],next_start_offset=boundary_gap[1],
            width=boundary_gap[1]-boundary_gap[0],qualification='link playheads only: does not prove programme retirement or host/controller quiescence'),
        physical_rom=dict(depth=4096,width=72,area_um2=area,outline_um=[38.016,62.91]),candidates=candidates,
        unresolved=['calpipe canonical INIT/RETIRE eligibility and per-user context-load edge manifest',
            'active request and response must share originating exchange eligibility, not independent start-time masks',
            'MU paired context selector must be emitted on both ends; missing-selector model cannot qualify admission',
            'retire-to-next-INIT window must include actual native/KV/controller lifetime, not merely link quiet',
            'P<=8 is a development candidate, not an irreversible admission count limit'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['H','origin','D0','rate','playhead_quiet_boundary']}))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--frame',type=int,default=16);a.add_argument('--calpipe-opcal',type=Path);v=a.parse_args();compare(v.out,v.frame,v.calpipe_opcal)
