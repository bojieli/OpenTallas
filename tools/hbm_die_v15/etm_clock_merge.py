#!/usr/bin/env python3
"""ETM clock-bus merge for synth_etm.sh (HBM-RTL4 2026-10-18).

Why: synth_etm.sh created ONE clock per clock-port BIT.  A master with wide clock buses (ot_hbm_idx_score_static:
clk_ctl 1 + clk_engine 4 + clk_meta 4 + clk_tail 4 + clk_chunk 16 + clk_hslice 512 = 541 clocks) then carries one
OpenSTA clock (path group, clock network, tag set) per bit; with 36.9 M flat cells the TT ETM was OOM-killed at
112/117 GB (10-18 02:31) and needed a 154 GB container on 10-16.  Every bit of such a bus is bound to the SAME die
clock domain (contract clock_resets: one hb_ckgen output per port), and the ETM is an ideal-clock estimate
(0 insertion on every pin), so one clock per wide bus gives the same arcs.

    etm_clock_merge.py netlist STA_V TOP MAX OUT_JSON   rewires, inside module TOP only, every connection of a clock
        bus wider than MAX bits to its lsb bit (in place); writes {merged: {bus: [width, lsb, lo]}, clocks: [...]}
        -- `clocks` is the port-bit list create_clock is applied to (unmerged bits + the lsb of each merged bus).
    etm_clock_merge.py lib LIB OUT_JSON                 restores the per-bit clock pins of each merged bus in the
        written model: every bit gets `clock : true`, the lsb pin's clock_tree_path arcs, and capacitance C/width
        (C = the lsb pin's capacitance, which carries the whole bus's sinks after the merge).

Setup/hold/clock->output arcs of the merged bus relate to its lsb pin only.  With ideal clocks they are identical
for every bit; at the die level the die tree drives all bits of the bus from one domain (neighbour skew applies
between the lsb pin and the others, exactly as between any two sinks of one root).  Masters whose clock buses are
all <= MAX bits are untouched (the tcl then sees the same per-bit clock list as before).
"""
import json, os, re, sys

CLK = re.compile(r'^(clk|clk_.*|.*_clk|.*_clk_.*|pg_clk.*)$')   # = synth_etm.sh get_ports {clk clk_* *_clk *_clk_* pg_clk*}


def top_span(txt, top):
    m = re.search(r'^module\s+' + re.escape(top) + r'\s*\(', txt, re.M)
    if not m:
        sys.exit(f'etm_clock_merge: module {top} not found')
    e = re.compile(r'^endmodule\b', re.M).search(txt, m.end())
    return m.start(), e.end()


def netlist(sta_v, top, mx, out_json):
    txt = open(sta_v).read()
    a, b = top_span(txt, top)
    body = txt[a:b]
    ports = {}                                   # clock input -> (msb, lsb) or None (scalar)
    nomerge = set()                              # clock-named outputs/inouts keep the old per-bit clocks, never merged
    for m in re.finditer(r'^\s*(input|output|inout)\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*;', body, re.M):
        if CLK.match(m.group(4)):
            ports[m.group(4)] = (int(m.group(2)), int(m.group(3))) if m.group(2) else None
            if m.group(1) != 'input':
                nomerge.add(m.group(4))
    merged, clocks = {}, []
    for p, r in sorted(ports.items()):
        if r is None:
            clocks.append(p)
            continue
        hi, lo = max(r), min(r)
        w = hi - lo + 1
        if w <= mx or p in nomerge:
            clocks += [f'{p}[{i}]' for i in range(lo, hi + 1)]
            continue
        lsb = r[1]
        merged[p] = [w, lsb, lo]
        clocks.append(f'{p}[{lsb}]')
    if merged:
        lines = body.split('\n')
        decl = re.compile(r'^\s*(input|output|inout|wire)\b')
        for i, ln in enumerate(lines):
            if decl.match(ln) or ln.startswith('module '):
                continue
            for p, (w, lsb, _lo) in merged.items():
                ref = f'{p}[{lsb}]'

                def sl(m):
                    x, y = int(m.group(1)), int(m.group(2))
                    return '{' + ', '.join([ref] * (abs(x - y) + 1)) + '}'
                ln = re.sub(r'(?<![.\w])' + p + r'\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]', sl, ln)
                ln = re.sub(r'(?<![.\w])' + p + r'\s*\[\s*\d+\s*\]', ref, ln)
                ln = re.sub(r'(?<![.\w])' + p + r'\b(?!\s*\[)', '{' + ', '.join([ref] * w) + '}', ln)
            lines[i] = ln
        body = '\n'.join(lines)
        open(sta_v, 'w').write(txt[:a] + body + txt[b:])
    json.dump(dict(top=top, max_bus=mx, merged=merged, clocks=clocks, clock_count=len(clocks),
                   port_bits=sum(1 if r is None else abs(r[0] - r[1]) + 1 for r in ports.values())),
              open(out_json, 'w'), indent=1)
    print(f'OT_ETM_CLOCK_MERGE ports={len(ports)} clocks={len(clocks)} merged={",".join(f"{p}:{v[0]}" for p, v in merged.items()) or "-"}')


def block(txt, start):
    i = txt.index('{', start)
    d = 0
    for j in range(i, len(txt)):
        d += txt[j] == '{'
        d -= txt[j] == '}'
        if d == 0:
            return start, j + 1
    sys.exit('etm_clock_merge: unbalanced lib')


def lib(path, js):
    M = json.load(open(js))['merged']
    if not M:
        return
    txt = open(path).read()
    for p, (w, lsb, lo) in M.items():
        m = re.search(r'^([ \t]*)pin\("' + re.escape(f'{p}[{lsb}]') + r'"\)', txt, re.M)
        if not m:
            sys.exit(f'etm_clock_merge: pin {p}[{lsb}] not in {path}')
        s, e = block(txt, m.start())
        ref = txt[s:e]
        cap = float(re.search(r'capacitance\s*:\s*([0-9.eE+-]+)', ref).group(1))
        each = re.sub(r'capacitance\s*:\s*[0-9.eE+-]+', f'capacitance : {cap / w:.4f}', ref, count=1)
        if 'clock : true' not in each:
            each = re.sub(r'(direction\s*:\s*input\s*;)', r'\1\n' + m.group(1) + '  clock : true;', each, count=1)
        txt = txt[:s] + each + txt[e:]
        done = 1
        for bit in range(lo, lo + w):
            name = f'{p}[{bit}]'
            if bit == lsb:
                continue
            mm = re.search(r'^[ \t]*pin\("' + re.escape(name) + r'"\)', txt, re.M)
            if not mm:
                sys.exit(f'etm_clock_merge: pin {name} not in {path}')
            s2, e2 = block(txt, mm.start())
            txt = txt[:s2] + each.replace(f'pin("{p}[{lsb}]")', f'pin("{name}")', 1) + txt[e2:]
            done += 1
        print(f'OT_ETM_CLOCK_LIB {p} bits={done} cap_each={cap / w:.4f}')
    tmp = path + '.merge_tmp'               # the ETM container writes the lib as root: replace it, never rewrite in place
    open(tmp, 'w').write(txt)
    os.replace(tmp, path)


if __name__ == '__main__':
    if sys.argv[1] == 'netlist':
        netlist(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])
    elif sys.argv[1] == 'lib':
        lib(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
