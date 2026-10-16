#!/usr/bin/env python3
"""Q-KVSYS-NETLIST 2026-10-16: the KV/system die netlist BOUND to its real RTL, for the strict bit-level port bind
(tools/die_port_bind.py, schema opentallas.die_port_bind.v2: BIND / STUB / PORTS / WIDTHS / NETS undriven + multi-driven).

The KV die netlist (kv_die.py case -> kv_expand.py: die.v) instantiates DIE masters (qkd_*) on die-port BUNDLES; a die
master is real only through its kv_die.BINDINGS entry (die port = concatenation of RTL ports of one RTL module, LSB first;
a 'sliced' die port continues its base port after its bits, base first, the others in binding_order.sliced_order).  A
bundle mixes directions (data forward + credit / ready back in one die port), so a pin-only WRAPPER module per die master
cannot carry the per-bit direction (it would need inout ports, which the strict checker counts as a driver of last
resort and so would hide every undriven bit).  Instead this tool REWRITES each instance of a bound die master into an
instance of its BINDINGS RTL module (#(BINDINGS parameters)), connecting every RTL port to exactly the die-net bits of
its slice of the bundle.  Nothing is added, dropped, tied or re-ordered: the same nets, the same instance names, the
same bit positions; the bound netlist differs from die.v only in master names and port granularity.

  * die masters that are already RTL modules by name (relays from kv_relays.py, die-placed closed leaves from
    kv_expand.py, identity-port bindings) are kept as they are;
  * die-top constant nets (kv_expand straps / RTL literals of the expanded parents, kv_die host / write-lane straps,
    reset-region delay straps, chain terminators) are folded into the reading port's connection; every (module, port)
    that receives one is written to the strap list (class = the generator's net class) so the strict check records them
    as STRAPS and still fails any other constant;
  * 'classed' RTL inputs whose source is OFF CHIP (package POR pad, reference clock, package die-id strap) become top
    inputs of the bound netlist (pad_<port>): an off-chip signal is a driver, never a tie;
  * the analog hard macros with no RTL (HBM3E PHY per-PC, clock / forwarded bumps) get a port model whose per-port
    direction is the complement of the real RTL endpoints on the same nets (checked: a port touching both directions
    fails); pass them to the checker with --allow-model.

    kv_bound_netlist.py DIE_V --relay-rtl RUN/case_kv/qkd_kv_relays.sv --expanded RUN/expand.json --out-dir OUT
writes OUT/die_bound.v, OUT/kv_hard_models.sv, OUT/straps.json, OUT/bound_netlist.json (per master: bound module, die bits
vs RTL bits per bundle, unassigned bits, constants folded); then run tools/die_port_bind.py on OUT/die_bound.v
(kv_port_bind_v2.sh does both).
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import die_port_bind as PB  # noqa: E402
import kv_die as K  # noqa: E402
from binding_order import sliced_order  # noqa: E402

SCHEMA = 'opentallas.qwen_kv_bound_netlist.v1'
# analog hard macros / pad cells with no RTL: port models (directions derived from the real endpoints)
HARD_MODELS = ('qkd_hbm3e_phy_pc', 'qkd_ckbump', 'qkd_fwdbump')
# classed inputs driven from OFF the die (package pads / package straps)
OFF_CHIP = ('por_n', 'refclk', 'die_id')
# die-top constant net classes (die.v 'assign n_<net> = const') -> why the constant is a die strap
CONST_CLASSES = [
    (r'^head_\w+__g_(t|front)_\d+__u_\w+__tie\d+$', 'rtl_literal', 'RTL literal of the expanded head parent (kv_expand)'),
    (r'^ectl_\w+__u_[abc]__tie\d+$', 'kv_expand_strap', 'engine-control cfg strap {engine, stack} of the expanded qkd_ectl frame (kv_expand)'),
    (r'^ctrl_\w+__u_(pc|kc)\d*__tie\d+$', 'rtl_literal', 'RTL literal of the expanded controller strip parent (kv_expand)'),
    (r'^\w+__(hid|cfg)\d*$|^\w+__strap_\w+$', 'kv_expand_strap', 'classed strap of an expanded frame (head index / engine-stack cfg)'),
    (r'^hlpc_\w+$', 'host_strap', 'per-slice logical-PC strap (kv_die host_ties)'),
    (r'^wlane_\w+$', 'lane_strap', 'write-leaf lane strap (kv_die wq_straps)'),
    (r'^wtail_\w+$', 'chain_terminator', 'write-lane chain tail (kv_die)'),
    (r'^rdly_\w+$', 'reset_delay_strap', 'reset-region release delay dly = D - d_r (kv_die reset_region_calendar)'),
    (r'^ht\w+_(WS|WN|ES|EN)$', 'chain_terminator', 'HOST slice chain terminator (the source parent assigns 0)'),
]


def const_class(net):
    for rx, cls, why in CONST_CLASSES:
        if re.match(rx, net[2:] if net.startswith('n_') else net):
            return cls, why
    return 'unclassified', 'die-top constant with no generator class'


def bit_tokens(expr, nets):
    """LSB-first list of ('n', net, i) | ('c', v) | ('z',) for one die connection expression"""
    b = PB.expr_bits(expr, nets)
    if b is None:
        raise ValueError(f'unparsable die connection {expr!r}')
    out = []
    for t in reversed(b):
        if t[0] == 'CONST':
            out.append(('c', t[1]))
        elif t[0] == 'Z':
            out.append(('z',))
        elif t[0] == 'UNDECL':
            raise ValueError(f'undeclared die net {t[1]}')
        else:
            out.append(('n', t[0], t[1]))
    return out


def render(bits):
    """LSB-first token list -> Verilog expression (MSB first), consecutive bits of one net as a range"""
    if not bits:
        return ''
    parts = []                                   # MSB-first groups
    i = len(bits) - 1
    while i >= 0:
        t = bits[i]
        if t[0] == 'n':
            j = i
            while j - 1 >= 0 and bits[j - 1][0] == 'n' and bits[j - 1][1] == t[1] and bits[j - 1][2] == bits[j][2] - 1:
                j -= 1
            hi, lo = t[2], bits[j][2]
            parts.append(f'{t[1]}[{hi}]' if hi == lo else f'{t[1]}[{hi}:{lo}]')
            i = j - 1
        elif t[0] == 'c':
            parts.append(f"1'b{t[1]}")
            i -= 1
        else:
            parts.append("1'bz")
            i -= 1
    return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'


def relay_segments(text):
    """kv_relays.py relay masters with inout a / b (mixed-direction bundles) -> {master: [(lo, hi, 'f'|'r')]}, every bit
    exactly once (forward a -> flop -> b, reverse b -> flop -> a), parsed from the generated RTL itself"""
    out = {}
    for m in re.finditer(r'^module (\w+) \((.*?)^endmodule', text, re.M | re.S):
        if 'inout' not in m.group(2):
            continue
        w = int(re.search(r'inout\s+wire\s+\[(\d+):0\]\s+a\b', m.group(2)).group(1)) + 1
        seg = []
        for g in re.finditer(r'<= (a|b)\[(\d+):(\d+)\]; assign (a|b)\[(\d+):(\d+)\]', m.group(2)):
            src, hi, lo, dst, hi2, lo2 = g.groups()
            if (hi, lo) != (hi2, lo2) or src == dst:
                raise SystemExit(f'relay {m.group(1)}: unexpected stage {g.group(0)}')
            seg.append((int(lo), int(hi), 'f' if src == 'a' else 'r'))
        bits = sorted(i for lo, hi, _d in seg for i in range(lo, hi + 1))
        if bits != list(range(w)):
            raise SystemExit(f'relay {m.group(1)}: bits not covered exactly once by its stages')
        out[m.group(1)] = sorted(seg)
    return out


def relay_dir_module(name, seg):
    """the same flops as the kv_relays.py master, its a / b split into per-direction ports a_<lo> / b_<lo>"""
    P, B = [], []
    for lo, hi, d in seg:
        w = hi - lo + 1
        P += [f'    {"input " if d == "f" else "output"} wire [{w - 1}:0] a_{lo}',
              f'    {"output" if d == "f" else "input "} wire [{w - 1}:0] b_{lo}']
        src, dst = ('a', 'b') if d == 'f' else ('b', 'a')
        B.append(f'    reg [{w - 1}:0] s_{lo}; always @(posedge ck) s_{lo} <= {src}_{lo}; assign {dst}_{lo} = s_{lo};')
    return f'module {name}__dir (\n' + ',\n'.join(P + ['    input  wire ck']) + '\n);\n' + '\n'.join(B) + '\nendmodule'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('die_v')
    ap.add_argument('--relay-rtl', help='RUN/case_kv/qkd_kv_relays.sv (kv_relays.py): the qkd_rly_* masters')
    ap.add_argument('--expanded', help='RUN/expand.json (kv_expand.py): die-placed closed leaves, bound by name')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--top')
    a = ap.parse_args(argv)
    K._set_geometry(True)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    nets, tin, tout, insts = PB.parse_die(a.die_v, a.top)
    top = a.top or re.search(r'^\s*module\s+(\w+)', Path(a.die_v).read_text(), re.M).group(1)
    files = [str(ROOT / b['file']) for b in K.BINDINGS.values() if (ROOT / b['file']).exists()]
    files += [a.relay_rtl] if a.relay_rtl else []
    idx, _amb = PB.rtl_index(['rtl'], files, {}, files)
    exp = json.loads(Path(a.expanded).read_text())['leaves'] if a.expanded else {}
    rseg = relay_segments(Path(a.relay_rtl).read_text()) if a.relay_rtl else {}

    # 1. die-top constants (assign n_x[i] = c / assign n_x = W'..) -> folded bits
    const = {}
    const_nets = defaultdict(int)
    for mst, s, _p, _c in insts:
        if mst != '__assign__':
            continue
        m = re.fullmatch(r'assign\s+(\S+?)\s*=\s*(.+)', s.strip(), re.S)
        lhs, rhs = bit_tokens(m.group(1), nets), bit_tokens(m.group(2), nets)
        if len(lhs) != len(rhs) or any(t[0] != 'n' for t in lhs) or any(t[0] != 'c' for t in rhs):
            raise SystemExit(f'kv_bound_netlist: die-top assign is not a constant strap: {s[:200]}')
        for l_, r_ in zip(lhs, rhs):
            if (l_[1], l_[2]) in const:
                raise SystemExit(f'kv_bound_netlist: constant bit {l_[1]}[{l_[2]}] assigned twice')
            const[(l_[1], l_[2])] = r_[1]
            const_nets[l_[1]] += 1

    def fold(bits):
        return [('c', const[(t[1], t[2])], t[1]) if t[0] == 'n' and (t[1], t[2]) in const else t for t in bits]

    # 2. per instance: master -> (module, params, {rtl port: LSB-first bits})
    rep = {}
    rows = []                                    # (module, inst, params, {port: bits})
    hard = defaultdict(lambda: defaultdict(set))   # hard model master -> port -> {(net, i)}
    hard_w = defaultdict(dict)                     # hard model master -> port -> width (every instance the same)
    straps = defaultdict(lambda: defaultdict(int))   # (module, port) -> class -> bits
    off_chip = set()
    for mst, inst, params, cm in insts:
        if mst == '__assign__':
            continue
        conns = {p: fold(bit_tokens(e, nets)) for p, e in cm.items()}
        r = rep.setdefault(mst, dict(instances=0, how=None, module=None, bundles={}, unassigned_bits=0,
                                     classed_inputs={}, constants_folded=0))
        r['instances'] += 1
        r['constants_folded'] += sum(1 for bs in conns.values() for t in bs if t[0] == 'c' and len(t) == 3)
        if mst in HARD_MODELS:
            r.update(how='hard_model', module=mst)
            for p, bs in conns.items():
                if hard_w[mst].setdefault(p, len(bs)) != len(bs):
                    raise SystemExit(f'hard model {mst}.{p}: instances disagree on the width')
                for t in bs:
                    if t[0] == 'n':
                        hard[mst][p].add((t[1], t[2]))
            rows.append((mst, inst, params, conns))
            continue
        if mst in K.BINDINGS and not (mst.startswith('qkd_rly') or mst in exp):
            b = K.BINDINGS[mst]
            mod = idx.get(b['module'])
            if mod is None:
                r.update(how='unbound', module=b['module'])
                rows.append((mst, inst, params, conns))
                continue
            prm = dict((b.get('parameters') or {}), **params)
            env = mod.env(prm)
            sliced = b.get('sliced') or {}
            groups = defaultdict(list)
            for p in conns:
                groups[sliced.get(p, p)].append(p)
            rc = {}
            for base, members in groups.items():
                if base not in b['ports']:
                    r['bundles'][base] = dict(error='die port has no binding', die_ports=members)
                    continue
                bits = []
                for p in sliced_order(base, members):
                    bits += conns[p]
                rtl_bits = 0
                for rp in b['ports'][base]:
                    w = mod.width(rp, env)
                    if w is None:
                        raise SystemExit(f'{mst}: RTL width of {b["module"]}.{rp} unresolved')
                    rc[rp] = bits[rtl_bits:rtl_bits + w]
                    rtl_bits += w
                r['bundles'][base] = dict(die_ports=sliced_order(base, members), die_bits=len(bits), rtl_bits=rtl_bits,
                                          rtl_ports=b['ports'][base])
                if len(bits) > rtl_bits:
                    r['unassigned_bits'] += len(bits) - rtl_bits
            for cp, why in (b.get('classed') or {}).items():
                if cp in mod.ports and mod.ports[cp][0] == 'input':
                    r['classed_inputs'][cp] = why
                    if cp in OFF_CHIP:
                        rc[cp] = [('n', f'pad_{cp}', i) for i in range(mod.width(cp, env) or 1)]
                        off_chip.add((cp, mod.width(cp, env) or 1))
            r.update(how='bound' if b['module'] != mst or rc.keys() != conns.keys() else 'identity', module=b['module'],
                     file=b['file'], parameters=b.get('parameters') or {})
            rows.append((b['module'], inst, {k: str(v) for k, v in prm.items()}, rc))
            continue
        if mst in rseg:
            # mixed-direction relay: the same flops with per-direction ports (an inout would count as a driver)
            r.update(how='relay_dir_split', module=mst + '__dir')
            rc = {'ck': conns['ck']}
            for lo, hi, _d in rseg[mst]:
                rc[f'a_{lo}'] = conns['a'][lo:hi + 1]
                rc[f'b_{lo}'] = conns['b'][lo:hi + 1]
            rows.append((mst + '__dir', inst, params, rc))
            continue
        r.update(how='relay' if mst.startswith('qkd_rly') else 'expanded_leaf' if mst in exp else 'by_name', module=mst)
        rows.append((mst, inst, params, conns))

    # 3. directions of the real endpoints (for the hard models and the strap list)
    rd, dr = defaultdict(int), defaultdict(int)
    for mod_, inst, params, conns in rows:
        m_ = idx.get(mod_)
        if m_ is None:
            continue
        for p, bs in conns.items():
            d = m_.ports.get(p, (None,))[0]
            for t in bs:
                if t[0] == 'n':
                    (rd if d == 'input' else dr if d == 'output' else defaultdict(int))[(t[1], t[2])] += 1
                elif t[0] == 'c' and len(t) == 3 and d == 'input':
                    straps[(mod_, p)][const_class(t[2])[0]] += 1
    model_dirs = {}
    for mst, ports in hard.items():
        model_dirs[mst] = {}
        for p, bs in ports.items():
            # a bit some real RTL drives is a model INPUT; a bit real RTL only reads is a model OUTPUT
            ins = sum(1 for x in bs if dr.get(x))
            outs = sum(1 for x in bs if not dr.get(x) and rd.get(x))
            if ins and outs:
                raise SystemExit(f'hard model {mst}.{p}: {ins} bits driven and {outs} bits only read by real RTL')
            model_dirs[mst][p] = 'output' if outs else 'input'

    # 4. write the bound netlist, the hard models, the strap list, the record
    L = [f'// GENERATED by tools/qwen_kv_die/kv_bound_netlist.py from {a.die_v} (sha256 '
         f'{hashlib.sha256(Path(a.die_v).read_bytes()).hexdigest()[:16]}): every bound die master rewritten into its',
         '// kv_die.BINDINGS RTL module on the same die-net bits; die-top constants folded into the reading pins. Do not edit.',
         f'module {top} (' + ', '.join(f'pad_{p}' for p, w in sorted(off_chip)) + ');']
    L += [f'  input wire [{w - 1}:0] pad_{p};' for p, w in sorted(off_chip)]
    for n, (w, lo) in nets.items():
        L.append(f'  wire [{lo + w - 1}:{lo}] {n};')
    for mod_, inst, params, conns in rows:
        ps = (' #(' + ', '.join(f'.{k}({v})' for k, v in params.items()) + ')') if params else ''
        cs = ', '.join(f'.{p}({render(bs)})' for p, bs in conns.items())
        L.append(f'  {mod_}{ps} {inst} ({cs});')
    L.append('endmodule')
    (out / 'die_bound.v').write_text('\n'.join(L) + '\n')
    M = ['// GENERATED by tools/qwen_kv_die/kv_bound_netlist.py: PORT MODELS of the KV die analog hard macros / pad cells',
         '// (allowed models: port-bind --allow-model).  Per-port direction = the complement of the real RTL on its nets.']
    for mst, ports in sorted(hard.items()):
        decl = []
        for p, bs in sorted(ports.items()):
            w = hard_w[mst][p]
            decl.append(f'    {model_dirs[mst][p]} wire [{w - 1}:0] {p}')
        M.append(f'module {mst} (\n' + ',\n'.join(decl) + '\n);\nendmodule')
    (out / 'kv_hard_models.sv').write_text('\n'.join(M) + '\n')
    (out / 'kv_relays_dir.sv').write_text('// GENERATED by tools/qwen_kv_die/kv_bound_netlist.py from ' + str(a.relay_rtl) +
                                          ': the mixed-direction relay masters, same flops, per-direction ports.\n' +
                                          '\n'.join(relay_dir_module(k, v) for k, v in sorted(rseg.items())) + '\n')
    sl = sorted([m_, p] for (m_, p) in straps)
    (out / 'straps.json').write_text(json.dumps(dict(
        straps=sl, classes={f'{m_}:{p}': dict(c) for (m_, p), c in sorted(straps.items())},
        class_reasons={c: w for _r, c, w in CONST_CLASSES}), indent=1) + '\n')
    rec = dict(schema=SCHEMA, die_v=str(a.die_v), die_sha256=hashlib.sha256(Path(a.die_v).read_bytes()).hexdigest(),
               top=top, masters=rep, hard_model_dirs=model_dirs, off_chip_inputs=sorted(p for p, _ in off_chip),
               constant_bits=len(const), constant_nets_by_class={}, straps=len(sl))
    by = defaultdict(int)
    for n, c in const_nets.items():
        by[const_class(n)[0]] += c
    rec['constant_nets_by_class'] = dict(by)
    (out / 'bound_netlist.json').write_text(json.dumps(rec, indent=1) + '\n')
    bad = {k: v for k, v in rep.items() if v['how'] == 'unbound' or v['unassigned_bits']}
    print(f'kv_bound_netlist: {len(rows)} instances, {len(rep)} masters, {sum(1 for v in rep.values() if v["how"] == "bound")} '
          f'rewritten, {len(const)} constant bits folded ({dict(by)}), {len(sl)} strap ports, off-chip {sorted(off_chip)}, '
          f'problems {sorted(bad)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
