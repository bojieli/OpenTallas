#!/usr/bin/env python3
"""Preserve frozen transport evidence and verify independent finite wait math."""
import hashlib
import json
from pathlib import Path
from verify_qwen_kv_credit_allocator_evidence import verify as predecessor_verify
from qwen_rom_kv_stall_bound import build as bounds
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_rom_kv_stall_attribution_20261002'

def verify():
    predecessor_verify()
    def read(p):return json.loads(p.read_text())
    def check(p,h):
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('pin mismatch: '+p)
    for name in ('artifact-sha256-r1.json','implementation-pins-r1.json'):
        for p,h in read(OUT/name).items():check(p,h)
    trace=read(OUT/'model-r3.json');old=read(ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json')
    for p,h in trace['source_sha256'].items():check(p,h)
    for p,h in trace['implementation_sha256'].items():check(p,h)
    check('results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json',trace['predecessor_sha256'])
    journal=[json.loads(l) for l in (OUT/'layer-journal-r1.jsonl').read_text().splitlines()]
    if journal!=trace['rows'] or len(journal)!=36:raise ValueError('incremental journal reconciliation')
    if trace['controller']['command_counts']!=old['controller']['command_counts'] or trace['controller']['commands_per_shared_path']!=old['controller']['commands_per_shared_path']:raise ValueError('command service perturbed')
    for row in journal:
        expected=old['calendar']['rows'][row['layer']]
        for field in ('reservation_sha256','command_count_per_stack','owned_data_and_grant_count_per_stack','fill_ready_ps','all_grants_ps','peak_live_cohorts','peak_pending_entries_per_PC','peak_write_slots_per_PC'):
            if row[field]!=expected[field]:raise ValueError('frozen replay '+field)
        elapsed=row['all_grants_ps']-row['begin_ps']
        waits=sum(row['diagnostic']['allocator_exclusive_wait_ps'].values())
        if waits!=elapsed:raise ValueError('exclusive allocator time accounting')
        work=row['diagnostic']['measured_group_lease_work_ps']
        if max(work.values())>16*elapsed or sum(work.values())>128*elapsed:raise ValueError('lease occupancy proof')
    if read(OUT/'bound-contract-r1.json')!=bounds():raise ValueError('bound replay')
    b=read(OUT/'bound-contract-r1.json')
    if b['fixed_lease']['minimum_uniform_group_credits']!=17 or b['fixed_lease']['minimum_global_credits']!=129:raise ValueError('integer requirement')
    if trace['hardware'] or trace['production'] or trace['adopted_rate'] is not None:raise ValueError('unsupported admission')
    return dict(verdict='PASS_FROZEN36_WAIT_ACCOUNTING_AND_SCOPED_LOWER_BOUNDS',sources=len(trace['source_sha256']),originals=28,layers=36,PHY=False,production=False,hardware=False)

if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
