#!/usr/bin/env python3
"""Export ROOT14 facts from the final placed KV netlist and actual LEF pins.

This runs after expansion, forwarding, health installation and final orientation.
Missing direction, pin geometry, placement or regional clock identity refuses the
export. Clock distribution is qualified separately by dieclk; data and reset
connections are checked here. A multi-root macro needs an explicit pin/root map;
its clock identity is never guessed from the instance centre or its name.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_macro_track_alignment as C

INST = re.compile(r'^\s+(\S+) (\S+) \((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')


def bits(expr, widths):
    """Die generator's explicit concatenations/ranges, LSB first."""
    expr = expr.strip()
    if expr.startswith('{') and expr.endswith('}'):
        return [b for e in reversed(expr[1:-1].split(',')) for b in bits(e, widths)]
    if not expr:
        return []
    if re.fullmatch(r"\d+'[bB][01]+", expr):
        return [None] * int(expr.split("'", 1)[0])
    m = re.fullmatch(r'(\S+)\[(\d+):(\d+)\]', expr)
    if m:
        name, hi, lo = m[1], int(m[2]), int(m[3])
        step = 1 if hi >= lo else -1
        return [f'{name}[{i}]' for i in range(lo, hi + step, step)]
    if re.fullmatch(r'\S+\[\d+\]', expr):
        return [expr]
    if expr in widths:
        return [f'{expr}[{i}]' for i in range(widths[expr])]
    if not re.fullmatch(r'[A-Za-z_$][\w$]*', expr):
        raise ValueError(f'unsupported connection {expr!r}')
    return [expr]


def free_rectangles(size, occupied):
    """Complement of actual placed macro envelopes; never call macro area a site."""
    width, height = size
    xs = sorted({0.0, width} | {max(0.0, min(width, r[k])) for r in occupied for k in (0, 2)})
    out = []
    for left, right in zip(xs, xs[1:]):
        if right <= left:
            continue
        ys = sorted((max(0.0, r[1]), min(height, r[3])) for r in occupied
                    if r[0] < right and r[2] > left and r[3] > 0 and r[1] < height)
        end = 0.0
        for bottom, top in ys:
            if bottom > end:
                out.append([left, end, right, bottom])
            end = max(end, top)
        if end < height:
            out.append([left, end, right, height])
    return out


def groups(text, kind):
    """Balanced Liberty groups; cell/pin names may be quoted."""
    pattern = re.compile(r'\b' + kind + r'\s*\(\s*"?([^"\s)]*)"?\s*\)\s*\{')
    pos = 0
    while match := pattern.search(text, pos):
        start, depth, quote = match.end(), 1, False
        pos = start
        while depth and pos < len(text):
            ch = text[pos]
            if ch == '"' and (pos == 0 or text[pos-1] != '\\'):
                quote = not quote
            if not quote:
                depth += (ch == '{') - (ch == '}')
            pos += 1
        if depth:
            raise ValueError(f'unclosed Liberty {kind} {match[1]}')
        yield match[1], text[start:pos-1]


def clock_pins(libs):
    result = {}
    hashes = {}
    if libs:
        for path in sorted(libs.glob('*_tt.lib')):
            raw = path.read_bytes()
            hashes[path.name] = hashlib.sha256(raw).hexdigest()
            for mst, body in groups(raw.decode(), 'cell'):
                for pin, pb in groups(body, 'pin'):
                    # Both setup/hold and clk->Q arcs carry their real clock
                    # pin, preserving per-port regions of hardened parents.
                    clocks = set()
                    for _, arc in groups(pb, 'timing'):
                        if re.search(r'timing_type\s*:\s*(?:"?)(?:setup_|hold_|recovery_|removal_|rising_edge|falling_edge)', arc):
                            for related in re.findall(r'related_pin\s*:\s*"([^";]+)"', arc):
                                clocks.update(related.split())
                    if clocks:
                        key = (mst, pin)
                        if key in result and result[key] != clocks:
                            raise ValueError(f'conflicting TT clock arcs for {mst}/{pin}')
                        result[key] = clocks
    return result, hashes


def export(case, pin_roots=None, libs=None, source_ports=None):
    paths = [case / 'die.v', case / 'elements.lef', case / 'place.tcl', case / 'manifest.json']
    paths += sorted(case.glob('phy*.lef'))
    text = paths[0].read_text()
    source_directions = None
    source_direction_sha = None
    if source_ports:
        raw = source_ports.read_bytes()
        source_directions = json.loads(raw)
        source_direction_sha = hashlib.sha256(raw).hexdigest()
        if source_directions.get('die_sha256') != hashlib.sha256(paths[0].read_bytes()).hexdigest():
            raise ValueError('source-port directions describe another die netlist')
    lef = '\n'.join(p.read_text() for p in paths if p.suffix == '.lef')
    macros = {m['name']: m for m in C.parse_lef(lef)}
    directions, cur, pin = {}, None, None
    for ln in lef.splitlines():
        t = ln.strip().split()
        if t[:1] == ['MACRO']:
            cur = t[1]
        elif t[:1] == ['PIN']:
            pin = t[1]
        elif t[:1] == ['DIRECTION']:
            directions[cur, pin] = t[1]
    placements = {n: (float(x) * 1000, float(y) * 1000, o)
                  for n, x, y, o in re.findall(r'ot_mts::place \[\$_blk findInst (\S+)\] (\S+) (\S+) (\S+)', paths[2].read_text())}
    widths = {n: int(hi) + 1 for hi, n in re.findall(r'wire\s+\[(\d+):0\]\s+(\S+);', text)}
    const = {bit for n in re.findall(r"assign\s+(\S+)\s*=\s*\d+'[bB][01]+\s*;", text)
             for bit in bits(n, widths)}
    insts = {m[2]: (m[1], dict(CONN.findall(m[3]))) for ln in text.splitlines()
             if (m := INST.match(ln)) and m[1] not in ('wire', 'module', 'input', 'output')}
    pins = {mst: {p['name']: p for p in m['pins']} for mst, m in macros.items()}
    clock_nets = set()
    for n, (mst, cs) in insts.items():
        for port, expr in cs.items():
            p = pins.get(mst, {}).get(port) or pins.get(mst, {}).get(port + '[0]')
            if (p and p['use'] == 'CLOCK') or port in ('ck', 'ckf', 'ck_s', 'ck_o'):
                clock_nets.update(bits(expr, widths))
    pin_roots = pin_roots or {}
    related_clocks, library_hashes = clock_pins(libs)
    def scalar(expr):
        value = bits(expr, widths)
        return value[0] if len(value) == 1 else None
    roots = {}
    for n, (mst, cs) in insts.items():
        roots[n] = sorted({scalar(v) for p, v in cs.items() if v.strip().startswith('n_clk_')
                           and not p.startswith('pll')})
    # A forwarded station remains on the source clock until the landing read.
    clock_drivers = {scalar(cs['ck_o']): n for n, (mst, cs) in insts.items() if 'ck_o' in cs}

    def region(n, port, bit=0, seen=()):
        for key in (f'{n}/{port}[{bit}]', f'{n}/{port}'):
            if key in pin_roots:
                return pin_roots[key]
        mst, cs = insts[n]
        if n in seen:
            return None
        if mst.startswith('qkd_landsh'):
            if port in ('a', 'ea'):
                if 'ck_s' in cs:
                    return scalar(cs['ck_s'])
                prev = clock_drivers.get(scalar(cs.get('ckf', '')))
                return region(prev, 'b', 0, seen + (n,)) if prev else None
            return scalar(cs.get('ck', ''))
        if mst.startswith('qkd_rlysh_'):
            prev = clock_drivers.get(scalar(cs.get('ckf', '')))
            return region(prev, 'b', 0, seen + (n,)) if prev else None
        related = related_clocks.get((mst, f'{port}[{bit}]'), related_clocks.get((mst, port), set()))
        values = set()
        for ck in related:
            match = re.fullmatch(r'(.+)\[(\d+)\]', ck)
            cp, cb = (match[1], int(match[2])) if match else (ck, 0)
            values.update(bits(cs.get(cp, ''), widths)[cb:cb+1])
        if len(values) == 1:
            return next(iter(values))
        return roots[n][0] if len(roots[n]) == 1 else None

    def geometry(n, port, bit):
        mst = insts[n][0]
        if mst not in macros or n not in placements:
            raise ValueError(f'missing macro/placement {n} {mst}')
        p = pins[mst].get(f'{port}[{bit}]') or (pins[mst].get(port) if bit == 0 else None)
        if p is None:
            raise ValueError(f'missing LEF pin {n}/{port}[{bit}]')
        x, y, o = placements[n]
        pts = []
        for _, rect in p['rects']:
            q = C.transform_rect(rect, o, macros[mst]['W'], macros[mst]['H'])
            pts.append(((x + (q[0] + q[2]) / 2) / 1000, (y + (q[1] + q[3]) / 2) / 1000))
        if not pts:
            raise ValueError(f'no LEF rectangles {n}/{port}[{bit}]')
        return pts

    nets = defaultdict(lambda: [[], [], []])
    for n, (mst, cs) in insts.items():
        for port, expr in cs.items():
            for bit, net in enumerate(bits(expr, widths)):
                # Clocks and local tie supplies are not synchronous die data.
                if net is None or net in clock_nets or net.startswith(('n_clk_', 'n_fck_')) or net in const:
                    continue
                dr = directions.get((mst, f'{port}[{bit}]'), directions.get((mst, port)))
                if source_directions:
                    per = source_directions.get('masters', {}).get(mst, {}).get('ports', {}).get(port, [])
                    if bit >= len(per):
                        raise ValueError(f'missing actual source-port direction {n}/{port}[{bit}]')
                    actual = per[bit]
                    if dr in ('INPUT', 'OUTPUT') and actual != dr:
                        raise ValueError(f'LEF/source direction conflict {n}/{port}[{bit}]: {dr} vs {actual}')
                    dr = actual if dr else None
                elif dr == 'INOUT':
                    # Generic geometric frames deliberately use INOUT even
                    # for real RTL inputs. It cannot establish a driver.
                    dr = None
                ep = (n, port, bit)
                if dr is None:
                    nets[net][2].append(ep)
                if dr in ('OUTPUT', 'INOUT'):
                    nets[net][0].append(ep)
                if dr in ('INPUT', 'INOUT'):
                    nets[net][1].append(ep)
    wires, crosses, regions = {}, {}, {}
    pairs = 0
    dangling = 0
    for net, (drivers, loads, unknown) in nets.items():
        # A private open output has no physical wire to another endpoint.
        # Retain its count; missing abstracts on a connected net still refuse.
        if unknown and len(drivers) + len(loads) + len(unknown) > 1:
            raise ValueError(f'missing LEF direction on connected net {net}: {unknown[:8]}')
        dangling += bool(unknown)
    undriven = [net for net, (drivers, loads, unknown) in nets.items() if loads and not drivers]
    if undriven:
        raise ValueError(f'{len(undriven)} loaded signal bits have no source: {undriven[:12]}')
    for net, (drivers, loads, unknown) in nets.items():
        for src in drivers:
            for dst in loads:
                if src == dst:
                    continue
                a, b = geometry(*src), geometry(*dst)
                distance, p, q = min((abs(p[0]-q[0])+abs(p[1]-q[1]), p, q) for p in a for q in b)
                key = f'{src[0]}/{src[1]}->{dst[0]}/{dst[1]}'
                pairs += 1
                if key not in wires or distance > wires[key]['max_um']:
                    wires[key] = dict(id=key, pts=[p, q], max_um=distance, witness_net=net,
                                      witness_bits=[src[2], dst[2]], kind='reset' if 'rst' in net else 'sync')
                r1, r2 = region(*src), region(*dst)
                # An unclocked tie/PLL is not a regional synchronous producer.
                if not r1 and not roots[src[0]] and insts[src[0]][0].startswith(('qkd_tie', 'qkd_pll')):
                    continue
                if r1 != r2 or r1 is None or r2 is None:
                    for r in (r1, r2):
                        regions[str(r)] = dict(root=r)
                    # For a crossing into a landing, the write endpoint uses
                    # source root; the ring itself explicitly crosses to ck.
                    crosses[key] = dict(id=key, src_region=str(r1), dst_region=str(r2), landing=None)
    # The ring's write->read crossing is internal to its hardened macro.
    for n, (mst, cs) in insts.items():
        if mst.startswith('qkd_landsh'):
            r1, r2 = region(n, 'a'), region(n, 'b')
            for r in (r1, r2):
                regions[str(r)] = dict(root=r)
            crosses[f'{n}/ring'] = dict(id=f'{n}/ring', src_region=str(r1), dst_region=str(r2), landing=n)
    occupied = []
    for n, (x, y, o) in placements.items():
        if n not in insts or insts[n][0] not in macros:
            raise ValueError(f'placement has no known netlist macro: {n}')
        m = macros[insts[n][0]]
        w, h = (m['H'], m['W']) if o in C.ROT_SET else (m['W'], m['H'])
        occupied.append([x/1000, y/1000, (x+w)/1000, (y+h)/1000])
    return dict(schema='opentallas.die_gen_safety_facts.v1', design='qwen_kv', reach_um=405,
                regions=regions, crossings=list(crosses.values()), wires=list(wires.values()),
                channels=free_rectangles(json.loads(paths[3].read_text())['die_um'], occupied),
                coverage=dict(instances=len(insts), net_bits=len(nets), driver_load_bit_pairs=pairs,
                              unconnected_without_abstract=dangling,
                              liberty_clock_pins=len(related_clocks),
                              source_ports_sha256=source_direction_sha,
                              liberty_sha256=library_hashes,
                              aggregation='maximum actual pin-pair Manhattan span per instance-port pair',
                              source_sha256={str(p.relative_to(case)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--pin-roots', type=Path)
    ap.add_argument('--libs', type=Path, help='actual bound TT Liberty directory; per-pin clock identity')
    ap.add_argument('--source-ports', type=Path, help='exact selected strict-bind RTL port directions')
    a = ap.parse_args()
    out = a.case / 'gen_safety_facts.json'
    # A refused export must not leave an earlier successful packet behind.
    out.unlink(missing_ok=True)
    facts = export(a.case, json.loads(a.pin_roots.read_text()) if a.pin_roots else None, a.libs, a.source_ports)
    out.write_text(json.dumps(facts, indent=1) + '\n')
    print('KV_GEN_SAFETY_FACTS ' + json.dumps(facts['coverage']))


if __name__ == '__main__':
    main()
