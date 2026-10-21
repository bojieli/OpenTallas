#!/usr/bin/env python3
"""slice_cut: cut a simulatable SLICE top out of a generated (portless) die netlist.

LAYERBENCH (owner 10-18 token-pass release gate): a whole Qwen die cannot be simulated, so every layer bench runs on a
slice cut AUTOMATICALLY from the die revision of record's GEN netlist.  The slice keeps every selected instance VERBATIM
(same master, same parameters, same die-net bits) and binds it to the same RTL the die's strict port bind uses (the
bind JSON's rtl_roots / rtl_files / defines); nothing inside the slice is a stand-in.  Every die-net bit that crosses the
slice boundary becomes a slice port:

  * input  i_<net>[...]  a bit read inside the slice whose die driver is outside (a neighbour tile, a relay outside the
                         slice, the reset sequencer, a PHY, a die pad).  The bench's replay model drives it.
  * output o_<net>[...]  a bit driven inside the slice that the die reads outside.  The bench's replay model checks it.

The die's undriven bits that the slice reads are reported (die_undriven) -- they are a die bug, never silently tied.

Selection: --inst REGEX (instance names) / --master REGEX (master names); --grow REGEX adds, transitively and only
along the signal direction (fan-in for slice inputs, fan-out for slice outputs), every instance of a matching master
that is directly connected -- e.g. the relay / landing / reset-repeater chains between a tile and its neighbours, so
the slice boundary sits at the next real tile and the die's own relays/landings are inside the slice.

Outputs (--out DIR): <top>.sv (slice top), <top>.f (Verilator file list: +define, +incdir, the RTL closure),
slice.json (instances, ports with die driver/loads, roles clock/reset/data, die_undriven, die sha256, bind sha256).

    python3 tools/qwen_layerbench/slice_cut.py --die-v DIE_V --bind PORT_BIND_JSON --src SRC_TREE \
        [--map OLD=NEW ...] (--inst RE | --master RE)... [--grow RE] [--exclude RE] --top NAME --out DIR
    python3 tools/qwen_layerbench/slice_cut.py ... --describe MASTER_RE     # print masters' port lists and stop
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as dpb  # noqa: E402  (the strict bind's own netlist + RTL parsers: the slice binds like the die)

SCHEMA = 'opentallas.die_slice.v1'
CLK_RE = re.compile(r'(^|_)(clk|ck|hck|fdi_ck|clock)(_|\d|$)|^clk|clk$|_ck$|^ck', re.I)
RST_RE = re.compile(r'(^|_)(rst|reset|por)(_|n|\d|$)|rst_n|^rst', re.I)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def remap(p, maps):
    for a, b in maps:
        if p.startswith(a):
            return b + p[len(a):]
    return p


def load_index(bind, src, maps):
    roots = []
    for r in bind['rtl_roots']:
        rp = remap(r, maps)
        roots.append(rp if Path(rp).is_absolute() else str(Path(src) / rp))
    files = [remap(f, maps) for f in bind['rtl_files']]
    files = [f if Path(f).is_absolute() else str(Path(src) / f) for f in files]
    defines = {d: '1' for d in bind.get('defines', [])}
    idx, amb = dpb.rtl_index([r for r in roots if Path(r).exists()], [f for f in files if Path(f).exists()],
                             defines, files)
    missing = [f for f in files if not Path(f).exists()]
    # AMBIGUOUS child modules (several different headers: e.g. ot_hdc_qadd in rtl/hdc/ot_hdc_fastfp.sv with #(L) and
    # parameterless copies in rtl/chip/physical/*): rtl_index keeps the first path in sort order.  Re-pick the canonical
    # definition: a bind rtl_file, then rtl/hdc, then the main rtl tree, then everything else (ref_tile kit copies last).
    def rank(path):
        q = str(path)
        if q in files:
            return 0
        if '/rtl/hdc/' in q and '/physical/' not in q:
            return 1
        if '/rtl/' in q and '/rtl/chip/' not in q and '/physical/' not in q and '/test/' not in q:
            return 2
        if '/physical/ref_tile/' in q:
            return 4
        return 3
    repicked = {}
    for name, paths in amb.items():
        best = sorted(paths, key=lambda q: (rank(q), q))[0]
        if best != idx[name].path:
            t = dpb.preprocess(dpb.strip_comments(Path(best).read_text(errors='replace')), defines)
            for mod in dpb.parse_modules(t, best):
                if mod.name == name:
                    idx[name] = mod
                    repicked[name] = best
    load_index.repicked = repicked
    load_index.rank = rank
    return idx, amb, files, roots, missing


def port_dir(idx, mst, port):
    m = idx.get(mst)
    if m is None or port not in m.ports:
        return None
    return m.ports[port][0]


def connectivity(nets, tin, insts, idx):
    """bit -> driver (inst, port) ; bit -> [loads]; per-instance list of (port, dir, bits)"""
    drv, loads, pins = {}, defaultdict(list), {}
    for n in tin:
        w, lo = nets[n]
        for i in range(lo, lo + w):
            drv[(n, i)] = ('__TOP__', n)
    bad = []
    for mst, inst, params, conns in insts:
        if mst == '__assign__':
            raise SystemExit('slice_cut: die netlist has assign statements; not supported (GEN dies are instance-only)')
        lst = []
        for pn, expr in conns.items():
            d = port_dir(idx, mst, pn)
            bits = dpb.expr_bits(expr, nets)
            if bits is None or d is None:
                bad.append((inst, pn, expr[:60], d))
                bits = bits or []
            lst.append((pn, d, bits))
            for b in bits:
                if b[0] in ('CONST', 'Z', 'UNDECL'):
                    continue
                if d in ('output', 'inout'):
                    drv[b] = (inst, pn)
                if d in ('input', 'inout'):
                    loads[b].append((inst, pn))
        pins[inst] = (mst, lst)
    return drv, loads, pins, bad


def select(insts, args):
    out = set()
    for mst, inst, _, _ in insts:
        if any(re.fullmatch(r, inst) for r in args.inst) or any(re.fullmatch(r, mst) for r in args.master):
            out.add(inst)
    return out


def grow(sel, pins, drv, loads, regex, exclude, max_iter=4096):
    """add instances of masters matching regex, transitively, fan-in from slice inputs / fan-out from slice outputs"""
    if not regex:
        return sel, 0
    rg, ex = re.compile(regex), re.compile(exclude) if exclude else None
    ok = lambda i: i in pins and rg.fullmatch(pins[i][0]) and not (ex and ex.fullmatch(i))  # noqa: E731
    sel = set(sel)
    fin, fout = set(sel), set(sel)        # frontier for fan-in / fan-out
    added = 0
    for _ in range(max_iter):
        nin, nout = set(), set()
        for i in fin:
            for pn, d, bits in pins[i][1]:
                if d in ('input', 'inout'):
                    for b in bits:
                        x = drv.get(b)
                        if x and x[0] not in sel and ok(x[0]):
                            nin.add(x[0])
        for i in fout:
            for pn, d, bits in pins[i][1]:
                if d in ('output', 'inout'):
                    for b in bits:
                        for x in loads.get(b, []):
                            if x[0] not in sel and ok(x[0]):
                                nout.add(x[0])
        if not nin and not nout:
            break
        sel |= nin | nout
        added += len(nin | nout)
        # every added instance's own inputs (clock / reset / enable of a fan-out relay) grow fan-in; fan-out continues
        # only from instances reached along the fan-out direction
        fin, fout = nin | nout, nout
    return sel, added


def runs(idxs):
    """sorted ints -> [(lo, hi)] contiguous runs"""
    out = []
    for i in sorted(idxs):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [tuple(r) for r in out]


def role(net, pairs):
    names = [p for _, p in pairs]
    if (names and all(CLK_RE.search(p) for p in names)) or re.match(r'n_clk', net):
        return 'clock'
    if (names and all(RST_RE.search(p) for p in names)) or re.match(r'n_(rst|rrs_n_rst|rs_)', net):
        return 'reset'
    return 'data'


def closure_files(idx, masters, always):
    seen, todo, files = set(), sorted(m for m in masters if m in idx), []
    unres = defaultdict(set)
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        p = idx[n].path
        if p not in files:
            files.append(p)
        kids = set(dpb.instantiated(idx[n].body))
        # fallback (instantiated() misses some forms, e.g. a child after a generate label): any known module name
        # followed by a parameter list or an instance name and a port list
        kids |= {t for t in re.findall(r'\b([A-Za-z_]\w*)\s*(?=#\s*\(|[A-Za-z_]\w*\s*(?:\[[^\]]*\]\s*)?\()',
                                       dpb._lexical_mask(idx[n].body, strings=True)) if t in idx}
        for c in sorted(kids - {n}):
            if c in idx:
                todo.append(c)
            else:
                unres[c].add(n)
    for f in always:
        if f not in files and Path(f).exists():
            files.append(f)
    return files, {k: sorted(v) for k, v in unres.items()}, sorted(seen)


def package_files(files, roots):
    """files defining packages that `files` import (pkg::), searched in the bind's roots"""
    want = set()
    for f in files:
        t = Path(f).read_text(errors='replace')
        want |= set(re.findall(r'\b([A-Za-z_]\w*)::', t))
    if not want:
        return []
    found = {}
    for r in roots:
        rp = Path(r)
        if not rp.exists():
            continue
        for p in list(rp.rglob('*.sv')) + list(rp.rglob('*.svh')):
            try:
                t = p.read_text(errors='replace')
            except Exception:
                continue
            for m in re.finditer(r'^\s*package\s+(\w+)\s*;', t, re.M):
                if m.group(1) in want and m.group(1) not in found:
                    found[m.group(1)] = str(p)
    return sorted(set(found.values()))


def emit(args, nets, insts, pins, drv, loads, sel, idx, files, roots, bind, die_sha):
    touched = defaultdict(set)          # net -> bits referenced by the slice
    for i in sel:
        for pn, d, bits in pins[i][1]:
            for b in bits:
                if b[0] not in ('CONST', 'Z', 'UNDECL'):
                    touched[b[0]].add(b[1])
    inb, outb, undriven = defaultdict(set), defaultdict(set), defaultdict(set)
    in_who, out_who = {}, {}
    for n, bs in touched.items():
        for b in bs:
            d = drv.get((n, b))
            ld = loads.get((n, b), [])
            inside_load = [x for x in ld if x[0] in sel]
            outside_load = [x for x in ld if x[0] not in sel]
            if d is None:
                if inside_load:
                    undriven[n].add(b)
                continue
            if d[0] in sel:
                if outside_load:
                    outb[n].add(b)
                    out_who.setdefault(n, (d, sorted(set(outside_load))[:4]))
            elif inside_load:
                inb[n].add(b)
                in_who.setdefault(n, (d, sorted(set(inside_load))[:4], inside_load))
    ports, decl, body = [], [], []
    meta_ports = []
    for n in sorted(touched):
        w, lo = nets[n]
        decl.append(f'  wire [{lo + w - 1}:{lo}] {n};')
    for n in sorted(inb):
        d, sample, il = in_who[n]
        rl = role(n, il)
        for a, b in runs(inb[n]):
            pn = f'i_{n}' if (a, b) == (nets[n][1], nets[n][1] + nets[n][0] - 1) else f'i_{n}__{b}_{a}'
            ports.append(f'  input  wire [{b - a}:0] {pn}')
            body.append(f'  assign {n}[{b}:{a}] = {pn};')
            meta_ports.append({'port': pn, 'dir': 'input', 'net': n, 'msb': b, 'lsb': a, 'width': b - a + 1,
                               'role': rl, 'die_driver': list(d), 'loads_in_slice': [list(x) for x in sample]})
    for n in sorted(outb):
        d, sample = out_who[n]
        for a, b in runs(outb[n]):
            pn = f'o_{n}' if (a, b) == (nets[n][1], nets[n][1] + nets[n][0] - 1) else f'o_{n}__{b}_{a}'
            ports.append(f'  output wire [{b - a}:0] {pn}')
            body.append(f'  assign {pn} = {n}[{b}:{a}];')
            meta_ports.append({'port': pn, 'dir': 'output', 'net': n, 'msb': b, 'lsb': a, 'width': b - a + 1,
                               'role': 'data', 'die_driver': list(d), 'loads_outside': [list(x) for x in sample]})
    # instances, verbatim from the die netlist text
    text = dpb.strip_comments(Path(args.die_v).read_text(errors='replace'))
    inst_txt = {}
    ovr = defaultdict(dict)
    for o in args.override:
        inst, rest = o.split(':', 1)
        pv, _reason = rest.split(':', 1)
        k, v = pv.split('=', 1)
        ovr[inst][k] = v
    # QLB-GEN 10-18: the die's master elaboration parameters (DIE_V.params.json, the GEN's compiler assignments, e.g.
    # qfd_tt_ctlm_dv XPF_TRANSPORT_EDGES / qfd_d2d_static TXDP) are inlined on every selected instance of that master,
    # as tools/die_port_bind.py elab_kit does; --override may only fill a parameter the die leaves unset
    side = {}
    pj = args.params or (args.die_v + '.params.json' if Path(args.die_v + '.params.json').exists() else None)
    if pj:
        side = {mst: {k: v for k, v in d.items() if not k.startswith('_')}
                for mst, d in json.loads(Path(pj).read_text()).get('masters', {}).items()}
    used_side = {}
    for st in text.split(';'):
        s = st.strip()
        m = re.match(r'(\\\S+|\w+)\s*(#\s*\(.*?\)\s*)?(\\\S+\s|\w+)\s*\(', s, re.S)
        if m and m.group(3).strip() in sel:
            name = m.group(3).strip()
            line = ' '.join(s.split())
            pv = dict(side.get(m.group(1), {}))
            if pv:
                used_side[name] = dict(master=m.group(1), **pv)
            for k in ovr.get(name, {}):
                if k in pv:
                    raise SystemExit(f'slice_cut: --override {name}.{k}: the die sets it ({pv[k]} in {pj})')
            pv.update(ovr.get(name, {}))
            if pv:
                if m.group(2):
                    raise SystemExit(f'slice_cut: parameters for {name}, which already has inline die parameters')
                ps = ', '.join(f'.{k}({sv_lit(v)})' for k, v in pv.items())
                line = f'{m.group(1)} #({ps}) {line[len(m.group(1)):].lstrip()}'
            inst_txt[name] = '  ' + line + ';'
    order = [inst for mst, inst, _, _ in insts if inst in sel]
    top = args.top
    out = [f'// GENERATED by tools/qwen_layerbench/slice_cut.py from {args.die_v}',
           f'// die sha256 {die_sha}; {len(sel)} instances, verbatim; slice ports = die-net bits crossing the slice edge.',
           f'// Do not edit.  Rebuild with the command in slice.json["command"].',
           f'module {top} (']
    out.append(',\n'.join(ports))
    out.append(');')
    out += decl + body
    out += [inst_txt[i] for i in order]
    out.append('endmodule')
    od = Path(args.out)
    od.mkdir(parents=True, exist_ok=True)
    (od / f'{top}.sv').write_text('\n'.join(out) + '\n')
    masters = sorted({pins[i][0] for i in sel})
    always = [f for f in files if Path(f).exists()]
    defs = {d: '1' for d in bind.get('defines', [])}
    rank = load_index.rank
    for _ in range(6):
        flist, unres, mods = closure_files(idx, masters, [])
        moved = False
        for f in flist:                      # same-header duplicates (rtl_index does not flag them): canonical wins
            t = dpb.preprocess(dpb.strip_comments(Path(f).read_text(errors='replace')), defs)
            for mod in dpb.parse_modules(t, f):
                cur = idx.get(mod.name)
                if cur is not None and cur.path != f and cur.path in flist and (rank(f), f) < (rank(cur.path), cur.path):
                    idx[mod.name] = mod
                    load_index.repicked[mod.name] = f
                    moved = True
        if not moved:
            break
    # bind rtl_files that define a module of the closure (die glue, macro models) are already in flist through idx
    # a file brought in for one module may define another module whose chosen definition is elsewhere: list them
    conflicts = {}
    for f in flist:
        try:
            t = dpb.preprocess(dpb.strip_comments(Path(f).read_text(errors='replace')), {d: '1' for d in bind.get('defines', [])})
        except Exception:
            continue
        for mod in dpb.parse_modules(t, f):
            if mod.name in idx and idx[mod.name].path != f and idx[mod.name].path in flist:
                conflicts[mod.name] = [idx[mod.name].path, f]
    emit.conflicts = conflicts
    pk = package_files(flist, roots)
    allf = pk + [f for f in flist if f not in pk]
    incd = sorted({str(Path(f).parent) for f in allf})
    fl = [f'+define+{d}' for d in bind.get('defines', [])] + [f'+incdir+{d}' for d in incd] + allf + \
         [str(od / f'{top}.sv')]
    (od / f'{top}.f').write_text('\n'.join(fl) + '\n')
    kinds = {m: ('model' if (Path(idx[m].path).name.endswith('_bb.v') or bind['masters'].get(m, {}).get('kind') == 'model')
                 else idx[m].kind(idx)) if m in idx else 'UNBOUND' for m in masters}
    rec = {
        'schema': SCHEMA, 'top': top, 'die_v': args.die_v, 'die_sha256': die_sha, 'bind': args.bind,
        'bind_sha256': sha(args.bind), 'bind_verdict': bind.get('verdict'), 'src': args.src,
        'command': ' '.join(sys.argv),
        'selection': {'inst': args.inst, 'master': args.master, 'grow': args.grow, 'exclude': args.exclude},
        'die_params_file': pj, 'die_params_applied': used_side,
        'die_gap_overrides': [dict(zip(('instance', 'param_value', 'reason'), (o.split(':', 1)[0],) +
                                       tuple(o.split(':', 1)[1].split(':', 1)))) for o in args.override],
        'instances': len(sel), 'masters': {m: sum(1 for i in sel if pins[i][0] == m) for m in masters},
        'master_kind': kinds,
        'ports': meta_ports,
        'n_in_bits': sum(p['width'] for p in meta_ports if p['dir'] == 'input'),
        'n_out_bits': sum(p['width'] for p in meta_ports if p['dir'] == 'output'),
        'die_undriven': {n: runs(b) for n, b in sorted(undriven.items())},
        'rtl_unresolved_children': unres, 'modules': len(mods), 'files': len(allf),
        'ambiguous_repicked': getattr(load_index, 'repicked', {}),
        'module_conflicts': conflicts,
    }
    (od / 'slice.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


def sv_lit(v):
    """a sidecar value as an SV literal (ints >= 2**31 sized, so a [31:0] vector parameter keeps its bits)."""
    if isinstance(v, int) and not 0 <= v < 2 ** 31:
        return f"{max(32, v.bit_length())}'d{v}" if v >= 0 else str(v)
    return str(v)


def describe(insts, idx, regex):
    seen = set()
    for mst, inst, params, conns in insts:
        if mst in seen or not re.fullmatch(regex, mst):
            continue
        seen.add(mst)
        m = idx.get(mst)
        print(f'== {mst} ({sum(1 for x in insts if x[0] == mst)} inst; e.g. {inst}) rtl={m.path if m else None}')
        if m:
            env = m.env(params)
            for pn in m.order:
                d, _ = m.ports[pn]
                print(f'   {d or "?":6} {m.width(pn, env)!s:>6} {pn}   <- {conns.get(pn, "(open)")[:90]}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--bind', required=True, help='the die strict port-bind JSON (rtl_roots, rtl_files, defines)')
    ap.add_argument('--src', required=True, help='source tree at the die revision commit (rtl_roots are relative to it)')
    ap.add_argument('--map', action='append', default=[], help='OLD=NEW path prefix remap for bind rtl_files')
    ap.add_argument('--inst', action='append', default=[])
    ap.add_argument('--master', action='append', default=[])
    ap.add_argument('--grow', default=None)
    ap.add_argument('--exclude', default=None, help='instance regex never added by --grow')
    ap.add_argument('--override', action='append', default=[],
                    help='INST:PARAM=VALUE:REASON -- a parameter the die netlist fails to set (a DIE GAP, recorded in '
                         'slice.json die_gap_overrides; never used to change a value the die sets)')
    ap.add_argument('--params', default=None, help='die master parameter sidecar (default DIE_V.params.json when present)')
    ap.add_argument('--top', default='slice_top')
    ap.add_argument('--out')
    ap.add_argument('--describe', default=None)
    a = ap.parse_args(argv)
    maps = [tuple(m.split('=', 1)) for m in a.map]
    bind = json.loads(Path(a.bind).read_text())
    nets, tin, tout, insts = dpb.parse_die(a.die_v, bind.get('top'))
    idx, amb, files, roots, missing = load_index(bind, a.src, maps)
    if missing:
        print('slice_cut: WARNING bind rtl_files missing:', missing, file=sys.stderr)
    if a.describe:
        describe(insts, idx, a.describe)
        return 0
    drv, loads, pins, bad = connectivity(nets, tin, insts, idx)
    sel = select(insts, a)
    if not sel:
        raise SystemExit('slice_cut: selection is empty')
    sel, added = grow(sel, pins, drv, loads, a.grow, a.exclude)
    rec = emit(a, nets, insts, pins, drv, loads, sel, idx, files, roots, bind, sha(a.die_v))
    badsel = [b for b in bad if b[0] in sel]
    rec['unparsed_in_slice'] = [list(b) for b in badsel]
    Path(a.out, 'slice.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f"slice_cut: {a.top}: {rec['instances']} instances (+{added} grown), {len(rec['masters'])} masters, "
          f"in {rec['n_in_bits']} bits / out {rec['n_out_bits']} bits, {rec['files']} files, "
          f"die_undriven {sum(len(v) for v in rec['die_undriven'].values())} runs, unparsed {len(badsel)}, "
          f"unresolved {len(rec['rtl_unresolved_children'])}, repicked {len(rec['ambiguous_repicked'])}, "
          f"conflicts {len(rec['module_conflicts'])}")
    return 0 if not badsel else 3


if __name__ == '__main__':
    sys.exit(main())
