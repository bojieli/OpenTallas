#!/usr/bin/env python3
"""QW-L1SEAM 10-19: cut the compute D2D seam (record_bundles COMPILER_BUNDLES + SEAM_SINGLE) of a GEN die.v +
fwd_lanes.json into a test fixture, and prove the cut gives the same record_bundles.seam_stages as the full die.

    cut_seam_fixture.py REPO_ROOT DIE_V FWD_LANES OUT_DIE_V OUT_LANES NOTE"""
import hashlib, json, re, sys
from pathlib import Path
WT = Path(sys.argv[1])
die_v, lanes, out_v, out_l, note = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]), sys.argv[6]
sys.path.insert(0, str(WT / 'tools/qwen_split'))
import record_bundles as RB
txt = die_v.read_text()
bset = {b: RB.BUNDLES[b] for b in RB.COMPILER_BUNDLES}; bset.update(RB.SEAM_SINGLE)
bmap, info, probs = RB.netlist_members(txt, bset)
assert not probs, probs
bids = sorted(bmap)
insts = {}
want_pins = {}
for b, mem in bset.items():
    for s, sp, d, dp in mem:
        want_pins.setdefault(s, set()).add(sp); want_pins.setdefault(d, set()).add(dp)
rly = re.compile(r'^\s*\w+\s+rly_(\w+)_(\d+)\s*\(')
wires, lines = [], []
for ln in txt.splitlines():
    m = re.match(r'^\s*wire\s*\[\d+:\d+\]\s*(\w+)\s*;', ln)
    if m:
        nm = m.group(1)
        if any(nm == f'n_{b}' or nm.startswith(f'n_{b}__r') or nm.startswith(f'n_ftk_{b}_') or nm.startswith(f'n_fep_{b}__')
               or nm.startswith(f'n_fck_{b}__') or nm == f'n_flt_{b}' for b in bids):
            wires.append(ln)
        continue
    m = rly.match(ln)
    if m and m.group(1) in bids:
        lines.append(ln); continue
    m = RB.INST_LINE.match(ln)
    if m and m.group(2) in want_pins:
        conns = RB.CONN.findall(m.group(3))
        keep_c = [f'.{p}({n})' for p, n in conns if p in want_pins[m.group(2)]]
        insts[m.group(2)] = f'  {m.group(1)} {m.group(2)} ({", ".join(keep_c)});'
sha = hashlib.sha256(die_v.read_bytes()).hexdigest()
hdr = [f'// QW-L1SEAM 10-19 fixture: the compute D2D seam (record_bundles COMPILER_BUNDLES + C.x3_slot) of {note} AS BUILT,',
       f'// cut from its GEN die.v (sha256 {sha}): seam wire declarations, the d2d_rom / native59 instances reduced to',
       '// their seam pins, and EVERY relay / lane instance line of the seam buses verbatim (cells, frames, K straps).',
       'module qfd_die ();']
out_v.write_text('\n'.join(hdr + wires + [insts[k] for k in sorted(insts)] + lines + ['endmodule']) + '\n')
fl = json.loads(lanes.read_text())
fl2 = {k: v for k, v in fl.items() if k != 'lanes'}
fl2['lanes'] = [r for r in fl['lanes'] if r['bid'] in bids]
fl2['qw_l1seam_cut'] = f'seam lanes of {lanes.name} (sha256 {hashlib.sha256(lanes.read_bytes()).hexdigest()})'
out_l.write_text(json.dumps(fl2, indent=1) + '\n')
full = RB.seam_stages(die_v, lanes); cut = RB.seam_stages(out_v, out_l)
print('full', full[0], full[2]); print('cut ', cut[0], cut[2]); assert full[0] == cut[0] and full[1]['bundles'] == cut[1]['bundles']
