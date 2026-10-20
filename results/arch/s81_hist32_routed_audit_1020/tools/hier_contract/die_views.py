#!/usr/bin/env python3
"""Die-iteration view assembly (qwendie 2026-10-12): real closed views where an element has closed, contract-budget
views for every open element.

Inputs: a die chain's libs dir (qfd_elements_<c>.lib = assumed single-flop constants, qfd_etm_<c>.lib = already bound
ETMs, views.json), the case LEF (die masters), the hier contract, and a bind map

  {"<die master>": {"view": "physical/qwen_die_masters/views/<v>", "clk": "clk",
                    "ports": {"<die port>": ["<elem bus or pin>", ...]}}}   # die bit i <- i-th bit of the concatenation

Every die bit not covered by an explicit list is bound by DIRECTION to the next element data pin of the same direction
(round-robin; clock / reset / PG excluded), so each bit carries a real routed-element arc (representative_by_role).
The element's exported Liberty (shared exporter: write_timing_model on the closed route) supplies the pin bodies; the
clock related_pin is renamed to the die master's clock pin.

Open elements (contract kind element / cluster, master still ASSUMED): BUDGET view = the assumed single-flop view with
every setup table shifted so its smallest-slew entry equals in_delay_frac * T and every clock->out table shifted so its
lightest-load entry equals out_delay_frac * T (the element's share of the cycle per the contract; registered pins make
this an upper bound).  Hold arcs and the whole FF (hold) corner stay the assumed single-flop constants (the contract carries no hold
budget; a budget clock->out at FF would make hold optimistic).
Hard macros / infrastructure masters (no contract element slot) keep their assumed view.

    python3 tools/hier_contract/die_views.py --libs IN --lef CASE/elements.lef --contract C.json --bind B.json --out OUT
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_die_etm_map import blocks, header, retarget, lef_ports, cell_text, types  # noqa: E402

SKIP = re.compile(r'^(VDD|VSS|rst_n|clk|.*_clk)$')


def bus_bits(blk, bus):
    if bus in blk:
        return [bus]
    bits = sorted((k for k in blk if re.fullmatch(re.escape(bus) + r'\[\d+\]', k)), key=lambda k: int(k[k.rindex('[') + 1:-1]))
    if not bits:
        raise KeyError(f'element pin {bus} not in view')
    return bits


def direction(body):
    m = re.search(r'direction\s*:\s*(\w+)', body)
    return m.group(1) if m else None


def cell_span(text, name):
    m = re.search(r'\n  cell \(' + re.escape(name) + r'\) \{', text)
    if not m:
        return None
    i, depth = m.end(), 1
    while depth:
        c = text[i]
        depth += (c == '{') - (c == '}')
        i += 1
    return m.start(), i


def assumed_dirs(text, master):
    """die bit -> direction from the assumed cell (bus groups with bus_type b<w>)."""
    s, e = cell_span(text, master)
    out = {}
    for m in re.finditer(r'bus \(([^)]+)\) \{ bus_type : b(\d+); direction : (\w+);', text[s:e]):
        out[m.group(1)] = (int(m.group(2)), m.group(3))
    return out


def shift_values(body, kind, target):
    """shift every values(...) of the timing groups of `kind` so the first entry == target."""
    def fix(tm):
        g = tm.group(0)
        def vals(vm):
            nums = [float(x) for x in re.findall(r'-?\d+\.?\d*', vm.group(1))]
            return nums
        first = re.search(r'values \(([^)]*)\)', g)
        if not first:
            return g
        d = target - float(re.findall(r'-?\d+\.?\d*', first.group(1))[0])
        return re.sub(r'values \(([^)]*)\)', lambda vm: 'values (' + ', '.join(
            '"' + ', '.join(f'{float(x) + d:.2f}' for x in s.split(',')) + '"'
            for s in re.findall(r'"([^"]*)"', vm.group(1))) + ')', g)
    if kind == 'setup':
        pat = r'timing \(\) \{ related_pin : "[^"]+"; timing_type : setup_rising;.*?\} \} '
    else:
        pat = r'timing \(\) \{ related_pin : "[^"]+"; timing_type : rising_edge; cell_rise.*?cell_fall \(load1\) \{[^}]*\} '
    return re.sub(pat, fix, body, flags=re.S)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--libs', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--bind', type=Path, required=True)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--corners', default='tt,ff')
    a = ap.parse_args(argv)
    con = json.loads(a.contract.read_text())
    T = float(con['clock_period_ps'])
    bind = json.loads(a.bind.read_text())
    views = json.loads((a.libs / 'views.json').read_text())
    assumed = set(views.get('assumed_constants') or [])
    budget_of = {}
    for s in con['slots']:
        if s.get('kind') in ('element', 'cluster') and s['cell'] in assumed and s['cell'] not in bind and not s['cell'].startswith('ot_'):
            io = s.get('io_budget') or {}
            budget_of[s['cell']] = (io.get('in_delay_frac', 0.2), io.get('out_delay_frac', 0.2))
    a.out.mkdir(parents=True, exist_ok=True)
    rec_bind = {}
    for c in a.corners.split(','):
        el = (a.libs / f'qfd_elements_{c}.lib').read_text()
        etm = (a.libs / f'qfd_etm_{c}.lib').read_text()
        cells, widths = [], set()
        for master, b in sorted(bind.items()):
            vdir = a.root / b['view']
            vlib = (vdir / f'{vdir.name}_{c}.lib').read_text()
            blk = blocks(vlib)
            dirs = assumed_dirs(el, master)
            mp = lef_ports(a.lef, master)
            ck = b.get('clk', 'clk')
            pool = {'input': [], 'output': []}
            for k in blk:
                base = re.sub(r'\[\d+\]$', '', k)
                d = direction(blk[k])
                if not SKIP.match(base) and d in pool and 'clock : true' not in blk[k]:
                    pool[d].append(k)
            rr = {'input': 0, 'output': 0}
            expl = {p: [x for bus in lst for x in bus_bits(blk, bus)] for p, lst in (b.get('ports') or {}).items()}
            pins = {}

            def src(p, i, master=master, dirs=dirs, mp=mp, ck=ck, expl=expl, blk=blk, pool=pool, rr=rr, pins=pins):
                ckname = 'ck[0]' if mp.get('ck', (1, False))[1] else 'ck'
                if p in ('ck', 'ckx', 'clk'):
                    sp = ck
                elif p in expl and i < len(expl[p]):
                    sp = expl[p][i]
                else:
                    d = dirs.get(p, (0, 'input'))[1]
                    d = d if d in pool else 'input'
                    sp = pool[d][rr[d] % len(pool[d])]
                    rr[d] += 1
                pins[f'{p}[{i}]' if mp[p][1] else p] = sp
                return retarget(blk[sp], {ck: ckname})
            widths |= {w for w, idx in mp.values() if idx}
            cells.append(cell_text(master, mp, src))
            el = el[:cell_span(el, master)[0]] + el[cell_span(el, master)[1]:]
            rec_bind[master] = dict(view=b['view'], kind='representative_by_role (closed route ETM, exported)',
                                    explicit_ports=sorted(expl), bits=len(pins))
        have = set(re.findall(r'type \("qd_b(\d+)"\)', etm))
        new_t = types({w for w in widths if str(w) not in have})
        k = etm.index('  cell (')
        etm = etm[:k] + new_t + '\n' + '\n'.join(cells) + '\n' + etm[k:]
        for master, (fi, fo) in sorted(budget_of.items() if c != 'ff' else ()):  # hold corner keeps the min view
            s, e = cell_span(el, master)
            body = shift_values(shift_values(el[s:e], 'setup', fi * T), 'cq', fo * T)
            el = el[:s] + body + el[e:]
        (a.out / f'qfd_etm_{c}.lib').write_text(etm)
        (a.out / f'qfd_elements_{c}.lib').write_text(el)
    v = dict(views)
    v['etm_bound'] = dict(views.get('etm_bound') or {}, **{m: f"{r['view']} ({r['kind']})" for m, r in rec_bind.items()})
    v['assumed_constants'] = sorted(assumed - set(rec_bind))
    v['budget_views'] = {m: dict(in_delay_ps=round(fi * T, 2), out_clk_to_q_ps=round(fo * T, 2))
                         for m, (fi, fo) in sorted(budget_of.items())}
    v['die_iter_bind'] = rec_bind
    (a.out / 'views.json').write_text(json.dumps(v, indent=1) + '\n')
    print(json.dumps(dict(bound_new=sorted(rec_bind), budget=sorted(budget_of),
                          assumed_left=sorted(assumed - set(rec_bind) - set(budget_of))), indent=1))


if __name__ == '__main__':
    main()
