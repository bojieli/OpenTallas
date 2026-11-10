#!/usr/bin/env python3
"""dv_bound_cut.py -- cut a slice top out of a strict bind's BOUND die top (TOK-VERIFY-1 S2, 11-10).

Port of dv_slice_cut.py from the as-built flat die.v to the bind's own emitted RTL (rtl/s81_bound_top.sv + rtl/<type>.sv):
the cut is a set of bound-top partition instances copied VERBATIM (same types, same parameter overrides, same net
names).  Every top net a member reads but no member drives becomes an input port; every net a member drives that is
read outside the cut (or is a die output) becomes an output port.  Top-level die inputs (clocks, rst_n, pins) the
members read are inputs of the same name.

Growth (--grow, default on): for every bind_latency lane whose src AND dst partitions are in the set, every partition
on its bound path (the stations / feed-through partitions, found by lane_arrival.py's walk of the emitted RTL) is added,
so a lane between two members runs through its real stations and clock landings inside the cut.  A lane with one end
outside enters (leaves) the cut at the first (last) member on its path: the port is the top net at that boundary.

  dv_bound_cut.py --bind BIND_DIR --insts seqhost,gunit,eng --out DIR [--name cut_top] [--no-grow] [--repo REPO]
Output: DIR/<name>.sv, DIR/cut_ports.json {port: {dir, width, kind (clock|reset|lane|forwarded_clock|die_input|other),
lanes [...], peers [outside instances]}}, DIR/cut_insts.json {inst: {type, how}}, DIR/cut.f (bind.f + the cut top).
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lane_arrival as LA  # noqa: E402
import ft_shell as FS  # noqa: E402

INST_RE = re.compile(r'^    ([A-Za-z_][A-Za-z0-9_]*) (#\(.*\) )?([A-Za-z_][A-Za-z0-9_]*) \($')
PORT_RE = re.compile(r'^\s*(input|output|inout)\s+(?:wire|reg|logic)?\s*(\[[^\]]+\])?\s*([A-Za-z_][A-Za-z0-9_]*)')


def top_blocks(text):
    """[(inst, type, first line, last line)] of the bound top (one instance statement per block, '    );' closes)"""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        m = INST_RE.match(lines[i])
        if m:
            j = i
            while lines[j].rstrip() != '    );':
                j += 1
            out.append((m.group(3), m.group(1), i, j))
            i = j + 1
            continue
        i += 1
    return lines, out


def port_dirs(path, mod):
    txt = LA.strip_comments(path.read_text())
    m = re.search(r'\bmodule\s+' + mod + r'\b(.*?)\)\s*;', txt, flags=re.S)
    hdr = txt[m.start():]
    dirs = {}
    for st in re.split(r'[;,\n]', hdr[:hdr.find('endmodule')]):
        pm = PORT_RE.match(st)
        if pm:
            dirs[pm.group(3)] = pm.group(1)
    return dirs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--bind', type=Path, required=True)
    ap.add_argument('--insts', required=True, help='comma list or @FILE of bound-top instance names')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--name', default='cut_top')
    ap.add_argument('--no-grow', action='store_true')
    ap.add_argument('--no-shell', action='store_true', help='keep grown pass-through partitions whole')
    ap.add_argument('--shell-mutant', default=None, help='INST:PORT:+1 -- one extra stage in that shell (must FAIL)')
    a = ap.parse_args()
    rtl = a.bind / 'rtl'
    tp = rtl / 's81_bound_top.sv'
    text = tp.read_text()
    lines, blocks = top_blocks(text)
    top = LA.parse_module(text, 's81_bound_top')
    by_name = {it['name']: it for it in top['insts']}
    blk = {b[0]: b for b in blocks}
    assert set(blk) == set(by_name), 'instance block scan disagrees with the parser'
    want = [x.strip() for x in (Path(a.insts[1:]).read_text().split() if a.insts.startswith('@') else a.insts.split(','))
            if x.strip() and not x.startswith('#')]
    miss = [w for w in want if w not in by_name]
    if miss:
        raise SystemExit(f'not bound-top instances: {miss}')
    how = {w: 'listed' for w in want}
    # top-level declarations: widths of nets and die ports
    width, die_dir = {}, {}
    for ln in lines:
        m = re.match(r'^\s*(input|output|inout)?\s*wire\s*(\[[^\]]+\])?\s*([A-Za-z_][A-Za-z0-9_]*)\s*;(.*)$', ln)
        if m:
            width[m.group(3)] = m.group(2) or ''
            if m.group(1):
                die_dir[m.group(3)] = m.group(1)
    tags = {}
    for ln in lines:
        m = re.match(r'\s*wire\s*(?:\[[^\]]*\])?\s*([A-Za-z_][A-Za-z0-9_]*)\s*;\s*//\s*lane\s+(\S+)', ln)
        if m:
            tags[m.group(1)] = m.group(2)
    users = defaultdict(list)
    for it in top['insts']:
        for p, e in it['conns'].items():
            for b in ([LA.base(e)[0]] if LA.base(e)[0] else re.findall(LA.ID, e)):
                users[b].append((it['name'], p))
    if not a.no_grow:
        lat = json.loads((a.bind / 'bind_latency.json').read_text())['buses']
        grown_lanes = set()
        for b in lat:
            if b['src'] in want and b['dst'] in want:      # lanes between LISTED members only (no cascade)
                grown_lanes.add(b['lane'])
                # every top net tagged with this lane names a partition on its path
                for net, ln in tags.items():
                    if ln == b['lane']:
                        for inst, _ in users[net]:
                            if inst not in how:
                                how[inst] = f"path of lane {b['lane']}"
    dirs_cache = {}
    shells, shell_rep = {}, {}
    if a.no_grow:
        grown_lanes = set()
    if not a.no_shell:
        for inst in [i for i in how if how[i] != 'listed']:
            it = by_name[inst]
            t = it['mod']
            tdirs = port_dirs(rtl / f'{t}.sv', t)
            keep = set()
            for p, e in it['conns'].items():
                n = LA.base(e)[0]
                if tdirs.get(p) == 'output' and tags.get(n) in grown_lanes:
                    keep.add(p)
                    if f'fclk_out_{p}' in tdirs:
                        keep.add(f'fclk_out_{p}')
            mut = None
            if a.shell_mutant and a.shell_mutant.split(':', 1)[0] == inst:
                mut = a.shell_mutant.split(':', 1)[1]
            try:
                txt, kept, r = FS.build((rtl / f'{t}.sv').read_text(), t, keep, mutant=mut)
            except ValueError as exc:
                shell_rep[inst] = dict(type=t, shell=None, refused=str(exc)[:400])
                continue
            sname = f'{t}__ftshell' + ('__mut' if mut else '')
            if mut:
                txt = txt.replace(f'module {t}__ftshell', f'module {sname}', 1)
            shells[inst] = dict(module=sname, text=txt, ports=set(kept))
            shell_rep[inst] = dict(r, shell=sname, kept_outputs=sorted(keep))
            it2 = dict(it, mod=sname, conns={p: e for p, e in it['conns'].items() if p in kept})
            by_name[inst] = it2
            dirs_cache[sname] = {p: d for p, d in tdirs.items() if p in kept}
        users = defaultdict(list)
        for it in by_name.values():
            for p, e in it['conns'].items():
                for b in ([LA.base(e)[0]] if LA.base(e)[0] else re.findall(LA.ID, e)):
                    users[b].append((it['name'], p))

    def pdir(inst, port):
        t = by_name[inst]['mod']
        if t not in dirs_cache:
            dirs_cache[t] = port_dirs(rtl / f'{t}.sv', t)
        return dirs_cache[t].get(port)

    members = set(how)
    ports, internal = {}, set()
    for net, us in users.items():
        ins = [(i, p) for i, p in us if i in members]
        if not ins:
            continue
        outs = [(i, p) for i, p in us if i not in members]
        drv_in = [(i, p) for i, p in ins if pdir(i, p) == 'output']
        drv_out = [(i, p) for i, p in outs if pdir(i, p) == 'output']
        if net in die_dir:
            d = 'input' if die_dir[net] == 'input' else ('output' if drv_in else 'input')
        elif drv_in:
            d = 'output' if [o for o in outs if pdir(*o) != 'output'] else None
        else:
            d = 'input'
        if d is None:
            internal.add(net)
            continue
        if d == 'input' and not drv_out and net not in die_dir:
            kind = 'undriven_in_die'
        elif net.startswith('clk_region') or net == 'clk_core':
            kind = 'clock'
        elif net.startswith('clock_landing_fwd') or net.startswith('cland_clock'):
            kind = 'forwarded_clock'
        elif net.startswith('rst') or 'rst' in net.split('_')[0]:
            kind = 'reset'
        elif net in tags:
            kind = 'lane'
        elif net in die_dir:
            kind = 'die_' + die_dir[net]
        else:
            kind = 'other'
        ports[net] = dict(dir=d, width=width.get(net, ''), kind=kind, lane=tags.get(net),
                          peers=sorted({i for i, _ in outs}), members=sorted({i for i, _ in ins}))
    order = sorted(ports)
    body = [f'// GENERATED by dv_bound_cut.py (TOK-VERIFY-1 S2) from {tp} sha256 '
            f'{hashlib.sha256(text.encode()).hexdigest()[:16]}: {len(members)} bound-top instances, verbatim.  Do not edit.',
            '`timescale 1ns/1ps', '`default_nettype none', f'module {a.name} ({", ".join(order)});']
    for n in order:
        body.append(f'    {ports[n]["dir"]} wire {ports[n]["width"] + " " if ports[n]["width"] else ""}{n};')
    for n in sorted(internal):
        body.append(f'    wire {width.get(n, "") + " " if width.get(n) else ""}{n};')
    for inst in sorted(members, key=lambda x: blk[x][2]):
        _, _, i, j = blk[inst]
        if inst in shells:            # same block, shell type, only the kept port connections
            sh = shells[inst]
            head = lines[i].replace(blk[inst][1], sh['module'], 1)
            cl = [ln for ln in lines[i + 1:j] if (lambda m: m and m.group(1) in sh['ports'])(re.match(r'^\s*\.(\w+)\(', ln))]
            cl = [ln.rstrip().rstrip(',') + (',' if k < len(cl) - 1 else '') for k, ln in enumerate(cl)]
            body += [head] + cl + [lines[j]]
        else:
            body += lines[i:j + 1]
    body += ['endmodule', '`default_nettype wire', '']
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f'{a.name}.sv').write_text('\n'.join(body))
    (a.out / 'cut_ports.json').write_text(json.dumps(dict(
        schema='tok-verify-1.bound_cut.v1', bind=str(a.bind), top_sha256=hashlib.sha256(text.encode()).hexdigest(),
        ports=ports), indent=1) + '\n')
    (a.out / 'cut_insts.json').write_text(json.dumps({i: dict(type=by_name[i]['mod'], how=how[i], shell=shell_rep.get(i))
                                                      for i in sorted(members)}, indent=1) + '\n')
    for inst, sh in shells.items():
        (a.out / f"{sh['module']}.sv").write_text(sh['text'])
    bf = [x for x in (a.bind / 'bind.f').read_text().split() if x.strip()]
    (a.out / 'cut.f').write_text('\n'.join([x for x in bf if not x.endswith('s81_bound_top.sv')] +
                                           sorted({str((a.out / f"{sh['module']}.sv").resolve()) for sh in shells.values()}) +
                                           [str((a.out / f'{a.name}.sv').resolve())]) + '\n')
    kinds = defaultdict(int)
    for p in ports.values():
        kinds[f"{p['dir']}:{p['kind']}"] += 1
    print(f'shells {len(shells)}, refused {sum(1 for v in shell_rep.values() if v.get("shell") is None)}: ' +
          '; '.join(f"{i} {v.get('refused')}" for i, v in shell_rep.items() if v.get('shell') is None)[:600])
    print(f'{a.name}: {len(members)} instances ({sum(v == "listed" for v in how.values())} listed), '
          f'{len(ports)} ports {dict(kinds)}, {len(internal)} internal nets')


if __name__ == '__main__':
    main()
