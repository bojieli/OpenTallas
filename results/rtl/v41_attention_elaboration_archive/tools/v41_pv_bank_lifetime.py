#!/usr/bin/env python3
"""Exact storage event proof for a proposed two-word PV load interface.
No RTL arithmetic result or implemented controller verdict is claimed.
Old value is read on a same-edge nonblocking write, matching attn_hdp.
"""
import json
from pathlib import Path

def skew(k):
    return 0 if k % 8 == 0 else 3*(k%8-1)

def analyze(banks,words=2,blocks=20):
    H,TD,R,DPT=16,32,2,8
    load_cycles=(H+words-1)//words
    interval=max(load_cycles,DPT)
    # At engine interface: e boundary -> tile R0 -> operand write (2edges).
    # Issue: e -> R0 -> dequant -> multiply operand capture (3edges+skew).
    events=[];violations=[]
    for block in range(blocks-banks):
        start=block*interval
        first_issue=start+load_cycles-1 # last load may coincide with first issue
        last_issue=first_issue+DPT-1
        overwrite_start=(block+banks)*interval
        for k in range(TD):
            old_last_read=last_issue+3+skew(k)
            next_write=overwrite_start+(k//R)//words+2
            event=dict(block=block,bank=block%banks,row=k,last_read=old_last_read,
                       first_overwrite=next_write,margin=next_write-old_last_read)
            events.append(event)
            if next_write<old_last_read:violations.append(event)
    return dict(banks=banks,p_words_per_cycle=words,block_interval=interval,
                storage_bytes=64*banks*16*32*2,
                min_margin=min(e['margin'] for e in events),
                violation_count=len(violations),first_violation=violations[0] if violations else None,
                events=events)

def replay_corruption(banks):
    """Read old value first, then NBA writes; observe actual replaced block IDs."""
    events={};blocks=20
    for b in range(blocks):
        start=b*8
        for k in range(32):
            events.setdefault(start+k//4+2,[]).append(('write',b,k))
            for beat in range(8):
                events.setdefault(start+7+beat+3+skew(k),[]).append(('read',b,k))
    memory={};bad=[]
    for cycle,ev in sorted(events.items()):
        for typ,b,k in ev:
            if typ=='read' and memory.get((b%banks,k)) != b:
                bad.append(dict(cycle=cycle,expected=b,observed=memory.get((b%banks,k)),row=k))
        for typ,b,k in ev:
            if typ=='write':memory[(b%banks,k)]=b
    return dict(errors=len(bad),first=bad[0] if bad else None)

if __name__=='__main__':
    out=Path(__file__).resolve().parents[1]/'pv-bank-lifetime.json'
    rec=dict(scope='Proposed PWORDS2 lifetime proof and event replay. No implemented numeric RTL result.',
             source_reference='rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv: stationary NBA write/read and skew; engine e boundary',
             assumptions=['all32rows populated','first PVissue overlaps last pword acceptance','8issuecycles/block','read-before-write NBA semantics','no guard/control bubbles'],
             candidates=[analyze(n) for n in (3,4)],
             overwrite_replay={str(n):replay_corruption(n) for n in (3,4)})
    out.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({str(n):{k:v for k,v in analyze(n).items() if k!='events'} for n in (3,4)}))
