#!/usr/bin/env python3
"""QC-TTCTLM-1119 R2: let synthesis see across the combinational bmath gates of an HP13 generated core.

The HP13 generated cores (qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_*) instantiate every 2-input gate as its own
(* keep=1, keep_hierarchy="yes" *) qfd_bmath_* cell.  The kit synthesis then maps each gate alone: no constant
propagation (mux(1'b0,b,s) stays INV+AND2+AO21 with a tied input), no multi-level restructuring, every mux 3 std-cell
levels.  On tt_ctlm this is the whole TT setup deficit (49 of the worst 50 ends: one 24-28 level flat cone).

This tool rewrites a kit's copies of the core netlist and its helpers file, function unchanged:
  * combinational qfd_bmath modules (and/or/not/xor/mux/ao21/oa21) lose keep_hierarchy, and their instances lose the
    keep / keep_hierarchy attribute, so the kit's flatten + abc (&dch, &if, &nf -D OT_ABC_TARGET_PS) restructures them;
  * flip-flop cells (qfd_bmath_dff_*) keep every attribute and name: the register set, reset forest and LEC
    correspondence are untouched;
  * --dup INST:N (optional) adds N-1 copies of a flip-flop (same C/D/R, kept) plus copies of its single-fanout
    inverter and the gate that inverter drives, and spreads that gate's readers round-robin over the copies
    (fanout split of the critical start register, 0 cycles).
Usage: bmath_flatten.py CORE.sv HELPERS.sv [--dup u_75259:4]   (files rewritten in place; copy the kit first)
"""
import argparse, collections, hashlib, json, re, sys
from pathlib import Path

COMB = ("and", "or", "not", "xor", "mux", "ao21", "oa21")
ATTR = '(* keep=1, keep_hierarchy="yes" *) '
CELL = re.compile(r'(?m)^(?P<attr>\(\*[^\n]*?\*\)\s*)?(?P<master>qfd_bmath_(?P<kind>\w+)) #\(\.ID\(0\)\) (?P<name>u_\d+)\((?P<pins>[^;]+)\);')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def pins_of(s):
    return dict(re.findall(r'\.(\w+)\(([^()]+)\)', s))


def fmt(master, name, pins, attr=ATTR):
    return f"{attr}{master} #(.ID(0)) {name}(" + ",".join(f".{k}({v})" for k, v in pins.items()) + ");"


def dup_split(text, inst, n):
    cells = {m['name']: m for m in CELL.finditer(text)}
    users = collections.defaultdict(list)
    for m in cells.values():
        for k, v in pins_of(m['pins']).items():
            if k not in ('Q', 'Y'):
                users[v].append((m['name'], k))
    f = cells[inst]
    fp = pins_of(f['pins'])
    assert f['kind'].startswith('dff'), inst
    q = fp['Q']
    qu = users[q]
    assert len(qu) == 1 and cells[qu[0][0]]['kind'] == 'not', ('expect one inverter reader', qu)
    inv = cells[qu[0][0]]
    ip = pins_of(inv['pins'])
    iu = users[ip['Y']]
    assert len(iu) == 1, ('expect one gate after the inverter', iu)
    g = cells[iu[0][0]]
    gp = pins_of(g['pins'])
    readers = users[gp['Y']]
    assert len(readers) >= n, (len(readers), n)
    # net -> literal "n_<int>" naming; new nets get fresh numbers above the max
    top = max(int(x) for x in re.findall(r'\bn_(\d+)\b', text)) + 1
    new_lines, decl, ren = [], [], {}
    for c in range(1, n):
        nq, ny, ng = f"n_{top}", f"n_{top+1}", f"n_{top+2}"
        top += 3
        decl += [nq, ny, ng]
        new_lines.append(fmt(f['master'], f"{inst}_d{c}", {**fp, 'Q': nq}))
        new_lines.append(fmt(inv['master'], f"{inv['name']}_d{c}", {**ip, 'A': nq, 'Y': ny}))
        g2 = {k: (ny if v == ip['Y'] else v) for k, v in gp.items()}
        g2['Y'] = ng
        new_lines.append(fmt(g['master'], f"{g['name']}_d{c}", g2))
        ren[c] = ng
    # round-robin the readers of the gate output: reader i -> copy i % n (copy 0 = the original)
    moved = []
    for i, (rname, rpin) in enumerate(sorted(readers)):
        c = i % n
        if c == 0:
            continue
        m = cells[rname]
        p = pins_of(m['pins'])
        assert p[rpin] == gp['Y']
        p[rpin] = ren[c]
        moved.append((rname, rpin, c, m))
    # apply reader edits from the end so match offsets stay valid
    for rname, rpin, c, m in sorted(moved, key=lambda x: -x[3].start()):
        p = pins_of(m['pins'])
        p[rpin] = ren[c]
        text = text[:m.start()] + fmt(m['master'], rname, p, m['attr'] or '') + text[m.end():]
    block = ("\n// QC-TTCTLM-1119 R2 fanout split of " + inst + f" into {n} kept copies (0 cycles)\n"
             "wire " + ", ".join(decl) + ";\n" + "\n".join(new_lines) + "\n")
    i = text.index('endmodule', text.index(f" {inst}("))
    text = text[:i] + block + text[i:]
    return text, {'inst': inst, 'copies': n, 'inverter': inv['name'], 'gate': g['name'], 'gate_readers': len(readers),
                  'moved': [(r, p, c) for r, p, c, _ in moved]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('core')
    ap.add_argument('helpers')
    ap.add_argument('--dup', default='')
    ap.add_argument('--keep-comb', action='store_true', help='do not flatten (dup only)')
    a = ap.parse_args()
    core, hel = Path(a.core), Path(a.helpers)
    rec = {'core_in': sha(core.read_bytes()), 'helpers_in': sha(hel.read_bytes())}
    text = core.read_text()
    if a.dup:
        inst, n = a.dup.split(':')
        text, rec['dup'] = dup_split(text, inst, int(n))
    if not a.keep_comb:
        cnt = collections.Counter()

        def strip(m):
            if m['kind'] in COMB and m['attr']:
                cnt[m['kind']] += 1
                return m.group(0)[len(m['attr']):]
            return m.group(0)
        text = CELL.sub(strip, text)
        rec['unkept_instances'] = dict(cnt)
        h = hel.read_text()
        for k in COMB:
            old = f'(* keep_hierarchy="yes" *) module qfd_bmath_{k} #('
            assert h.count(old) == 1, k
            h = h.replace(old, f'module qfd_bmath_{k} #(', 1)
        hel.write_text(h)
    core.write_text(text)
    rec['core_out'] = sha(core.read_bytes())
    rec['helpers_out'] = sha(hel.read_bytes())
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
