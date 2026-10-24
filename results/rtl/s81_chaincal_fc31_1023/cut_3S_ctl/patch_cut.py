#!/usr/bin/env python3
"""S81-P9-FC: carry the frame_chain_reset_v2 (v2 calendar) die delta into a dv_slice_cut slice_top of the same die
lineage: the cut is verbatim die instances, so the delta is the die's own new station lines + the receiving frame
rst_n rewire (+ the bench flight rs pin dv_slice_cut copies from the frame rst_n).  Every station line is copied
byte-exact from the corrected die; refuses when a referenced net is missing from the cut.
usage: patch_cut.py <cut slice_top.sv> <corrected die.v> <frame_chain_reset_v2.json> <out slice_top.sv>"""
import json, re, sys
cut, die, rep, out = sys.argv[1:5]
t = open(cut).read(); d = open(die).read(); r = json.load(open(rep))
log = []
for inst, c in r['changes'].items():
    m = re.search(r'#\(\.INSTANCE\("%s"\)\) %s \(.*?\.rst_n\((\w+)\)' % (inst, inst), t)
    if not m:
        continue
    cur = m[1]; new = c['new_reset']
    chain = [c['reset']] + [f'rsfc2_{inst}_{k}' for k in range(c['delay'])]
    assert cur in chain and new == chain[-1], (inst, cur, new)
    have = chain.index(cur)
    add_w, add_s = [], []
    for k in range(have, c['delay']):
        net = f'rsfc2_{inst}_{k}'
        wl = re.search(r'^  wire %s;$' % net, d, re.M)[0]
        sl = re.search(r'^  \w+ st_%s \(.*\);.*$' % net, d, re.M)[0]
        assert not re.search(r'\b%s\b' % net, t), ('already in cut', net)
        add_w.append(wl); add_s.append(sl)
    ck = re.search(r'\.ck\((\w+)\)', add_s[0])[1]
    assert re.search(r'\b%s\b' % ck, t) and re.search(r'\b%s\b' % cur, t), (inst, ck, cur)
    # rewire: frame rst_n and the bench flight rs (dv_slice_cut: .rs(<frame rst_n>)) -- every use of cur EXCEPT the
    # existing station that drives it and the new first station that reads it
    n_frame = len(re.findall(r'\.rst_n\(%s\)' % cur, t)); n_fl = len(re.findall(r'__flight \(.*?\.rs\(%s\)' % cur, t))
    t = re.sub(r'\.rst_n\(%s\)' % cur, f'.rst_n({new})', t)
    t = re.sub(r'(__flight \(.*?\.rs\()%s\)' % cur, r'\g<1>%s)' % new, t)
    assert n_frame == 1, (inst, n_frame)
    first = t.index('\nendmodule')
    assert t.index('module slice_top') < first and t.find('\nmodule ', t.index('module slice_top') + 1) in (-1,) + tuple(
        i for i in [t.find('\nmodule ', t.index('module slice_top') + 1)] if i > first), 'slice_top must be the first module'
    t = t[:first] + '\n' + '\n'.join(add_w + add_s) + t[first:]
    log.append(dict(inst=inst, from_reset=cur, to_reset=new, stations_added=len(add_s), flight_rs_rewired=n_fl))
open(out, 'w').write(t)
print(json.dumps(log))
