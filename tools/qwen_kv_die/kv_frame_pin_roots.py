#!/usr/bin/env python3
"""Per-port clock roots of multi-root frame masters, from their bound RTL (KV GEN-safety --pin-roots).

kv_gen_safety.py gives a crossing endpoint the clock of its Liberty related_pin, else the
instance's single n_clk_* root. A stand-in frame master with no Liberty clock arcs and two or
more clock roots (qkd_kvs_pc_h: hck/ck, qkd_host_rt: four roots, ...) gets no region, and every
crossing on it fails C1/C2. The exporter takes an explicit map ('<inst>/<port>' or
'<inst>/<port>[bit]' -> die clock net), which must never be guessed from names. This tool derives
it from the actual RTL that the strict bind (port_bind_v2) bound to each master:

  * the master's module, parameters and source come from port_bind_v2/bound_netlist.json and
    port_bind_v2.json; its child closure is resolved with die_port_bind.rtl_index over the
    record's own rtl_roots/rtl_files, and every variant child must resolve to the file the
    binder chose (variant_children[].chosen), else REFUSE;
  * the pinned yosys elaborates it (hierarchy -chparam, proc, flatten, memory -nomap);
  * every sequential cell's clock (CLK, latch EN, $mem_v2 RD/WR_CLK) is traced back through
    combinational cells to the module's clock input ports;
  * an input bit is synchronous to the clocks of the sequential inputs (D/EN/reset/address/
    data) it reaches through combinational logic; an output bit to the clocks of the sequential
    outputs (Q / clocked read data) that reach it;
  * die_bound.v (RTL port bit -> die net) and die.v (die port bit -> die net) map each die port
    bit to RTL port bits on the same instance, and each RTL clock port to its die clock net.

A bit whose cone holds sequential cells of two different die clock nets, or none, is REPORTED
(report JSON) and left out of the map: the exporter then keeps refusing it (region None).
Port bits with Liberty clock arcs are not mapped (Liberty stays authoritative); qkd_landsh* /
qkd_rlysh_* have their own explicit rule in the exporter.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent))
import die_port_bind as DPB  # noqa: E402
from kv_gen_safety import INST, CONN, bits, clock_pins, groups  # noqa: E402

PINNED_YOSYS = Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'
SEQ_CLK = {'$dff': 'CLK', '$dffe': 'CLK', '$adff': 'CLK', '$adffe': 'CLK', '$sdff': 'CLK', '$sdffe': 'CLK',
           '$sdffce': 'CLK', '$aldff': 'CLK', '$aldffe': 'CLK', '$dffsr': 'CLK', '$dffsre': 'CLK',
           '$dlatch': 'EN', '$adlatch': 'EN', '$dlatchsr': 'EN'}
SEQ_OUT = 'Q'
BITWISE1 = {'$not', '$pos', '$buf'}
BITWISE2 = {'$and', '$or', '$xor', '$xnor', '$bweqx'}
CLOCK_NET = re.compile(r'n_clk_')


def die_instances(path):
    text = Path(path).read_text()
    widths = {n: int(hi) + 1 for hi, n in re.findall(r'wire\s+\[(\d+):0\]\s+(\S+);', text)}
    for ln in text.splitlines():
        m = INST.match(ln)
        if m and m[1] not in ('wire', 'module', 'input', 'output'):
            yield m[1], m[2], dict(CONN.findall(m[3])), widths


def bound_instances(path, wanted):
    """die_bound.v: '<module> [#(...)] <inst> (...)' lines of the wanted instances -> {inst: conns}."""
    text = Path(path).read_text()
    widths = {n: int(hi) + 1 for hi, n in re.findall(r'wire\s+\[(\d+):0\]\s+(\S+);', text)}
    pat = re.compile(r'^\s+(\S+)\s+(?:#\((.*?)\)\s+)?(\S+) \((.*)\);\s*$')
    out = {}
    for ln in text.splitlines():
        m = pat.match(ln)
        if m and m[3] in wanted:
            out[m[3]] = (m[1], dict(CONN.findall(m[4])))
    return out, widths



USE_BEFORE_DECL = re.compile(r"(\S+):(\d+): ERROR: Failed to detect width of signal access `\\([\w$]+)\.([\w$]+)'")


def hoist(path, line, block, sig):
    """Yosys's frontend refuses a generate-block net used before its declaration (legal for the
    simulators/STA flow that bound it). Move that pure declaration statement (no initialiser) to
    the start of its own generate block; anything else refuses."""
    text = Path(path).read_text()
    at = sum(len(x) for x in text.splitlines(keepends=True)[:int(line)])
    starts = [m for m in re.finditer(r'\bbegin\s*:\s*' + re.escape(block) + r'\b', text) if m.start() < at]
    start = starts[-1] if starts else None
    if not start:
        raise ValueError(f'{path}: generate block {block} not found')
    decl = re.compile(r'\b(?:wire|logic|reg)\b[^;=()]*?\b' + re.escape(sig) + r'\b[^;=()]*;')
    m = decl.search(text, start.end())
    if not m:
        raise ValueError(f'{path}: no pure declaration of {block}.{sig} to hoist')
    stmt = m.group(0)
    text = text[:m.start()] + text[m.end():]
    return text[:start.end()] + '\n ' + stmt + text[start.end():], stmt


def elaborate(yosys, files, top, params, defines, work, lib_files=()):
    work.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha256(json.dumps([top, params, files, defines, list(lib_files)]).encode()).hexdigest()[:12]
    out = work / f'{top}_{tag}.json'
    hoists = []
    if out.exists():
        hj = Path(f'{out}.hoists.json')
        return json.loads(out.read_text()), out, (json.loads(hj.read_text()) if hj.exists() else [])
    files = list(files)
    for _ in range(64):
        try:
            return _elaborate(yosys, files, top, params, defines, work, tag, out, lib_files), out, hoists
        except RuntimeError as exc:
            m = USE_BEFORE_DECL.search(str(exc))
            if not m:
                raise
            src = m[1]
            if src not in files:
                raise
            copy = work / 'hoisted' / tag / Path(src).name
            copy.parent.mkdir(parents=True, exist_ok=True)
            text, stmt = hoist(src, m[2], m[3], m[4])
            copy.write_text(text)
            files[files.index(src)] = str(copy)
            orig = next((h['source'] for h in hoists if h['copy'] == src), src)
            hoists.append(dict(source=orig, copy=str(copy), block=m[3], signal=m[4], statement=stmt))
            Path(f'{out}.hoists.json').write_text(json.dumps(hoists, indent=1) + '\n')
    raise RuntimeError(f'{top}: too many use-before-declaration hoists')


def _elaborate(yosys, files, top, params, defines, work, tag, out, lib_files=()):
    dflags = ' '.join(f'-D{d}' for d in defines)
    # hard memory macros: interface only here; their port clocks come from their own elaboration
    script = [f'read_verilog -sv -lib {dflags} {f}' for f in lib_files]
    script += [f'read_verilog -sv -defer {dflags} {f}' for f in files]
    chp = ' '.join(f'-chparam {k} {v}' for k, v in sorted(params.items()))
    script += [f'hierarchy -check -top {top} {chp}', 'proc', 'flatten', 'opt_clean', 'memory -nomap', 'opt_clean',
               f'write_json {out}.tmp']
    ys = work / f'{top}_{tag}.ys'
    ys.write_text('\n'.join(script) + '\n')
    log = work / f'{top}_{tag}.log'
    r = subprocess.run([str(yosys), '-q', '-l', str(log), '-s', str(ys)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    if r.returncode:
        tail = log.read_text(errors='replace').splitlines()[-6:] if log.exists() else []
        raise RuntimeError(f'yosys elaboration of {top} failed: ' + ' | '.join(tail))
    os.replace(f'{out}.tmp', out)
    return json.loads(out.read_text())


def macro_model(mod):
    """Hard memory macro: its own TT Liberty (next to the model) gives each pin's clock; the
    behavioural model only fixes widths. A pin with arcs to two clocks refuses; a pin with none
    (the clock itself, static repair inputs) is not a synchronous endpoint."""
    lib = Path(mod.path).with_name(f'{mod.name}_tt.lib')
    if not lib.exists():
        raise ValueError(f'{mod.name}: hard macro without TT Liberty {lib}')
    cells = dict(groups(lib.read_text(), 'cell'))
    if mod.name not in cells:
        raise ValueError(f'{lib}: no cell {mod.name}')
    env = mod.env()
    model = {}
    for kind in ('pin', 'bus'):
        for pin, body in groups(cells[mod.name], kind):
            if pin not in mod.ports:
                continue
            clocks = set()
            for _, arc in groups(body, 'timing'):
                if re.search(r'timing_type\s*:\s*"?(?:setup_|hold_|recovery_|removal_|rising_edge|falling_edge)', arc):
                    clocks.update(re.findall(r'related_pin\s*:\s*"([^";]+)"', arc))
            direction = mod.ports[pin][0]
            if not clocks:
                # the clock pin itself, or an untimed (static repair/config) pin: no synchronous region
                continue
            if len(clocks) != 1:
                raise ValueError(f'{mod.name}/{pin}: Liberty arcs to {sorted(clocks)}')
            ck = clocks.pop()
            for i in range(mod.width(pin, env)):
                model[pin, i] = dict(dir=direction, keys={frozenset({(ck, 0)})}, thru=False)
    return model


def port_clocks(netlist, top, clock_ports, macros=None):
    """{(rtl_port, bit): {clock key}} plus diagnostics. A clock key is a frozenset of (clock_port, bit)
    top input bits in the sequential cell's clock cone; frozenset() = no module clock port reaches it."""
    mod = netlist['modules'][top]
    ports = {p: d for p, d in mod['ports'].items()}
    in_bits, out_bits = {}, {}
    for p, d in ports.items():
        for i, b in enumerate(d['bits']):
            if not isinstance(b, int):
                continue
            if d['direction'] == 'input':
                in_bits.setdefault(b, []).append((p, i))
            elif d['direction'] == 'output':
                out_bits.setdefault(b, []).append((p, i))
            else:
                raise ValueError(f'{top}/{p}: inout port has no synchronous direction')
    fwd, bwd = defaultdict(set), defaultdict(set)
    sinks, sources = defaultdict(set), defaultdict(set)   # bit -> {clock bit id}
    blackbox = defaultdict(int)

    def edge(a, y):
        if isinstance(a, int) and isinstance(y, int):
            fwd[a].add(y)
            bwd[y].add(a)

    for name, c in mod['cells'].items():
        t, conn, dirs = c['type'], c['connections'], c.get('port_directions', {})
        if t in SEQ_CLK:
            ck = conn[SEQ_CLK[t]][0]
            for pn, bl in conn.items():
                if pn in (SEQ_CLK[t], SEQ_OUT):
                    continue
                for b in bl:
                    if isinstance(b, int):
                        sinks[b].add(ck)
            for b in conn[SEQ_OUT]:
                if isinstance(b, int):
                    sources[b].add(ck)
            continue
        if t == '$mem_v2':
            prm = c['parameters']
            width, abits = int(prm['WIDTH'], 2), int(prm['ABITS'], 2)
            nrd, nwr = int(prm['RD_PORTS'], 2), int(prm['WR_PORTS'], 2)
            rd_clk_en = prm['RD_CLK_ENABLE'][::-1] if nrd else ''
            wclks = [conn['WR_CLK'][k] for k in range(nwr)]
            for k in range(nwr):
                for pn, w in (('WR_EN', width), ('WR_ADDR', abits), ('WR_DATA', width)):
                    for b in conn[pn][k*w:(k+1)*w]:
                        if isinstance(b, int):
                            sinks[b].add(wclks[k])
            for k in range(nrd):
                data = conn['RD_DATA'][k*width:(k+1)*width]
                ctrl = conn['RD_ADDR'][k*abits:(k+1)*abits] + conn['RD_EN'][k:k+1] + \
                    conn['RD_ARST'][k:k+1] + conn['RD_SRST'][k:k+1]
                if rd_clk_en[k] == '1':
                    ck = conn['RD_CLK'][k]
                    for b in ctrl:
                        if isinstance(b, int):
                            sinks[b].add(ck)
                    for b in data:
                        if isinstance(b, int):
                            sources[b].add(ck)
                else:
                    # asynchronous read: data = stored words (write clocks) via the address mux
                    for y in data:
                        for a in conn['RD_ADDR'][k*abits:(k+1)*abits]:
                            edge(a, y)
                        for ck in wclks:
                            if isinstance(y, int):
                                sources[y].add(ck)
            continue
        if macros and t in macros:
            model = macros[t]
            for (mp, mi), v in model.items():
                b = conn.get(mp, [])[mi] if mi < len(conn.get(mp, [])) else None
                if not isinstance(b, int):
                    continue
                cks = [conn[kp][ki] for key in v['keys'] for kp, ki in key]
                (sinks if v['dir'] == 'input' else sources)[b].update(cks)
                if v['dir'] == 'output' and v['thru']:
                    for (ip, ii), iv in model.items():
                        if iv['dir'] == 'input' and ii < len(conn.get(ip, [])):
                            edge(conn[ip][ii], b)
            continue
        if not t.startswith('$'):
            blackbox[t] += 1
        ins = {p: conn[p] for p, d in dirs.items() if d == 'input'}
        outs = {p: conn[p] for p, d in dirs.items() if d == 'output'}
        if t.startswith('$') and t in ('$ff', '$sr', '$fsm', '$mem', '$memrd', '$memwr', '$memrd_v2', '$memwr_v2',
                                       '$memwr_v2', '$meminit', '$meminit_v2', '$print', '$check', '$assert',
                                       '$assume', '$cover', '$live', '$fair'):
            if t in ('$print', '$check', '$assert', '$assume', '$cover', '$live', '$fair', '$meminit', '$meminit_v2'):
                continue
            raise ValueError(f'{top}: unsupported sequential cell {t} ({name})')
        Y = outs.get('Y')
        if t in BITWISE1 and Y is not None and set(ins) == {'A'}:
            A = ins['A']
            for i, y in enumerate(Y):
                for a in ([A[i]] if i < len(A) else A):
                    edge(a, y)
        elif t in BITWISE2 and Y is not None and set(ins) == {'A', 'B'}:
            for i, y in enumerate(Y):
                for P in (ins['A'], ins['B']):
                    for a in ([P[i]] if i < len(P) else P):
                        edge(a, y)
        elif t == '$mux' and Y is not None:
            for i, y in enumerate(Y):
                edge(ins['A'][i], y)
                edge(ins['B'][i], y)
                for s in ins['S']:
                    edge(s, y)
        elif t == '$pmux' and Y is not None:
            w = len(Y)
            for i, y in enumerate(Y):
                edge(ins['A'][i], y)
                for k in range(len(ins['B']) // w):
                    edge(ins['B'][k*w+i], y)
                for s in ins['S']:
                    edge(s, y)
        else:
            for P in ins.values():
                for a in P:
                    for Q in outs.values():
                        for y in Q:
                            edge(a, y)

    # clock cone of every sequential clock bit -> its clock-port input bits
    key_of = {}
    derived = 0
    for ck in {c for s in list(sinks.values()) + list(sources.values()) for c in s}:
        if not isinstance(ck, int):
            key_of[ck] = frozenset()
            continue
        seen, todo, hit = {ck}, [ck], set()
        while todo:
            b = todo.pop()
            if b in in_bits:
                # any module input in the clock cone: a die clock port, or an RTL clock arriving on a
                # data-named die port (reported; never mapped to a die clock root)
                hit.update(in_bits[b])
            for a in bwd.get(b, ()):
                if a not in seen:
                    seen.add(a)
                    todo.append(a)
        derived += not hit
        key_of[ck] = frozenset(hit)

    def flood(seed, graph):
        reach = defaultdict(set)
        by_key = defaultdict(set)
        for b, cks in seed.items():
            for ck in cks:
                by_key[key_of[ck]].add(b)
        for key, start in by_key.items():
            todo = list(start)
            for b in start:
                reach[b].add(key)
            while todo:
                b = todo.pop()
                for a in graph.get(b, ()):
                    if key not in reach[a]:
                        reach[a].add(key)
                        todo.append(a)
        return reach

    reach_in = flood(sinks, bwd)        # bit -> keys of sequential inputs it reaches forward
    reach_out = flood(sources, fwd)     # bit -> keys of sequential outputs reaching it
    # combinational input -> output feedthrough
    thru = set()
    todo = list(in_bits)
    seen = set(todo)
    while todo:
        b = todo.pop()
        if b in out_bits:
            thru.add(b)
        for y in fwd.get(b, ()):
            if y not in seen:
                seen.add(y)
                todo.append(y)
    result = {}
    for b, names in in_bits.items():
        for pb in names:
            if any(pb in k for k in key_of.values()):
                result[pb] = dict(dir='input', keys=set(), thru=False, rtl_clock=True)
            elif pb[0] not in clock_ports:
                result[pb] = dict(dir='input', keys=reach_in.get(b, set()), thru=False)
    for b, names in out_bits.items():
        for pb in names:
            result[pb] = dict(dir='output', keys=reach_out.get(b, set()), thru=b in thru)
    rtl_clock_inputs = sorted({f'{p}[{i}]' for k in key_of.values() for p, i in k if p not in clock_ports})
    stats = dict(cells=len(mod['cells']), seq_clock_nets=len(key_of), unclocked_seq_clock_nets=derived,
                 rtl_clock_inputs_on_data_ports=rtl_clock_inputs, blackbox_cells=dict(blackbox))
    return result, stats


def build(case, records, root, libs, work, yosys, only=None):
    root = Path(root).resolve()
    bound = json.loads((records / 'bound_netlist.json').read_text())
    bind = json.loads((records / 'port_bind_v2.json').read_text())
    die_sha = hashlib.sha256((case / 'die.v').read_bytes()).hexdigest()
    if bound['die_sha256'] != die_sha:
        raise ValueError('strict binder describes another die netlist')
    if bind['verdict'] != 'PASS':
        raise ValueError('frame pin roots need a passing exact strict bind')
    related, _ = clock_pins(libs) if libs else ({}, {})
    insts = {}
    for mst, n, cs, widths in die_instances(case / 'die.v'):
        insts[n] = (mst, cs, widths)
    roots = defaultdict(set)
    for n, (mst, cs, widths) in insts.items():
        r = {v.strip() for p, v in cs.items() if v.strip().startswith('n_clk_') and not p.startswith('pll')}
        if len(r) > 1:
            roots[mst].add(n)
    targets = sorted(m for m in roots if not m.startswith(('qkd_landsh', 'qkd_rlysh_')) and (not only or m in only))
    # RTL index exactly as the binder resolved it
    cc = bind.get('child_closure', {})
    if cc.get('ambiguous_children'):
        raise ValueError(f"binder child closure is ambiguous: {sorted(cc['ambiguous_children'])[:6]}")
    variants = cc.get('variant_children', {})
    rtl_roots = [str(root / r) if not Path(r).is_absolute() else r for r in bind['rtl_roots']]
    prefer = list(bind['rtl_files']) + sorted({v['chosen'] for v in variants.values()})
    defines = {d.partition('=')[0]: d.partition('=')[2] for d in bind.get('defines', [])}
    idx, _amb = DPB.rtl_index(rtl_roots, bind['rtl_files'], defines, prefer)
    wanted = {n for m in targets for n, (mst, _, _) in insts.items() if mst == m}
    bound_inst, bwidths = bound_instances(bind['die_v'], wanted)
    pin_roots, report = {}, dict(schema='opentallas.kv_frame_pin_roots_report.v1', die_sha256=die_sha,
                                 masters={})
    for mst in targets:
        ent = bound['masters'][mst]
        module = ent['module']
        sel = bind['masters'][module]
        psets = list(sel.get('param_sets') or {'{}': 0})
        if len(psets) != 1:
            raise ValueError(f'{mst}: {len(psets)} parameter sets; one elaboration per set is not implemented')
        params = json.loads(psets[0])
        top = idx.get(module)
        if top is None or Path(top.path).resolve() != (root / sel['rtl']).resolve() and \
                Path(top.path).resolve() != Path(sel['rtl']).resolve():
            raise ValueError(f'{mst}: {module} resolves to {top and top.path}, binder chose {sel["rtl"]}')
        files, seen, todo, macro_mods = [], set(), [module], set()
        while todo:
            name = todo.pop()
            if name in seen:
                continue
            seen.add(name)
            mod = idx.get(name)
            if mod is None:
                raise ValueError(f'{mst}: unresolved child {name}')
            if name in variants and Path(mod.path).resolve() != Path(variants[name]['chosen']).resolve():
                raise ValueError(f'{mst}: child {name} resolves to {mod.path}, binder chose {variants[name]["chosen"]}')
            if name != module and DPB._macro_rank(mod.path) is not None:
                macro_mods.add(name)
                continue
            if mod.path not in files:
                files.append(mod.path)
            todo += sorted(mod.children(idx) - seen)
        # every module defined in the read files must be the selected definition (no silent redefinition)
        for f in files:
            for m in DPB.parse_modules(DPB.preprocess(DPB.strip_comments(Path(f).read_text(errors='replace')),
                                                      dict(defines)), f):
                if m.name in seen and Path(idx[m.name].path).resolve() != Path(f).resolve():
                    raise ValueError(f'{mst}: {m.name} defined in {f} and selected from {idx[m.name].path}')
        my = [n for n, (m, _, _) in insts.items() if m == mst]
        clock_ports = set()
        for n in my:
            if n not in bound_inst:
                raise ValueError(f'{n}: missing from die_bound.v')
            bmod, bcs = bound_inst[n]
            if bmod != module:
                raise ValueError(f'{n}: die_bound.v binds {bmod}, record says {module}')
            for rp, expr in bcs.items():
                if any(b and CLOCK_NET.match(b) for b in bits(expr, bwidths)):
                    clock_ports.add(rp)
        macros = {mm: macro_model(idx[mm]) for mm in sorted(macro_mods)}
        lib_files = []
        for mm in sorted(macro_mods):
            # interface-only view: the behavioural array would be expanded to registers even under -lib
            bb = Path(idx[mm].path).with_name(f'{mm}_bb.v')
            if not bb.exists():
                raise ValueError(f'{mm}: hard macro without interface view {bb}')
            lib_files.append(str(bb))
        net, ypath, hoists = elaborate(yosys, files, module, params, sorted(bind.get('defines', [])), work, lib_files)
        ytop = module if module in net['modules'] else next(
            (k for k in net['modules'] if k.startswith(f'$paramod') and k.endswith(f'\\{module}')), None)
        if ytop is None or ytop not in net['modules']:
            raise ValueError(f'{mst}: elaborated top {module} not found in {ypath}')
        pc, stats = port_clocks(net, ytop, clock_ports, macros)
        stats['macro_models'] = sorted(macros)
        bad = [t for t in stats['blackbox_cells'] if t not in macros]
        if bad:
            raise ValueError(f'{mst}: unelaborated cells {bad[:6]}')
        mrep = dict(module=module, source=top.path, params=params, files=len(files), elaboration=str(ypath),
                    use_before_declaration_hoists=hoists,
                    clock_ports=sorted(clock_ports), stats=stats, instances=len(my),
                    rtl_bits=dict(total=len(pc), single=0, none=0, multi=0, feedthrough=0),
                    die_bits=dict(mapped=0, none=0, multi=0, liberty=0), ambiguous_ports={}, none_ports={})
        for pb, v in pc.items():
            k = len(v['keys'])
            mrep['rtl_bits']['single' if k == 1 else 'none' if k == 0 else 'multi'] += 1
            mrep['rtl_bits']['feedthrough'] += v['thru']
        for n in my:
            _, cs, widths = insts[n]
            _, bcs = bound_inst[n]
            on_net = defaultdict(list)
            cknet = {}
            for rp, expr in bcs.items():
                for i, b in enumerate(bits(expr, bwidths)):
                    if b is None:
                        continue
                    on_net[b].append((rp, i))
                    if rp in clock_ports:
                        cknet[rp, i] = b
            for dp, expr in cs.items():
                dbits = bits(expr, widths)
                per = []
                for i, b in enumerate(dbits):
                    if b is None or b.startswith(('n_clk_', 'n_fck_')):
                        per.append(('skip', None))
                        continue
                    if (mst, f'{dp}[{i}]') in related or (mst, dp) in related:
                        # Liberty clock arcs stay authoritative in the exporter
                        per.append(('liberty', None))
                        mrep['die_bits']['liberty'] += 1
                        continue
                    nets, why = set(), []
                    for pb in on_net.get(b, []):
                        v = pc.get(pb)
                        if v is None:
                            continue
                        for key in v['keys']:
                            kn = {cknet.get(x) for x in key}
                            if None in kn or not kn:
                                bad = sorted(f'{x[0]}[{x[1]}]' for x in key if (x[0], x[1]) not in cknet)
                                why.append(f'{pb[0]}[{pb[1]}]:unmapped clock ' + ','.join(bad[:3]))
                            nets |= {x for x in kn if x}
                        if v.get('rtl_clock'):
                            why.append(f'{pb[0]}[{pb[1]}]:RTL clock input on a data die port')
                        elif not v['keys']:
                            why.append(f'{pb[0]}[{pb[1]}]:no sequential cell' + (' (feedthrough)' if v['thru'] else ''))
                    odd = [w for w in why if 'unmapped' in w or 'RTL clock' in w]
                    if len(nets) == 1 and not odd:
                        per.append(('ok', next(iter(nets))))
                        mrep['die_bits']['mapped'] += 1
                    elif nets:
                        per.append(('multi', sorted(nets)))
                        mrep['die_bits']['multi'] += 1
                        mrep['ambiguous_ports'].setdefault(dp, sorted(nets) + odd[:2])
                    else:
                        per.append(('none', why[:2]))
                        mrep['die_bits']['none'] += 1
                        mrep['none_ports'].setdefault(dp, why[:2])
                oks = [x for x in per if x[0] == 'ok']
                if not oks:
                    continue
                if len(oks) == len(dbits) and len({x[1] for x in oks}) == 1:
                    pin_roots[f'{n}/{dp}'] = oks[0][1]
                else:
                    for i, (st, v) in enumerate(per):
                        if st == 'ok':
                            pin_roots[f'{n}/{dp}[{i}]'] = v
        # keep the report short: port names only for a representative instance of the master
        report['masters'][mst] = mrep
    report['pin_roots'] = len(pin_roots)
    return pin_roots, report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case', type=Path, required=True, help='case_kv directory (die.v)')
    ap.add_argument('--records', type=Path, required=True, help='port_bind_v2 record directory')
    ap.add_argument('--root', type=Path, required=True, help='source worktree the binder indexed')
    ap.add_argument('--libs', type=Path, help='bound TT Liberty directory (masters with clock arcs are skipped)')
    ap.add_argument('--work', type=Path, required=True, help='elaboration scratch directory')
    ap.add_argument('--out', type=Path, required=True, help='pin-roots JSON for kv_gen_safety.py --pin-roots')
    ap.add_argument('--report', type=Path, help='report JSON (default <out>.report.json)')
    ap.add_argument('--yosys', type=Path, default=PINNED_YOSYS)
    ap.add_argument('--master', action='append', help='restrict to these die masters')
    a = ap.parse_args()
    a.out.unlink(missing_ok=True)
    pin_roots, report = build(a.case, a.records, a.root, a.libs, a.work, a.yosys, set(a.master or []))
    a.out.write_text(json.dumps(pin_roots, indent=0, sort_keys=True) + '\n')
    (a.report or Path(str(a.out) + '.report.json')).write_text(json.dumps(report, indent=1) + '\n')
    for m, r in report['masters'].items():
        print(f"KV_FRAME_PIN_ROOTS {m} module={r['module']} inst={r['instances']} rtl_bits={r['rtl_bits']} "
              f"die_bits={r['die_bits']} ambiguous={sorted(r['ambiguous_ports'])[:8]} none={sorted(r['none_ports'])[:8]}")
    print(f"KV_FRAME_PIN_ROOTS keys={len(pin_roots)}")


if __name__ == '__main__':
    main()
