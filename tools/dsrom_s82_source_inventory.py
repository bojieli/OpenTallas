#!/usr/bin/env python3
"""Small intake list and implementation interfaces for the immutable 717 S82 map.

Print paths for explicit git restore; do not import the W2 historical attempts.
Peers can consume the source checkout directly, without a second payload copy.
"""
import argparse, gzip, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = '717a32dcf35c09ccff432068691a3da40b610863'
BASE = 'results/uarch/dsrom_s73_pair1_20261003/'
SELECTED = BASE + 'baseline_s82_successor_r1/'
FILES = ['tools/dsrom_s73_pair1.py', 'tools/dsrom_s73_pair1_records.py'] + [
    SELECTED + n for n in (
        'model.json', 'inventory.json', 'area_ledger.json', 'matrix_map.jsonl.gz',
        'stage_map.json', 'auxiliary_map.json', 'shipped_weight_directory.jsonl.gz',
        'physical_contract.json', 'uarch_contract.json', 'return_baseline.json',
        'indexer_multicast_model.json', 'weight_conservation.json',
        'inputs/W1_RD4_rejection.json', 'inputs/W3.json', 'inputs/W4.json')
] + [BASE + 'baseline_s82_mapping_r1/mapping_verdict.json',
     BASE + 'baseline_s82_mapping_r1/providers.json']

def export(out):
    out.mkdir(parents=True, exist_ok=False)
    # Reference exact 717 artifacts; no repacking or copies of previous attempts.
    for relative in FILES:
        source = ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
    for relative in ['tools/dsrom_s82_source_inventory.py','tools/dsrom_s82_payload_interface.py',
                     'tests/test_dsrom_s82_payload_interface.py']:
        target=out/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.symlink_to(ROOT/relative)
    inv = json.loads((ROOT / SELECTED / 'inventory.json').read_text())
    sm = json.loads((ROOT / SELECTED / 'stage_map.json').read_text())
    bounds = sm['region_bounds']
    bf = set(sm['BF_site_IDs'])
    with gzip.open(out / 'element_interfaces.jsonl.gz', 'wt') as f:
        for r in range(128):
            for p in range(bounds[r], bounds[r+1]):
                f.write(json.dumps(dict(pair=p, region=r, element='BF_DUAL' if p in bf else 'Q_ONLY',
                    weight_macro_ids=list(range(4*p,4*p+4)), logical_slots=2,
                    physical_rows=4096, physical_bits=274, ROM_ECC=False,
                    retained_return_input=32*r+p-bounds[r],
                    return_bits=126, forward_bits=1067 if p in bf else 549))+'\n')
    providers = json.loads((ROOT / FILES[-1]).read_text())
    for p in providers:
        cursor=0
        for d in p['declarations']:
            if p['kind']=='HE':
                d['native_bank_word_base']=cursor
                cursor+=d['rows']*((d['K']+63)//64)
            else:
                d['native_FP32_element_base']=cursor
                cursor+=d['elements']
        p['physical_owner_rank']=0
        p['ROM_ECC']=False
        p['delivery_to_other_ranks_qualified']=False
    (out/'provider_interfaces.json').write_text(json.dumps(providers, separators=(',',':'))+'\n')
    interface=dict(source_commit=PIN, source_checkout=str(ROOT), intake_paths=FILES,
        intake_bytes=sum((ROOT/p).stat().st_size for p in FILES),
        stage_count=82, rank_die_count=328, total_die_count=372,
        pairs_per_rank_die=2388, BF_dual=512, q_only=1876,
        weight_macros_per_rank_die=9552, compiled_weight_macros=3133056,
        field_power2_padding=0, selected_return='EXISTING_NP4096_RD64_ROOTD128',
        return_area_mm2=52.89758742528, all_numbers='MODEL_UNVALIDATED', adopted=False,
        die_inventory=inv['per_die'], configuration_macro_inventory=inv['configuration_macro_inventory'],
        software_API='tools/dsrom_s82_payload_interface.py: matrix_word / payload_value / execution_fragments',
        blockers=['Source-equivalent configuration macros need real frame/pin/timing join',
            'Head/table layouts and transport, indexer multicast, row gather need execution/physical qualification',
            'No contextual SS/FF or routing admission'])
    (out/'source_inventory.json').write_text(json.dumps(interface,separators=(',',':'))+'\n')
    (out/'intake_paths.txt').write_text('\n'.join(FILES)+'\n')
    return dict(output=str(out),paths=len(FILES),bytes=interface['intake_bytes'])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args()
    if a.out:print(json.dumps(export(a.out)))
    else:print('\n'.join(FILES))
