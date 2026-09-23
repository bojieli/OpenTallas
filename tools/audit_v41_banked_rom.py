#!/usr/bin/env python3
"""Bank word/depth, compute and power requirements for address-striped ROM."""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def bank_requirements(payload_bytes, delivered_TB_s, word_bytes=256, clock_hz=1e9,
                      delivery=.65, mac_utilization=.65):
    if min(payload_bytes,delivered_TB_s,word_bytes,clock_hz)<=0 or not 0<delivery<=1 or not 0<mac_utilization<=1:
        raise ValueError('Invalid resource assumptions')
    banks=math.ceil(delivered_TB_s*1e12/(word_bytes*clock_hz*delivery))
    depth=math.ceil(payload_bytes/(banks*word_bytes))
    # One byte per two FP4 weights, plus one scale byte per 32 weights.
    mac_rate=delivered_TB_s*1e12/(.5+1/32)
    return {'delivered_TB_s':delivered_TB_s,'independent_logical_banks':banks,
            'word_bytes':word_bytes,'depth_words_per_bank':depth,
            'address_bits':math.ceil(math.log2(depth)),
            'capacity_bytes_per_bank':depth*word_bytes,
            'rounded_capacity_bytes':banks*depth*word_bytes,
            'scalar_MAC_s_to_consume_stream':mac_rate,
            'scalar_lanes_at_assumed_clock_and_utilization':math.ceil(mac_rate/(clock_hz*mac_utilization)),
            'read_path_power_W_by_pJ_per_delivered_bit':{str(e):delivered_TB_s*8*e for e in (.1,.5,1,2)},
            'read_energy_pJ_per_bit_if_100W_budget':100/(delivered_TB_s*8)}


def main():
    names=['results/architecture/v41_array_mapping.json','tools/audit_v41_banked_rom.py']
    a=json.loads((ROOT/names[0]).read_text())
    r=next(r for r in a['rows'] if r['chips']==80 and r['shards_per_island']==4 and r['layers_per_stage']==20)
    rows=[bank_requirements(r['rom_payload_per_chip'],b) for b in (4.5,18,72)]
    expert_shard_bytes=18800640//4
    resident_shards=r['layers_per_stage']*r['max_experts_per_layer_per_island']
    for row in rows:
        stripe=row['independent_logical_banks']*row['word_bytes']
        padded=math.ceil(expert_shard_bytes/stripe)*stripe
        row['expert_shard_padded_bytes']=padded
        row['expert_padding_bytes_per_chip']=resident_shards*(padded-expert_shard_bytes)
        row['backbone_plus_expert_padding_bytes']=r['max_backbone_bytes_per_chip']+row['expert_padding_bytes_per_chip']
        row['backbone_plus_expert_padding_fits']=row['backbone_plus_expert_padding_bytes']<=r['rom_payload_per_chip']
    out={'schema':'opentallas.v41-banked-rom.v1','status':'logical_bank_candidate_joint_physical_contract_unqualified',
         'capacity_bytes_per_chip':r['rom_payload_per_chip'],'rom_area_mm2_assumed':500,
         'remaining_chip_area_mm2':315,'clock_hz_assumed':1e9,'delivery_fraction_assumed':.65,
         'scalar_mac_utilization_assumed':.65,'rows':rows,
         'mapping':'For a packed byte address within a padded expert shard, bank=(address//256)%N, row=expert_base_row+address//(256*N), byte_lane=address%256. Distinct expert base rows include layer identity.',
         'limits':['Bank count and word/depth describe logical service endpoints, not characterized physical macros. A logical bank may need many subarrays and a routed mux hierarchy.',
                   'Expert-major address regions stripe each expert over every bank. Inactive expert capacity shares row depth rather than receiving separately stranded read ports.',
                   'One full stripe per cycle serves one expert stream. Multiple selected experts time-share those banks; this is pooled serial service, not six independent full-rate reads.',
                   'Expert stripe padding is charged for the selected map; dense/head/draft alignment and remaining object placement are still open. The 2% reserve is not usable payload.',
                   'Compute demand applies to packed routed FP4/scale streams only; dense formats require a separate lane/format ledger.',
                   'Read energy includes whichever ROM/mux/wire/scale delivery costs the physical measurement defines. Arithmetic, leakage, clock, SRAM, fabric and external memory remain additional.',
                   '100W read allocation is only an energy sensitivity; it is not a selected chip or package power cap.',
                   'No N5 density/clock/energy is inferred from the 130nm macro. No physical feasibility or throughput claim.'],
         'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/v41_banked_rom.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
