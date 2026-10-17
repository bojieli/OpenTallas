#!/usr/bin/env python3
"""S81 column cluster kits (H-C27 c27): --cluster-mode GEN outputs -> tools/die_cluster boundary specs
(schema opentallas.die_cluster.spec.v1, ROOT CLUSTER-FLOW 10-16) + the cluster RTL for the hardening flow.

    cluster_kit.py --work GEN_WORK [--lef elements.lef] --out DIR

GEN_WORK is the real/netlist work dir of a --cluster-mode GEN (cluster_mode.json, die_clusters.v, die_glue.sv,
elements.lef).  Per master dsfd_s81_col_<class>:
  DIR/<master>/spec.json   outline [0,0,w,h] (cluster-relative), bodies = every child (cluster_mode placement),
                           ports with 'at' = the die-top LEF pin (S face, die tool assigned, never moved), allowed S
  DIR/<master>/ports.json  port -> direction / bits
  DIR/kits.json            index + the hard / soft child census (soft = glue RTL synthesised in the cluster; hard =
                           closed views or constant macros; stand-ins listed explicitly: they block hardening)
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

SCHEMA = 'opentallas.die_cluster.spec.v1'


def lef_pins(text, macro):
    """port base -> [(bit, layer, cx, cy)] from MACRO `macro` of a LEF text."""
    m_ = re.search(r'\nMACRO %s\b(.*?)\nEND %s\b' % (re.escape(macro), re.escape(macro)), text, re.S)
    assert m_, ('macro not in LEF', macro)
    out = collections.defaultdict(list)
    for pm in re.finditer(r'\n\s*PIN (\S+)\s*\n(.*?)\n\s*END \1', m_.group(1), re.S):
        name = pm.group(1)
        if re.search(r'USE\s+(POWER|GROUND)', pm.group(2)):
            continue
        lm = re.search(r'LAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', pm.group(2))
        assert lm, ('pin without rect', macro, name)
        x0, y0, x1, y1 = map(float, lm.groups()[1:])
        bm = re.fullmatch(r'(.*)\[(\d+)\]', name)
        base, bit = (bm.group(1), int(bm.group(2))) if bm else (name, 0)
        out[base].append((bit, lm.group(1), round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--lef', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    rep = json.loads((a.work / 'cluster_mode.json').read_text())
    lef = (a.lef or a.work / 'elements.lef').read_text()
    glue = (a.work / 'die_glue.sv').read_text()
    glue_mods = set(re.findall(r'^module\s+(\w+)', glue, re.M))
    a.out.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, rec in sorted(rep['masters'].items()):
        w, h = rec['outline_um']
        pins = lef_pins(lef, name)
        ports = []
        for p, (d, bits) in sorted(rec['ports'].items()):
            got = sorted(pins.get(p, []))
            assert len(got) == bits, ('LEF pin count', name, p, len(got), bits)
            for bit, layer, cx, cy in got:
                assert abs(cy) < 1.0, ('cluster port not on the S face', name, p, bit, cy)
                ports.append(dict(name=p if bits == 1 else f'{p}[{bit}]', direction=d, at=[cx, cy], layer=layer))
        bodies = [dict(name=n, master=mst, x=x, y=y, w=ww, h=hh, orient=o) for n, mst, x, y, ww, hh, o in rec['placement']]
        soft = sorted({b['master'] for b in bodies if b['master'] in glue_mods})
        hard = sorted({b['master'] for b in bodies if b['master'] not in glue_mods})
        spec = dict(schema=SCHEMA, name=name, outline=[0.0, 0.0, w, h], bodies=bodies, ports=ports, allowed_edges='S',
                    pin=dict(spacing_tracks=1), snap=dict(policy='fail'),
                    source=dict(gen_work=str(a.work), representative_root=rec['representative'], roots=rec['roots']))
        d = a.out / name
        d.mkdir(exist_ok=True)
        (d / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
        (d / 'ports.json').write_text(json.dumps(rec['ports'], indent=1) + '\n')
        index[name] = dict(cls=rec['cls'], roots=len(rec['roots']), outline_um=rec['outline_um'], children=len(bodies),
                           port_bits=rec['port_bits'], soft_glue_masters=soft, hard_masters=hard,
                           children_by_master=rec['children_by_master'])
    (a.out / 'kits.json').write_text(json.dumps(dict(schema='opentallas.s81.cluster_kits.v1', masters=index), indent=1) + '\n')
    for n_, r_ in index.items():
        print('KIT', n_, r_['outline_um'], 'children', r_['children'], 'port_bits', r_['port_bits'], 'roots', r_['roots'])


if __name__ == '__main__':
    main()
