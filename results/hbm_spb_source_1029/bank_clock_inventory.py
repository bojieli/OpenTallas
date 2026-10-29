"""Plan-native SPB kept-bit clock membership; no source/CTS qualification.

Use the same cell lower-left Manhattan metric as clock_taps.tcl. Actual GEN
must compare its physical net assignment with this inventory after importing
these exact sites. Reset/START and non-bank loads remain in the full budget.
"""
import collections
import json
import sys
from pathlib import Path


def inventory(placement, delta):
    taps = [(x['name'], *x['xy']) for x in delta['clock_update']['taps'] if x['kind'] == 'glue']
    if len(taps) != 8:
        raise ValueError('expected reviewed eight soft taps')
    bits = {}
    counts = collections.Counter()
    margin = float('inf')
    for entry in placement['entries']:
        key = (entry['instance'], entry['stage'])
        if key in bits:
            raise ValueError('duplicate native FF bank')
        bank = []
        for bit, (x, y) in enumerate(entry['sites_um']):
            choices = sorted((abs(x-tx)+abs(y-ty), i, name) for i, (name, tx, ty) in enumerate(taps))
            dist, _, tap = choices[0]
            margin = min(margin, choices[1][0]-dist)
            bank.append(dict(bit=bit, tap=tap, site_um=[x,y], distance_um=round(dist,6)))
            counts[tap] += 1
        bits[key] = bank
    if sum(counts.values()) != 4104:
        raise ValueError('expected exactly 4104 native bank bits')
    groups = collections.Counter()
    for inst, width in [('u_hbm_spb0_rx',514), ('u_hbm_spb0_tx',512)]:
        for stage in range(3):
            src, dst = bits[(inst,stage)], bits[(inst,stage+1)]
            if len(src) != width or len(dst) != width:
                raise ValueError('native bank width changed')
            for a,b in zip(src,dst):
                groups[(inst,stage,a['tap'],b['tap'])] += 1
    return dict(schema='opentallas.hbm.spb0_bank_clock_inventory.v1',
                status='PLANNED_NATIVE_BANKS_ONLY_NOT_ACTUAL_BOUND_GEN_OR_CTS',
                physical_assignment_rule='clock_taps.tcl cell-lower-left Manhattan, original tap order tie-break',
                source='reviewed ot_hbm_spb0_regs kept stage/bit identity',
                bits=4104, native_ff_loads=dict(sorted(counts.items())),
                smallest_second_tap_distance_margin_um=round(margin,6),
                internal_stage_clock_groups=[dict(instance=i,launch_stage=s,capture_stage=s+1,
                    launch_tap=a,capture_tap=b,bits=n) for (i,s,a,b),n in sorted(groups.items())],
                banks=[dict(instance=i,stage=s,bits=v) for (i,s),v in sorted(bits.items())],
                conditions=['actual selected raw wrapper and delivered clock/reset contract required',
                            'actual GEN must preserve sites and check these exact kept-bit assignments',
                            'full control/face loads remain separate and must not be subtracted',
                            'endpoint source/capture groups withheld until actual bound contract'])


if __name__ == '__main__':
    placement,delta,out = map(Path,sys.argv[1:])
    result=inventory(json.loads(placement.read_text()),json.loads(delta.read_text()))
    out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='banks'},indent=1))
