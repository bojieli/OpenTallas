#!/usr/bin/env python3
"""TOK-FUNC-S81 (10-21): die-source tree for dv_layer_compile --die-src from a 72-frame die bind (RTL-only assembly).

The compiler's Die model reads the bind9 layout (results/arch/s81_dv_1016/{bind9/die.v.gz, p4l/plan.json,
landing/p4l/land_plan.json}).  This writes that layout from any die bind (G7 assembly or, at die closure, the GEN netlist):

  mk_tree.py --die-v DIE.v --plan PLAN.json --land LAND.json --out TREE [--tag NAME]

Landed links that die.v lands (dsfd_dvland ld_<link> with a K strap) but the land plan does not list get a land-plan row
E = the die.v K strap (source 'die_v_K_strap'); they are listed in TREE/tree_receipt.json (these are the die's K-1
placeholder landings; the replay asserts the cycles the RTL actually has).
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path

LD_RE = re.compile(r"^\s*(dsfd_dvland\w*)\s+ld_(\w+)\s*\(.*\.k\((\d+)'[dh]([0-9a-fA-F]+)\)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--land', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tag', default='tokfunc')
    a = ap.parse_args()
    T = Path(a.out)
    base = T / 'results/arch/s81_dv_1016'
    for d in ('bind9', 'p4l', 'landing/p4l'):
        (base / d).mkdir(parents=True, exist_ok=True)
    raw = Path(a.die_v).read_bytes()
    (base / 'bind9/die.v.gz').write_bytes(gzip.compress(raw, 6))
    plan = json.loads(Path(a.plan).read_text())
    (base / 'p4l/plan.json').write_text(json.dumps(plan))
    land = json.loads(Path(a.land).read_text())
    have = {l['link'] for l in land['links']}
    added = []
    for line in raw.decode().splitlines():
        m = LD_RE.match(line)
        if not m:
            continue
        master, lk, _, k = m.groups()
        if lk in have:
            continue
        kv = int(k, 16 if "'h" in line.split('.k(')[1][:8] else 10)
        row = dict(link=lk, cls='die_v_K_strap', dst=None, E=kv, K=kv, master=master, source='die_v_K_strap')
        land['links'].append(row)
        added.append(dict(link=lk, K=kv, master=master))
        have.add(lk)
    # plan links with stations but neither a land-plan row nor a die.v landing: unlanded relay lanes (E 0 in pricing)
    unlanded = []
    for l in plan['links']:
        nm = l['i'].replace('-', '_')
        if l['s'] > 0 and nm not in have:
            # x_f_<frame>_l<k>: lands INSIDE the receiving frame (_l4 / _lp crs4, lk strap 3 b per lane) -> cls x_frame (the
            # compiler then reads the receiver's lk strap, as dv_cut_replay does); anything else is an unlanded relay lane
            xf = re.fullmatch(r'x_f_.+_l\d+', nm) is not None
            dst = plan['blocks'][l['e'][1][0]]['name']
            land['links'].append(dict(link=nm, cls='x_frame' if xf else 'unlanded_relay', dst=dst, E=0, K=None,
                                      source='frame_internal_landing' if xf else 'no_landing_in_die_v'))
            unlanded.append(nm)
            have.add(nm)
    (base / 'landing/p4l/land_plan.json').write_text(json.dumps(land))
    rec = dict(schema='opentallas.tokfunc_s81.tree.v1', tag=a.tag,
               die_v=str(a.die_v), die_v_sha256=hashlib.sha256(raw).hexdigest(),
               plan=str(a.plan), plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
               land=str(a.land), land_sha256=hashlib.sha256(Path(a.land).read_bytes()).hexdigest(),
               land_rows_from_die_v_K=added, unlanded_relay_links=unlanded)
    (T / 'tree_receipt.json').write_text(json.dumps(rec, indent=1))
    (T / '.done').write_text(a.tag + '\n')
    print(f'mk_tree: die.v {rec["die_v_sha256"][:12]} land rows from die.v K {len(added)} unlanded relay links {len(unlanded)}')


if __name__ == '__main__':
    main()
