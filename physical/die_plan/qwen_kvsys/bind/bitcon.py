#!/usr/bin/env python3
"""KV-P2 10-23: BIT-LEVEL as-built connectivity of the KV die (rtl6 GEN die.v), the input of the generated-die binder.
For every content-leaf INPUT bit: its driving content-leaf OUTPUT bit after collapsing the pass-through masters
(relays / landing / reset-region cells, extract_asbuilt.PASS_RE), or a constant (tie) or nothing (undriven).
Port directions per bit from gen_source_ports.json (LSB-first lists, checked on host.fdi; extract_asbuilt read them MSB-first, which is
why the mixed-direction FDI bundles came out 1-2 bits wide).
    python3 bind/bitcon.py --die die.v --ports gen_source_ports.json --out bitcon.json.gz"""
import argparse, collections, gzip, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import extract_asbuilt as X  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die', required=True)
    ap.add_argument('--ports', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    masters = json.load(open(a.ports))['masters']
    wires, insts = {}, {}
    drv, sinks = {}, collections.defaultdict(list)
    const_in = []                         # (inst, port, idx) tied in die.v
    open_in = []
    for ln in open(a.die):
        m = X.WIRE_RE.match(ln)
        if m:
            wires[m.group(4)] = (int(m.group(2)), int(m.group(3))) if m.group(1) else (0, 0)
            continue
        m = X.INST_RE.match(ln)
        if not m or m.group(1) in ('assign', 'wire', 'module'):
            continue
        mst, name, body = m.groups()
        pdef = masters.get(mst, {}).get('ports')
        if pdef is None:
            raise SystemExit(f'no ports for master {mst}')
        insts[name] = mst
        seen = set()
        for p, e in X.split_ports(body):
            dirs = pdef.get(p)
            if dirs is None:
                raise SystemExit(f'{name}: unknown port {p} of {mst}')
            seen.add(p)
            bits = X.expr_bits(e, wires)
            w = len(dirs)
            if len(bits) != w:
                raise SystemExit(f'{name}.{p}: {len(bits)} bits bound to a {w}-bit port')
            for k, nb in enumerate(bits):
                idx = w - 1 - k
                if dirs[idx] == 'OUTPUT':          # dirs are LSB-first (host.fdi[0] = tx_up is an INPUT)
                    if nb is not None:
                        drv[nb] = (name, p, idx)
                else:
                    if nb is None:
                        const_in.append((name, p, idx))
                    else:
                        sinks[nb].append((name, p, idx))
        for p, dirs in pdef.items():
            if p not in seen:
                for k, d in enumerate(dirs):
                    if d != 'OUTPUT':
                        open_in.append((name, p, k))
    print('insts', len(insts), 'driven bits', len(drv), file=sys.stderr)
    # qkd_rlyi_258s is a MUX relay (b <= s ? y : a, the PV result T-chain): logic, not a pass cell (extract_asbuilt
    # collapsed it, so the plan's 8 RH gathers lost their select stages)
    is_pass = {n: bool(X.PASS_RE.match(m)) and m != 'qkd_rlyi_258s' for n, m in insts.items()}
    out_of = {(i, idx): nb for nb, (i, p, idx) in drv.items() if is_pass[i] and p == 'b'}
    # resolve each net bit to its content driver (walk back through pass cells: b <- a/y same index)
    pass_in = {}
    for nb, lst in sinks.items():
        for (i, p, idx) in lst:
            if is_pass[i] and p in X.PASS_IN:
                pass_in[(i, idx)] = nb
    memo = {}

    def root(nb, depth=0):
        if nb in memo:
            return memo[nb]
        r = None
        d = drv.get(nb)
        if d is None:
            r = ('undriven', nb)
        elif not is_pass[d[0]]:
            r = ('leaf', d)
        elif d[1] != 'b':                      # landing tie_hi / tie_lo / fault / eb / ck_o: not a data pass
            r = ('pass_aux', d)
        else:
            up = pass_in.get((d[0], d[2]))
            if up is None:
                r = ('const_pass', d)          # a pass cell input tied / open
            else:
                r = root(up, depth + 1) if depth < 5000 else ('loop', d)
        memo[nb] = r
        return r
    sys.setrecursionlimit(20000)
    conns = collections.defaultdict(list)
    undriven, tied_pass = [], []
    for nb, lst in sinks.items():
        for (i, p, idx) in lst:
            if is_pass[i]:
                continue
            r = root(nb)
            if r[0] == 'leaf':
                s, sp, sidx = r[1]
                conns[(s, sp, i, p)].append((sidx, idx))
            elif r[0] == 'undriven':
                undriven.append((i, p, idx))
            else:
                tied_pass.append((i, p, idx, r[0], insts[r[1][0]] if r[0] in ('pass_aux', 'const_pass') else '',
                                  r[1][1] if r[0] in ('pass_aux', 'const_pass') else ''))
    used_out = {(s, sp, si) for (s, sp, d, dp), v in conns.items() for si, _ in v}
    unused_out = collections.Counter()
    for nb, (i, p, idx) in drv.items():
        if not is_pass[i] and (i, p, idx) not in used_out:
            unused_out[(insts[i], p)] += 1
    for (i, p, idx) in const_in:
        pass
    leaf_const = [(i, p, idx) for (i, p, idx) in const_in if not is_pass[i]]
    leaf_open = [(i, p, idx) for (i, p, idx) in open_in if not is_pass[i]]
    out = dict(schema='opentallas.kv_p2.bitcon.v1', die=a.die,
               blocks={n: m for n, m in insts.items() if not is_pass[n]},
               conns=[dict(s=s, sp=sp, d=d, dp=dp, pairs=sorted(v)) for (s, sp, d, dp), v in conns.items()],
               leaf_inputs_tied=leaf_const, leaf_inputs_open=leaf_open, leaf_inputs_undriven=undriven,
               leaf_inputs_tied_via_pass=tied_pass,
               unused_leaf_output_bits={f'{m}.{p}': n for (m, p), n in unused_out.items()})
    json.dump(out, gzip.open(a.out, 'wt'))
    print('conns', len(conns), 'bits', sum(len(v) for v in conns.values()), 'tied', len(leaf_const), 'open', len(leaf_open),
          'undriven', len(undriven), 'tied_via_pass', len(tied_pass), 'unused_out_bits', sum(unused_out.values()),
          file=sys.stderr)


if __name__ == '__main__':
    main()
