#!/usr/bin/env python3
"""HEAD l48hp1 strap-site and raw-pin event: rebuild the event plan from the prepared l48hp1 plan.

The wave's prepared l48hp1 plan (head_wave_kit_rtl.py prepare) skips count-strap sites for its HELD types, so
hd_ctl and hd_serdes reached the wave without them (PIN_AUDIT extra).  hd_host_e rst_start_raw_0/2 sit on the
clk_t8/clk_t1 tap pins (M7 shorts).  delta.json records exactly those fields; nothing else changes.
    apply_delta.py PREPARED_source_plan.json OUT.json
"""
import hashlib, json, sys
from pathlib import Path

def main(base, out):
    d = json.loads((Path(__file__).parent / 'delta.json').read_text())
    raw = Path(base).read_bytes()
    if hashlib.sha256(raw).hexdigest() != d['base_sha256']:
        raise SystemExit('base plan is not the prepared l48hp1 plan')
    p = json.loads(raw)
    for t, straps in d['count_straps'].items():
        by = {s['name']: s for s in p['partition_types'][t]['count_straps']}
        for name, v in straps.items():
            by[name].update(layer=v['layer'], sites_um=v['sites_um'])
    for t, pins in d['landing_pins_xy_um'].items():
        by = {x['name']: x for x in p['partition_types'][t]['clock']['landing_contract']['pins']}
        for name, xy in pins.items():
            by[name]['xy_um'] = xy
    text = json.dumps(p, indent=1) + '\n'
    if hashlib.sha256(text.encode()).hexdigest() != d['result_sha256']:
        raise SystemExit('result differs from the recorded event plan')
    Path(out).write_text(text)

if __name__ == '__main__':
    main(*sys.argv[1:])
