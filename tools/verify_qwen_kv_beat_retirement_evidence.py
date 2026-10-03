#!/usr/bin/env python3
"""Verify failed causal alternative, source recipe journal and old immutable pins."""
import gzip
import hashlib
import json
from collections import Counter
from uarch_model_qwen_kv_beat_retirement import ROOT,OUT,price,bounds,A
from qwen_kv_beat_retirement_composition import build
from verify_qwen_kv_credit17_evidence import verify as predecessor_verify

def verify():
    predecessor_verify()
    read=lambda p:json.loads(p.read_text())
    for name in ('artifact-sha256-r1.json','implementation-pins-r1.json'):
        for p,h in read(OUT/name).items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('pin '+p)
    m=read(OUT/'model-r3.json');raw=read(OUT/'model-r2.json');old=read(ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json')
    for name in ('source_sha256','peer_input_sha256'):
        for p,h in m[name].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('source '+p)
    if m!=build() or m['cells']!=price(old):raise ValueError('composition/pricing replay')
    if hashlib.sha256((ROOT/'tools/uarch_model_qwen_kv_beat_retirement.py').read_bytes()).hexdigest()!=m['implementation_sha256']:raise ValueError('completed implementation')
    diagnostic=read(OUT/'model-r1.json')
    if hashlib.sha256((OUT/'inputs/pre-Ampere-diagnostic-r1.py').read_bytes()).hexdigest()!=diagnostic['implementation_sha256']:raise ValueError('diagnostic preserved')
    rows=[json.loads(l) for l in (OUT/'layer-journal-r2.jsonl').read_text().splitlines()]
    if rows!=raw['calendar']['rows'] or len(rows)!=36:raise ValueError('incremental layers')
    recipes=[Counter() for _ in range(36)];counts=Counter()
    with gzip.open(OUT/'causal-journal-r2.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line);layer=r['layer'];kind=r['kind'];base=r['base'];n=r['length'];g=r['group']
            if A.burst_group(base,n)!=g:raise ValueError('source bank ownership')
            words=set() if kind in ('KW','VW') else A.cohort_words(layer,base,n)[0]
            if r['words']!=len(words) or not r['all_quarter_masks_complete'] or not r['all_grants_consumed'] or not r['copy_readers_drained_at_visible'] or r['actual_production_journal']:raise ValueError('causal visibility/drain scope')
            if r['retired_third_ps']<r['allocated_third_ps']:raise ValueError('causal lease')
            recipes[layer][g,kind,base,n]+=1;counts[layer]+=1
    for layer,row in enumerate(rows):
        expected=Counter()
        for g in range(8):
            cursor=A.GroupCursor(layer,g)
            while cursor.head is not None:
                expected[(g,*cursor.head)]+=1;cursor.advance()
        if recipes[layer]!=expected or counts[layer]!=2084:raise ValueError('complete source demand coverage')
        if row['command_count_per_stack']!=[32736]*4 or row['owned_DATA_GRANT_count_per_stack']!=[65472]*4:raise ValueError('port/demand')
        if row['peak_live_cohorts']>128 or row['peak_pending_per_PC']>64 or row['peak_words_per_pool']>80 or row['peak_write_per_PC']>4 or not row['all_tags_and_epochs_drained']:raise ValueError('finite capacities')
    if m['calendar']['clears1percent'] or m['calendar']['meets3k'] or m['admission']['hardware'] or m['admission']['adopted'] or m['calendar']['actual_rate'] is not None:raise ValueError('lost rejection')
    if m['cells']['mutable_storage_protection_area_mm2'] is not None or m['admission']['actual_PHY_Bps'] is not None:raise ValueError('unknown erased')
    return dict(verdict='PASS_EVIDENCE_OF_REJECTED_JOINED_POLICY',sources=57,originals=28,layers=36,cohort_causal_records=sum(counts.values()),conditional_us=m['calendar']['total_conditional_s']*1e6,gain_percent=100*m['calendar']['gain_fraction'],independent_full_calendar=False,hardware=False,production=False)

if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
