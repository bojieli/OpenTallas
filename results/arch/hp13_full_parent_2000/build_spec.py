#!/usr/bin/env python3
"""Rebuild the source-bound fields of the full HP13 cpub39 parent kit specs.

History: Codex 492952f4e generated the specs from an sp6a template with hard-coded /home/ubuntu/wt/codex-* paths;
later Codex commits (6ce47330a..5c54c6532) hand-edited them (projected physical_abi sources, frozen witness control,
indexed ck_core[0]/ck_hr[0] roots, io_flop_at_pins, keep_pin_regs). QDIE5-TLD-K 2026-10-22: this script now runs from
the repository root, takes the committed spec.json as the template (keeping every Codex edit), and re-derives from the
CURRENT sources everything that is source-bound:
  * memory macro census (asserted 19) -> soft_root_macro_bindings, macro instance/view set (placements kept);
  * DATA_CLOCK_OWNERS.json (results/arch/hp13_corepub39_1021) -> clock_entry_domains inputs/outputs;
  * port list of the source -> asserted equal to the pin-face assignment.
It prints what changed; it never changes geometry. Then run `python3 tools/ref_tile/ref_tile.py gen <spec> --area-um2 A`.
"""
from pathlib import Path
import json, re, sys

r = Path(__file__).resolve().parents[3]
audit = json.loads((r / 'results/arch/hp13_corepub39_1021/DATA_CLOCK_OWNERS.json').read_text())
base = 'rtl/qwen_dv/headprep13/'
h16 = base + 'h16za/native32_1r_param.v'
ROOT_OF = {'ck_core': 'ck_core[0]', 'ck_hr': 'ck_hr[0]'}


def census(rel_top):
    mac = []
    for rel, prefix, root in [(rel_top, '', 'ck_core'), (h16, 'u_hr.', 'ck_hr')]:
        for line in (r / rel).read_text().splitlines():
            s = re.sub(r'^\(\*.*?\*\)\s*', '', line)
            m = re.match(r'\s*(ot_(?:sram|rom)_\w+)\s+(?:#\(.*?\)\s+)?(\\[^\s]+|\w+)\s*\(', s)
            if m:
                typ, inst = m.groups()
                mac.append((typ, prefix + inst.lstrip('\\'), root))
    return mac


changed = False
for variant, name in [(1, 'main'), (2, 'alt')]:
    a = audit[variant - 1]
    kit = r / 'physical/ref_tile' / f'qfd_hp13_cpub39_full_{name}'
    j = json.loads((kit / 'spec.json').read_text())
    old = json.dumps(j, sort_keys=True)
    assert j['top'] == a['master'], (j['top'], a['master'])
    proj = base + f'physical_abi/{a["master"]}_physical.sv'
    assert j['sources'][0] == proj, j['sources'][0]
    mac = census(a['rtl'])
    assert len(mac) == 19, len(mac)
    assert int(a['macro_cells']) == sum(1 for m in mac if not m[1].startswith('u_hr.')), a['macro_cells']
    views = sorted({x[0] for x in mac})
    assert j['soft_root_macro_masters'] == views, (j['soft_root_macro_masters'], views)
    j['soft_root_macro_bindings'] = {inst: {'master': typ, 'clock_pin': 'clk', 'root': ROOT_OF[clk]}
                                     for typ, inst, clk in mac}
    have = sorted((m['view'].split('/')[-1], m['inst']) for m in j['macros'])
    want = sorted((t, i) for t, i, _ in mac)
    assert have == want, 'macro instance set changed -> floorplan must be redone structurally'
    domains = {x: {'inputs': [], 'outputs': []} for x in ROOT_OF}
    for p, v in a['ports'].items():
        if v['status'] == 'PROVEN' and len(v.get('clock_ports', [])) == 1:
            domains[v['clock_ports'][0]]['inputs' if p in a['input_captures'] else 'outputs'].append(p)
    domains['ck_core']['inputs'] += ['rst_n', 'dh_user']
    for k, c in [('core', 'ck_core'), ('hr', 'ck_hr')]:
        j['clock_entry_domains'][k].update(ports=[ROOT_OF[c]], **domains[c])
    ports = re.findall(r'^(?:input|output) wire \[[^\]]+\] (\w+);', (r / a['rtl']).read_text(), re.M)
    faces = sorted(p for f in j['pins'].values() for p in f)
    assert sorted(ports) == faces, 'port list changed'
    new = json.dumps(j, sort_keys=True)
    if new != old:
        changed = True
        (kit / 'spec.json').write_text(json.dumps(j, indent=1) + '\n')
    print(f'{name}: top {a["master"]} rtl {a["rtl_sha256"][:8]} macros {len(mac)} ports {len(ports)} '
          f'spec {"UPDATED" if new != old else "unchanged"}')
sys.exit(0)
