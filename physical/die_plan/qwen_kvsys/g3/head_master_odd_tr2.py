#!/usr/bin/env python3
"""TYPE-REDUCE-2/KVQC 2026-10-25: ODD head_eighth ID strap masters (OWNER 10-25 07:01 option B), cause (2) only.

Measured on the head kits (epyc1 ~/scratch/kv-g3/cores/kits38x, lane names normalised): the four odd eighths
e1/e3/e5/e7 are the same RTL except the 2-bit .bsel(2'bXX) constant of both ot_qkh_lane8 lanes (e1 00, e3 01, e5 10,
e7 11) and the lane-numbered port prefixes g_t_<2k>/g_t_<2k+1>.  HID is chain-driven inside the odd cores (.hid(n1)),
so BSEL is the only ID.  Pin tables: e3 == e1 and e7 == e5 exactly after lane-neutral names (0 pins move); e1 vs e5
differ (68 pins W vs S face), so cause (3) is NOT applied here (proposal only: needs a PATH-KV floorplan call).

Result: odd cores 4 -> 2 masters (e1 = {e1, e3}, e5 = {e5, e7}), each with strap_bsel[1:0] tied at the parent.
Same mechanism as g3/head_master_v39f.py (even e4 -> e6): module + pins_file re-point, straps declared on the hard
core, core_conns.json / internal_stations port names mapped to the master's lane prefixes.  0 schedule cycles.

    python3 physical/die_plan/qwen_kvsys/g3/head_master_odd_tr2.py physical/die_plan/qwen_kvsys/die_plan.json \
        --report physical/die_plan/qwen_kvsys/g3/head_master_odd_tr2.json
"""
import argparse
import json
import re
from pathlib import Path

MASTER = {1: 1, 3: 1, 5: 5, 7: 5}                      # odd eighth -> master eighth (identical pin tables)
LANES = {1: (2, 3), 3: (6, 7), 5: (10, 11), 7: (14, 15)}  # g_t_<lane> prefixes of each eighth
# strap_bsel on the N face, M5, at the core centre line (free on both master tables; same spot as the even hid straps)
STRAP_PINS = [('strap_bsel[0]', 'M5', 107.976, 216.0), ('strap_bsel[1]', 'M5', 108.072, 216.0)]


def portmap(name, e):
    m = MASTER[e]
    if m == e:
        return name
    (a0, a1), (b0, b1) = LANES[e], LANES[m]
    return re.sub(r'\bg_t_(\d+)_', lambda x: {a0: f'g_t_{b0}_', a1: f'g_t_{b1}_'}.get(int(x.group(1)), x.group(0)), name)


def apply(plan, report):
    plan = Path(plan)
    raw = json.loads(plan.read_text())
    conns_fn = plan.parent / 'core_conns.json'
    conns = json.loads(conns_fn.read_text())
    updates = []
    for m in sorted(set(MASTER.values())):
        fn = plan.parent / 'cores' / f'kv3_head_eighth_e{m}_pins.json'
        d = json.loads(fn.read_text())
        if any(p['name'].startswith('strap_') for p in d['pins']):
            raise ValueError(f'{fn}: already has straps')
        taken = {(p['layer'], round(p['x'], 3), round(p['y'], 3)) for p in d['pins']}
        near = [p for p in d['pins'] if p['y'] > 215 and abs(p['x'] - 108.0) < 2.0]
        if near or any((l, x, y) in taken for _, l, x, y in STRAP_PINS):
            raise ValueError(f'{fn}: strap pin sites not free: {near}')
        d['pins'] += [dict(name=n, layer=l, x=x, y=y) for n, l, x, y in STRAP_PINS]
        fc = d.setdefault('faces', {}).setdefault('N', {'pins': 0, 'layers': ['M5']})
        fc['pins'] = fc.get('pins', 0) + len(STRAP_PINS)
        if 'M5' not in fc.setdefault('layers', []):
            fc['layers'].append('M5')
        d['source'] = d.get('source', '') + ' | TYPE-REDUCE-2 odd head strap master (strap_bsel N face M5)'
        updates.append((fn, d))
    records = []
    for tn, t in raw['partition_types'].items():
        for hc in t.get('hard_cores', []):
            mm = re.fullmatch(r'head([0-3])_e([1357])', hc['inst'])
            if not mm:
                continue
            hid, e = map(int, mm.groups())
            if hc.get('module') != f'kv3_head_eighth_e{e}' or hc.get('orient', 'R0') != 'R0':
                raise ValueError(f'{tn}.{hc["inst"]}: expected module kv3_head_eighth_e{e} at R0, got {hc.get("module")}')
            m = MASTER[e]
            bsel = (e - 1) // 2
            hc['module'] = f'kv3_head_eighth_e{m}'
            hc['pins_file'] = f'cores/kv3_head_eighth_e{m}_pins.json'
            hc['straps'] = [dict(port='strap_bsel', width=2, value=f"2'b{bsel:02b}")]
            hc['note'] = hc.get('note', '') + f' | odd ID strap master e{m}; BSEL={bsel:02b} (was .bsel constant of e{e}); 0 schedule cycles'
            n_conn = n_st = 0
            if m != e:
                ports = conns.get(tn, {}).get(hc['inst'], {})
                changed = {portmap(k, e): v for k, v in ports.items()}
                if len(changed) != len(ports):
                    raise ValueError(f'{tn}.{hc["inst"]}: port rename collision')
                if ports:
                    conns[tn][hc['inst']] = changed
                n_conn = sum(1 for k in ports if portmap(k, e) != k)
                for st in t.get('internal_stations', []):
                    for key in ('launch', 'capture'):
                        if str(st.get(key, '')).startswith(hc['inst'] + '.'):
                            new = portmap(st[key], e)
                            n_st += new != st[key]
                            st[key] = new
            records.append(dict(type=tn, inst=hc['inst'], was=f'kv3_head_eighth_e{e}', master=hc['module'],
                                strap_bsel=f"2'b{bsel:02b}", conns_renamed=n_conn, stations_renamed=n_st))
    if len(records) == 0:
        raise ValueError('no odd head cores found')
    for fn, d in updates:
        fn.write_text(json.dumps(d, indent=0))   # core pin tables: indent 0, no trailing newline (as stored)
    conns_fn.write_text(json.dumps(conns, indent=1) + '\n')
    plan.write_text(json.dumps(raw, indent=1) + '\n')
    Path(report).write_text(json.dumps(dict(
        lane='TYPE-REDUCE-2/KVQC 2026-10-25', rule='OWNER 2026-10-25 07:01 option B (ID straps tied at parent)',
        evidence='odd kits38x RTL diff after lane-neutral names: only .bsel(2\'bXX) x2 differs; pin tables e3==e1, e7==e5',
        masters={'kv3_head_eighth_e1': ['e1 bsel 00', 'e3 bsel 01'], 'kv3_head_eighth_e5': ['e5 bsel 10', 'e7 bsel 11']},
        strap_pins=STRAP_PINS, schedule_cycles=0,
        lec='each master vs each old constant variant with strap_bsel tied to its value (tools/die_plan/lec.py)',
        kit='gen_core_kit_kv.py --head-strap-odd (cores/harden/head_strap_odd.py: bsel -> strap_bsel; RTL substitution proof IDENTICAL e1/e3 e5/e7)', instances=records), indent=1) + '\n')
    print(f'odd head ID masters: {len(records)} type-core instances -> 2 odd masters (e1, e5)')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    apply(a.plan, a.report)


if __name__ == '__main__':
    main()
