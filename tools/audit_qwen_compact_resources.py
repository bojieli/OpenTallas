#!/usr/bin/env python3
"""Compact dense-model capacity and conditional service ceilings, no deadline."""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    names=['configs/models/qwen3-8b.json','configs/architecture/rom_hbm_review_v3.json',
           'results/architecture/redesign_recurrence_feasibility.json',
           'tools/audit_qwen_compact_resources.py']
    m,c,r=[json.loads((ROOT/n).read_text()) for n in names[:3]]
    checkpoint=m['checkpoint_bytes'];weight=m['dense_weight_bytes']
    rom_density=c['rom_bytes_per_mm2_assumed'];reserve=c['rom_reserved_fraction']
    kv=8192*36*4096
    rows=[]
    for area in (300,400,500,815):
        payload=area*rom_density*(1-reserve)
        rows.append({'rom_mm2_per_die':area,'usable_ROM_bytes_per_die':payload,
                     'minimum_dies_for_full_bf16_checkpoint':math.ceil(checkpoint/payload),
                     'non_rom_mm2_per_815mm2_die':815-area})
    floor=r['linear_dependency_floor_us_by_recurrence_cycles']['1']
    rates=[]
    for bandwidth in (4.5,18,72):
        memory=(weight+kv)/(bandwidth*1e6)
        latency=max(memory,floor)
        rates.append({'aggregate_delivered_weight_and_KV_TB_s_assumed':bandwidth,
                      'single_shared_service_weight_KV_floor_us':memory,
                      'unchanged_sequential_contract_combined_floor_us':latency,
                      'conditional_single_sequence_tokens_s_ceiling':1e6/latency})
    out={'schema':'opentallas.qwen-compact-resources.v1',
         'status':'capacity_and_contract_bounds_not_physical_performance',
         'full_bf16_checkpoint_bytes':checkpoint,'active_bf16_weight_bytes':weight,
         'context':8192,'kv_bytes':kv,'capacity_rows':rows,
         'single_die_density_multiplier_required_if_all_815mm2_ROM':checkpoint/(815*rom_density*(1-reserve)),
         'minimum_ROM_area_mm2_full_checkpoint':checkpoint/(rom_density*(1-reserve)),
         'ideal_SRAM_area_mm2_for_KV_only':kv/c['sram_bytes_per_mm2_assumed'],
         'service_sensitivity':rates,
         'limits':['Full retained BF16 checkpoint, no quantization or external weight capacity credited.',
                   'All-ROM die allocation is a capacity impossibility screen, not a viable compute die.',
                   'KV assumes 8K BF16 cache and excludes allocator, ECC and scratch. Reading all dense KV once is a byte-service screen, not an executable attention ledger.',
                   'Shared weight/KV service rows assume one aggregate bottleneck and perfect concurrency across assigned regions; separate ports require separate bounds.',
                   'Maximum of independent memory and recurrence floors is a necessary bound, not proof that overlap is realizable.',
                   'Sequential bound assumes whole-producer dependencies and unchanged whole-K RNE contract at 1GHz; a different admitted numerical/scheduling design needs a new bound.',
                   'Bandwidth values are sensitivities only, not qualified ROM rates. Power, bank locality, compute throughput, attention and cross-chip service still need qualification.',
                   'A compact multi-die package may be local at system level but is not a single physical tile with free inter-die links.'],
         'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/qwen_compact_resources.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('input_sha256','limits')},indent=2))


if __name__=='__main__':main()
