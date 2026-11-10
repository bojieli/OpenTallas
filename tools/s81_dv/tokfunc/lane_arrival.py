#!/usr/bin/env python3
"""TOK-VERIFY-1 S1 (11-10): RTL arrival of the S81 statically scheduled control lanes on a strict bind's OWN emitted RTL.

For every lane of layer_prog/bound_ctl_lanes.LANES (or --lanes):
  1. walk the bound die top (bind rtl/s81_bound_top.sv) from the source partition's bus_out port, through every
     feed-through partition (port X_i -> X_o), to the sink leaf pin in the destination partition, using the top's own
     port connections (the `// lane <name>` wire tags are only cross-checked);
  2. inside each partition module (rtl/<type>.sv as emitted) follow the bus net by net. Accepted path cells:
     ot_dp_st (d->q), ot_dp_dly (d->q, D edges), ot_dp_clk_landing (d->q, mesochronous ring, its real RTL), assign /
     port alias. Any other cell on the path ends the walk and the lane FAILs (UNTRACED);
  3. build ONE Verilator bench holding every lane's extracted cell chain with the REAL cell bodies (bind_cells.sv for
     ot_dp_st / ot_dp_dly, the bind's own ot_dp_clk_landing.sv + ot_meso_fifo.sv from bind.f for landings). Each
     partition gets its own clock (same period, phase offset per --phases set); a landing's write clock is the clock of
     the partition before it.  A random word per source cycle is launched; the sink sample after its posedge m must
     equal the word launched at source cycle m - N, with N constant over 1000 cycles and the epoch bit set;
  4. PASS iff measured N == bind_latency bound_stages == the compiled programme's depth (prog/bound_ctl_lanes.json)
     at every phase set, and the sink leaf pin is the one in bus_groups.json.
--mutant LANE:+1 / LANE:-1 adds / removes one ot_dp_st in that lane's chain (a one-stage RTL change): it must FAIL.
Exit 0 = every lane PASS, 1 = any FAIL.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

STAGE = {'ot_dp_st': ('d', 'q'), 'ot_dp_dly': ('d', 'q'), 'ot_dp_clk_landing': ('d', 'q')}
ID = r'[A-Za-z_][A-Za-z0-9_$]*'
KW = {'module', 'input', 'output', 'inout', 'wire', 'reg', 'logic', 'assign', 'localparam', 'parameter', 'always',
      'initial', 'generate', 'if', 'for', 'else', 'begin', 'end', 'genvar', 'integer'}


def strip_comments(t):
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    return re.sub(r'//[^\n]*', '', t)


def split_conns(body):
    out, i, n = {}, 0, len(body)
    while True:
        j = body.find('.', i)
        if j < 0:
            break
        m = re.match(r'\.\s*(' + ID + r')\s*\(', body[j:])
        if not m:
            i = j + 1
            continue
        k = j + m.end()
        depth, s = 1, k
        while k < n and depth:
            depth += {'(': 1, ')': -1}.get(body[k], 0)
            k += 1
        out[m.group(1)] = body[s:k - 1].strip()
        i = k
    return out


def parse_module(text, want):
    for m in re.finditer(r'\bmodule\s+(' + ID + r')\b(.*?)\bendmodule\b', strip_comments(text), flags=re.S):
        if m.group(1) != want:
            continue
        insts, assigns = [], []
        for st in m.group(2).split(';'):
            s = st.strip()
            a = re.match(r'assign\s+(.+?)\s*=\s*(.+)$', s, flags=re.S)
            if a:
                assigns.append((a.group(1).strip(), a.group(2).strip()))
                continue
            im = re.match(r'(' + ID + r')\s*(#\s*\((.*)\))?\s*(' + ID + r')\s*\((.*)\)\s*$', s, flags=re.S)
            if im and im.group(1) not in KW:
                insts.append(dict(mod=im.group(1), name=im.group(4), params=split_conns(im.group(3) or ''),
                                  conns=split_conns(im.group(5))))
        regs = set(re.findall(r'\breg\s*(?:\[[^\]]*\])?\s*(' + ID + r')\s*;', m.group(2)))
        flops = {r: 'clk' for r in set(re.findall(r'(' + ID + r')\s*<=', m.group(2))) & regs}   # inlined leaf flops
        return dict(insts=insts, assigns=assigns, flops=flops)
    raise KeyError(want)


def base(expr):
    m = re.match(r'^(' + ID + r')\s*(?:\[\s*([^\]]+)\s*\])?$', (expr or '').strip())
    return (m.group(1), m.group(2)) if m else (None, expr)


def ival(s, dflt):
    m = re.search(r'\d+', s or '')
    return int(m.group(0)) if m else dflt


def cell(it, part):
    d = ival(it['params'].get('D'), 1) if it['mod'] == 'ot_dp_dly' else 1
    return dict(mod=it['mod'], name=it['name'], part=part, edges=d, wneg=ival(it['params'].get('WNEG'), 0),
                freg=ival(it['params'].get('FREG'), 0), fclk=it['conns'].get('fclk'), clk=it['conns'].get('clk', 'clk'))


class Part:
    def __init__(self, mod, name):
        self.name = name
        self.cons, self.drv = defaultdict(list), defaultdict(list)
        for it in mod['insts']:
            io = STAGE.get(it['mod'])
            for p, e in it['conns'].items():
                nets = [base(e)[0]] if base(e)[0] else re.findall(ID, e)
                for b in nets:
                    if io:
                        if p == io[1] or p == 'eq':
                            self.drv[b].append((it, p))
                        elif p in (io[0], 'ea'):
                            self.cons[b].append((it, p))
                    else:
                        self.cons[b].append((it, p))
                        self.drv[b].append((it, p))
        self.flops = mod.get('flops', {})   # inlined leaf flops (structural_full): reg -> clock
        self.af, self.ab = defaultdict(list), defaultdict(list)
        self.comb = set()
        for l, r in mod['assigns']:
            bl, br = base(l)[0], base(r)[0]
            if bl and br:
                self.af[br].append(bl)
                self.ab[bl].append(br)
            elif bl:
                self.comb.add(bl)   # combinational source term (concat / expression of leaf outputs)

    def forward(self, net, ports):
        """[(chain, end)], end = ('port', p) | ('leaf', inst, mod, pin) | ('dangling', net)"""
        res, todo, seen = [], [(net, [])], set()
        while todo:
            n, chain = todo.pop()
            if (n, len(chain)) in seen:
                continue
            seen.add((n, len(chain)))
            if n in ports and n != net:
                res.append((chain, ('port', n)))
                continue
            nxt = False
            for it, p in self.cons.get(n, []):
                io = STAGE.get(it['mod'])
                if io:
                    if p != io[0]:
                        continue
                    todo.append((base(it['conns'][io[1]])[0], chain + [cell(it, self.name)]))
                else:
                    res.append((chain, ('leaf', it['name'], it['mod'], p)))
                nxt = True
            for a in self.af.get(n, []):
                todo.append((a, chain))
                nxt = True
            if not nxt:
                res.append((chain, ('dangling', n)))
        return res

    def backward(self, net):
        chain, n = [], net
        for _ in range(10000):
            st = [it for it, p in self.drv.get(n, []) if STAGE.get(it['mod']) and p == STAGE[it['mod']][1]]
            if st:
                chain.insert(0, cell(st[0], self.name))
                dexpr = st[0]['conns'][STAGE[st[0]['mod']][0]]
                n = base(dexpr)[0]
                if n is None:   # concatenation of several leaf outputs into one bus
                    ends = []
                    for b in re.findall(ID, dexpr):
                        m = b
                        while self.ab.get(m):
                            m = self.ab[m][0]
                        lf = [(it, p) for it, p in self.drv.get(m, []) if not STAGE.get(it['mod'])]
                        if any(STAGE.get(it['mod']) for it, p in self.drv.get(m, [])):
                            return chain, ('undriven', f'concat member {b} driven by a path cell')
                        if lf:
                            ends.append((lf[0][0]['name'], lf[0][0]['mod'], lf[0][1]))
                        elif m in self.flops:
                            ends.append((m, 'inlined_flop', 'q'))
                        elif m in self.comb:
                            ends.append((m, 'comb_assign', 'y'))
                        else:
                            return chain, ('undriven', f'concat member {b}')
                    return chain, ('leaf', '+'.join(e[0] for e in ends), '+'.join(sorted({e[1] for e in ends})),
                                   '+'.join(e[2] for e in ends))
                continue
            if self.ab.get(n):
                n = self.ab[n][0]
                continue
            leaf = [(it, p) for it, p in self.drv.get(n, []) if not STAGE.get(it['mod'])]
            if leaf:
                return chain, ('leaf', leaf[0][0]['name'], leaf[0][0]['mod'], leaf[0][1])
            if n in self.flops:
                return chain, ('leaf', n, 'inlined_flop', 'q')
            return chain, ('undriven', n)
        raise RuntimeError('loop')


def bench(lanes, phases, W=32, fwd=0.0, force_wneg=None):
    """one bench: every (lane, end) chain; returns verilog text"""
    doms = sorted({c['dom'] for L in lanes for c in L['chain']} | {L['src_dom'] for L in lanes})
    di = {d: i for i, d in enumerate(doms)}
    v = ['`timescale 1ns/1ps', 'module tb;', f'  localparam integer ND = {len(doms)};', '  reg rst_n = 0;',
         '  reg [ND-1:0] ck = 0;', '  integer cyc [0:ND-1];', '  integer i0;',
         '  initial for (i0 = 0; i0 < ND; i0 = i0 + 1) cyc[i0] = 0;']
    for d, i in di.items():
        ph = phases.get(d, 0.0)
        v.append(f'  initial begin #({5.0 + ph:.3f}); forever begin ck[{i}] = 1; cyc[{i}] = cyc[{i}] + 1; #5; '
                 f'ck[{i}] = 0; #5; end end  // {d} phase {ph:+.3f} ns')
    v.append('  initial begin #95 rst_n = 1; end')
    for k, L in enumerate(lanes):
        s = di[L['src_dom']]
        v += [f'  // probe {k}: {L["lane"]} -> {L["sink"]}', f'  reg [{W-1}:0] src{k}; reg sea{k};',
              f'  reg [{W-1}:0] h{k} [0:4095];',
              f'  initial begin src{k} = 0; sea{k} = 0; end',
              f'  always @(negedge ck[{s}]) begin src{k} = $urandom; sea{k} = rst_n; h{k}[cyc[{s}] % 4096] = src{k}; end']
        prev, pe, pdom = f'src{k}', f'sea{k}', s
        for j, c in enumerate(L['chain']):
            dd = di[c['dom']]
            o, oe = f'l{k}_{j}', f'l{k}_{j}e'
            v.append(f'  wire [{W-1}:0] {o}; wire {oe};')
            if c['mod'] == 'ot_dp_st':
                v.append(f'  ot_dp_st #(.W({W})) u{k}_{j} (.clk(ck[{dd}]), .rst_n(rst_n), .d({prev}), .ea({pe}), .q({o}), .eq({oe}));')
            elif c['mod'] == 'ot_dp_dly':
                v.append(f'  ot_dp_dly #(.W({W + 1}), .D({c["edges"]})) u{k}_{j} (.clk(ck[{dd}]), .d({{{pe}, {prev}}}), .q({{{oe}, {o}}}));')
            else:
                wn = c['wneg'] if force_wneg is None else force_wneg
                v.append(f'  wire r{k}_{j}, f{k}_{j}, fk{k}_{j};')
                v.append(f'  assign #({fwd:.3f}) fk{k}_{j} = ck[{pdom}];  // forwarded clock: upstream clock + {fwd} ns')
                v.append(f'  ot_dp_clk_landing #(.W({W + 1}), .WNEG({wn}), .FREG({c["freg"]})) u{k}_{j} '
                         f'(.fclk(fk{k}_{j}), .clk(ck[{dd}]), .rst_n(rst_n), .d({{{pe}, {prev}}}), .q({{{oe}, {o}}}), '
                         f'.ready(r{k}_{j}), .fault(f{k}_{j}));')
            prev, pe, pdom = o, oe, dd
        t = di[L['chain'][-1]['dom']] if L['chain'] else s
        v += [f'  integer n{k}, lat{k} = -9, bad{k} = 0, got{k};',
              f'  always @(posedge ck[{t}]) begin #0.5; if (cyc[{t}] > 300 && cyc[{t}] < 1300) begin got{k} = -1;',
              f'    for (n{k} = 0; n{k} < 200; n{k} = n{k} + 1) if (got{k} < 0 && {prev} === h{k}[(cyc[{t}] - n{k}) % 4096]) got{k} = n{k};',
              f'    if (!{pe}) bad{k} = bad{k} + 1; if (lat{k} == -9) lat{k} = got{k}; else if (lat{k} != got{k}) bad{k} = bad{k} + 1; end end']
    v.append('  initial begin #14000;')
    for k in range(len(lanes)):
        v.append(f'    $display("LAT {k} %0d %0d", lat{k}, bad{k});')
    v += ['    $finish; end', 'endmodule']
    return '\n'.join(v) + '\n'


def run_bench(text, work, cell_files, tag):
    d = work / tag
    d.mkdir(parents=True, exist_ok=True)
    (d / 'tb.v').write_text(text)
    for f in cell_files:
        (d / f.name).write_text(f.read_text())
    cmd = ['timeout', '1500', 'docker', 'run', '--rm', '--memory', '16g', '-u', f'{os.getuid()}:{os.getgid()}',
           '-e', 'HOME=/w', '-e', 'CCACHE_DISABLE=1', '-v', f'{d}:/w', '-w', '/w', 'verilator/verilator:v5.032',
           '--binary', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-j', '8', '--top-module', 'tb', 'tb.v'] + \
          [f.name for f in cell_files] + ['-o', 'sim']
    r = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit(f'verilator build failed, see {d}/build.log')
    r = subprocess.run([str(d / 'obj_dir' / 'sim')], capture_output=True, text=True, timeout=1800)
    (d / 'sim.log').write_text(r.stdout + r.stderr)
    out = {}
    for line in r.stdout.splitlines():
        if line.startswith('LAT '):
            _, k, lat, bad = line.split()
            out[int(k)] = (int(lat), int(bad))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('bind', type=Path)
    ap.add_argument('prog', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--lanes', default=None)
    ap.add_argument('--mutant', action='append', default=[])
    ap.add_argument('--phases', default='0,1,2', help='phase sets: 0 = all clocks aligned; n>0 = seeded random '
                    'per-partition offsets within +-2.0 ns of the 10 ns period')
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--skew-ns', type=float, default=2.0, help='random region phase range +- (10 ns period)')
    ap.add_argument('--fwd-ns', type=float, default=0.0, help='forwarded clock delay at every landing (ns)')
    ap.add_argument('--force-wneg', type=int, default=None, help='what-if: override every landing WNEG')
    ap.add_argument('--cut', type=Path, default=None, help='walk a dv_bound_cut directory instead of the whole bound '
                    'top: its <name>.sv top and its generated pass-through shells (<type>__ftshell*.sv)')
    a = ap.parse_args()
    sys.path[:0] = [str(a.repo / 'tools/s81_dv/layer_prog')]
    import bound_ctl_lanes as BCL
    rtl = a.bind / 'rtl'
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    work = a.out / 'sim'
    cm = strip_comments((rtl / 'bind_cells.sv').read_text())
    cells = a.out / 'cells_st_dly.sv'
    cells.write_text('`timescale 1ns/1ps\n' + '\n'.join(
        m.group(0) for m in re.finditer(r'\bmodule\s+(ot_dp_st|ot_dp_dly)\b.*?\bendmodule\b', cm, flags=re.S)) + '\n')
    bf = [Path(x.strip()) for x in (a.bind / 'bind.f').read_text().split() if x.strip().endswith('.sv')]
    land = [f for f in bf if f.name in ('ot_dp_clk_landing.sv', 'ot_meso_fifo.sv')]
    if len(land) != 2:
        raise SystemExit(f'landing sources not found in bind.f: {land}')
    cell_files = [cells] + land
    lat = {b['lane']: b for b in json.loads((a.bind / 'bind_latency.json').read_text())['buses']}
    sinks = defaultdict(set)
    for g in json.loads((a.bind / 'bus_groups.json').read_text())['landing']:
        for mm in g['members']:
            if mm.get('lane'):
                sinks[mm['lane']].add((g['sink'], mm['sink_port']))
    prog_ctl = json.loads((a.prog / 'bound_ctl_lanes.json').read_text())['lanes']
    topf, topm, extra = rtl / 's81_bound_top.sv', 's81_bound_top', {}
    if a.cut:
        cf = [Path(x) for x in (a.cut / 'cut.f').read_text().split() if x.endswith('.sv')]
        topf = cf[-1]
        topm = topf.stem
        extra = {f.stem: f for f in cf if '__ftshell' in f.stem}
    toptxt = topf.read_text()
    top = parse_module(toptxt, topm)
    tags = {}
    for line in toptxt.splitlines():
        m = re.match(r'\s*wire\s*(?:\[[^\]]*\])?\s*(' + ID + r')\s*;\s*//\s*lane\s+(' + ID + ')', line)
        if m:
            tags[m.group(1)] = m.group(2)
    by_name = {it['name']: it for it in top['insts']}
    users = defaultdict(list)
    for it in top['insts']:
        for p, e in it['conns'].items():
            if base(e)[0]:
                users[base(e)[0]].append((it['name'], p))
    cache = {}

    def part(inst):
        mod = by_name[inst]['mod']
        if mod not in cache:
            cache[mod] = parse_module((extra.get(mod) or rtl / f'{mod}.sv').read_text(), mod)
        return Part(cache[mod], inst)

    mut = {s.rsplit(':', 1)[0]: int(s.rsplit(':', 1)[1]) for s in a.mutant}
    lanes = a.lanes.split(',') if a.lanes else sorted(BCL.LANES)
    rows, probes = [], []
    for lane in lanes:
        b = lat[lane]
        row = dict(lane=lane, src=b['src'], dst=b['dst'], bus_out=b['bus_out'], bus_in=b['bus_in'],
                   bound_stages=b['bound_stages'], plan_cycles=b.get('plan_cycles'), prog_depth=prog_ctl.get(lane),
                   problems=[], ends=[])
        rows.append(row)
        if b['src'] not in by_name:
            row['problems'].append(f'source instance {b["src"]} not in the bound top')
            continue
        P = part(b['src'])
        pre, start = P.backward(b['bus_out'])
        row['source_leaf'] = list(start)
        if start[0] != 'leaf':
            row['problems'].append(f'source port {b["bus_out"]} not driven from a leaf through path cells: {start}')
        seg0 = dict(part=b['src'], seg=f'{start[1]}.{start[-1]} -> {b["bus_out"]}', cells=[c['mod'] for c in pre])
        frontier = [(base(by_name[b['src']]['conns'].get(b['bus_out'], ''))[0], b['src'], [seg0], pre)]
        while frontier:
            net, frm, path, chain = frontier.pop()
            if tags.get(net) not in (None, lane):
                row['problems'].append(f'top wire {net} tagged {tags.get(net)}')
            us = [(i, p) for i, p in users.get(net, []) if i != frm]
            if not us:
                row['problems'].append(f'top net {net} has no consumer')
            for inst, port in us:
                Q = part(inst)
                conns = by_name[inst]['conns']
                for ch, end in Q.forward(port, set(conns)):
                    for c in ch:
                        if c['mod'] == 'ot_dp_clk_landing' and c['fclk'] in conns:
                            c['fclk_top'] = conns[c['fclk']]
                    seg = dict(part=inst, cells=[c['mod'] for c in ch])
                    if end[0] == 'port':
                        seg['seg'] = f'{port} -> {end[1]}'
                        if len(path) > 64:
                            row['problems'].append('path over 64 partitions')
                            continue
                        frontier.append((base(conns.get(end[1], ''))[0], inst, path + [seg], chain + ch))
                    elif end[0] == 'leaf':
                        seg['seg'] = f'{port} -> {end[1]}.{end[3]}'
                        row['ends'].append(dict(sink=f'{inst}.{end[1]}', sink_mod=end[2], sink_pin=end[3],
                                                path=path + [seg], chain=chain + ch))
                    else:
                        row['problems'].append(f'{inst}.{port}: walk ends at {end}')
        if not row['ends']:
            row['problems'].append('no sink leaf reached')
        for e in row['ends']:
            ch = list(e['chain'])
            if lane in mut:
                if mut[lane] > 0:
                    ch = ch + [dict(mod='ot_dp_st', name='MUT', part=ch[-1]['part'], edges=1, wneg=0, freg=0,
                                    clk=ch[-1]['clk'])] * mut[lane]
                else:
                    i = next(i for i, c in enumerate(ch) if c['mod'] == 'ot_dp_st')
                    ch = ch[:i] + ch[i + 1:]
            for c in ch:   # clock domain = the top-level clock net on the partition port the cell is clocked by
                c['dom'] = base(by_name[c['part']]['conns'].get(c['clk'], f"{c['part']}.{c['clk']}"))[0] or f"{c['part']}.{c['clk']}"
            src_dom = base(by_name[b['src']]['conns'].get('clk', b['src'] + '.clk'))[0]
            prevd = src_dom
            for c in ch:
                if c['dom'] != prevd and c['mod'] != 'ot_dp_clk_landing':
                    row['problems'].append(f"{c['part']}.{c['name']}: clock {c['dom']} != upstream {prevd} with no landing")
                prevd = c['dom']
            e['domains'] = sorted({c['dom'] for c in ch} | {src_dom})
            e['cells'] = {m: sum(c['mod'] == m for c in ch) for m in STAGE}
            e['dly_edges'] = sum(c['edges'] for c in ch if c['mod'] == 'ot_dp_dly')
            e['landings'] = [dict(part=c['part'], name=c['name'], fclk_top=c.get('fclk_top'), wneg=c['wneg'])
                             for c in ch if c['mod'] == 'ot_dp_clk_landing']
            # bus_groups names the as-built sink (e.g. u_s_7N.u_lep); the bind emits the leaf inside the dst partition
            # with a prefixed name (s_7N_LP.u_u_lep): same dst partition, leaf name ends with the as-built leaf, same pin
            pi, li = e['sink'].split('.', 1)
            # a whole-partition core (as-built u_bk_sel) is emitted as <dst>.u_core
            e['named_in_bus_groups'] = pi == row['dst'] and any(
                (li.endswith(s.rsplit('.', 1)[-1]) or (s == f'u_{row["dst"]}' and li == 'u_core')) and p == e['sink_pin']
                for s, p in sinks.get(lane, ()))
            e['bus_groups_sinks'] = sorted(f'{s}.{p}' for s, p in sinks.get(lane, ()))
            e['probe'] = len(probes)
            probes.append(dict(lane=lane, sink=e['sink'], src=b['src'], src_dom=src_dom, chain=ch))
            del e['chain']
    meas = defaultdict(dict)
    doms = sorted({c['dom'] for p in probes for c in p['chain']} | {p['src_dom'] for p in probes})
    for ps in [int(x) for x in a.phases.split(',')]:
        rnd = random.Random(1000 + ps)
        phases = {d: (0.0 if ps == 0 else rnd.uniform(-a.skew_ns, a.skew_ns)) for d in doms}
        res = run_bench(bench(probes, phases, fwd=a.fwd_ns, force_wneg=a.force_wneg), work, cell_files, f'phase{ps}')
        for k in range(len(probes)):
            meas[k][ps] = res.get(k, (None, None))
    ok_all = True
    for row in rows:
        for e in row['ends']:
            m = meas[e['probe']]
            e['measured'] = {str(ps): dict(edges=v[0], bad_samples=v[1]) for ps, v in m.items()}
            vals = {v[0] for v in m.values()}
            stable = all(v[1] == 0 for v in m.values())
            e['verdict'] = 'PASS' if (stable and vals == {row['bound_stages']} and row['prog_depth'] == row['bound_stages']
                                      and e['named_in_bus_groups'] and not row['problems']) else 'FAIL'
        row['verdict'] = 'PASS' if row['ends'] and all(e['verdict'] == 'PASS' for e in row['ends']) and not row['problems'] else 'FAIL'
        ok_all &= row['verdict'] == 'PASS'
        print(f"{row['verdict']} {row['lane']}: bound {row['bound_stages']} prog {row['prog_depth']} | "
              + '; '.join(f"{e['sink']}.{e['sink_pin']} parts {len(e['path'])} cells {e['cells']} dly {e['dly_edges']} "
                          f"sim {[(v['edges'], v['bad_samples']) for v in e['measured'].values()]}"
                          f"{'' if e['named_in_bus_groups'] else ' SINK-NOT-IN-BUS-GROUPS'}" for e in row['ends'])
              + (f" | problems {row['problems'][:3]}" if row['problems'] else ''), flush=True)
    rep = dict(schema='tok-verify-1.lane_arrival.v2', bind=str(a.bind), cut=str(a.cut) if a.cut else None,
               shells=sorted(extra), prog=str(a.prog), mutants=a.mutant,
               phase_sets=a.phases, skew_ns=a.skew_ns, fwd_ns=a.fwd_ns, force_wneg=a.force_wneg, lanes=len(rows), passed=sum(r['verdict'] == 'PASS' for r in rows),
               verdict='PASS' if ok_all else 'FAIL', status='DO_NOT_COUNT', rows=rows,
               cell_sources=[str(f) for f in cell_files])
    (a.out / 'lane_arrival.json').write_text(json.dumps(rep, indent=1, default=str) + '\n')
    print('VERDICT', rep['verdict'], rep['passed'], '/', rep['lanes'])
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
