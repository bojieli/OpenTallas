#!/usr/bin/env python3
"""Synthetic check of fault_or_plan.py: reach, fanin cap, landed clock changes, fail-closed bit count."""
import json, subprocess, sys, tempfile
from pathlib import Path
T = Path(__file__).resolve().parent / 'fault_or_plan.py'


def run(rows, bits, place):
    d = Path(tempfile.mkdtemp())
    (d / 'inv.json').write_text(json.dumps(dict(actual_unused_bits=bits, rows=rows)))
    (d / 'p.tcl').write_text(''.join(f'ot_mts::place [$_blk findInst {i}] {x} {y} R0\n' for i, (x, y) in place.items()))
    (d / 'a.lef').write_text('MACRO L\n  SIZE 10 BY 10 ;\n  PIN fault\n    PORT\n      RECT 0 0 1 1 ;\n    END\n  END fault\nEND L\n'
                             'MACRO qfd_sys_face\n  SIZE 100 BY 100 ;\nEND qfd_sys_face\n')
    r = subprocess.run([sys.executable, T, '--inventory', d / 'inv.json', '--place', d / 'p.tcl', '--lef', d / 'a.lef',
                        '--out', d / 'o.json'], capture_output=True, text=True)
    sys.stderr.write(r.stderr[-800:])
    return r.returncode, (json.loads((d / 'o.json').read_text()) if (d / 'o.json').exists() else None)


rows = [dict(instance=f'l{i}', master='L', port='fault', port_width=1, unused_bits=[0], clock='ck_a' if i < 30 else 'ck_b')
        for i in range(40)]
place = {f'l{i}': (i * 150.0, 0.0) for i in range(40)} | {'sys_face': (0.0, 500.0)}
rc, o = run(rows, 40, place)
s = o['summary']
assert rc == 0 and s['bits'] == 40 and s['max_leaf_src_um'] <= 405 and s['max_node_fanin'] <= 16, s
assert all(n['up_relays'] == max(0, -(-n['up_um'] // 405) - 1) for n in o['nodes'][1:]), 'relay count'
assert s['landings'] >= 2, s            # ck_a and ck_b both differ from the sink clock n_clk_d2d
rc, _ = run(rows, 41, place)
assert rc == 1, 'bit-count mismatch must fail closed'
print('test_fault_or_plan PASS')
