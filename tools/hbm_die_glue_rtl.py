#!/usr/bin/env python3
"""HBM die (contract v14, OWNER NO STUBS 2026-10-14 08:05): emit REAL RTL for every die-generated glue master of a die
model -- the clock buffers (hfd_ckb), the staged reset relays (hfd_rrl), the data relays / stations / meso / multicast /
gather / control-distribution stations (hfd_rly_*, hfd_stn_*, hfd_meso_*, hfd_mcast_*, hfd_gath_*, hfd_cdist_*,
hfd_att_su_relay ...) -- so the die netlist binds RTL under every glue name (v13: 86,701 glue instances had none).

The function of a glue master follows from its die nets (the die model is the single source of its ports):
  ckb    o = i                                      clock buffer (CTS maps it to a clock buffer cell)
  rrl    o <= i @ ck                                one stage of the staged (pipelined) reset release tree
  copy   every output <= the single data input      relay / station / multicast (each output as wide as the input)
  cat    {outputs} <= {inputs} @ ck                 gather / bundle station: the inputs concatenated in port order
         (t0, t1, t2, t3, a, a2, then the rest by name) and split over the outputs in the same order; widths must sum
  GAP    anything else (no input, ambiguous direction, widths that neither copy nor sum): reported, no module written
Every register stage has its D at the input pin and its Q at the output pin (in -> flop -> out, no logic at a pin), so
the die hop rule (register at the pin -> wire <= 500 um -> register at the pin) holds by construction.  Stations with a
`rst` pin clear their flops while it is high (the die reset net is active-high, released down the staged tree).

    python3 tools/hbm_die_glue_rtl.py --model m.pkl --out DIR      (pickle: hbm_r25gq_windows.py --dump-model)
"""
import argparse
import collections
import json
import pickle
import re
import sys
from pathlib import Path

ORDER = ('t0', 't1', 't2', 't3', 'a', 'a2')


def base_idx(port):
    if '@' not in port:
        return port, None
    b, r = port.split('@', 1)
    ix = []
    for it in r.split(','):         # 'lo:hi[,lo:hi]' or single bit indices
        lo, hi = (int(x) for x in it.split(':')) if ':' in it else (int(it), int(it))
        ix += [lo, hi]
    return b, (min(ix), max(ix))


def glue_ports(m):
    """{master: {port: [dir, width]}} over every instance of every waypoint master (union of the copies' ports)"""
    I = m['insts']
    kind = {n: v[1] for n, v in I.items()}
    mst = {n: v[0] for n, v in I.items()}
    P = collections.defaultdict(lambda: collections.defaultdict(lambda: [set(), 0]))
    for bid, cls, bits, eps in m['buses']:
        for i, (inst, port) in enumerate(eps):
            if inst == 'TOP' or kind.get(inst) != 'waypoint':
                continue
            b, r = base_idx(port)
            w = (r[1] + 1) if r else bits
            rec = P[mst[inst]][b]
            rec[0].add('output' if i == 0 else 'input')
            rec[1] = max(rec[1], w)
    return P


def sv_module(name, ports):
    """(rule, text) for one glue master"""
    dirs = {p: (d.pop() if len(d) == 1 else 'inout') for p, (d, _) in ports.items() for d in [set(d)]}
    W = {p: w for p, (_, w) in ports.items()}
    if any(d == 'inout' for d in dirs.values()):
        return 'GAP: a port both drives and loads die nets: ' + ','.join(p for p, d in dirs.items() if d == 'inout'), None
    hdr = ',\n'.join(f'    {dirs[p]} wire {"[%d:0] " % (W[p] - 1) if W[p] > 1 else ""}{p}' for p in sorted(ports))
    head = f'module {name} (\n{hdr}\n);\n'
    if name == 'hfd_ckb' or (set(ports) == {'i', 'o'} and 'ck' not in ports):
        if not (dirs.get('i') == 'input' and dirs.get('o') == 'output'):
            return 'GAP: clock buffer without i -> o', None
        return 'ckb', head + '    assign o = i;      // clock buffer (CTS cell)\nendmodule\n'
    ck = 'ck' if 'ck' in ports else None
    if ck is None:
        return 'GAP: register stage without a clock pin', None
    rst = 'rst' if dirs.get('rst') == 'input' else None
    ins = [p for p in ports if dirs[p] == 'input' and p not in ('ck', 'rst')]
    outs = [p for p in ports if dirs[p] == 'output']
    if not ins or not outs:
        return f'GAP: no data input ({ins}) or output ({outs})', None
    key = lambda p: (ORDER.index(p) if p in ORDER else len(ORDER), p)
    ins.sort(key=key)
    outs.sort(key=key)
    body = []
    if len(ins) == 1 and all(W[o] == W[ins[0]] for o in outs):
        rule, src = 'copy', ins[0]
        for o in outs:
            body.append(f'    reg [{W[o] - 1}:0] r_{o};\n    assign {o} = r_{o};')
        upd = '\n'.join(f'            r_{o} <= {src};' for o in outs)
        rs = '\n'.join(f"            r_{o} <= '0;" for o in outs)
    elif sum(W[p] for p in ins) == sum(W[p] for p in outs):
        rule = 'cat'
        tot = sum(W[p] for p in ins)
        body.append(f'    reg [{tot - 1}:0] r_cat;')
        lo = 0
        for o in outs:
            body.append(f'    assign {o} = r_cat[{lo + W[o] - 1}:{lo}];')
            lo += W[o]
        cat = '{' + ', '.join(reversed(ins)) + '}'
        upd = f'            r_cat <= {cat};'
        rs = "            r_cat <= '0;"
    else:
        return (f'GAP: data widths neither copy nor sum (in {[(p, W[p]) for p in ins]}, out {[(p, W[p]) for p in outs]})',
                None)
    if name == 'hfd_rrl':
        rule = 'rrl'
    seq = (f'    always @(posedge {ck}) begin\n' +
           (f'        if ({rst}) begin\n{rs}\n        end else begin\n{upd}\n        end\n' if rst else
            f'        begin\n{upd}\n        end\n') + '    end\n')
    return rule, head + '\n'.join(body) + '\n' + seq + 'endmodule\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    m = pickle.load(open(a.model, 'rb'))
    P = glue_ports(m)
    cnt = collections.Counter(v[0] for v in m['insts'].values() if v[1] == 'waypoint')
    a.out.mkdir(parents=True, exist_ok=True)
    txt = ['// GENERATED by tools/hbm_die_glue_rtl.py from the die model: die-generated glue masters (real RTL, no stubs)',
           '`default_nettype none']
    rep = dict(schema='opentallas.hbm_die_glue_rtl.v1', model=str(a.model), masters={}, rules=collections.Counter(),
               instances=collections.Counter())
    for name in sorted(cnt):
        ports = P.get(name)
        if not ports:
            rule, mod = 'GAP: master on no die net', None
        else:
            rule, mod = sv_module(name, ports)
        r_ = rule.split(':')[0]
        rep['rules'][r_] += 1
        rep['instances'][r_] += cnt[name]
        rep['masters'][name] = dict(rule=rule, instances=cnt[name],
                                    ports={p: [sorted(d)[0] if len(d) == 1 else 'inout', w] for p, (d, w) in (ports or {}).items()})
        if mod:
            txt.append(mod)
    txt.append('`default_nettype wire\n')
    (a.out / 'hbm_die_glue.sv').write_text('\n'.join(txt))
    rep['rules'], rep['instances'] = dict(rep['rules']), dict(rep['instances'])
    (a.out / 'glue_rtl.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(dict(masters=len(cnt), rules=rep['rules'], instances=rep['instances'])))
    gaps = {k: v['rule'] for k, v in rep['masters'].items() if v['rule'].startswith('GAP')}
    for k, v in list(gaps.items())[:20]:
        print('  ', k, v[:200])
    return 0


if __name__ == '__main__':
    sys.exit(main())
