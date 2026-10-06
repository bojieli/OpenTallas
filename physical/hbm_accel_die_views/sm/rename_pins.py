#!/usr/bin/env python3
"""CLAUDE HBM-ABSTRACTS (sm): rename an exported SM view (RTL pin names, macro ot_hbm_accel_sm_v) to the die master
hfd_sm: every RTL pin bit becomes the die port bit the die_top_lint SM binding assigns it (d / q / x / r / c / ck /
rst, r16g); pin positions are kept as routed/placed, so the die placement sees the element's real faces.

    python3 physical/hbm_accel_die_views/sm/rename_pins.py --lef IN.lef --lib-ss IN_ss.lib --lib-ff IN_ff.lib --out DIR
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))


def binding():
    import hbm_die_views as V
    m, pw, M, real = V.model()
    b = real['hfd_sm']['binding']
    rmap = {}
    for port, names in b.items():
        for i, n in enumerate(list(names)[:pw[('hfd_sm', port)]]):
            assert n not in rmap, n
            rmap[n] = f'{port}[{i}]'
    return rmap


def lef_rename(t, rmap, master):
    name = re.search(r'^MACRO (\S+)', t, re.M).group(1)
    unbound = []

    def pin(mm):
        old = mm.group(1)
        if old in rmap:
            return mm.group(0).replace(f'PIN {old}\n', f'PIN {rmap[old]}\n', 1).replace(f'END {old}', f'END {rmap[old]}')
        if re.search(r'USE (POWER|GROUND)', mm.group(0)):
            return mm.group(0)
        unbound.append(old)
        return ''               # an RTL pin with no die bit (e.g. a tie / spare): not a die pin
    t = re.sub(r'\n  PIN (\S+)\n.*?\n  END \1(?=\n)', lambda mm: '\n' + pin(mm).lstrip('\n'), t, flags=re.S)
    t = t.replace(f'MACRO {name}\n', f'MACRO {master}\n').replace(f'FOREIGN {name} ', f'FOREIGN {master} ')
    t = t.replace(f'END {name}\n', f'END {master}\n')
    return t, unbound


def groups(t, i0, i1):
    """top-level groups between i0 and i1: [(head, start, end)] with t[start:end] the whole group text."""
    out, i = [], i0
    pat = re.compile(r'(\w+)\s*\(([^)]*)\)\s*\{')
    while True:
        mm = pat.search(t, i, i1)
        if not mm:
            break
        d, j = 1, mm.end()
        while d:
            c = t[j]
            d += (c == '{') - (c == '}')
            j += 1
        out.append((mm.group(1), mm.group(2).strip().strip('"'), mm.start(), j))
        i = j
    return out


def lib_rename(t, rmap, master, corner, widths):
    """ETM (write_timing_model): every pin group is re-keyed to its die bit and regrouped into the die buses
    d / q / x / r / c / ck / rst (types rebuilt); bus-level attributes are taken from the die direction (mixed buses
    q / c: inout at bus level, each bit keeps its own direction)."""
    lib_g = groups(t, 0, len(t))[0]
    body0, body1 = t.index('{', lib_g[2]) + 1, lib_g[3] - 1
    top = groups(t, body0, body1)
    cell = next(g for g in top if g[0] == 'cell')
    head = t[body0:cell[2]]
    head = re.sub(r'\n\s*type\s*\([^)]*\)\s*\{[^}]*\}', '', head)
    c0, c1 = t.index('{', cell[2]) + 1, cell[3] - 1
    cg = groups(t, c0, c1)
    cell_attrs = t[c0:cg[0][2]] if cg else t[c0:c1]
    pins, other, dirs = {}, [], {}
    for g in cg:
        txt = t[g[2]:g[3]]
        if g[0] == 'bus':
            b0 = txt.index('{') + 1
            for pg in groups(txt, b0, len(txt) - 1):
                if pg[0] == 'pin':
                    pins[pg[1]] = txt[pg[2]:pg[3]]
        elif g[0] == 'pin':
            pins[g[1]] = txt
        else:
            other.append(txt)
    out_pins = {}
    unbound = []
    for n, txt in pins.items():
        new = rmap.get(n)
        if new is None:
            if n in ('VDD', 'VSS'):
                other.append(txt)
            else:
                unbound.append(n)
            continue
        txt = re.sub(r'^pin\s*\("?[^")]+"?\)', f'pin("{new}")', txt)
        txt = re.sub(r'related_pin\s*:\s*"([^"]+)"', lambda mm: f'related_pin : "{rmap.get(mm.group(1), mm.group(1))}"', txt)
        dm = re.search(r'direction\s*:\s*(\w+)', txt)
        base, idx = re.match(r'(\w+)\[(\d+)\]', new).groups()
        dirs.setdefault(base, set()).add(dm.group(1) if dm else 'input')
        out_pins.setdefault(base, {})[int(idx)] = txt
    types, cells = [], []
    for base in sorted(out_pins):
        w = widths[base]
        types.append(f'  type ("{base}") {{\n    base_type : array;\n    data_type : bit;\n    bit_width : {w};\n'
                     f'    bit_from : {w - 1};\n    bit_to : 0;\n  }}\n')
        dset = dirs[base]
        d = next(iter(dset)) if len(dset) == 1 else 'inout'
        missing = [i for i in range(w) if i not in out_pins[base]]
        assert not missing, (base, missing[:5])
        cells.append(f'    bus("{base}") {{\n      bus_type : {base};\n      direction : {d};\n'
                     + ''.join('    ' + out_pins[base][i] + '\n' for i in range(w)) + '    }\n')
    txt = (t[:lib_g[2]] + f'library ({master}_{corner}) {{' + head + ''.join(types)
           + f'  cell ({master}) {{' + cell_attrs + ''.join(cells) + ''.join('    ' + o + '\n' for o in other)
           + '  }\n}\n')
    return txt, unbound


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lef', required=True)
    ap.add_argument('--lib-ss')
    ap.add_argument('--lib-ff')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rmap = binding()
    widths = {}
    for n in rmap.values():
        b, i = re.match(r'(\w+)\[(\d+)\]', n).groups()
        widths[b] = max(widths.get(b, 0), int(i) + 1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t, unbound = lef_rename(Path(a.lef).read_text(), rmap, 'hfd_sm')
    (out / 'hfd_sm.lef').write_text(t)
    rec = dict(binding_bits=len(rmap), rtl_pins_without_die_bit=unbound)
    for c, p in (('ss', a.lib_ss), ('ff', a.lib_ff)):
        if p:
            lt, unb = lib_rename(Path(p).read_text(), rmap, 'hfd_sm', c, widths)
            rec[f'lib_{c}_rtl_pins_without_die_bit'] = unb
            (out / f'hfd_sm_{c}.lib').write_text(lt)
    print(json.dumps(rec))


if __name__ == '__main__':
    main()
