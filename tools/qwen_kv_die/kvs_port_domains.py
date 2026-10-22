#!/usr/bin/env python3
"""KV-INTEG/KITS-B 2026-10-18: clock domain + pin-register facts of every port of a generated KV static tile, measured on
the elaborated RTL (yosys proc + flatten; no guessing from port names).

Per port bit, traced through combinational cells only:
  input  -> the registers / memories it reaches (their clock = a top clock port) and any output port it reaches (feed-through);
  output -> the registers / memories / input ports it comes from.
A port's domain = the set of clock ports of those registers ('ck', 'hck', ...); 'none' = pure feed-through / constant.
A mixed-domain port also lists its per-bit domains ('bit_domains' runs [msb, lsb, domains], TW2-KVGRP 10-19).
'depth' = the largest number of combinational cells between the pin and the first register (0 = the pin IS a register D / Q).

    # on a fleet host (yosys): elaborate + analyse
    python3 tools/qwen_kv_die/kvs_port_domains.py --top qkd_kvs_grp --src FILE [--src FILE ...] --out ports.json
    # analyse an existing yosys JSON
    python3 tools/qwen_kv_die/kvs_port_domains.py --top qkd_kvs_grp --json flat.json --out ports.json
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict, deque
from pathlib import Path

SEQ_CLK = {'$dff': ['CLK'], '$dffe': ['CLK'], '$adff': ['CLK'], '$adffe': ['CLK'], '$sdff': ['CLK'], '$sdffe': ['CLK'],
           '$sdffce': ['CLK'], '$aldff': ['CLK'], '$aldffe': ['CLK'], '$dffsr': ['CLK'], '$dffsre': ['CLK'],
           '$mem': ['RD_CLK', 'WR_CLK'], '$mem_v2': ['RD_CLK', 'WR_CLK'], '$memrd': ['CLK'], '$memwr': ['CLK'],
           '$memrd_v2': ['CLK'], '$memwr_v2': ['CLK'], '$dlatch': ['EN'], '$adlatch': ['EN'], '$dlatchsr': ['EN']}
ASYNC = {'ARST', 'SET', 'CLR', 'AD', 'ALOAD'}      # asynchronous controls: reset tree, not a data domain


def elaborate(top, srcs, defines=()):
    with tempfile.TemporaryDirectory() as d:
        js = Path(d) / 'flat.json'
        dl = ' '.join(f'-D{x}' for x in defines)
        ys = (f'read_verilog -defer -sv -DSYNTHESIS {dl} ' + ' '.join(srcs) + f'\nhierarchy -check -top {top}\nproc\nflatten\n'
              f'opt_clean\nwrite_json {js}\n')
        (Path(d) / 's.ys').write_text(ys)
        ys_bin = os.environ.get('YOSYS') or next((str(c) for c in (Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys',)
                                                   if c.exists()), 'yosys')
        r = subprocess.run([ys_bin, '-q', '-s', str(Path(d) / 's.ys')], capture_output=True, text=True)
        if r.returncode:
            sys.exit('yosys failed:\n' + r.stdout[-3000:] + r.stderr[-3000:])
        return json.loads(js.read_text())


def runs(bd):
    """TW2-KVGRP 10-19: a MIXED-domain port gets its per-bit domains as runs {'bit_domains': [[msb, lsb, [domains]], ...]}
    (LSB first), so the kit SDC can constrain each bit in its own launch / capture domain (a port-level 'ck' constraint on
    the hck bits of o_pc* / o_ctl gave -490 ps of false output hold through the ignore-latency crossing min delay)"""
    if len({tuple(x) for x in bd}) <= 1:
        return {}
    out, lo = [], 0
    for i in range(1, len(bd) + 1):
        if i == len(bd) or bd[i] != bd[lo]:
            out.append([i - 1, lo, bd[lo]])
            lo = i
    return {'bit_domains': out}


def analyse(top, J):
    mod = J['modules'][top]
    ports = mod['ports']
    blackbox = {n for n, m in J['modules'].items() if m.get('attributes', {}).get('blackbox')}
    bit_port = {}
    for pn, p in ports.items():
        for i, b in enumerate(p['bits']):
            if isinstance(b, int):
                bit_port.setdefault(b, []).append((pn, i))
    netname = {}
    for nn, nv in sorted(mod.get('netnames', {}).items(), key=lambda kv: kv[1].get('hide_name', 0)):
        for i, b in enumerate(nv['bits']):
            if isinstance(b, int) and b not in netname:
                netname[b] = nn + (f'[{i}]' if len(nv['bits']) > 1 else '')
    drivers, sinks = {}, defaultdict(list)
    seq = {}
    for cn, c in mod['cells'].items():
        t = c['type']
        dirs = c.get('port_directions', {})
        clk_ports = SEQ_CLK.get(t)
        if clk_ports is None and (t in blackbox or not t.startswith('$')):
            clk_ports = [p for p in c['connections'] if p.lower() in ('clk', 'ck', 'clock') or p.lower().startswith('clk')]
        if clk_ports is not None:
            cks = set()
            for p in clk_ports:
                for b in c['connections'].get(p, []):
                    if isinstance(b, int):
                        cks.update(n for n, _ in bit_port.get(b, [(f'?{netname.get(b, b)}', 0)]))
            seq[cn] = cks or {'?const'}
        for p, bits in c['connections'].items():
            d = dirs.get(p, 'input')
            for b in bits:
                if not isinstance(b, int):
                    continue
                if d == 'output':
                    drivers[b] = (cn, p)
                else:
                    sinks[b].append((cn, p))
    cells = mod['cells']

    def outs_of(cn):
        c = cells[cn]
        return [b for p, bs in c['connections'].items() if c.get('port_directions', {}).get(p) == 'output'
                for b in bs if isinstance(b, int)]

    def ins_of(cn):
        c = cells[cn]
        return [b for p, bs in c['connections'].items() if c.get('port_directions', {}).get(p, 'input') != 'output'
                for b in bs if isinstance(b, int)]

    res = {}
    clk_ports = {n for s in seq.values() for n in s}
    for pn, p in ports.items():
        dom, thru, depth, regs = set(), set(), 0, 0
        if p['direction'] == 'input':
            if pn in clk_ports:
                res[pn] = dict(dir='input', width=len(p['bits']), role='clock')
                continue
            asy = False
            bd = []
            for b0 in p['bits']:
                if not isinstance(b0, int):
                    bd.append(['none'])
                    continue
                d0 = set(dom)
                dom = set()
                q, seen = deque([(b0, 0)]), {b0}
                while q:
                    b, k = q.popleft()
                    for opn, _ in bit_port.get(b, []):
                        if ports[opn]['direction'] == 'output':
                            thru.add(opn)
                    for cn, cp in sinks.get(b, []):
                        if cn in seq:
                            if cp in ASYNC:
                                asy = True
                                continue
                            dom |= seq[cn]
                            regs += 1
                            depth = max(depth, k)
                            continue
                        for ob in outs_of(cn):
                            if ob not in seen:
                                seen.add(ob)
                                q.append((ob, k + 1))
                bd.append(sorted(dom) or ['none'])
                dom |= d0
            res[pn] = dict(dir='input', width=len(p['bits']), domains=sorted(dom) or ['none'], feedthrough=sorted(thru),
                           depth=depth, reg_sinks=regs, async_reset=asy, **runs(bd))
        else:
            src_in = set()
            bd = []
            for b0 in p['bits']:
                if not isinstance(b0, int):
                    bd.append(['none'])
                    continue
                d0 = set(dom)
                dom = set()
                q, seen = deque([(b0, 0)]), {b0}
                while q:
                    b, k = q.popleft()
                    for ipn, _ in bit_port.get(b, []):
                        if ports[ipn]['direction'] == 'input':
                            src_in.add(ipn)
                    dr = drivers.get(b)
                    if dr is None:
                        continue
                    cn, _cp = dr
                    if cn in seq:
                        dom |= seq[cn]
                        regs += 1
                        depth = max(depth, k)
                        continue
                    for ib in ins_of(cn):
                        if ib not in seen:
                            seen.add(ib)
                            q.append((ib, k + 1))
                bd.append(sorted(dom) or ['none'])
                dom |= d0
            res[pn] = dict(dir='output', width=len(p['bits']), domains=sorted(dom) or ['none'], from_inputs=sorted(src_in),
                           depth=depth, reg_sources=regs, **runs(bd))
    return dict(top=top, registers=len(seq), clock_ports=sorted(clk_ports), ports=res)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--top', required=True)
    ap.add_argument('--src', action='append', default=[])
    ap.add_argument('--define', action='append', default=[])
    ap.add_argument('--json')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    J = json.loads(Path(a.json).read_text()) if a.json else elaborate(a.top, a.src, a.define)
    r = analyse(a.top, J)
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    mixed = [p for p, v in r['ports'].items() if len(v.get('domains', [])) > 1]
    print(f"{a.top}: {r['registers']} register cells, clocks {r['clock_ports']}, {len(r['ports'])} ports, mixed {mixed}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
