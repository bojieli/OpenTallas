#!/usr/bin/env python3
"""qwen-tp8 die lead r10 (2026-10-13, coordinator: first die route + STA with every real view bound, PATHFINDING).

Builds the die STA library set of a tp8b case (tools/qwen_tp8/relay_data_run.py OUT --case, then bind_real.py):
  qfd_etm_<master>_<c>.lib   the Liberty of every master bind_real bound to a closed view (the view's own file, by name)
                             + the hard-macro abstracts' own libs (ot_hbm3e_phy)
  qfd_elements_<c>.lib       ASSUMED single-flop views (tools/qwen_die_element_lib.py constants) of every other master:
                             placeholders, relay frames, reset repeaters; pin directions from the generator's bus list
                             (case/port_dirs.json, driver first)
  clocks_<c>.tcl            planned phi-R delivery at every leaf clock pin, per actual corner boundary mean;
                             one related clock per domain, propagated ETM insertion ("# DOMS" for sta_tcl.py)
  views.json                 which master has which kind of view
c = tt, ff, ss.  Limits (pathfinding): ideal planned delivery, no physical die CTS proof; a generated
bundle whose bits run both ways takes the bundle's direction; a port the bus list does not name is an input.

    die_sta_libs.py --case CASE --repo ROOT --bind bind.json --out LIBDIR
"""
import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qwen_die_element_lib as E   # noqa: E402
from hier_contract.pinreg_audit import parse_lib, clock_refs

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


def measured_clock_refs(lib_path, insertion_path, corner):
    """Require the bound view's own per-clock boundary measurement, never a lib estimate."""
    if not insertion_path.is_file():
        raise ValueError(f"missing real clock insertion: {insertion_path}")
    lib = parse_lib(lib_path)
    refs = clock_refs(lib, json.loads(insertion_path.read_text()), corner)
    clocks = {p for p, v in lib['pins'].items() if v['clock'] or p in refs}
    result = {}
    for pin in clocks:
        r = refs.get(pin)
        if not r or r['src'] != 'insertion.json boundary mean' or not math.isfinite(r['rise']):
            raise ValueError(f"missing {corner} boundary mean for {lib_path}:{pin}")
        result[pin] = r['rise']
    return result


def assumed_clock_refs(master, ports, physical_ports=None):
    """Use the exact generated Liberty/LEF names, including one-bit buses.

    The die Verilog connects .ck(net), but a generated LEF may expose ck[0].
    E.write_lib deliberately preserves that spelling; clock delivery must too.
    """
    vec = {}
    if physical_ports is not None:
        # Generated physical clock buses retain indexed pin names, including scalar ck[0].
        for p in ports:
            if p in E.CLOCKS and p not in physical_ports:
                bits = sorted(q for q in physical_ports if q.startswith(p + '[') and q.endswith(']'))
                if bits:
                    indices = [int(re.fullmatch(re.escape(p) + r'\[(\d+)\]', q).group(1)) for q in bits]
                    if set(indices) != set(range(len(indices))):
                        raise ValueError(f'{master}.{p}: incomplete physical clock bus')
                    vec[p] = sorted(bits, key=lambda q: int(q.rsplit('[', 1)[1][:-1]))
        missing=[p for p in ports if p in E.CLOCKS and p not in physical_ports and p not in vec]
        if missing:
            raise ValueError(f'{master}: clock inputs missing from generated physical LEF: {missing}')
    out = {}
    for p in ports:
        if p not in E.CLOCKS:
            continue
        for q in vec.get(p, [f'{p}[0]' if (master, p) in E.IDX else p]):
            out[q] = 0.0
    return out


def clock_tcl(doms, leaves, corner):
    # Each domain has related shallow / earlier-tap clock objects. Separate
    # domains remain asynchronous; no exception is created between levels.
    # Source latency shifts the boundary while propagated ETMs retain insertion.
    lines = ['# DOMS ' + ' '.join(sorted(doms)), '# INSERTION_COMPENSATED ' + corner,
             '# OWNER_CLOCK_BUDGET v1', 'set_cmd_units -time ps', 'set ot_clock_bound 0']
    domain_clocks = {}
    for d, entries in sorted(doms.items()):
        levels = {}
        for pin, master, libpin in entries:
            level = int(leaves[master]['tt'][libpin] > 300.0)
            levels.setdefault(level, []).append((pin, master, libpin))
        names = {level: d if level == 0 else d + '__early' for level in levels}
        domain_clocks[d] = list(names.values())
        for level, group in sorted(levels.items()):
            name = names[level]
            lines.append('set ot_pins {}')
            for pin, _, _ in group:
                lines += [f'set p [get_pins -quiet {{{pin}}}]',
                          f'if {{[llength $p] != 1}} {{ error "clock boundary pin missing or ambiguous: {pin}" }}',
                          'lappend ot_pins [lindex $p 0]']
            lines.append(f'create_clock -name {name} -period {PERIOD.get(d, 1024.0):.6f} $ot_pins')
            for pin, master, libpin in group:
                r = leaves[master][corner][libpin]
                lines += [f'set_clock_latency -source -clock [get_clocks {name}] {-r:.6f} [get_pins {{{pin}}}]',
                          'incr ot_clock_bound']
        # Exact owner tree-link budget: pair_check.py SKEW_SHALLOW / SKEW_DEEP,
        # HOLD_TREE (50 ps margin + 50 ps die skew). Either earlier end costs150.
        for launch, lname in sorted(names.items()):
            for capture, cname in sorted(names.items()):
                skew = 150.0 if launch or capture else 90.0
                lines += [f'# BUDGET {lname} -> {cname}: setup 60 + skew {skew:g} ps; hold H1 100 ps',
                          f'set_clock_uncertainty -setup {60.0 + skew:.6f} -from [get_clocks {lname}] -to [get_clocks {cname}]',
                          f'set_clock_uncertainty -hold 100.000000 -from [get_clocks {lname}] -to [get_clocks {cname}]']
    if len(domain_clocks) > 1:
        lines.append('set_clock_groups -asynchronous ' + ' '.join(
            '-group [get_clocks {' + ' '.join(names) + '}]' for names in domain_clocks.values()))
    lines += ['set_propagated_clock [all_clocks]',
              f'puts "OT_COMPENSATED_CLOCK corner={corner} bound=$ot_clock_bound"']
    return '\n'.join(lines) + '\n'


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
    leaves = {}
    for mst, r in bind['masters_detail'].items():
        if not r.get('bound'):
            continue
        libs = r.get('libs') or {}
        if not libs.get('tt') or not libs.get('ff'):
            continue                               # LEF bound, no Liberty: stays on the assumed view
        vd = Path(r['view'])
        vd = vd if vd.is_absolute() else root / vd
        if set(libs) != {'tt', 'ff', 'ss'}:
            raise ValueError(f'{mst}: real view requires actual TT, FF, SS Liberty, got {sorted(libs)}')
        sheet = vd / f'{mst}.json'
        if sheet.exists() and str(json.loads(sheet.read_text()).get('schema', '')).startswith(
                'opentallas.qwen-missing.link-phy-abstract'):
            # licensed link-PHY hard macro (tools/qwen_missing/link_phy_gen.py): its Liberty IS the boundary model
            # (registered FDI pins, ASSUMED timing); there is no routed clock tree to measure, as for HARD
            for c, rel in libs.items():
                shutil.copy(root / rel, out / f'qfd_etm_{mst}_{c}.lib')
            views['hard_macro'][mst] = str(r['view'])
            skip.add(mst)
            continue
        leaves[mst] = {c: measured_clock_refs(root / libs[c], vd / 'insertion.json', c) for c in ('tt', 'ff', 'ss')}
        for c, rel in libs.items():
            shutil.copy(root / rel, out / f'qfd_etm_{mst}_{c}.lib')
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
    all_physical_ports = dict(lef)
    lef = {k: q for k, q in lef.items() if k not in skip}
    stubs = {mst: {p: [d, 0, set()] for p, d in ports.items()} for mst, ports in dirs.items()}
    for corner in ('tt', 'ff', 'ss'):
        E.write_lib(corner, lef, stubs, out / f'qfd_elements_{corner}.lib')
    views['assumed'] = sorted(lef)
    views['assumed_clock_insertion'] = {m: 'ideal zero-insertion assumption, no measured boundary evidence'
                                       for m in dirs if m not in leaves}
    # ---- clock sources: the output pins that drive a net with a clock pin on it
    txt = (case / 'die.v').read_text()
    drv, sinks, sink_pins = {}, set(), {}
    for m in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);', txt, re.M):
        mst, inst, body = m.group(1), m.group(2), m.group(3)
        if mst in ('wire', 'module'):
            continue
        for p in re.finditer(r'\.(\S+?)\(([^(){}]*)\)', body):
            port, net = p.group(1).lstrip('\\').strip(), p.group(2).strip()
            if not net or "'" in net:
                continue
            real_clocks = leaves.get(mst, {}).get('tt', {})
            if port in E.CLOCKS or any(re.sub(r'\[\d+\]$', '', p) == port for p in real_clocks):
                sinks.add(net)
                sink_pins.setdefault(net, []).append((inst, mst, port))
            elif dirs.get(mst, {}).get(port) == 'output' and (port.startswith('pll') or net.startswith('n_clk')):
                drv.setdefault(net, []).append(f'{inst}/{port}')
    doms = {}
    for net in sorted(sinks):
        for pin in drv.get(net, []):
            doms.setdefault(domain(net), []).append(pin)
    undriven = sorted(n for n in sinks if n not in drv)
    # Unbound generated elements remain explicit ideal single-flop assumptions.
    # Bound views are never assigned zero insertion when evidence is missing.
    for mst, ports in dirs.items():
        if mst not in leaves:
            leaves[mst] = {c: assumed_clock_refs(mst, ports, all_physical_ports.get(mst, {})) for c in ('tt', 'ff', 'ss')}
    leaf_doms = {}
    for net in sorted(sinks):
        for inst, mst, port in sink_pins[net]:
            refs = leaves.get(mst, {}).get('tt', {})
            hits = [p for p in refs if p == port or re.sub(r'\[\d+\]$', '', p) == port]
            if not hits:
                raise ValueError(f'{inst}/{port}: no Liberty clock pin / boundary reference for {mst}')
            for pin in hits:
                leaf_doms.setdefault(domain(net), []).append((f'{inst}/{pin}', mst, pin))
    for c in ('tt', 'ff', 'ss'):
        (out / f'clocks_{c}.tcl').write_text(clock_tcl(leaf_doms, leaves, c))
    # Existing callers naming clocks.tcl are redirected by sta_tcl.py per corner.
    (out / 'clocks.tcl').write_text(clock_tcl(leaf_doms, leaves, 'tt'))
    views.update(schema='opentallas.qwen-tp8.die-sta-libs.v1', clocks={d: len(p) for d, p in leaf_doms.items()},
                 clock_source_drivers={d: len(set(p)) for d, p in doms.items()},
                 clock_nets=len(sinks), clock_nets_without_driver=undriven[:40],
                 clock_delivery='phi - measured boundary mean, per corner; ideal planned delivery at leaf pins',
                 clock_budget='related shallow/early levels: setup 60 + 90 ps shallow/shallow, 60 + 150 ps when either TT R > 300 ps; hold H1 50 margin + 50 skew = 100 ps',
                 insertion_ps={m: v for m, v in leaves.items() if m in views['real']},
                 note='PATHFINDING: unbound masters remain assumed single-flop views; no physical die CTS proof')
    (out / 'views.json').write_text(json.dumps(views, indent=1) + '\n')
    print(json.dumps(dict(real=len(views['real']), hard_macro=len(views['hard_macro']), assumed=len(lef), clocks=views['clocks'],
                          clock_nets=len(sinks), undriven=len(undriven))))


if __name__ == '__main__':
    main()
