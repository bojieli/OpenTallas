#!/usr/bin/env python3
"""Kit-local grid-tap move (S81-TYPES-7-LEAFB): tap_moves from leaf_channel_open.py --tapmove JSON.
Moves the interior clk_tNN pin in io.tcl by (to - frm) and the reset relays placed at that tap in reset_tree.tcl."""
import json, re, sys
K, J = sys.argv[1:3]
tm = json.load(open(J)).get('tap_moves', {})
io = open(K + '/io.tcl').read(); rt = open(K + '/reset_tree.tcl').read()
for name, v in tm.items():
    dx = v['to'][0] - v['frm'][0]; dy = v['to'][1] - v['frm'][1]
    pat = re.compile(r'(place_pin -pin_name ' + re.escape(name) + r' -layer \S+ -location \{)([\d.]+) ([\d.]+)(\})')
    m = pat.search(io); assert m, name
    io = pat.sub(lambda m: m.group(1) + '%.4f %.4f' % (float(m.group(2)) + dx, float(m.group(3)) + dy) + m.group(4), io, count=1)
    old = '%.3f %.3f' % tuple(v['frm']); new = '%.3f %.3f' % tuple(v['to'])
    k = rt.count(' ' + old + ' ')
    rt = rt.replace(' ' + old + ' ', ' ' + new + ' ')
    print(name, 'pin', m.group(2), m.group(3), '-> +%.2f +%.2f' % (dx, dy), 'reset relays moved', k)
open(K + '/io.tcl', 'w').write(io); open(K + '/reset_tree.tcl', 'w').write(rt)
