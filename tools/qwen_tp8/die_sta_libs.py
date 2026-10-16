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
from die_port_bind import parse_die, expr_bits

HARD = {'ot_hbm3e_phy': 'physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy'}
PERIOD = dict(stream=833.333, serial=833.333 * 4.0 / 3.0, ucie=833.333, serdes=833.333)


def domain(net):
    n = net[2:] if net.startswith('n_') else net
    if n == 'clk_coll_blk':
        return 'coll_blk'
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


def assumed_clock_refs(master, ports, physical_ports=None, clock_ports=None):
    """Use the exact generated Liberty/LEF names, including one-bit buses.

    The die Verilog connects .ck(net), but a generated LEF may expose ck[0].
    E.write_lib deliberately preserves that spelling; clock delivery must too.
    """
    selected = [p for p in ports if p in E.CLOCKS or p in (clock_ports or {}).get(master, ())]
    if physical_ports is not None:
        missing=[p for p in selected if p not in physical_ports]
        if missing:
            raise ValueError(f'{master}: clock inputs missing from generated physical LEF: {missing}')
    refs = {}
    for p in selected:
        width = (physical_ports or {}).get(p, 1)
        for k in range(width):
            refs[f'{p}[{k}]' if width > 1 or (master, p) in E.IDX else p] = 0.0
    return refs


def clock_tcl(doms, leaves, corner, periods=None, related_domains=()):
    # Each domain has related shallow / earlier-tap clock objects. Separate
    # domains remain asynchronous; no exception is created between levels.
    # Source latency shifts the boundary while propagated ETMs retain insertion.
    if periods is not None:
        missing = set(doms) - set(periods)
        if missing:
            raise ValueError(f'missing source clock periods: {sorted(missing)}')
        if any(not math.isfinite(periods[d]) or periods[d] <= 0 for d in doms):
            raise ValueError('invalid source clock period')
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
            lines.append(f'create_clock -name {name} -period {(periods[d] if periods is not None else PERIOD.get(d, 1024.0)):.6f} $ot_pins')
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
    # Preserve every relation explicitly declared by the source programme.
    # An asynchronous group is permitted only between independent groups.
    groups = []
    remaining = set(domain_clocks)
    for related in related_domains:
        ds = remaining.intersection(related)
        if ds:
            groups.append(sorted(ds))
            remaining -= ds
    groups.extend([d] for d in sorted(remaining))
    for group in groups:
        for launch in group:
            for capture in group:
                if launch == capture:
                    continue
                for lname in domain_clocks[launch]:
                    for cname in domain_clocks[capture]:
                        skew = 150.0 if lname.endswith('__early') or cname.endswith('__early') else 90.0
                        lines += [f'set_clock_uncertainty -setup {60+skew:.6f} -from [get_clocks {lname}] -to [get_clocks {cname}]',
                                  f'set_clock_uncertainty -hold 100.000000 -from [get_clocks {lname}] -to [get_clocks {cname}]']
    if len(groups) > 1:
        lines.append('set_clock_groups -asynchronous ' + ' '.join(
            '-group [get_clocks {' + ' '.join(name for d in group for name in domain_clocks[d]) + '}]' for group in groups))
    lines += ['set_propagated_clock [all_clocks]',
              f'puts "OT_COMPENSATED_CLOCK corner={corner} bound=$ot_clock_bound"']
    return '\n'.join(lines) + '\n'


def clock_connections(path, dirs, leaves, clock_ports=None):
    """Resolve scalar and concatenated vector clock nets at actual physical bits."""
    nets, _, _, instances = parse_die(path)
    drivers, sinks, pins = {}, set(), {}
    for master, inst, _, connections in instances:
        for port, expression in connections.items():
            refs = leaves.get(master, {}).get('tt', {})
            hits = [p for p in refs if re.sub(r'\[\d+\]$', '', p) == port]
            is_clock = port in E.CLOCKS or port in (clock_ports or {}).get(master, ()) or hits
            bits = expr_bits(expression, nets)
            if is_clock:
                if not bits or any(net in ('CONST', 'Z', 'UNDECL') for net, _ in bits):
                    raise ValueError(f'{inst}/{port}: missing or non-net clock connection')
                if len(hits) != len(bits):
                    raise ValueError(f'{inst}/{port}: {len(bits)} connected clock bits but {len(hits)} physical clock references')
                for pin in hits:
                    match = re.search(r'\[(\d+)\]$', pin)
                    k = int(match.group(1)) if match else 0
                    net, bit = bits[len(bits)-1-k]
                    if nets[net][0] != 1 or bit != 0:
                        raise ValueError(f'{inst}/{pin}: clock trunk must be a scalar declared net')
                    sinks.add(net)
                    pins.setdefault(net, []).append((inst, master, pin))
            elif dirs.get(master, {}).get(port) == 'output' and port.startswith('pll'):
                if bits and len(bits) == 1 and bits[0][0] in nets:
                    drivers.setdefault(bits[0][0], []).append(f'{inst}/{port}')
    return drivers, sinks, pins


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
    contract_path = case / 'clock_contract.json'
    contract = json.loads(contract_path.read_text()) if contract_path.exists() else {}
    declared_clocks = contract.get('clock_ports', {})
    if 'qfd_collective_static_io_production' in dirs and not contract:
        raise ValueError('static production collective requires a source clock contract; legacy clock inference is incomplete')
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
        E.write_lib(corner, lef, stubs, out / f'qfd_elements_{corner}.lib', clock_ports=declared_clocks)
    views['assumed'] = sorted(lef)
    views['assumed_clock_insertion'] = {m: 'ideal zero-insertion assumption, no measured boundary evidence'
                                       for m in dirs if m not in leaves}
    # All source-declared clocks, including vector ports, require one actual
    # physical reference per connected bit before any STA can be launched.
    for mst, ports in dirs.items():
        if mst not in leaves:
            leaves[mst] = {c: assumed_clock_refs(mst, ports, all_physical_ports.get(mst, {}), declared_clocks)
                           for c in ('tt', 'ff', 'ss')}
    drv, sinks, sink_pins = clock_connections(case / 'die.v', dirs, leaves, declared_clocks)
    doms = {}
    for net in sorted(sinks):
        for pin in drv.get(net, []):
            doms.setdefault(domain(net), []).append(pin)
    undriven = sorted(n for n in sinks if n not in drv)
    leaf_doms = {}
    for net in sorted(sinks):
        for inst, mst, pin in sink_pins[net]:
            leaf_doms.setdefault(domain(net), []).append((f'{inst}/{pin}', mst, pin))
    if contract and undriven:
        raise ValueError(f'source-declared clock nets without drivers: {undriven}')
    periods = contract.get('periods_ps')
    related = contract.get('related_domains', ())
    for c in ('tt', 'ff', 'ss'):
        (out / f'clocks_{c}.tcl').write_text(clock_tcl(leaf_doms, leaves, c, periods, related))
    # Existing callers naming clocks.tcl are redirected by sta_tcl.py per corner.
    (out / 'clocks.tcl').write_text(clock_tcl(leaf_doms, leaves, 'tt', periods, related))
    views.update(source_clock_contract=contract, schema='opentallas.qwen-tp8.die-sta-libs.v1', clocks={d: len(p) for d, p in leaf_doms.items()},
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
