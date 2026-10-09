#!/usr/bin/env python3
"""Die model extractor for the top-down timing budgets (CLAUDE BUDGETS, 2026-10-06).

Runs INSIDE a source tree of the generator branch (git archive of the pinned commit; never a live worktree) and dumps
one uniform, compact die model that tools/budgets/{clock_plan,budget_sheet}.py read:

  die      name, outline, generator + options, source commit
  insts    [name, master, kind, region, domain, x, y, w, h, orient]
  buses    [id, class, bits, [[inst, port, dir], ...]]   endpoint 0 = driver (generator convention); dir from the
                                                          die_top_lint DIRECTION MODEL where it resolves ('in'/'out'/
                                                          'io'/'?')
  ports    {master: {port: [x, y]}}    port anchor in master coordinates (generated face centre, or the centre of the
                                        real LEF pin group); missing -> the consumer uses the outline (box gap)
  regions  clock regions (S81: option-C field regions + hub / band regions; HBM: hbm_accel_die_fp.clock_regions)

  python3 tools/budgets/extract_die.py --src SRC --die s81r8_layer --s81-opts "--rev r9 --cc-reach-um 215 --vch-interleave" --out X.json.gz
  python3 tools/budgets/extract_die.py --src SRC --die hbm --out X.json.gz
  python3 tools/budgets/extract_die.py --src SRC --die qwen_rom --qwen-recipe r21b --out X.json.gz
      (die-gaps 2026-10-08: the Qwen ROM die; regions = the generator's decision-C clock_regions, ports = the
       generated face anchors (Qwen masters are Q.Master abstracts; ETM-bound masters keep the generator's pins))
"""
import argparse
import gzip
import json
import os
import sys
from pathlib import Path


def anchor(Mx, port):
    """face-port centre in master coordinates (Q.Master: ('face', width, face, layer, centre, pitch))"""
    p = Mx.ports.get(port)
    if p and p[0] == 'rects':
        if not p[1]:
            return None
        return [sum((r[axis]+r[axis+2])/2 for _,_,r in p[1])/len(p[1]) for axis in (0,1)]
    if not p or p[0] != 'face':
        if p and p[0] == 'area':
            return [p[2], p[3]]
        return None
    _, _, face, _, c, _ = p
    return {'N': [c, Mx.h], 'S': [c, 0.0], 'E': [Mx.w, c], 'W': [0.0, c]}[face]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, type=Path)
    ap.add_argument('--die', required=True)
    ap.add_argument('--s81-opts', default='')
    ap.add_argument('--hbm-variant', default='')
    ap.add_argument('--qwen-recipe', default='r21b')
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    src = a.src.resolve()
    os.chdir(src)
    sys.path.insert(0, str(src / 'tools'))
    import die_top_lint as L  # noqa: E402
    L.S81_OPTS = a.s81_opts
    if a.hbm_variant:
        L.VARIANT = a.hbm_variant
    if a.die == 'qwen_rom':
        L.QWEN_RECIPE = a.qwen_recipe
    m, pw, M, tool = L.build(a.die)
    by = {it.name: it for it in m['insts']}
    try:
        real = L.real_blocks(a.die, m)
    except Exception as e:  # noqa: BLE001
        print('real_blocks failed:', repr(e), file=sys.stderr)
        real = {}
    buses = []
    nodir = 0
    for bus in m['buses']:
        bid, cls, bits, eps = bus
        out = []
        for j, (inst, port) in enumerate(eps):
            d = '?'
            if inst != 'TOP':
                try:
                    seg, _ = L.endpoint_dirs(a.die, real, by, bus, j)
                    ds = {s[2] for s in seg} if seg else set()
                    d = ds.pop() if len(ds) == 1 else ('mixed' if ds else '?')
                except Exception:  # noqa: BLE001
                    nodir += 1
            out.append([inst, port, d])
        buses.append([bid, cls, bits, out])
    ports = {}
    for name, Mx in M.items():
        if hasattr(Mx, 'ports'):
            pp = {p: anchor(Mx, p) for p in Mx.ports}
            ports[name] = {p: [round(v, 3) for v in xy] for p, xy in pp.items() if xy}
    # real LEF masters: centre of each die port's pin group (generator real-port maps)
    try:
        if a.die == 'qwen_rom':
            raise LookupError('qwen_rom: generated face anchors only')
        if a.die == 'hbm':
            L.H._init_real()
            files, rp = dict(L.H.REAL), L.H.real_ports(m)
        else:
            L.S._init_real()
            files = dict(L.S.REAL_FILES)
            rp = L.S.real_ports_r8() if a.die.startswith('s81r8') else L.S.real_ports()
        for mst, groups in rp.items():
            if mst not in files:
                continue
            pins = L.S.real_lef(files[mst])['pins']
            d = ports.setdefault(mst, {})
            for port, names in groups.items():
                xs = [pins[n][1] for n in names if n in pins]
                if xs:
                    d[port] = [round(sum((r[0] + r[2]) / 2 for r in xs) / len(xs), 3),
                               round(sum((r[1] + r[3]) / 2 for r in xs) / len(xs), 3)]
    except LookupError:
        pass
    except Exception as e:  # noqa: BLE001
        print('real port anchors failed:', repr(e), file=sys.stderr)
    if a.die == 'qwen_rom':
        regions = [dict(name=r['name'], kind=r.get('kind', 'region'), rect=r['rect']) for r in m.get('clock_regions', [])]
        die_wh = [m['die']['w'], m['die']['h']]
    elif a.die == 'hbm':
        H = L.H
        regions = H.clock_regions(m)
        die_wh = [m['geo']['W'], m['geo']['H']]
    else:
        S = L.S
        regions = [dict(name=c['name'], kind='field', rect=c['rect'], fifo=c.get('fifo')) for c in m.get('cregions', [])]
        regions += [dict(name=r['name'], kind=r.get('kind', 'region'), rect=r['rect']) for r in m.get('regions', [])]
        die_wh = list(S.DIE)
    rec = dict(schema='opentallas.budgets.die_model.v1', die=a.die, tool=tool, s81_opts=a.s81_opts,
               qwen_recipe=a.qwen_recipe if a.die == 'qwen_rom' else None,
               source_commit=(src / 'SOURCE_COMMIT').read_text().strip() if (src / 'SOURCE_COMMIT').exists() else None,
               outline_um=die_wh, regions=regions,
               insts=[[it.name, it.master, it.kind, getattr(it, 'region', ''), getattr(it, 'domain', ''), round(it.x, 3),
                       round(it.y, 3), round(it.w, 3), round(it.h, 3), it.orient] for it in m['insts']],
               buses=buses, ports=ports, fclk_buses=sorted(m.get('fclk', {})),
               pin_stage_buses=sorted(m.get('pin_stage_buses', [])),
               relay_rule=bool(a.die == 'hbm' and (m.get('variant') or {}).get('relay_all')),
               budget_stages=bool(a.die == 'hbm' and (m.get('variant') or {}).get('budget_stages')),
               path_buses=sorted({b for ids in m.get('paths', {}).values() for b in ids}), real_masters=sorted(real), endpoint_dir_failures=nodir)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.out, 'wt') as f:
        json.dump(rec, f, separators=(',', ':'))
    print(json.dumps(dict(die=a.die, insts=len(rec['insts']), buses=len(buses), masters=len({i[1] for i in rec['insts']}),
                          regions=len(regions), real=len(real), dir_failures=nodir)))


if __name__ == '__main__':
    main()
