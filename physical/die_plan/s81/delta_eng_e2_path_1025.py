#!/usr/bin/env python3
"""Reserve the actual E2 core in eng__t1 and move existing FT0 cells; zero cycles."""
import json
import sys
from pathlib import Path
import compact_plan


def apply(raw):
    t = raw['partition_types']['eng__t1']
    core = next(h for h in t['hard_cores'] if h['inst'] == 'u_eng.u_e')
    if core['outline_um'] == [410.4, 466.56]:
        return False
    if core['outline_um'] != [345.6, 466.56] or core['origin_um'] != [855.36,717.12]:
        raise ValueError('unexpected eng core contract; replan FT0 from the new geometry')
    core['outline_um'] = [410.4,466.56]
    core['lef'] = 'physical/die_plan/s81/cores/eng/lef/dsdv_eng_rr_e_e2.lef'
    core['pins_file'] = 'inputs/core_pins/dsdv_eng_rr_e_e2.json'
    slot = next(s for s in t['ft_slots'] if s['name'] == 'ft0')
    bits = slot['bit_sites_um']; string = isinstance(bits,str)
    bits = json.loads(bits) if string else bits
    if len(bits) != 9:
        raise ValueError('unexpected FT0 register depth')
    for i, (dx,dy) in enumerate([(69.12,34.56),(69.12,0),(69.12,0),(34.56,0)]):
        slot['regs_um'][i+1] = [round(slot['regs_um'][i+1][0]+dx,6),round(slot['regs_um'][i+1][1]+dy,6)]
        for q in bits[i]:
            q[0],q[1] = round(q[0]+dx,6),round(q[1]+dy,6)
    slot['bit_sites_um'] = json.dumps(bits,separators=(',',':')) if string else bits
    return True

if __name__ == '__main__':
    src=Path(sys.argv[1]);dst=Path(sys.argv[2]) if len(sys.argv)>2 else src
    raw=json.loads(src.read_text());apply(raw);dst.write_text(compact_plan.dumps(raw))
