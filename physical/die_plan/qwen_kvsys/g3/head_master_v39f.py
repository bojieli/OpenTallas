#!/usr/bin/env python3
"""Adopt the exact-proved three EVEN head masters and parent ID straps.

This merges e4 into the e6 RTL master. Odd cores remain distinct. The HID
constants are read from the original head identity (head0..head3), matching
actual kv3_hg/hgi_part_bound.sv S_head*_g_front_*_u_front_hid defaults.
No data strap or asynchronous clock exception is introduced.
"""
import argparse
import json
import re
from pathlib import Path

# Actual f26 master pins, verified by KV-HEADCLK. All master instances use R0.
PINS = {
    0: [('strap_hid[0]', 'M5', 107.976, 0.0), ('strap_hid[1]', 'M5', 108.072, 0.0),
        ('strap_bsel[0]', 'M4', 0.0, 107.976), ('strap_bsel[1]', 'M4', 0.0, 108.072)],
    2: [('strap_hid[0]', 'M4', 0.0, 107.976), ('strap_hid[1]', 'M4', 0.0, 107.880),
        ('strap_bsel[0]', 'M4', 0.0, 108.072), ('strap_bsel[1]', 'M4', 0.0, 108.168)],
    6: [('strap_hid[0]', 'M5', 107.976, 216.0), ('strap_hid[1]', 'M5', 108.072, 216.0),
        ('strap_bsel[0]', 'M4', 0.0, 107.976), ('strap_bsel[1]', 'M4', 0.0, 108.072)],
}


def portmap(name):
    return name.replace('g_front_2_u_front__', 'g_front_3_u_front__').replace('g_t_8_', 'g_t_12_').replace('g_t_9_', 'g_t_13_')


def apply(plan, report):
    plan = Path(plan)
    raw = json.loads(plan.read_text())
    conns_fn = plan.parent / 'core_conns.json'
    conns = json.loads(conns_fn.read_text())
    updates = []
    for master, pins in PINS.items():
        fn = plan.parent / 'cores' / f'kv3_head_eighth_e{master}_pins.json'
        d = json.loads(fn.read_text())
        if any(p['name'].startswith('strap_') for p in d['pins']):
            raise ValueError(f'{fn}: already has master straps')
        names = {p['name'] for p in d['pins']}
        if any('hid' in n for n in names):
            raise ValueError(f'{fn}: unhandled old HID port')
        d['pins'] += [dict(name=n, layer=l, x=x, y=y) for n, l, x, y in pins]
        d['source'] = d.get('source', '') + ' | even head strap master, exact f26 ID pin coordinates'
        updates.append((fn, d))
    records = []
    for tn, t in raw['partition_types'].items():
        for hc in t.get('hard_cores', []):
            m = re.fullmatch(r'head([0-3])_e([0246])', hc['inst'])
            if not m:
                continue
            hid, e = map(int, m.groups())
            if hc.get('orient', 'R0') != 'R0':
                raise ValueError(f'{tn}.{hc["inst"]}: expected original R0 orientation')
            master = 6 if e == 4 else e
            hc['module'] = f'kv3_head_eighth_e{master}'
            hc['pins_file'] = f'cores/kv3_head_eighth_e{master}_pins.json'
            hc['straps'] = [dict(port='strap_hid', width=2, value=f"2'b{hid:02b}"),
                            dict(port='strap_bsel', width=2, value=f"2'b{e // 2:02b}")]
            hc['note'] = hc.get('note', '') + f' | even ID strap master e{master}; head HID={hid}, BSEL={e//2}; 0 schedule cycles'
            if e == 4:
                ports = conns.get(tn, {}).get(hc['inst'], {})
                changed = {portmap(k): v for k, v in ports.items()}
                if len(changed) != len(ports):
                    raise ValueError(f'{tn}.{hc["inst"]}: port rename collision')
                conns.setdefault(tn, {})[hc['inst']] = changed
                # Internal station endpoints name the concrete core port.
                for st in t.get('internal_stations', []):
                    for key in ('launch', 'capture'):
                        if str(st.get(key, '')).startswith(hc['inst'] + '.'):
                            st[key] = portmap(st[key])
            records.append(dict(type=tn, inst=hc['inst'], master=hc['module'], hid=hid, bsel=e//2))
    for fn, d in updates:
        fn.write_text(json.dumps(d, indent=1) + '\n')
    conns_fn.write_text(json.dumps(conns, indent=1) + '\n')
    plan.write_text(json.dumps(raw, indent=1) + '\n')
    Path(report).write_text(json.dumps(dict(source='claude/kv-headclk-1025@a321bdc532',
        proof='codex/kv-headclk-0719@685203e5c', even_master_count=3, odd_masters_unchanged=True,
        schedule_cycles=0, instances=records), indent=1) + '\n')
    print(f'even head ID masters: {len(records)} type-core instances, 3 even masters; odd cores unchanged')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    apply(a.plan, a.report)


if __name__ == '__main__':
    main()
