#!/usr/bin/env python3
"""HBMc/TOKEN2 (10-22): make Verilator hierarchical verilation actually hierarchical for parameterised masters.

Finding (toy + PV r18 bench, Verilator 5.050 and Debian 5.032): a /*verilator hier_block*/ module that has
parameters is NOT substituted by its protect-lib wrapper in the top pass (even at default values) -- the top is
elaborated FLAT (PV r18 top: 16.9 GB of C++ / 109 GB, r18 source slice > 330 GB) and every hier library is built
for nothing.  A hier block WITHOUT parameters is substituted.  So: for every parameterised hier master instantiated
by the slice, emit one parameter-free wrapper per distinct parameter set,

    module <M>_hw<k> #(localparam ... = <value>, ...) (<M's ANSI port list>); /*verilator hier_block*/
        <M> #(.P(P), ...) u (.*);
    endmodule

drop the hier_block mark from <M>, and instantiate the wrapper in the slice.  Function is unchanged (the same
master, the same parameter values, ports connected by name).

  hier_param_wrap.py --bundle B   (after flatten_masters.py) -> B/slice/slice_hw.v, B/slice/hier_wraps.sv; prints a summary
"""
import argparse, re, sys
from pathlib import Path

MARK = '/*verilator hier_block*/'


def match_paren(t, i):
    d = 0
    for j in range(i, len(t)):
        if t[j] == '(':
            d += 1
        elif t[j] == ')':
            d -= 1
            if d == 0:
                return j
    raise ValueError('unbalanced')


def split_top(s):
    out, d, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            d += 1
        elif ch in ')]}':
            d -= 1
        if ch == ',' and d == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def header(t, m):
    mm = re.search(r"\bmodule\s+" + re.escape(m) + r"\s*#\s*\(", t)
    if not mm:
        return None
    p0 = mm.end() - 1; p1 = match_paren(t, p0)
    q0 = t.index('(', p1 + 1); q1 = match_paren(t, q0)
    params = []
    for item in split_top(t[p0 + 1:p1]):
        it = re.sub(r'//[^\n]*', '', item).strip()
        x = re.match(r"(parameter|localparam)?\s*(.*?)\b([A-Za-z_]\w*)\s*=\s*(.*)$", it, re.S)
        if not x:
            sys.exit(f'hier_param_wrap: cannot parse parameter {it!r} of {m}')
        params.append((x.group(1) or 'parameter', x.group(2).strip(), x.group(3), x.group(4).strip()))
    return dict(params=params, ports=t[q0 + 1:q1], end=q1, start=mm.start())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--min-bytes', type=int, default=0, help='opt-in: masters smaller than this (relays, pads) are left unwrapped and elaborate in their parent (equiv-checked on the collar slice: collar2 bit-exact)')
    a = ap.parse_args(); B = Path(a.bundle)
    sv = (B / 'slice' / 'slice.v').read_text()
    inst_re = re.compile(r"^(  )([A-Za-z_]\w*)(?:\s*#\((.*?)\))?(\s+[A-Za-z_]\w*\s*\()", re.M)
    hdrs, sets, wraps, n_inst = {}, {}, [], 0

    def sub(mo):
        nonlocal n_inst
        m, ov = mo.group(2), mo.group(3)
        f = B / 'masters' / f'{m}.sv'
        if not f.exists():
            return mo.group(0)
        if m not in hdrs:
            t = f.read_text()
            hdrs[m] = header(t, m) if MARK in t else None
            if hdrs[m] and len(t) < a.min_bytes:
                hdrs[m]['small'] = True
        h = hdrs[m]
        if not h or h.get('small'):
            return mo.group(0)            # parameter-free master: Verilator substitutes it already
        ovd = {}
        for it in split_top(ov or ''):
            x = re.match(r"\s*\.(\w+)\s*\((.*)\)\s*$", it, re.S)
            if x:
                ovd[x.group(1)] = x.group(2).strip()
        key = (m, tuple(sorted(ovd.items())))
        if key not in sets:
            k = sum(1 for kk in sets if kk[0] == m)
            name = f'{m}_hw{k}'
            sets[key] = name
            plist = ', '.join(f"localparam {ty + ' ' if ty else ''}{nm} = {ovd.get(nm, dv)}" for kind, ty, nm, dv in h['params'] if kind == 'parameter')
            lps = [f"localparam {ty + ' ' if ty else ''}{nm} = {dv}" for kind, ty, nm, dv in h['params'] if kind == 'localparam']
            plist = ', '.join([plist] + lps) if lps else plist
            conn = ', '.join(f'.{nm}({nm})' for kind, ty, nm, dv in h['params'] if kind == 'parameter')
            wraps.append(f"module {name} #({plist}) ({h['ports']}); {MARK}\n  {m} #({conn}) u (.*);\nendmodule\n")
        n_inst += 1
        return f"{mo.group(1)}{sets[key]}{mo.group(4)}"

    out = inst_re.sub(sub, sv)
    # the parameterised masters lose their own hier mark (they are elaborated inside the wrapper blocks)
    for m, h in hdrs.items():
        if h:
            f = B / 'masters' / f'{m}.sv'; t = f.read_text()
            i = t.find(MARK, h['end'])
            if i >= 0 and i - h['end'] < 40:
                f.write_text(t[:i] + '/* hier_block moved to its _hw wrappers */' + t[i + len(MARK):])
    (B / 'slice' / 'slice_hw.v').write_text(out)
    (B / 'slice' / 'hier_wraps.sv').write_text('`timescale 1ns/1ps\n' + '\n'.join(wraps))
    print(f'HIER_PARAM_WRAP masters={sum(1 for h in hdrs.values() if h and not h.get("small"))} small_unmarked={sum(1 for h in hdrs.values() if h and h.get("small"))} wrappers={len(wraps)} instances={n_inst}')


if __name__ == '__main__':
    main()
