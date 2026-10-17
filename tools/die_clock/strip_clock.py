#!/usr/bin/env python3
"""DIE-CLOCK: strip an existing (modelled / graph-mode) die clock network from an ODB and tie every sink clock pin
straight to its domain root net, so build.py can grow the physical regional trees from a clean root (Claude DIE-CLOCK-HBM
2026-10-16).

  openroad -python -no_init -exit strip_clock.py --odb IN.odb --out OUT.odb --roots inst/pin[,inst/pin...]
      [--inst-glob 'dk?_*'] [--net-glob 'dk?_*,n_dk?_*'] [--report sinks.json]

From each root pin's net, walks forward through every instance whose name matches --inst-glob (input iterm -> output
iterms), collecting the INPUT iterms of all other instances reached (the sinks).  Then deletes the matched instances,
deletes every net matching --net-glob (or left with no iterm), and connects each sink to the root net.  A sink reached
from two roots, or a glob instance not reachable from any root, is an error (the domains must be disjoint trees).
"""
import argparse
from collections import defaultdict
import fnmatch
import json
from pathlib import Path


def walk(root_net, is_clk):
    """root net -> (sinks [iterm], clock insts [inst]); is_clk(inst) selects the network to strip."""
    sinks, insts, seen, todo = [], [], set(), [root_net]
    while todo:
        net = todo.pop()
        if net.getName() in seen:
            continue
        seen.add(net.getName())
        for it in net.getITerms():
            if it.getIoType() != 'INPUT':
                continue
            inst = it.getInst()
            if is_clk(inst.getName()):
                insts.append(inst)
                for o in inst.getITerms():
                    if o.getIoType() == 'OUTPUT' and o.getNet():
                        todo.append(o.getNet())
            else:
                sinks.append(it)
    return sinks, insts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--odb', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--roots', required=True)
    ap.add_argument('--inst-glob', default='dk?_*')
    ap.add_argument('--net-glob', default='dk?_*,n_dk?_*')
    ap.add_argument('--report')
    a = ap.parse_args()
    from openroad import Tech, Design
    import odb
    tech = Tech()
    design = Design(tech)
    design.readDb(a.odb)
    blk = design.getBlock()
    ig = a.inst_glob.split(',')
    is_clk = lambda n: any(fnmatch.fnmatchcase(n, g) for g in ig)
    rep, owner, all_clk = {}, {}, set()
    plan = []
    for r in a.roots.split(','):
        it = blk.findITerm(r)
        if not it or not it.getNet():
            raise SystemExit(f'root {r} missing or unconnected')
        net = it.getNet()
        sinks, insts = walk(net, is_clk)
        for s in sinks:
            k = f'{s.getInst().getName()}/{s.getMTerm().getName()}'
            if k in owner:
                raise SystemExit(f'sink {k} reached from {owner[k]} and {r}')
            owner[k] = r
        all_clk.update(i.getName() for i in insts)
        per_m = defaultdict(int)
        for s in sinks:
            per_m[s.getInst().getMaster().getName()] += 1
        rep[r] = dict(net=net.getName(), sinks=len(sinks), sink_insts=len({s.getInst().getName() for s in sinks}),
                      clock_insts=len(insts), sinks_by_master=dict(sorted(per_m.items())))
        plan.append((net, sinks))
        print('root', r, json.dumps(rep[r]['sinks']), 'sinks', rep[r]['sink_insts'], 'insts', len(insts), 'clock cells',
              flush=True)
    stray = [i.getName() for i in blk.getInsts() if is_clk(i.getName()) and i.getName() not in all_clk]
    if stray:
        raise SystemExit(f'{len(stray)} clock instances not reachable from any root, e.g. {stray[:5]}')
    for net, sinks in plan:
        for s in sinks:
            s.disconnect()
    for i in list(blk.getInsts()):
        if i.getName() in all_clk:
            odb.dbInst.destroy(i)
    ng = a.net_glob.split(',')
    root_nets = {n.getName() for n, _ in plan}
    dead = 0
    for n in list(blk.getNets()):
        if n.getName() in root_nets:
            continue
        if any(fnmatch.fnmatchcase(n.getName(), g) for g in ng) or (n.getSigType() == 'CLOCK' and not n.getITerms()
                                                                     and not n.getBTerms()):
            odb.dbNet.destroy(n)
            dead += 1
    for net, sinks in plan:
        net.setSigType('CLOCK')
        for s in sinks:
            s.connect(net)
    print('stripped', len(all_clk), 'clock cells,', dead, 'nets', flush=True)
    design.writeDb(a.out)
    if a.report:
        Path(a.report).write_text(json.dumps(dict(schema='opentallas.die_clock.strip.v1', odb=a.odb, out=a.out,
                                                  inst_glob=a.inst_glob, net_glob=a.net_glob, stripped_cells=len(all_clk),
                                                  stripped_nets=dead, roots=rep), indent=1) + '\n')
    print('DIE_CLOCK_STRIP_DONE', flush=True)


if __name__ == '__main__':
    main()
