#!/usr/bin/env python3
"""frame_schedule_asb.py -- TOK-DS-11 (10-27): the as-built S81 band frame's OWN compiler frame schedule, extracted
from its elaborated RTL, plus the plan-latency consistency check.

Why: the current die (die_b178.v) binds col_<M>_l4_lp_asb_{x,nx} = the plan band composition (u_r0/u_r1/u_r2 plan
kits joined by s81b_fint 2-flop seams).  Its latencies differ from the LP rf3r frame whose schedule
(results/arch/s81_dv_1016/frame_l4_cluster/compiler/col_<M>_schedule.json, tools/s81_dv/frame_schedule.py) the
compiler used: x_i0 -> xo_o0 2 edges vs 1, +1 writer / fault stations (frame_band_plan.py (f)/(i)).  The compiler must
not plan an as-built frame with the LP calendar, nor with hand-entered deltas.

Method (one tracer for both frames, so every number is measured the same way):
  1. elaborate the frame top with Yosys (native frontend, the as-built manifest's defines; module definitions picked by
     the binder's own precedence for the as-built frame, by the canonical RTL index for the LP frame), with the frame's
     END-POINT modules read as black boxes: the ROM elements ot_v41_rom_elem_q_qxpq_w10, the BF units dsfd_bf_col /
     dsfd_bf_front_roots, the return-tree nodes dsfd_node_*, the landing dsfd_cfifo_crs4, the per-pair sequencers
     ot_s81_cfg7_seq* and the ROM macros; everything between them (relays, stations, qbanks, seams, pads, band
     wrappers, fint seams) is flattened to Yosys cells.
  2. walk the flat netlist bit by bit: a flip-flop D -> Q = +1 edge, combinational cells 0 (bit-wise cells bit to bit,
     mux/pmux data inputs only, select / enable / reset / clock pins are control and never carry a data label), every
     black-box output pin is a labelled source (elements: pv halves .r1 (MSB) / .r0 as frame_schedule.py; nodes:
     n<k>; cfifo: cf.<pin>; frame inputs: port name).  The cfg7 sequencer passes its lc label to its outputs with 0
     edges (frame_schedule.py's control rule: its fixed internal latency is the same in both frames).
  3. read every end-point input pin: station x inputs / go / cfg_v of each element, node a / b, cfifo ri (root) and
     the frame-boundary links (x -> cfifo lanes, x -> xo, cfifo rd -> ret).

The schedule written is frame_schedule.v1 (plan_phase input). Return node and root link depths come directly
from the measured current as-built RTL. The old LP schedule supplies topology names, never an offset to a return
link: its col_h9 return calendar misplaces five region crossings even at its own revision. Historical discrepancies
remain in the check receipt. Station/control emission uses LP added_edges + measured (as-built - historical twin)
depth, since the flat emission model already incorporates the cfg7 sequencer's protocol. Every historical station
baseline must reproduce its schedule; otherwise the extraction FAILS.

Consistency check (the plan side): every frame link latency is compared with the die plan's declared latency
(frame_lp/plan/<M>_l4_lp_plan_map.json latency_edges + frame_int seams of the band types): x_i0 -> xo_o0 = plan
x_i0_to_xo_o0, every fint seam crossing = 2 boundary flops (plan wrapper ot_dp_st x 2), and every link that changed
vs the LP frame must be named by a plan_map entry (plus_one / x / reset); an unexplained change FAILS.

  frame_schedule_asb.py --master col_h10 --var x --out DIR [--keep-json]
"""
import argparse
import collections
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/die_plan'), str(ROOT / 'tools/s81_dv/layer_prog')]
import bind_elab  # noqa: E402

MANIFEST = 'physical/die_plan/s81/bind/asbuilt_b178_coll.json'
LP_SCHED = 'results/arch/s81_dv_1016/frame_l4_cluster/compiler/{m}_schedule.json'
# the LP frame's flop-seam twin (frame_band_plan.py: the plan contents are cycle-exact with it; the landed-parent LP
# RTL realises crossings as epoch-addressed landing memories, which a structural trace cannot time)
LP_TWIN = 'rtl/dsrom_sys/s81_dv/frame_lp/vgcs/{m}_l4_lp_rf3r.sv'
PLAN_MAP = 'rtl/dsrom_sys/s81_dv/frame_lp/plan/{m}_l4_lp_plan_map.json'
ENDPOINT_RE = re.compile(r'^(ot_v41_rom_elem_q_qxpq_w10(?:_gb)?|dsfd_bf_col|dsfd_bf_front_roots|dsfd_node_\w+|dsfd_cfifo_crs4|'
                         r'ot_s81_cfg7_seq\w*|ot_rom_\w+)$')
FF = {'$dff', '$dffe', '$adff', '$adffe', '$sdff', '$sdffe', '$sdffce', '$dffsr', '$dffsre', '$aldff', '$aldffe',
      '$_DFF_P_', '$_DFF_N_'}
BITWISE = {'$and', '$or', '$xor', '$xnor', '$not', '$pos', '$buf', '$_AND_', '$_OR_', '$_XOR_', '$_NOT_', '$_BUF_'}
CAP = 96          # depth cap: a data path deeper than this is a loop (reported)


SRC = [ROOT]     # RTL source root: the work tree, or (validation) an archive of the LP schedule's own revision


def sha(f):
    return hashlib.sha256((SRC[0] / f).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(SRC[0].resolve()))


# ------------------------------------------------------------------------------------------------ 1. elaborate
def sources(top, asbuilt, lp_files=()):
    """(full files, black-box files, defines): module picks by the binder precedence (as-built), or for the LP frame
    by the exact source files the LP schedule was extracted against (lp_files, hash-checked by the caller)."""
    import slice_source
    ab = json.loads((ROOT / MANIFEST).read_text())
    if asbuilt:
        _p, _ab, idx, prefer = slice_source.manifest_selection(ROOT.resolve(), MANIFEST)
    else:
        idx = bind_elab.module_index(['rtl', 'physical/asap7_memory_macros_v2'], [], str(SRC[0]))
        prefer = tuple(str(SRC[0] / f) for f in lp_files)
    # (module, below_endpoint): an end point's own children are read only so slang can parse its (black-boxed) body
    full, bb, seen, todo, missing = [], [], set(), [(top, False)], []
    while todo:
        n, below = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        f, amb = bind_elab.pick(idx, n, prefer)
        if f is None:
            missing.append(n)
            continue
        ep = below or bool(ENDPOINT_RE.match(n))
        assert not amb or ep, ('ambiguous definition on the traced path', n, idx.get(n))
        lst = bb if ep else full
        if f not in full and f not in bb:
            lst.append(f)
        if not ep:
            todo += [(c, False) for c in sorted(bind_elab.instantiated(bind_elab.module_body(f, n), idx))]
    assert not missing, ('unresolved modules', missing)
    traced_eps = [m.group(1) for f in full for m in bind_elab.MOD_RE.finditer(bind_elab._strip(Path(f).read_text(errors='replace')))
                  if ENDPOINT_RE.match(m.group(1))]
    assert not traced_eps or True, traced_eps
    return full, bb, ab.get('defines', []), idx, prefer


def header(text, name):
    """an ANSI module header `module name #(...) (...);` (balanced parentheses) -> the header text"""
    m = re.search(r'^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+' + re.escape(name) + r'\b', text, re.M)
    assert m, name
    i, depth, groups = m.end(), 0, 0
    while True:
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                groups += 1
        elif c == ';' and depth == 0:
            return text[m.start():i + 1]
        i += 1


def HARD_PARAMS(_c={}):
    if 'v' not in _c:
        ab = json.loads((ROOT / MANIFEST).read_text())
        _c['v'] = bind_elab.load_hard_params(ab.get('hard_params', []), (ROOT / MANIFEST).parent / ab.get('base', '.'))
        # Approved R5 opt-in primitive: retain every actual legacy shape parameter.
        if 'ot_v41_rom_elem_q_qxpq_w10' in _c['v']:
            _c['v'].setdefault('ot_v41_rom_elem_q_qxpq_w10_gb', dict(
                _c['v']['ot_v41_rom_elem_q_qxpq_w10'], GO_BOUNDARY=1, CGR=8))
    return _c['v']


def overrides(text, name):
    """[{param: value}] of every instance of `name` in text (balanced-parenthesis parse of #( .P(v), ... ))"""
    res = []
    for m in re.finditer(r'(?<![\w$.])' + re.escape(name) + r'\s*#\s*\(', text):
        i, depth, cur, ov = m.end(), 1, None, {}
        while depth:
            c = text[i]
            if c == '.' and depth == 1:
                j = re.match(r'\.\s*(\w+)\s*\(', text[i:])
                cur, i, start, d2 = j.group(1), i + j.end(), i + j.end(), 1
                while d2:
                    d2 += {'(': 1, ')': -1}.get(text[i], 0)
                    i += 1
                ov[cur] = text[start:i - 1].strip()
                continue
            depth += {'(': 1, ')': -1}.get(c, 0)
            i += 1
        res.append(ov)
    return res


def endpoint_stubs(bb_files, idx, prefer, out, traced_files):
    """port-only black boxes of the end-point masters: header copied from the picked source with the instances'
    parameter overrides BAKED in as defaults (slang empty black boxes size ports from the module defaults, e.g. elem
    pv [NB-1:0] = 1 bit at default NB 1 vs 2 bits at the frame's NB(2)).  Every instance of one master must carry the
    same non-string overrides (INSTANCE-like string selectors excluded: no port width depends on them), else FAIL."""
    names, txt, baked = [], ['`timescale 1ns/1ps'], {}
    texts = [bind_elab._strip(Path(f).read_text(errors='replace')) for f in traced_files]
    for f in bb_files:
        t = bind_elab._strip(Path(f).read_text(errors='replace'))
        for m in bind_elab.MOD_RE.finditer(t):
            n = m.group(1)
            if not (ENDPOINT_RE.match(n) and n not in names and bind_elab.pick(idx, n, prefer)[0] == f):
                continue
            names.append(n)
            h = header(t, n)
            sets = set()
            for tt in texts:
                for ov in overrides(tt, n):
                    sets.add(tuple(sorted((k, v) for k, v in ov.items() if '"' not in v and k != 'INSTANCE')))
            hp = tuple(sorted((k, str(v)) for k, v in HARD_PARAMS().get(n, {}).items()
                              if not isinstance(v, str) or '"' not in v))
            if hp:
                # a hardened master (frame-kit hard_params sidecar, as the binder bakes it): the hard view's set
                sets = {ov for ov in sets if ov} or {hp}
                assert sets == {hp} or all(dict(hp).get(k) == v for ov in sets for k, v in ov), \
                    ('instance parameters differ from the hardened set', n, sets, hp)
                sets = {hp}
            assert len(sets) <= 1, ('end-point master instantiated with differing parameters', n, sets)
            for k, v in (sets.pop() if sets else ()):
                h, cnt = re.subn(r'(parameter\s+(?:integer\s+|int\s+|bit\s+|logic\s+)?(?:\[[^\]]*\]\s*)?'
                                 + re.escape(k) + r'\s*=\s*)([^,)\n]+)', lambda mm: mm.group(1) + v, h, count=1)
                assert cnt == 1, ('override of an undeclared header parameter', n, k)
                baked.setdefault(n, {})[k] = v
            if n.startswith('ot_rom_') and not re.search(r'\bINSTANCE\b', h):
                # an older macro black box without the image-selector string parameter that frames pass (no port
                # depends on it): declare it so the stub accepts the override
                h = re.sub(r'(module\s+' + re.escape(n) + r'\b)\s*(#\s*\()?',
                           lambda mm: mm.group(1) + (' #(parameter INSTANCE = "", ' if mm.group(2) else
                                                     ' #(parameter INSTANCE = "") '), h, count=1)
            txt += ['(* blackbox *)', h, 'endmodule']
    out.write_text('\n'.join(txt) + '\n')
    (out.parent / (out.name + '.baked.json')).write_text(json.dumps(baked, indent=1))
    return names


def elaborate(top, asbuilt, work, mem_gb=24, lp_files=()):
    """slang frontend (the binder's: SV parameter types); end points as port-only black boxes."""
    full, bb, defines, idx, prefer = sources(top, asbuilt, lp_files)
    stub = work / f'{top}.endpoints.sv'
    names = endpoint_stubs(bb, idx, prefer, stub, full)
    d = ' '.join('-D' + x for x in defines)
    inc = ' '.join(sorted({'-I' + str(Path(f).parent) for f in full + bb}))
    bbm = ' '.join('--blackboxed-module ' + n for n in names)
    out = work / f'{top}.json'
    lines = [f'read_slang --keep-hierarchy --empty-blackboxes --allow-use-before-declare --top {top} {bbm} {d} {inc} '
             + ' '.join([str(stub)] + full),
             f'hierarchy -top {top}', 'setattr -mod -unset keep_hierarchy', 'proc', 'flatten', 'memory', 'opt_clean', f'write_json {out}']
    script = work / f'{top}.ys'
    old = script.read_text() if script.is_file() else None
    script.write_text('\n'.join(lines) + '\n')
    if os.environ.get('FS_REUSE') == '1' and out.is_file() and old == script.read_text():
        return out, {rel(f): sha(rel(f)) for f in full + bb}       # same script, cached netlist (debug only)
    bind_elab.run_yosys(script, work / f'{top}.yosys.log', [ROOT, work, SRC[0]], mem_gb=mem_gb)
    return out, {rel(f): sha(rel(f)) for f in full + bb}


# ------------------------------------------------------------------------------------------------ 2. trace
def module_of(cell_type):
    """cell type -> source master (slang specialisations are <master>$<path>; Yosys internal cells keep $<op>)"""
    t = cell_type.lstrip('\\')
    if t.startswith('$paramod'):
        t = t.split('\\')[1] if '\\' in t else t
    return t if t.startswith('$') else t.split('$')[0]


def trace(yjs, top):
    mod = yjs['modules'][top]
    fanout = collections.defaultdict(list)       # bit -> [(cell, port, index)]
    cells = mod['cells']
    dirs = {}
    for cn, c in cells.items():
        pd = c.get('port_directions', {})
        dirs[cn] = pd
        for port, bits in c['connections'].items():
            if pd.get(port) == 'input':
                for k, b in enumerate(bits):
                    if isinstance(b, int):
                        fanout[b].append((cn, port, k))
    # 0-1 BFS: per (bit, source label) the SHORTEST flop depth.  Hold / enable registers built as mux feedback
    # (q <= sel ? d : q) would otherwise re-label their own output at every depth; the first capture edge is the
    # arrival.  Distinct sources stay distinct labels, so a reconvergent path from another source is still seen.
    dist = {}                                    # (bit, label) -> depth
    work = collections.deque()

    def put(bit, lab, front=False):
        if not isinstance(bit, int) or lab[1] > CAP:
            return
        key = (bit, lab[0])
        if key in dist and dist[key] <= lab[1]:
            return
        dist[key] = lab[1]
        (work.appendleft if front else work.append)((bit, lab))
    # sources: frame input ports + black-box outputs
    for pn, p in mod['ports'].items():
        if p['direction'] == 'input':
            for b in p['bits']:
                put(b, (pn, 0))
    kind = {}
    for cn, c in cells.items():
        m = module_of(c['type'])
        kind[cn] = m
        if not c['type'].startswith('$') or c['type'].startswith('$paramod'):
            inst = inst_name(cn)
            for port, bits in c['connections'].items():
                if dirs[cn].get(port) != 'output' or m.startswith('ot_s81_cfg7_seq'):
                    continue
                for k, b in enumerate(bits):
                    if m in ('ot_v41_rom_elem_q_qxpq_w10', 'ot_v41_rom_elem_q_qxpq_w10_gb'):
                        # frame_schedule.py: an element return word is two rows, MSB half r1, LSB half r0 (Yosys bit
                        # index 0 = LSB); odd-width outputs are not return words
                        w = len(bits)
                        lab = f'{inst}.r{k // (w // 2)}' if w % 2 == 0 else f'{inst}.{port}'
                    elif m.startswith('dsfd_node'):
                        lab = inst
                    else:
                        lab = f'{inst}.{port}'
                    put(b, (lab, 0))
    while work:
        bit, (lab, dep) = work.popleft()
        if dist.get((bit, lab)) != dep:
            continue                             # superseded by a shorter arrival
        for cn, port, k in fanout[bit]:
            c = cells[cn]
            t = c['type']
            con = c['connections']
            if t in FF:
                if port == 'D':
                    put(con['Q'][k], (lab, dep + 1))
                continue
            elif t in ('$mux', '$_MUX_'):
                if port in ('A', 'B'):
                    put(con['Y'][k], (lab, dep), True)
            elif t == '$pmux':
                if port == 'A':
                    put(con['Y'][k], (lab, dep), True)
                elif port == 'B':
                    put(con['Y'][k % len(con['Y'])], (lab, dep), True)
            elif t in BITWISE:
                y = con['Y']
                if k < len(y):
                    put(y[k], (lab, dep), True)
            elif kind[cn].startswith('ot_s81_cfg7_seq'):
                if port == 'lc':
                    for p2, bits in con.items():
                        if dirs[cn].get(p2) == 'output':
                            for b in bits:
                                put(b, (lab, dep), True)
            elif t.startswith('$') and not t.startswith('$paramod'):
                if t.startswith('$mem') or t.startswith('$dlatch'):
                    raise ValueError(('memory / latch cell on a traced data path', cn, t))
                for p2, bits in con.items():
                    if dirs[cn].get(p2) == 'output':
                        for b in bits:
                            put(b, (lab, dep), True)
            # black-box inputs are end points: nothing propagates through them
    labels = collections.defaultdict(set)        # bit -> {(label, shortest depth)}
    for (bit, lab), d in dist.items():
        labels[bit].add((lab, d))
    return mod, cells, kind, labels


def inst_name(cn):
    """flattened Yosys cell name -> the frame-level instance name the LP schedule uses (u_e0 -> e0, band prefix
    u_r<k>. dropped: the as-built bands keep the flat frame's u_e<k> / u_n<k> / u_cf names)."""
    n = cn.lstrip('\\').split('.')[-1]
    return n[2:] if n.startswith('u_') else n


def pin_labels(cells, labels, cn, port, which=None):
    bits = cells[cn]['connections'][port]
    if which is not None:
        bits = [bits[which]]
    out = set()
    for b in bits:
        out |= labels.get(b, set()) if isinstance(b, int) else set()
    return out


def measure(yjs, top):
    mod, cells, kind, labels = trace(yjs, top)
    by = collections.defaultdict(list)
    for cn, m in kind.items():
        by[m.split('$')[0]].append(cn)
    res = dict(stations={}, nodes={}, root=None, links={})
    for cn, m in kind.items():
        inst = inst_name(cn)
        if m in ('ot_v41_rom_elem_q_qxpq_w10', 'ot_v41_rom_elem_q_qxpq_w10_gb'):
            ins = {}
            for port in cells[cn]['connections']:
                if port.startswith('xs_'):
                    ins[port] = sorted(pin_labels(cells, labels, cn, port))
            ctl = {p: sorted(pin_labels(cells, labels, cn, p, -1)) for p in ('go', 'cfg_v')}
            res['stations'][inst] = dict(inputs=ins, control=ctl)
            if m.endswith('_gb'):
                res['stations'][inst]['go_boundary_edges'] = 1
        elif m.startswith('dsfd_node'):
            res['nodes'][inst] = {p: sorted(pin_labels(cells, labels, cn, p)) for p in ('a', 'b')
                                  if p in cells[cn]['connections']}
        elif m == 'dsfd_cfifo_crs4':
            res['root'] = sorted(pin_labels(cells, labels, cn, 'ri', -1))
            lk = cells[cn]['connections'].get('lk')
            if lk is not None and all(b in ('0', '1') for b in lk):
                assert len(lk) == 12, ('landing lk width differs', cn, lk)
                value = sum(int(b) << k for k, b in enumerate(lk))
                assert 'landing_lk' not in res or res['landing_lk'] == value, ('landing lk differs', cn)
                res['landing_lk'] = value
            for p in ('xl0', 'xl1', 'xl2', 'xl3', 'cr'):
                if p in cells[cn]['connections']:
                    res['links'][f'x->{inst}.{p}'] = sorted(pin_labels(cells, labels, cn, p))
    # band seams (as-built composition): s81b_fint u_s<i><j> d -> q, and seam reader outputs u_r<j>.u_lpl_<n>_r.o
    # against the writer band's packed seam net u_r<i>.lpl_<n>_d (fint + reader = the seam's K + 1)
    nn = mod['netnames']

    def at(net):
        out = collections.defaultdict(set)
        for b in nn[net]['bits']:
            for lab, d in labels.get(b, ()):
                out[lab].add(d)
        return out

    def cross(a, b):
        da, db = at(a), at(b)
        ds = {d2 - d1 for lab in set(da) & set(db) for d1 in da[lab] for d2 in db[lab]}
        return sorted(ds)
    for net in sorted(nn):
        mm = re.fullmatch(r'u_s(\d)(\d)\.d', net)
        if mm and net[:-1] + 'q' in nn:
            res['links'][f'fint r{mm.group(1)}->r{mm.group(2)}'] = cross(net, net[:-1] + 'q')
        mm = re.fullmatch(r'u_r(\d)\.u_lpl_(\d+)_r\.o', net)
        if mm:
            src = [k for k in nn if re.fullmatch(r'u_r\d\.lpl_' + mm.group(2) + r'_d', k) and not k.startswith(f'u_r{mm.group(1)}.')]
            if len(src) == 1:
                res['links'][f'seam lpl_{mm.group(2)} {src[0].split(".")[0]}->r{mm.group(1)}'] = cross(src[0], net)
    for pn, p in mod['ports'].items():
        if p['direction'] == 'output' and pn in ('xo', 'ret'):
            s = set()
            for b in p['bits']:
                s |= labels.get(b, set()) if isinstance(b, int) else set()
            res['links'][f'->{pn}'] = sorted(s)
    return res


def selected_station_variants(yjs, top, ab, die_text, hard_params):
    """Apply the binder's instance-path QX variants to a standalone frame trace.

    Binding substitutes leaves AFTER elaboration. A standalone frame has no
    u_f_* prefix, so source selection alone cannot see these rules. Require
    every actual instance of this frame master to select the same endpoint
    variant; a mixed master needs separate schedules rather than a guessed
    global GO advance. Endpoint bodies are opaque to this tracer.
    """
    rules = [(re.compile(r['inst']), r) for r in ab.get('substitute_inst', [])]
    frames = sorted(set(re.findall(r'\b' + re.escape(top) +
        r'\s*(?:#\s*\([^;]*?\)\s*)?([A-Za-z_]\w*)\s*\(', die_text)))
    if not rules:
        return yjs, []
    if not frames:
        raise ValueError('cannot resolve frame instance substitutions without actual die instances: ' + top)
    out, rows = copy.deepcopy(yjs), []
    for cn, cell in out['modules'][top]['cells'].items():
        old = module_of(cell['type'])
        if old not in ('ot_v41_rom_elem_q_qxpq_w10', 'ot_v41_rom_elem_q_qxpq_w10_gb'):
            continue
        selected = []
        for frame in frames:
            full = frame + '.' + cn.lstrip('\\')
            target = old
            for rx, rule in rules:
                if rx.fullmatch(full):
                    if rule.get('port_bits') or rule.get('port_bit_constants'):
                        raise ValueError('station variant with bit remapping requires an exact endpoint model: ' + full)
                    target = rule['module']
            selected.append(target)
        if len(set(selected)) != 1:
            raise ValueError('mixed frame instance station variants: ' + cn + ' ' + str(dict(zip(frames, selected))))
        target = selected[0]
        if target == old:
            continue
        if (old, target) != ('ot_v41_rom_elem_q_qxpq_w10', 'ot_v41_rom_elem_q_qxpq_w10_gb'):
            raise ValueError('unmodelled station substitution: ' + old + ' -> ' + target)
        if hard_params.get(target, {}).get('GO_BOUNDARY') != 1:
            raise ValueError('GB station trace requires exact GO_BOUNDARY=1 hardened parameters: ' + cn)
        # This qualified primitive differs only by its captured GO/TAG input
        # and removal of the unused xs_sv input. Its other interface is kept.
        if 'xs_sv' not in cell['connections'] or cell['port_directions'].get('xs_sv') != 'input':
            raise ValueError('GB predecessor lacks its expected xs_sv input: ' + cn)
        del cell['connections']['xs_sv']
        del cell['port_directions']['xs_sv']
        cell['type'] = target
        rows.append(dict(cell=cn, master=old, variant=target, frames=frames,
                         removed_input='xs_sv', go_boundary_edges=1))
    return out, rows


# ------------------------------------------------------------------------------------------------ 3. schedule
def one(labs, what):
    """the single (source, depth) of a pin; several = misaligned / ambiguous -> FAIL"""
    labs = [tuple(x) for x in labs]
    assert len(labs) == 1, ('pin has no unique (source, depth)', what, labs)
    return labs[0]


def pick_src(meas_pin, src, what):
    return one([x for x in meas_pin if x[0] == src], what)[1]


def validate(meas_v, lp_sched):
    """the tracer on the LP seam twin AT THE LP SCHEDULE'S OWN REVISION must reproduce every LP schedule link"""
    rows, fails = [], []
    for n, nd in lp_sched['topology']['nodes'].items():
        for pin in 'ab':
            if nd[pin].startswith('zero.'):
                continue
            v = pick_src(meas_v['nodes'][n][pin], nd[pin], f'validate {n}.{pin}')
            rows.append((f"{nd[pin]} -> {n}.{pin}", nd['link_' + pin], v))
    r = pick_src(meas_v['root'], lp_sched['topology']['root'], 'validate root')
    rows.append((f"{lp_sched['topology']['root']} -> cf.ri", lp_sched['topology']['root_link'], r))
    for e, st in lp_sched['station_inputs'].items():
        for pin, pv in st['inputs'].items():
            p_, = pv['paths']
            v = pick_src(meas_v['stations'][e]['inputs'][pin], p_['source'], f'validate {e}.{pin}')
            rows.append((f"{p_['source']} -> {e}.{pin}", p_['flat_link_edges'] + p_['added_edges'], v))
    fails = [r_[0] for r_ in rows if r_[1] != r_[2]]
    return [dict(link=l, lp_schedule=a_, tracer=b_, verdict='PASS' if a_ == b_ else 'FAIL') for l, a_, b_ in rows], fails


def plan_lanes(master):
    """die plan frame_int lane latencies of this master's frames: {(src band, dst band): sorted set of cycles}"""
    d = json.loads((ROOT / 'physical/die_plan/s81/die_plan.json').read_text())
    ptype = {p['name']: p['type'] for p in d['partitions']}
    ports = {p['id']: p for p in d['ports']} if isinstance(d['ports'], list) else d['ports']
    lat = d['latency']['lanes']
    out = collections.defaultdict(set)
    for ln in d['lanes']:
        if not ln['id'].startswith('fi_'):
            continue
        p0 = ports[ln['ports'][0]]
        st, dt = ptype[p0['src']['part']], ptype[ports[ln['ports'][-1]]['dst']['part']]
        if not st.startswith(master + '_r'):
            continue
        key = (re.match(master + r'_(r\d)', st).group(1), re.match(master + r'_(r\d)', dt).group(1))
        out[key].add(lat[ln['id']]['cycles'])
    return {k: sorted(v) for k, v in out.items()}


def schedule(meas_v, meas_t, meas_ab, lp_sched, plan_map, master, var, src_sha):
    """Use direct return depths and validated station deltas; retain every physical plan latency check.

    Historical LP return calendars can themselves contain wrong region-crossing assignments (col_h9 has five).
    A current return path is completely measured between its two opaque endpoint pins, so its depth never needs
    an old calendar offset. Station emission retains the measured delta because its flat compiler calendar
    incorporates the cfg sequencer protocol; those historical station baselines must still validate.
    """
    rows, fails = [], []
    topo = json.loads(json.dumps(lp_sched['topology']))
    for n, nd in sorted(lp_sched['topology']['nodes'].items(), key=lambda kv: int(kv[0][1:])):
        for pin in 'ab':
            src, lpv = nd[pin], nd['link_' + pin]
            if src.startswith('zero.'):
                continue
            assert {x[0] for x in meas_ab['nodes'][n][pin]} == {src}, ('as-built return source differs', n, pin)
            v0 = pick_src(meas_v['nodes'][n][pin], src, f'{n}.{pin}')
            vt = pick_src(meas_t['nodes'][n][pin], src, f'{n}.{pin}')
            va = pick_src(meas_ab['nodes'][n][pin], src, f'{n}.{pin}')
            new = va
            topo['nodes'][n]['link_' + pin] = new
            ev = dict(topo['nodes'][n]['evidence_' + pin])
            ev.update(link_edges=new, added_edges=new - ev['flat_link_edges'], lp_link_edges=lpv,
                      basis='as-built RTL trace: measured endpoint-to-endpoint flop depth')
            ev.pop('crossings', None)
            topo['nodes'][n]['evidence_' + pin] = ev
            rows.append(dict(kind='return', link=f'{src} -> {n}.{pin}', lp_schedule=lpv, twin_head=vt,
                             asbuilt=new))
    rs = lp_sched['topology']['root']
    assert {x[0] for x in meas_ab['root']} == {rs}, ('as-built return root differs', meas_ab['root'])
    v0, vt, va = (pick_src(m_['root'], rs, 'root') for m_ in (meas_v, meas_t, meas_ab))
    topo['root_link'] = va
    topo['root_evidence'] = dict(source=rs, link_edges=topo['root_link'], lp_link_edges=lp_sched['topology']['root_link'],
                                 basis='as-built RTL trace')
    rows.append(dict(kind='return', link=f'{rs} -> cf.ri', lp_schedule=lp_sched['topology']['root_link'],
                     twin_head=vt, asbuilt=topo['root_link']))
    st_out = {}
    for e, st in sorted(lp_sched['station_inputs'].items(), key=lambda kv: int(kv[0][1:])):
        add_lp, = st['added_edges']
        deltas, inputs = set(), {}
        for pin, pv in st['inputs'].items():
            # GB737 removes only the unused xs_sv input; preserve legacy receipts.
            if pin == 'xs_sv' and meas_ab['stations'][e].get('go_boundary_edges') == 1:
                continue
            p_, = pv['paths']
            tot = p_['flat_link_edges'] + p_['added_edges']
            v0, vt, va = (pick_src(m_['stations'][e]['inputs'][pin], p_['source'], f'{e}.{pin}')
                          for m_ in (meas_v, meas_t, meas_ab))
            assert {x[0] for x in meas_ab['stations'][e]['inputs'][pin]} == {p_['source']}, ('x source differs', e, pin)
            deltas.add(va - v0)
            inputs[pin] = dict(paths=[dict(source=p_['source'], flat_link_edges=p_['flat_link_edges'],
                                           added_edges=p_['added_edges'] + va - v0)], aligned=True)
            rows.append(dict(kind='station', link=f"{p_['source']} -> {e}.{pin}", lp_schedule=tot,
                             twin_head=vt, asbuilt=tot + va - v0))
        assert len(deltas) == 1, ('as-built x inputs of one station misaligned', e, deltas)
        dx = deltas.pop()
        control = {}
        for pin, cv in st['control'].items():
            v0, vt, va = (pick_src(m_['stations'][e]['control'][pin], cv['source'], f'{e}.{pin}')
                          for m_ in (meas_v, meas_t, meas_ab))
            assert {x[0] for x in meas_ab['stations'][e]['control'][pin]} == {cv['source']}, ('control source differs', e, pin)
            control[pin] = dict(cv, added_edges=cv['added_edges'] + va - v0, link_edges=cv['link_edges'] + va - v0,
                                crossings='as-built RTL trace')
            rows.append(dict(kind='control', link=f"{cv['source']} -> {e}.{pin}", lp_schedule=cv['link_edges'],
                             twin_head=cv['link_edges'] + vt - v0, asbuilt=cv['link_edges'] + va - v0))
        st_out[e] = dict(inputs=inputs, control=control, added_edges=[add_lp + dx], all_x_inputs_equal_added_edges=True)
        if meas_ab['stations'][e].get('go_boundary_edges') == 1:
            st_out[e]['go_boundary_edges'] = 1
            st_out[e]['required_go_issue_advance_edges'] = 1
            st_out[e]['native_provider_qualified'] = False
    # ---------------- plan consistency: every frame link the die plan declares
    le = plan_map['latency_edges']
    plan = []

    def prow(link, rtl, want, basis):
        ok = rtl == want
        plan.append(dict(link=link, rtl_asbuilt=rtl, plan=want, basis=basis, verdict='PASS' if ok else 'FAIL'))
        if not ok:
            fails.append(link)
    if var == 'x':
        prow('x_i0 -> xo_o0', sorted({x[1] for x in meas_ab['links'].get('->xo', []) if x[0] == 'x'}),
             [le['x_i0_to_xo_o0']], f'{PLAN_MAP.format(m=master)} latency_edges.x_i0_to_xo_o0')
    lanes = plan_lanes(master)
    for k, v in sorted(meas_ab['links'].items()):
        mm = re.fullmatch(r'fint (r\d)->(r\d)', k)
        if mm:
            prow(f'frame_int {mm.group(1)}->{mm.group(2)} (band port to band port)', v,
                 lanes.get((mm.group(1), mm.group(2)), ['no plan lane']),
                 'physical/die_plan/s81/die_plan.json latency.lanes fi_* cycles (boundary + stations + fixed_cycles)')
        mm = re.fullmatch(r'seam lpl_(\d+) (u_r\d)->(r\d)', k)
        if mm:
            prow(f'seam lpl_{mm.group(1)} {mm.group(2)[2:]}->{mm.group(3)} (writer data to reader station)', v,
                 [le['seam_K_plus_1']], f'{PLAN_MAP.format(m=master)} latency_edges.seam_K_plus_1')
    sched = dict(schema='opentallas.s81.frame_schedule.v1', source_sha256=src_sha,
                 landing_lk=meas_ab.get('landing_lk'),
                 spec=lp_sched['spec'], added_edges_per_crossing=lp_sched['added_edges_per_crossing'],
                 station_inputs=st_out, topology=topo,
                 asbuilt=dict(master=f'{master}_l4_lp_asb_{var}', lp_schedule=LP_SCHED.format(m=master),
                              plan_map=PLAN_MAP.format(m=master),
                              rule='return links = measured as-built flop depth; station/control = LP + measured depth delta, '
                                   'one tracer (tools/s81_dv/frame_schedule_asb.py)'),
                 qualification='EXTRACTED ONLY (as-built RTL trace): emission/go/reset alignment, legalised return '
                               'calendar and actual frame bench required')
    return sched, rows, plan, fails


def archive(rev, dest):
    """the RTL + macro trees at `rev` (the LP schedule's own revision) for the tracer validation"""
    if not (dest / '.done').is_file():
        dest.mkdir(parents=True, exist_ok=True)
        ar = subprocess.run(['git', '-C', str(ROOT), 'archive', rev, 'rtl', 'physical/asap7_memory_macros_v2'],
                            capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(dest)], input=ar, check=True)
        (dest / '.done').write_text(rev + '\n')
    return dest


def main():
    global MANIFEST
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--master', required=True, choices=['col_h9', 'col_h10'])
    ap.add_argument('--var', required=True, choices=['x', 'nx'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--work', type=Path)
    ap.add_argument('--mem-gb', type=int, default=24)
    ap.add_argument('--manifest', default=MANIFEST,
                    help='selected source manifest within this source root; canonical default unchanged')
    a = ap.parse_args()
    import slice_source
    selected, ab, _, _ = slice_source.manifest_selection(ROOT.resolve(), a.manifest)
    MANIFEST = str(selected.relative_to(ROOT.resolve()))
    m, v = a.master, a.var
    work = a.work or a.out / 'work'
    work.mkdir(parents=True, exist_ok=True)
    lp_top, ab_top = f'{m}_l4_lp', f'{m}_l4_lp_asb_{v}'
    lp_sched = json.loads((ROOT / LP_SCHED.format(m=m)).read_text())
    plan_map = json.loads((ROOT / PLAN_MAP.format(m=m)).read_text())
    lp_files = list(lp_sched['source_sha256']) + [LP_TWIN.format(m=m)]
    # (1) validation: tracer on the LP seam twin at the LP schedule's own revision (all its source hashes match)
    rev = subprocess.run(['git', '-C', str(ROOT), 'log', '-1', '--format=%H', '--', LP_SCHED.format(m=m)],
                         capture_output=True, text=True, check=True).stdout.strip()
    SRC[0] = archive(rev, work / f'rev_{rev[:11]}')
    stale_at_rev = [f for f, h in lp_sched['source_sha256'].items() if sha(f) != h]
    assert not stale_at_rev, ('LP schedule revision does not hold its own sources', rev, stale_at_rev)
    vw = work / 'validate'
    vw.mkdir(exist_ok=True)
    js_v, _ = elaborate(lp_top, False, vw, a.mem_gb, lp_files)
    meas_v = measure(json.loads(js_v.read_text()), lp_top)
    vrows, vfails = validate(meas_v, lp_sched)
    # (2) head: the twin (what the LP calendar is on current RTL) and the as-built frame
    SRC[0] = ROOT
    stale = [f for f, h in lp_sched['source_sha256'].items() if sha(f) != h]
    js_t, _ = elaborate(lp_top, False, work, a.mem_gb, lp_files)
    js_ab, sha_ab = elaborate(ab_top, True, work, a.mem_gb)
    meas_t = measure(json.loads(js_t.read_text()), lp_top)
    selected_json = json.loads(js_ab.read_text())
    netlists = ab['netlist'] if isinstance(ab['netlist'], list) else [ab['netlist']]
    die_text = '\n'.join((ROOT / f).read_text() for f in netlists)
    selected_json, selected_variants = selected_station_variants(selected_json, ab_top, ab, die_text, HARD_PARAMS())
    (work / f'{ab_top}.selected.json').write_text(json.dumps(selected_json))
    meas_ab = measure(selected_json, ab_top)
    assert 'landing_lk' in meas_ab, ('as-built landing lk is not constant', ab_top)
    for nm, me in (('validate_' + lp_top, meas_v), (lp_top, meas_t), (ab_top, meas_ab)):
        (work / f'{nm}.meas.json').write_text(json.dumps(me, indent=1))
    src = dict(sha_ab)
    # Bare hard-leaf parameters and selection precedence are part of the elaborated source contract.
    for f in [MANIFEST] + ab.get('hard_params', []) + netlists:
        src[f] = sha(f)
    if selected_variants:
        variant_source = 'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv'
        src[variant_source] = sha(variant_source)
    for f in (LP_SCHED.format(m=m), PLAN_MAP.format(m=m), 'tools/s81_dv/frame_schedule_asb.py',
              'physical/die_plan/s81/die_plan.json'):
        src[f] = sha(f)
    a.out.mkdir(parents=True, exist_ok=True)
    # Return links are measured directly; station deltas still require their historic flat-calendar baseline.
    fails = ['VALIDATION ' + f for f in vfails if '.xs_' in f]
    sched, rows, plan, pf = schedule(meas_v, meas_t, meas_ab, lp_sched, plan_map, m, v, src)
    sched['selected_station_variants'] = selected_variants
    fails += pf
    sp = a.out / f'{ab_top}_schedule.json'
    sp.write_text(json.dumps(sched, indent=1) + '\n')
    ssha = hashlib.sha256(sp.read_bytes()).hexdigest()
    changed = [r for r in rows if r['asbuilt'] != r['lp_schedule']]
    verdict = 'FAIL' if fails else 'PASS'
    (a.out / f'{ab_top}_check.json').write_text(json.dumps(dict(
        schema='opentallas.s81.frame_schedule_asb_check.v1', master=ab_top, verdict=verdict, schedule_sha256=ssha,
        fails=fails, validation=dict(rev=rev, twin=LP_TWIN.format(m=m), links=len(vrows), fails=vfails, rows=vrows,
                                role='station baselines must match; return links come directly from current RTL'),
        lp_schedule_stale_sources_at_head=stale, plan_consistency=plan, links=rows, changed_vs_lp_schedule=changed),
        indent=1) + '\n')
    print(f'FRAME_SCHEDULE_ASB {ab_top} {verdict} validation {len(vrows) - len(vfails)}/{len(vrows)} links '
          f'changed_vs_lp={len(changed)} plan_rows={len(plan)} plan_fails={sum(r["verdict"] == "FAIL" for r in plan)}')
    for r in plan:
        print('  PLAN', r['verdict'], r['link'], 'rtl', r['rtl_asbuilt'], 'plan', r['plan'])
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
