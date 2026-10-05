#!/usr/bin/env python3
"""Verify the one completed17 calendar, complete composition and historical pins."""
import hashlib
import json
from uarch_model_qwen_kv_credit17 import ROOT, OUT, sizing
from qwen_rom_kv_credit17_compose import build
from verify_qwen_kv_stall_evidence import verify as predecessor_verify

def verify():
    previous=predecessor_verify()
    read=lambda p:json.loads(p.read_text())
    check=lambda p,h: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    for name in ('artifact-sha256-r1.json','implementation-pins-r1.json'):
        for p,h in read(OUT/name).items():
            if not check(p,h):raise ValueError('pin mismatch '+p)
    m=read(OUT/'model-r3.json');raw=read(OUT/'model-r2.json')
    for name in ('source_sha256','implementation_sha256','source_join_inputs_sha256'):
        for p,h in m[name].items():
            if not check(p,h):raise ValueError('source mismatch '+p)
    if m!=build():raise ValueError('independent composition replay')
    if m['calendar']!=raw['calendar']:raise ValueError('composition changed calendar')
    old=read(ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json')
    if m['cells']!=sizing(old):raise ValueError('cell price replay')
    c=m['ONE_configuration'];expected={'return_groups_per_stack':8,'column_paths_per_stack':4,'global_fill_lanes':7,'global_cohort_slots':136,'group_cohort_slots':17,'pending_per_PC':68,'words_per_pool':85}
    for key,value in expected.items():
        if c[key]!=value:raise ValueError('topology '+key)
    rows=m['calendar']['rows']
    if len(rows)!=36:raise ValueError('whole token')
    for row in rows:
        if row['cohorts']!=2084 or row['command_count_per_stack']!=[32736]*4 or row['owned_data_and_grant_count_per_stack']!=[65472]*4:raise ValueError('traffic')
        if row['peak_live_cohorts']>136 or row['peak_pending_entries_per_PC']>68 or row['peak_words_per_group_lane_pool']>85 or row['peak_write_slots_per_PC']>4:raise ValueError('finite capacity')
        if not row['all_reverse_grants_reserved'] or row['physical_or_payload_qualification']:raise ValueError('lifecycle scope')
    for key in ('hardware','new_RTL','new_PnR','physical','adoption'):
        if m['admission'][key]:raise ValueError('unsupported admission')
    if m['calendar']['clears_model_1percent'] or m['calendar']['meets_3k_conditional'] or m['calendar']['adopted_rate'] is not None:raise ValueError('lost FAIL')
    if m['physical']['actual_sustained_PHY_Bps'] is not None or m['cells']['mutable_storage_protection_area_mm2'] is not None:raise ValueError('unknown silently priced')
    if m['routing_cost']['fill_control_track_deficit']!=6613:raise ValueError('route deficit')
    return dict(verdict='PASS_EVIDENCE_FOR_FAILED_ONE17_COMPOSITION',sources=previous['sources'],originals=previous['originals'],layers=36,conditional_us=m['calendar']['total_conditional_s']*1e6,hardware=False,production=False,independent_full_calendar_replayed=False)

if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
