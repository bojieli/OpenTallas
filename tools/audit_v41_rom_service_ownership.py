#!/usr/bin/env python3
"""Separate pooled ROM delivery from bandwidth fixed to resident expert banks."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def ownership(layers_per_stage, experts_per_island, shards, region_TB_s,
              selected_in_island=1, expert_bytes=18800640, layers=40):
    if min(layers_per_stage,experts_per_island,shards,region_TB_s,selected_in_island)<=0 or selected_in_island>experts_per_island:
        raise ValueError('Invalid bank ownership')
    resident_slots=layers_per_stage*experts_per_island
    return {'resident_expert_shards_per_chip':resident_slots,
            'routed_bytes_per_chip':resident_slots*expert_bytes/shards,
            'selected_shards_per_active_layer':selected_in_island,
            'region_aggregate_TB_s_assumed':region_TB_s,
            'fixed_bank_active_TB_s':region_TB_s*selected_in_island/resident_slots,
            'fully_pooled_expert_read_us':layers*selected_in_island*expert_bytes/(shards*region_TB_s*1e6),
            'uniform_fixed_bank_expert_read_us':layers*resident_slots*expert_bytes/(shards*region_TB_s*1e6),
            'pooling_advantage_factor':resident_slots/selected_in_island}


def main():
    names=['results/architecture/v41_array_mapping.json','configs/hardware/technology_inputs.json',
           'physical/ihp_sg13g2_rom_macro/macro_contract.json',
           'tools/audit_v41_rom_service_ownership.py']
    mapping=json.loads((ROOT/names[0]).read_text())
    rows=[]
    for r in mapping['rows']:
        if r['chips']==80 and r['shards_per_island']==4 and r['backbone_capacity_fits']:
            for q in sorted(set([r['best_route_experts_per_hot_island'],r['worst_route_experts_per_hot_island']])):
                rows.append({'layers_per_stage':r['layers_per_stage'],'experts_per_island':r['max_experts_per_layer_per_island'],
                             **ownership(r['layers_per_stage'],r['max_experts_per_layer_per_island'],4,72,q)})
    out={'schema':'opentallas.v41-rom-service-ownership.v1',
         'status':'bank_ownership_sensitivity_joint_macro_feasibility_unqualified',
         'rows':rows,
         'physical_evidence_findings':[
             'technology_inputs.json ROM density anchor is fabricated 28nm ROM-CIM; bandwidth anchor is a different simulated 28nm ROM-CIM design.',
             'Bandwidth anchor is derived from in-array MAC operations, not measured encoded bytes delivered to separate general-purpose arithmetic.',
             'The 130nm routed IHP macro evidence includes area/periphery costs but its contract explicitly prohibits extrapolation to N5/N4 area or timing.',
             'No evidence inspected establishes the assumed N5 density together with a fully pooled 72TB/s expert region and the required arithmetic contract.'],
         'limits':[
             '72TB/s is an intentionally identical hypothetical region rate for both organizations; it is not a measured ROM property.',
             'Region bandwidth is reserved for routed weights only. Dense reads, compute, fabric and control are excluded.',
             'Fixed-bank model allocates bandwidth equally to every resident expert shard across layers. It is one organization, not a universal ROM bound.',
             'Pooled model assumes the entire regional service can be directed to selected shards with conflict-free banks and sufficient mux/wiring/ports. This requires a physical proof.',
             'Read times sum forty dependent layers. Uniform fixed-bank service makes selected shards concurrent but leaves other bank service unavailable.',
             'Neither changing labels nor selecting fewer experts turns in-array CIM operations into an external read port. Native arithmetic must be qualified separately.'],
         'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/v41_rom_service_ownership.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    for r in rows: print(r['layers_per_stage'],r['selected_shards_per_active_layer'],round(r['fully_pooled_expert_read_us'],3),round(r['uniform_fixed_bank_expert_read_us'],3))


if __name__=='__main__':main()
