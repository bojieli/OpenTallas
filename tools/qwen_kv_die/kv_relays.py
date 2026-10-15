#!/usr/bin/env python3
"""qwen-split/kvsys v1.2 (2026-10-14, owner 08:05 PT NO STUBS): REAL RTL of the KV/system die's relay stations.

Every die relay qkd_rly_<W> is one register stage of a die bus on the core clock.  A die bus may carry bits in both
directions (a word + valid down, a credit back): the per-bit direction is the die's DIRECTION MODEL (tools/die_top_lint.py
endpoint_dirs: real masters through their RTL ports, the bus-class rules otherwise), which die_top_lint already writes into
its registered placeholder stubs (a bit the stub assigns on port b runs a -> b, a bit it assigns on port a runs b -> a).
This tool turns those per-bit directions into the relay RTL itself:

    forward bits  a[i] -> flop -> b[i]          reverse bits  b[i] -> flop -> a[i]

one flop a bit, no reset (a relay is a pipeline register: while the endpoints are held in reset their reset-state
words flush every chain within its depth; contract rule: the KV die's reset sequencer releases rso_* >= RELAY_FLUSH core
cycles after the core clock runs), no logic between pin and flop.  A master whose bits all run a -> b gets plain
input / output ports; a mixed one declares a / b inout (each BIT still has exactly one driver: the flop on its far side).
Every bit must be exactly one of forward / reverse (a conflicting or undirected bit is an error: no stubs).

    python3 tools/qwen_kv_die/kv_relays.py --stubs LINT/qwen_kv_lint_top_stubs.sv --out FILE.sv [--json FILE.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

RELAY_FLUSH = 128


def parse(stubs):
    """{master: dict(w, fwd=set, rev=set)} for every qkd_rly_* stub"""
    out, cur = {}, None
    for ln in Path(stubs).read_text().splitlines():
        m = re.match(r'\s*module (qkd_rly_\w+)', ln)
        if m:
            cur = out.setdefault(m.group(1), dict(w=None, fwd=set(), rev=set(), ports={}))
            continue
        if cur is None:
            continue
        if re.match(r'\s*endmodule', ln):
            cur = None
            continue
        m = re.match(r'\s*(input|output|inout) wire \[(\d+):0\] (\w+)', ln)
        if m:
            cur['ports'][m.group(3)] = (m.group(1), int(m.group(2)) + 1)
            continue
        for m in re.finditer(r'assign (\w+) ?\[(\d+):(\d+)\] = r_', ln):   # main 10-14: die_top_lint writes 'b [h:l]'
            rng = set(range(int(m.group(3)), int(m.group(2)) + 1))
            (cur['fwd'] if m.group(1) == 'b' else cur['rev'] if m.group(1) == 'a' else set()).update(rng)
    for mst, r in out.items():
        if set(r['ports']) != {'a', 'b', 'ck'}:
            raise SystemExit(f'{mst}: relay ports {sorted(r["ports"])} != a / b / ck')
        w = r['ports']['a'][1]
        if r['ports']['b'][1] != w:
            raise SystemExit(f'{mst}: a / b widths differ')
        r['w'] = w
        both = r['fwd'] & r['rev']
        none = set(range(w)) - r['fwd'] - r['rev']
        if both or none:
            raise SystemExit(f'{mst}: bits with no single direction: both {sorted(both)[:8]} none {sorted(none)[:8]}')
    return out


def crosscheck(rel, die_v, split=True):
    """every relay chain whose end is a REAL bound master (kv_die.BINDINGS): the direction of each bit at that end (its
    RTL port direction) must equal the relay's.  Returns [(relay inst, end, bit, relay dir, rtl dir)] conflicts."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kv_die as K
    from binding_order import sliced_order
    import die_port_bind_kv as P
    K._set_geometry(split)
    root = Path(__file__).resolve().parents[2]
    wires, insts = P.parse_die(die_v)
    by_net = {}
    inst_m = {}
    for mst, inst, conns in insts:
        inst_m[inst] = mst
        for c in re.finditer(r'\.(\\?\S+?)\(([^()]*)\)', conns):
            by_net.setdefault(c.group(2).strip(), []).append((inst, c.group(1)))
    hdr = {}

    def rtl_dirs(mst, port):
        b = K.BINDINGS.get(mst)
        if b is None:
            return None
        if mst not in hdr:
            f = root / b['file']
            hdr[mst] = P.header(f.read_text(errors='replace'), b['module']) if f.exists() else (None, None)
        params, ports = hdr[mst]
        if ports is None:
            raise ValueError(f'{mst}: bound RTL header could not be parsed')
        params = dict(params or {}, **{k: str(v) for k, v in (b.get('parameters') or {}).items()})
        base = (b.get('sliced') or {}).get(port, port)
        if base not in b['ports']:
            raise ValueError(f'{mst}.{port}: no bound RTL port mapping')
        bits = []
        for rp in b['ports'][base]:
            d, w = ports[rp]
            width = P.evalw(w, params)
            if width is None:
                raise ValueError(f'{mst}.{rp}: unresolved RTL width {w}')
            bits += [d] * width
        if base != port:      # k-th slice of the base concatenation (slices in die-port order)
            sl = sliced_order(base, [base] + [k for k, v in b['sliced'].items() if v == base])
            n = len(bits) // len(sl)
            k = sl.index(port)
            bits = bits[k * n:(k + 1) * n]
        return bits

    conf, checked = [], 0
    relays = [(mst, inst, conns) for mst, inst, conns in insts if mst.startswith('qkd_rly')]
    relay_conns = {i: c for _, i, c in relays}
    heads = [x for x in relays if not any(inst_m[i].startswith('qkd_rly') for i, _ in
             by_net.get(re.search(r'\.a\(([^()]*)\)', x[2]).group(1).strip(), []) if i != x[1])]
    visited = set()
    for mst, inst, conns in heads:
        r = rel[mst]
        na = re.search(r'\.a\(([^()]*)\)', conns).group(1).strip()
        ea = [(i, p) for i, p in by_net.get(na, []) if i != inst]
        if len(ea) > 1:
            raise ValueError(f'{inst}: multiple upstream endpoints need a bit-level direction check')
        cur, tail = inst, conns
        chain = set()
        while True:
            if cur in chain:
                raise ValueError(f'{inst}: cyclic relay chain at {cur}')
            chain.add(cur)
            visited.add(cur)
            other = rel[inst_m[cur]]
            if other['w'] != r['w'] or other['fwd'] != r['fwd'] or other['rev'] != r['rev']:
                raise ValueError(f'{inst}: relay direction changes at {cur}')
            nb = re.search(r'\.b\(([^()]*)\)', tail).group(1).strip()
            nx = [(i, p) for i, p in by_net.get(nb, []) if i != cur]
            if len(nx) == 1 and inst_m[nx[0][0]].startswith('qkd_rly'):
                if nx[0][1] != 'a':
                    raise ValueError(f'{cur}: relay b connects to {nx[0][0]}.{nx[0][1]}, expected a')
                cur = nx[0][0]
                tail = relay_conns[cur]
                continue
            if len(nx) > 1:
                raise ValueError(f'{cur}: branched relay net needs a bit-level direction check')
            eb = nx[0] if len(nx) == 1 else None
            break
        for endpoint, side in ((ea[0] if ea else None, 'a'), (eb, 'b')):
            if endpoint is None:
                continue
            i, p = endpoint
            d = rtl_dirs(inst_m[i], p.lstrip('\\'))
            if d is None:
                continue
            checked += 1
            for k, dk in enumerate(d[:r['w']]):
                fwd = k in r['fwd']
                want_fwd = (dk == 'output') if side == 'a' else (dk == 'input')
                if dk in ('input', 'output') and fwd != want_fwd:
                    conf.append((inst, f'{i}.{p}', k, 'fwd' if fwd else 'rev', dk))
    missed = set(relay_conns) - visited
    if missed:
        raise ValueError(f'relay chains without an upstream head: {sorted(missed)[:6]}')
    return conf, checked


def runs(bits):
    s = sorted(bits)
    out, i = [], 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[j] + 1:
            j += 1
        out.append((s[i], s[j]))
        i = j + 1
    return out


def emit(rel, mut=0):
    """mut (bench mutants, never published): 1 = every relay's highest forward bit is NOT registered (a wire: the
    stage drops a cycle on that bit), 2 = reverse bits are driven from the a side (direction lost)"""
    L = ['// GENERATED by tools/qwen_kv_die/kv_relays.py (qwen-split/kvsys v1.2): the KV/system die relay stations.',
         '// One register a bit on the core clock ck, per-bit direction from the die direction model (forward a -> b,',
         f'// reverse b -> a), no reset (flush rule: rso_* released >= {RELAY_FLUSH} core cycles after the clock runs).',
         '`timescale 1ns/1ps', '']
    for mst in sorted(rel, key=lambda k: (rel[k]['w'], k)):
        r = rel[mst]
        w = r['w']
        mixed = bool(r['rev'])
        L.append(f'module {mst} (')
        if mixed:
            L.append(f'    inout  wire [{w - 1}:0] a,       // forward bits in, reverse bits out')
            L.append(f'    inout  wire [{w - 1}:0] b,       // forward bits out, reverse bits in')
        else:
            L.append(f'    input  wire [{w - 1}:0] a,')
            L.append(f'    output wire [{w - 1}:0] b,')
        L.append('    input  wire ck')
        L.append(');')
        for lo, hi in runs(r['fwd']):
            if mut == 1 and hi == max(r['fwd']):
                L.append(f'    assign b[{hi}] = a[{hi}];   // MUT 1')
                if hi == lo:
                    continue
                hi -= 1
            L.append(f'    reg [{hi - lo}:0] f_{lo}; always @(posedge ck) f_{lo} <= a[{hi}:{lo}]; assign b[{hi}:{lo}] = f_{lo};')
        for lo, hi in runs(r['rev']):
            src = 'a' if mut == 2 else 'b'
            L.append(f'    reg [{hi - lo}:0] r_{lo}; always @(posedge ck) r_{lo} <= {src}[{hi}:{lo}]; assign a[{hi}:{lo}] = r_{lo};')
        L.append('endmodule')
        L.append('')
    return '\n'.join(L)


def bench(rel):
    """self-checking bench: every relay master, random forward words on a / reverse words on b each cycle; after each
    edge b[fwd] must equal the previous a[fwd] and a[rev] the previous b[rev] (prints RELAY_BENCH PASS / FAIL n)"""
    L = ['`timescale 1ns/1ps', 'module tb_qkd_kv_relays;', '    reg ck = 0; integer err = 0, cyc;']
    for k, mst in enumerate(sorted(rel)):
        r = rel[mst]
        w = r['w']
        fm = ''.join('1' if i in r['fwd'] else '0' for i in reversed(range(w)))
        L += [f'    wire [{w - 1}:0] a{k}, b{k}; reg [{w - 1}:0] da{k}, db{k}, pa{k}, pb{k};',
              f"    localparam [{w - 1}:0] F{k} = {w}'b{fm};",
              f'    genvar g{k}; for (g{k} = 0; g{k} < {w}; g{k} = g{k} + 1) begin : d{k}',
              f"        assign a{k}[g{k}] = F{k}[g{k}] ? da{k}[g{k}] : 1'bz; assign b{k}[g{k}] = F{k}[g{k}] ? 1'bz : db{k}[g{k}];",
              '    end',
              f'    {mst} u{k} (.a(a{k}), .b(b{k}), .ck(ck));']
    L.append('    task rnd; begin')
    for k, mst in enumerate(sorted(rel)):
        w = rel[mst]['w']
        L.append(f'        da{k} = {{{(w + 31) // 32}{{$urandom}}}}; db{k} = {{{(w + 31) // 32}{{$urandom}}}};')
    L.append('    end endtask')
    L += ['    initial begin', '        rnd; #1;', '        for (cyc = 0; cyc < 64; cyc = cyc + 1) begin']
    for k, mst in enumerate(sorted(rel)):
        L.append(f'            pa{k} = da{k}; pb{k} = db{k};')
    L += ['            ck = 1; #1; rnd; #1;   // new inputs before the check: a combinational path shows']
    for k, mst in enumerate(sorted(rel)):
        L.append(f'            if (((b{k} ^ pa{k}) & F{k}) !== 0 || ((a{k} ^ pb{k}) & ~F{k}) !== 0) begin err = err + 1; '
                 f'if (err < 5) $display("MISMATCH {mst} cyc %0d", cyc); end')
    L += ['            #1 ck = 0; #1;', '        end',
          '        if (err == 0) $display("RELAY_BENCH PASS"); else $display("RELAY_BENCH FAIL %0d", err);',
          '        $finish;', '    end', 'endmodule', '']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--stubs', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--json', type=Path)
    ap.add_argument('--die-v', help='cross-check every relay chain against the RTL port directions of its REAL ends')
    ap.add_argument('--bench', type=Path, help='also write the self-checking bench (tb_qkd_kv_relays)')
    ap.add_argument('--mut', type=int, default=0, help='bench mutant (never published)')
    a = ap.parse_args(argv)
    rel = parse(a.stubs)
    if not rel:
        raise SystemExit('no qkd_rly_* stubs found')
    if a.die_v:
        conf, checked = crosscheck(rel, a.die_v)
        print(json.dumps(dict(crosscheck_real_ends=checked, conflicts=len(conf), examples=conf[:6])))
        if conf:
            raise SystemExit('relay direction conflicts with a REAL end (fix the die bus class): '
                             + '; '.join(f'{c[0]} end {c[1]} bit {c[2]} relay {c[3]} rtl {c[4]}' for c in conf[:6]))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(emit(rel, a.mut))
    if a.bench:
        a.bench.write_text(bench(rel))
    rec = dict(schema='opentallas.qwen_kvsys_relays.v1', file=str(a.out), flush_rule_cycles=RELAY_FLUSH,
               masters={m: dict(width=r['w'], forward=len(r['fwd']), reverse=runs(r['rev'])) for m, r in sorted(rel.items())})
    if a.json:
        a.json.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(masters=len(rel), mixed=sum(1 for r in rel.values() if r['rev']),
                          flops=sum(r['w'] for r in rel.values()))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
