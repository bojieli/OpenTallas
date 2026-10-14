#!/usr/bin/env python3
"""qwen-tp8 die lead r10 (2026-10-13, coordinator: first die route + STA with every real view bound, PATHFINDING).

Builds the die STA library set of a tp8b case (tools/qwen_tp8/relay_data_run.py OUT --case, then bind_real.py):
  qfd_etm_<master>_<c>.lib   the Liberty of every master bind_real bound to a closed view (the view's own file, by name)
                             + the hard-macro abstracts' own libs (ot_hbm3e_phy)
  qfd_elements_<c>.lib       ASSUMED single-flop views (tools/qwen_die_element_lib.py constants) of every other master:
                             placeholders, relay frames, reset repeaters; pin directions from the generator's bus list
                             (case/port_dirs.json, driver first)
  clocks.tcl                 ideal clocks on every clock driver pin of the netlist (PLL / clock receiver / strip PLL
                             outputs), grouped stream | hclk_<q> | serial | ucie | serdes ("# DOMS" header for sta_tcl.py)
  views.json                 which master has which kind of view
c = tt, ff, ss.  Limits (pathfinding): ideal clocks (no insertion-compensated delivery, no clock plan); a generated
bundle whose bits run both ways takes the bundle's direction; a port the bus list does not name is an input.

    die_sta_libs.py --case CASE --repo ROOT --bind bind.json --out LIBDIR
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qwen_die_element_lib as E   # noqa: E402

HARD = {'ot_hbm3e_phy': 'physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy'}
PERIOD = dict(stream=833.333, serial=833.333 * 4.0 / 3.0, ucie=833.333, serdes=833.333)


def domain(net):
    n = net[2:] if net.startswith('n_') else net
    m = re.match(r'clk_hbm_(\w+?)(?:__.*)?$', n)
    if m:
        return 'hclk_' + m.group(1)
    for k in ('serial', 'ucie', 'serdes'):
        if n.startswith('clk_' + k):
            return k
    return 'stream'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--case', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--bind', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    case, root, out = Path(a.case), Path(a.repo).resolve(), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    bind = json.loads(Path(a.bind).read_text())
    dirs = json.loads((case / 'port_dirs.json').read_text())
    views = dict(real={}, hard_macro={}, assumed=[])
    skip = set()
    for mst, r in bind['masters_detail'].items():
        if not r.get('bound'):
            continue
        libs = r.get('libs') or {}
        if not libs.get('tt') or not libs.get('ff'):
            continue                               # LEF bound, no Liberty: stays on the assumed view
        for c, rel in libs.items():
            shutil.copy(root / rel, out / f'qfd_etm_{mst}_{c}.lib')
        if 'ss' not in libs:
            shutil.copy(root / libs['tt'], out / f'qfd_etm_{mst}_ss.lib')
        views['real'][mst] = dict(view=r['view'], instances=r['instances'], corners=sorted(libs))
        skip.add(mst)
    for mst, d in HARD.items():
        ok = all((root / d / f'{mst}_{c}.lib').exists() for c in ('tt', 'ff', 'ss'))
        if ok:
            for c in ('tt', 'ff', 'ss'):
                shutil.copy(root / d / f'{mst}_{c}.lib', out / f'qfd_etm_{mst}_{c}.lib')
            views['hard_macro'][mst] = d
            skip.add(mst)
    lef = E.lef_pins(case / 'elements.lef')
    if (case / 'phy_ew.lef').exists():
        for k, q in E.lef_pins(case / 'phy_ew.lef').items():
            lef.setdefault(k, q)
    lef = {k: q for k, q in lef.items() if k not in skip}
    stubs = {mst: {p: [d, 0, set()] for p, d in ports.items()} for mst, ports in dirs.items()}
    for corner in ('tt', 'ff', 'ss'):
        E.write_lib(corner, lef, stubs, out / f'qfd_elements_{corner}.lib')
    views['assumed'] = sorted(lef)
    # ---- clock sources: the output pins that drive a net with a clock pin on it
    txt = (case / 'die.v').read_text()
    drv, sinks = {}, set()
    for m in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);', txt, re.M):
        mst, inst, body = m.group(1), m.group(2), m.group(3)
        if mst in ('wire', 'module'):
            continue
        for p in re.finditer(r'\.(\S+?)\(([^(){}]*)\)', body):
            port, net = p.group(1).lstrip('\\').strip(), p.group(2).strip()
            if not net or "'" in net:
                continue
            if port in E.CLOCKS:
                sinks.add(net)
            elif dirs.get(mst, {}).get(port) == 'output' and (port.startswith('pll') or net.startswith('n_clk')):
                drv.setdefault(net, []).append(f'{inst}/{port}')
    doms = {}
    for net in sorted(sinks):
        for pin in drv.get(net, []):
            doms.setdefault(domain(net), []).append(pin)
    undriven = sorted(n for n in sinks if n not in drv)
    L = ['# DOMS ' + ' '.join(sorted(doms))]
    for d, pins in sorted(doms.items()):
        per = PERIOD.get(d, 1024.0)
        L.append(f'create_clock -name {d} -period {per:.3f} [get_pins -quiet {{{" ".join(sorted(set(pins)))}}}]')
    (out / 'clocks.tcl').write_text('\n'.join(L) + '\n')
    views.update(schema='opentallas.qwen-tp8.die-sta-libs.v1', clocks={d: len(set(p)) for d, p in doms.items()},
                 clock_nets=len(sinks), clock_nets_without_driver=undriven[:40],
                 note='PATHFINDING: ideal clocks, assumed single-flop views for every unbound master')
    (out / 'views.json').write_text(json.dumps(views, indent=1) + '\n')
    print(json.dumps(dict(real=len(views['real']), hard_macro=len(views['hard_macro']), assumed=len(lef), clocks=views['clocks'],
                          clock_nets=len(sinks), undriven=len(undriven))))


if __name__ == '__main__':
    main()
