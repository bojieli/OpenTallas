"""V2: replace only VP store SRAMs with their qualified fixed no-repair view.

Merge this source-only delta into the batched S81 plan; it does not change
outlines, origins, regular pin positions, clock latency or public cycles.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

OLD='ot_sram_1r1w_512x128_m4_r2c2'
NEW=OLD+'_nr'
VIEW=f'physical/asap7_memory_macros_v2/{NEW}/{NEW}.lef'
PINS=f'inputs/core_pins/{NEW}.json'


def apply(raw):
    uses=Counter(p['type'] for p in raw['partitions'])
    changed=[];instances=0
    for tn,t in raw['partition_types'].items():
        for h in t.get('hard_cores',[]):
            if h['module']!=OLD or not re.fullmatch(r'u_lf\.u_vp\.u_b[01]',h['inst']):continue
            if h['outline_um']!=[174.12,29.736]:raise ValueError(f'{tn}: unexpected old outline')
            h.update(module=NEW,lef=VIEW,pins_file=PINS)
            changed.append([tn,h['inst']]);instances+=uses[tn]
    return dict(type_entries=len(changed),placed_macro_instances=instances,planned_input_pins_removed=32*instances,
                changed=changed,cycles_added=0,geometry_changed=False,
                actual_bind_target_instances=160,actual_tied_repair_bits=5120,
                remaining_kv_macro_declarations=160-instances)


def manifest_patch():
    bb=f'physical/asap7_memory_macros_v2/{NEW}/{NEW}_bb.v'
    return dict(asbuilt_patch=dict(files=[bb],prefer=[bb],substitute_inst=[dict(inst=r'.*\.u_vp\.u_b[01]',module=NEW,reason='V2 qualified fixed no-repair store; old repair inputs all zero')]),
                required_bind_comparison=dict(instances=160,removed_input_bits={NEW+'.rr_en':320,NEW+'.rr_addr':2240,NEW+'.cr_en':320,NEW+'.cr_sel':2240},unrelated_proof_counts='unchanged'),
                physical_gate='Use new macro master/views and regenerate affected parent kits; no old signoff transfer')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);raw=json.loads(a.plan.read_text());r=apply(raw)
    (a.out/'die_plan.json').write_text(json.dumps(raw,separators=(',',':'))+'\n')
    (a.out/'ledger.json').write_text(json.dumps(r,indent=2)+'\n')
    (a.out/'manifest_patch.json').write_text(json.dumps(manifest_patch(),indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='changed'}))
