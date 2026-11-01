#!/usr/bin/env python3
"""Complete the KV HG/PC physical inventory without changing the external ABI or schedule.

HG children reuse the existing signed views only after module and full pin-table identity.
The ASTK EP and PC group memories stay RTL leaves, with explicit physical sites in the
inter-core channels. Invoke with INPUT.json OUTPUT.json REPORT.json (same plan directory).
"""
import copy
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def memory_part(master, inst, xy, family):
    d = Path('physical') / family / master
    lef = d / f'{master}.lef'
    text = (REPO / lef).read_text()
    wh = [float(x) for x in re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text).groups()]
    return dict(physical_inst=inst, physical_master=master, lef=str(lef), lib=str(d / f'{master}_tt.lib'),
                origin_um=xy, outline_um=wh, orient='R0',
                note='CODEX KV macro-inventory class: explicit SRAM leaf in an inter-core channel; no added cycles')


def apply(raw, pdir):
    p = copy.deepcopy(raw)
    ts = p['partition_types']
    ref = ts['kv3_hg_v1']
    report = dict(types={}, views=0, memory_sites=0, external_abi_unchanged=True, added_cycles=0)
    def pins(c):
        return json.loads((pdir / c['pins_file']).read_text())['pins']
    signed = [(c, pins(c)) for c in ref['hard_cores']]
    tapref = {t['name']: t for t in ref['clock']['taps']}
    for tn, t in ts.items():
        if not ((tn.startswith('kv3_hg') and not tn.startswith('kv3_hgi')) or tn.startswith('kv3_pc')):
            continue
        old = copy.deepcopy(t)
        nviews = 0
        if tn.startswith('kv3_hg'):
            for c in t['hard_cores']:
                matches = [r for r, pp in signed if r['module'] == c['module'] and pp == pins(c)]
                assert matches, (tn, c['inst'], 'no signed module+pin-table match')
                # Prefer same logical position, then same master/pin table elsewhere in the repeated head grid.
                r = next((r for r in matches if r['inst'] == c['inst']), matches[0])
                for k in ('lef', 'lib'):
                    assert (REPO / r[k]).is_file(), r[k]
                    c[k] = r[k]
                c['physical_inst'] = c.get('physical_inst', f"u_bound.u_{c['inst']}")
                c['physical_master'] = r.get('physical_master', c['module'])
                nviews += int(not next(x for x in old['hard_cores'] if x['inst'] == c['inst']).get('lef'))
            t['core_pg_connect'] = copy.deepcopy(ref['core_pg_connect'])
            for tap in t['clock']['taps']:
                if tap['kind'] == 'core':
                    r = tapref[tap['name']]
                    for k in ('insertion_ps', 'insertion_ff_ps', 'budget_owner'):
                        if k in r:
                            tap[k] = r[k]
            ep = next(c for c in t['contents'] if c['module'] in ('qkd_astk_ep_s_head_e', 'qkd_astk_ep_s_e'))
            stem = 'u_bound.u_' + ep['inst'].replace('__', '_')
            ep['physical_parts'] = [memory_part('ot_sram_1r1w_64x128_m1_r2c2', f'{stem}.u_e{i}',
                                               [570.24, 449.28 + i * 51.84], 'qkd_astk_strip/macros') for i in range(4)]
            ep['physical_parts'] += [memory_part('ot_sram_1r1w_256x128_m1_r2c2', f'{stem}.u_sc{i}',
                                                [570.24, 656.64 + i * 69.12], 'qkd_astk_strip/macros') for i in range(2)]
            nmem = 6
        else:
            slg = next(c for c in t['contents'] if c['inst'] == 'slg')
            slg['physical_parts'] = [memory_part('ot_sram_1r1w_128x256_m1_r2c2',
                    f'u_bound.u_slg.u_core.u_slg.g_pc[{i}].u_pc.u_rows',
                    [[380.16, 691.2], [561.6, 691.2], [561.6, 829.44], [380.16, 829.44]][i],
                    'asap7_memory_macros_v2') for i in range(4)]
            nmem = 4
        t['core_pg_connect'] = True  # every declared child/SRAM PG pin lands on the partition straps
        # Physical child inventory and internal clock means only; preserve external release contract exactly.
        for k in ('module', 'outline_um', 'buses', 'ft_slots', 'reset', 'internal_stations', 'count_straps'):
            assert t.get(k) == old.get(k), (tn, k)
        report['types'][tn] = dict(new_signed_views=nviews, memory_sites=nmem)
        report['views'] += nviews
        report['memory_sites'] += nmem
    return p, report


if __name__ == '__main__':
    src, out, rpt = map(Path, sys.argv[1:])
    p, r = apply(json.loads(src.read_text()), src.resolve().parent)
    out.write_text(json.dumps(p, indent=1) + '\n')
    rpt.write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps(r, sort_keys=True))
