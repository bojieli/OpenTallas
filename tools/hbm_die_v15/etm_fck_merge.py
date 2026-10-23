#!/usr/bin/env python3
"""ETM-CK (2026-10-22): keep forwarded-clock pass-through arcs combinational in a clocked synth ETM.

synth_etm.sh clocks the relay / landing kits on ck / ckf (before: no clock -> no arcs at all, die STA untimed every
relay hop).  With ck a clock, write_timing_model turns the landing-hop forwarded clock output (ck_o = ~ck) into
rising/falling_edge arcs, which stop clock propagation through the hop chain at die level.  For every output pin whose
CLOCK-LESS model has a combinational arc related to a clock input (ck/ckf/ck_*/ckf_*), the pin's timing groups are
taken from the clock-less model; every other pin keeps the clocked model (setup/hold/clk->Q).  Each such pin must have
ONLY clock-related arcs in the clocked model (a data output from ck is never replaced).

  etm_fck_merge.py CLOCKED.lib NOCLK.lib       (rewrites CLOCKED.lib in place; prints ETM_FCK_MERGE <n> pins)
"""
import re, sys

CK = re.compile(r'^(ck|ckf|ck_\w+|ckf_\w+)$')


def blocks(text, head):
    """(start, end, name) of every `head("name") { ... }` block (brace matched)."""
    out = []
    for m in re.finditer(head + r'\s*\(\s*"([^"]*)"\s*\)\s*\{', text):
        d, i = 1, m.end()
        while d:
            ch = text[i]
            d += ch == '{'
            d -= ch == '}'
            i += 1
        out.append((m.start(), i, m.group(1)))
    return out


def timings(block):
    return [block[a:b] for a, b, _ in blocks(block.replace('timing()', 'timing("")'), 'timing')]


def related(t):
    m = re.search(r'related_pin\s*:\s*"([^"]+)"', t)
    return m.group(1) if m else None


def ttype(t):
    m = re.search(r'timing_type\s*:\s*"?(\w+)', t)
    return m.group(1) if m else 'combinational'


def main(clocked, noclk):
    a, b = open(clocked).read(), open(noclk).read()
    nb = {n: b[s:e] for s, e, n in blocks(b, 'pin')}
    out, last, n = [], 0, 0
    for s, e, name in blocks(a, 'pin'):
        blk = a[s:e]
        if 'direction : output' not in blk or name not in nb:
            continue
        src = [t for t in timings(nb[name]) if CK.match(related(t) or '') and ttype(t).startswith('combinational')]
        if not src:
            continue
        cur = timings(blk)
        if any(not CK.match(related(t) or '') for t in cur):
            sys.exit(f'ETM_FCK_MERGE_FAIL {name}: output also has data arcs in the clocked model')
        first = blk.find('timing()')
        head = blk[:first] if first >= 0 else blk[:blk.rfind('}')]
        new = head + ''.join(x.replace('timing("")', 'timing()') + '\n      ' for x in src).rstrip() + '\n    }'
        out += [a[last:s], new]
        last, n = e, n + 1
    out.append(a[last:])
    open(clocked, 'w').write(''.join(out))
    print(f'ETM_FCK_MERGE {n} pins {clocked}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
