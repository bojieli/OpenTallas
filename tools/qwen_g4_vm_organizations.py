#!/usr/bin/env python3
"""Finite-port alternatives on retained issued trace; not physical proof."""
import json
from collections import defaultdict,Counter
from pathlib import Path
try:
 from tools.qwen_g4_trace_banks import load_csv
except ModuleNotFoundError:
 from qwen_g4_trace_banks import load_csv

def evaluate(rows,banks=4,fold=0,lane_banks=False,read_replicas=1):
    events=Counter(); max_r=max_w=0; estimated_stall=0; same_word_merges=0
    for cycle in rows:
        rd=defaultdict(set);wr=defaultdict(set); masks={}
        def bank(word,lane):
            b=(word^(word>>fold) if fold else word)&(banks-1)
            return (b,lane) if lane_banks else b
        for r in cycle['vm_reads']:
            word,lane=divmod(r['addr'],16);rd[bank(word,lane)].add(word)
        for w in cycle['vm_writes']:
            word,mask=w['addr'],w['mask']
            if not mask:continue
            if word in masks:
                same_word_merges+=1
                if masks[word]&mask:events['overlapping_lane_writes_unqualified']+=1
            masks[word]=masks.get(word,0)|mask
        for word,mask in masks.items():
            if lane_banks:
                for lane in range(16):
                    if mask>>lane&1:wr[bank(word,lane)].add(word)
            else:wr[bank(word,0)].add(word)
        nr=max(map(len,rd.values()),default=0);nw=max(map(len,wr.values()),default=0)
        max_r=max(max_r,nr);max_w=max(max_w,nw)
        events['read_conflict_cycles']+=nr>read_replicas
        events['write_conflict_cycles']+=nw>1
        # Counts replay service only, not whole program stalls (dependent timing changes).
        estimated_stall+=max((nr+read_replicas-1)//read_replicas,nw,1)-1
        for b in rd:
            events['read_write_same_address_unqualified']+=len(rd[b]&wr.get(b,set()))
    return dict(banks=banks,fold=fold,lane_banks=lane_banks,read_replicas=read_replicas,
                logical_single_read_single_write_slices=banks*(16 if lane_banks else 1)*read_replicas,
                storage_replication=read_replicas,max_distinct_reads_per_bank=max_r,
                max_distinct_writes_per_bank=max_w,events=dict(events),same_word_merges=same_word_merges,
                isolated_replay_extra_service_cycles=estimated_stall,
                unchanged_trace_ports_fit=not any(events.values()))

def report():
    root=Path(__file__).resolve().parents[1]
    rows=load_csv(root/'results/contracts/qwen_g4_boundary_trace.csv.gz')
    return dict(scope='synthetic issued trace only; no full program or physical timing claim',
      cycles=len(rows),candidates=[evaluate(rows),evaluate(rows,lane_banks=True),
      evaluate(rows,banks=4,fold=3),evaluate(rows,banks=4,fold=3,read_replicas=2),
      evaluate(rows,banks=8,fold=2),evaluate(rows,banks=8,fold=2,lane_banks=True)])
if __name__=='__main__':print(json.dumps(report(),indent=2))
