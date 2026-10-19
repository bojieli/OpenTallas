#!/usr/bin/env python3
"""Compare calpipe-owned exact cyclic admission manifests. No player/word/schema changes."""
import argparse
import hashlib
import json
import math
from pathlib import Path

def compare(inputs, out):
    rows=[]
    for path in inputs:
        s=json.loads(path.read_text());area=s['rom_area_per_macro'];H=s['H'];S=s['superframe']
        expanded=max(v['words'] for v in s['expanded_lists']['lists'].values())
        mask_words={}
        for c,starts in s['expanded_link_starts'].items():
            union=sorted({(t%H,seg,u) for t,seg,u in starts})
            # A periodic mask table has one GO per distinct base-H consumer edge. Wait splits are bounded below;
            # exact frame compiler emits final words once origin/startup/phase clock contract is selected.
            mask_words[c]=len(union)+1
        for encoding,leaf_banks,leaf_words,list_words,phase_state in [
                ('expanded leaf + expanded legacy OVL',s['leaf_banks_expanded'],s['leaf_expanded'],expanded,'none'),
                ('masked leaf + expanded legacy OVL',s['leaf_banks_mask'],s['leaf_base'],expanded,'leaf only'),
                ('masked leaf + masked OVL',s['leaf_banks_mask'],s['leaf_base'],max(mask_words.values()),'leaf and OVL')]:
            list_banks=4*math.ceil(list_words/4096)
            rows.append(dict(frame_tokens=s['frame_tokens'],encoding=encoding,H=H,superframe=S,
                leaf_words=leaf_words,leaf_rom_banks=leaf_banks,list_words_per_direction=list_words,
                list_rom_banks_total=list_banks,total_control_rom_area_um2=(leaf_banks+list_banks)*area,
                leaf_counter_bits=s['leaf_counter_bits_expanded'] if phase_state=='none' else s['leaf_time_bits_per_H'],
                phase_state=phase_state,uses_existing_leaf_22bit_period=(phase_state!='none' or s['leaf_counter_bits_expanded']<=22),
                output_tok_s=s['lifecycle_tok_s'],production_bound=s['production_bound']))
        for u,b in s['boundaries'].items():
            if b['load_slot']['bank_load']>=b['init']:raise ValueError(f'{path}: init before contextbankload user{u}')
            if b['retire_end']>=b['load_slot']['bank_load']+S:raise ValueError(f'{path}: active-generation reload user{u}')
        for c,v in s['expanded_lists']['lists'].items():
            if v['words']>4096:raise ValueError(f'{path}: list capacity overrun {c}')
    record=dict(schema='opentallas.qwen.phase-representation-comparison.v2',model_only=True,
        input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},options=rows,
        startup_blockers=['expanded origin247497 is a steady cyclic rotation; initial epoch needs an explicit cold prefix/origin0 plan',
            'align actual listplayer/pin launch edges with positive leaf L0 anchor before any first-token claim',
            'user0 initial context and embedding prelude must precede its first L0/attention exchange',
            'OVL raw context loads require full face identity validation, measured candidateRXslot+3',
            'root must select exact word/schema before wrappers change; no phase count frozen'])
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('inputs',type=Path,nargs='+');p.add_argument('--out',type=Path,required=True);a=p.parse_args();compare(a.inputs,a.out)
