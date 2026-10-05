#!/usr/bin/env python3
"""Exact pins and finite address calendar; never production/physical admission."""
import hashlib
import json
from pathlib import Path
import subprocess
from verify_qwen_kv_successor_evidence import verify as predecessor_verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002'

def verify():
    predecessor_verify()
    def read(p):return json.loads(p.read_text())
    def check(p,h):
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('pin mismatch: '+p)
    artifacts=read(OUT/'artifact-sha256-r1.json')
    for p,h in artifacts.items():check(p,h)
    for p,h in read(OUT/'implementation-pins-r1.json').items():check(p,h)
    extra=read(OUT/'dependency-pins-r1.json')
    for p,receipt in extra.items():
        check(p,receipt['sha256'])
        raw=subprocess.check_output(['git','show',receipt['commit']+':'+p],cwd=ROOT)
        if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:raise ValueError('dependency commit pin: '+p)
    m=read(OUT/'model-r4.json')
    check('results/uarch/qwen_rom_kv_successor_20261002/model-r7.json',m['predecessor_successor_sha256'])
    for p,h in m['implementation_sha256'].items():check(p,h)
    for p,h in m['source_sha256'].items():check(p,h)
    if len(m['calendar']['rows'])!=36:raise ValueError('36 sequential layers')
    for r in m['calendar']['rows']:
        if r['cohorts']!=2084 or r['maximum_descriptor_heads']!=8:raise ValueError('bounded LEN1 descriptor heads')
        if r['command_count_per_stack']!=[32736]*4 or r['owned_data_and_grant_count_per_stack']!=[65472]*4:raise ValueError('once-only byte debit')
        for name,bound in [('peak_live_cohorts',128),('peak_words_per_group_lane_pool',80),('peak_pending_entries_per_PC',64),('peak_write_slots_per_PC',4)]:
            if r[name]>bound:raise ValueError('finite credit '+name)
    if m['request_allocator']['heterogeneous_write_request_LEN']!=1:raise ValueError('r14 actual write payload')
    if m['admission']['hardware'] or m['admission']['production_qualified'] or m['calendar']['adopted_rate'] is not None or m['physical']['actual_sustained_PHY_Bps'] is not None:raise ValueError('unqualified admission')
    if m['calendar']['meets_3k_in_conditional_reservation']:raise ValueError('expected explicit finite deficit')
    return dict(verdict='PASS_PINS_AND_CONDITIONAL_FINITE_DEFICIT_ONLY',source_pins=len(m['source_sha256']),
        dependency_pins=len(extra),artifacts=len(artifacts),originals=28,layers=36,physical=False,production=False)

if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
