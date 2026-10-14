#!/usr/bin/env python3
"""Verify TP8 real leaf composition without allocating relays or running physical jobs.

Usage: python tools/qwen_tp8/real_leaf_probe.py OUT
The minimal case includes the five changed master LEFs and the full generated wire
netlist; it checks binding, complete input coverage, and all three source corners.
This is a composition check, not a die route or timing verdict.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as D

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
D.QWEN_RECIPE = 'tp8b'
D.QWEN_RECIPES['tp8b'] = dict(D.QWEN_TP8B, relay_pitch=0)
v, model = D.load_qwen()[:2]
M = v.masters(model, 1)
pw = v.port_widths(model, 1)
keep = {'qkd_ectl_a', 'qkd_ectl_b', 'qkd_ectl_c', 'qfd_crom_g', 'qfd_su_cbuf_g'}
v.EMIT_SPLIT = True
lefs = [v.lef_text(q, 1, {p: pw.get((mn, p), 0) for p in q.order})[0]
        for mn, q in M.items() if mn in keep]
(out / 'elements.lef').write_text('VERSION 5.8 ;\n' + '\n'.join(lefs) + '\nEND LIBRARY\n')
v.write_netlist(model, 1, out / 'die.v')
subprocess.run([sys.executable, str(ROOT / 'tools/qwen_tp8/bind_real.py'), '--case', str(out),
                '--repo', str(ROOT), '--out', str(out / 'bind.json')], check=True)
report = json.loads((out / 'bind.json').read_text())
for mn in keep:
    q = report['masters_detail'][mn]
    assert q['bound'], q
    assert not q['inputs_without_die_net'], q
    assert set(q['libs']) == {'tt', 'ff', 'ss'}, q
    assert q['insertion'], q
    print('BOUND', mn, q['instances'], q['pin_centroid_move_um'])
assert report['instances_bound'] == 112, report
assert not any(i.master == 'qkd_ectl' for i in model['insts'])
assert all(i.orient == 'MX' for i in model['insts'] if i.master in ('qfd_crom_g', 'qfd_su_cbuf_g'))
(out / 'composition.json').write_text(json.dumps(dict(ectl=model['tp8b_v5']['ectl_leaves'],
    rom=model['tp8b_v5']['real_rom_ports'], views={mn: model['tp8b_v5']['views'][mn] for mn in keep}), indent=1)+'\n')
print('REAL_LEAF_COMPOSITION_PASS')
