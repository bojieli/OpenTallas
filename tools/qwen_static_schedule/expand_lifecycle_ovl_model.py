#!/usr/bin/env python3
"""Emit and check origin0 legacy32 OVL lists from Calpipe's selected expanded lifecycle MODEL.
Does not qualify user0 cold prelude or a production absolute anchor.
"""
import argparse
import hashlib
import json
from pathlib import Path
from .d2d_phase_storage_model import words

# Canonical paired context slot: duration from segment start to its calendar's last event +1.
SPAN={('C_tx',0):42,('K_rx',0):40,('C_rx',0):35,('K_tx',0):35,
      ('C_tx',1):30,('K_rx',1):32,('C_rx',1):254,('K_tx',1):255}

def emit(inp,out):
    s=json.loads(inp.read_text());S=s['superframe'];D0=16;checks={};out.mkdir(parents=True,exist_ok=True)
    for c,seq in s['expanded_link_starts'].items():
        seq=sorted((int(t),int(seg),int(u)) for t,seg,u in seq)
        for (t,sg,u),(n,ns,nu) in zip(seq,seq[1:]+[(seq[0][0]+S,seq[0][1],seq[0][2])]):
            if t+SPAN[c,sg]>n:raise ValueError(f'{c} calendar overlaps {t,sg,u} vs {n,ns,nu}')
        fixed=[(t+D0,seg,u) for t,seg,u in seq]
        ws=words(fixed,S)
        if len(ws)>4096:raise ValueError(f'{c}: {len(ws)} entries exceed4096')
        # Independent absolute-time decode of emitted GO entries, including whole-superframe wrap.
        decoded=[];t=0
        for w in ws:
            t+=w>>12
            if w&2048:decoded.append((t,(w>>10)&1,(w>>8)&3))
        if decoded!=fixed or t!=S or not ws[-1]&128:raise ValueError(f'{c}: bad legacy encoding')
        (out/f'list_{c}.memh').write_text(''.join(f'{w:08x}\n' for w in ws))
        checks[c]=dict(starts=len(seq),words=len(ws),address_bits=(len(ws)-1).bit_length(),
            first_raw=seq[0][0],last_raw=seq[-1][0],first_encoded=fixed[0][0],
            last_end_raw=seq[-1][0]+SPAN[c,seq[-1][1]],wrap_playhead_slack=S+seq[0][0]-seq[-1][0]-SPAN[c,seq[-1][1]],
            minimum_entry_dt=min(w>>12 for w in ws),logical_word_bits=32)
    result=dict(schema='opentallas.qwen.expanded-origin0-ovl.model.v1',production_bound=False,
        input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),H=s['H'],superframe=S,origin=0,D0=D0,lists=checks,
        context_slot=s['context_slot_binding'],normal_tokens_per_superframe=s['normal_tokens_per_superframe'],
        leaf_L0_anchor_constraint='list_anchor +16+ measured(player output + pin launch ages)',
        player_changes='AW12 for selectedF16 (3260words); physical4096x72 ROM unchanged; existing32-bit entry decoder unchanged',
        unresolved=['user0 initial validated context/embedding prelude must precede rawL0',
                    'absolute epoch FIRST and wrapper pin ages not yet production bound',
                    'fullidentity ctx_x129 output and measured+3 load age not yet implemented',
                    'pergeneration host record source/context identities require actual cyclic bench'])
    (out/'origin0_manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();emit(a.input,a.out)
