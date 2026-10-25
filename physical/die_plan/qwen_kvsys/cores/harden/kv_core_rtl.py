#!/usr/bin/env python3
"""KVG3-CORES 10-24: core RTL + split partition RTL for the PLANNED hard cores of the KV die plan (v3.8s).

    kv_core_rtl.py --plan die_plan.json --type kv3_hub_Eo --core astk_EN --kit-rtl ~/scratch/kv-g3/kit_rtl/g3
                   --kv41 ~/scratch/kv-g3/kv41/rtl --out DIR [--split]   (--core may repeat; --all-cores = every
                   planned core of the type except qkd_hr_* / reuse-closed views)
    kv_core_rtl.py --plan die_plan.json --type kv3_hub_Wi --core host__qkd_hr_cdc_host --hr-wrappers WDIR --out DIR
                   [--hr-filelist F] [--hr-keep-families]
                   (KV-CORES2 10-25, OPT-IN; without --hr-wrappers nothing changes): qkd_hr_* host-root cores of
                   kv3_hub_Wi from the HOST-CLUSTER WRAPPERS (tools/qwen_kv_die/host_cluster/gen_cluster.py, r2
                   partition: one clock port per family ck_core / ck_host / ck_ingest / ck_phy_fam).  BRIEFING 16a:
                   ck_core / ck_host / ck_ingest collapse onto ONE core pin `ck` (die clock), ck_phy_fam -> `ck_phy`
                   (the PHY side keeps its clock; the only async FIFO left is the PHY edge, qkd_hr_cdc_pc); every
                   member CDC whose two clocks collapse gets SAMECLK=1 (ot_qwen_die_cdc_ch, qkd_host_native_qm_debt:
                   same-clock register stage + buffer).  Writes DIR/<module>/<module>.sv (top <module> with the
                   collapsed clock face around <module>__fam = the wrapper body) + <module>_core.json (ports, clock
                   classes, SAMECLK edits, CDC-fork blockers, pins-file comparison vs the plan, lint).  r2 'direct'
                   children (phy_pad, core_rx, phy_adp: kit top = member module) are reported, no wrapper emitted.

For one plan type (its G3 kit RTL: <kit-rtl>/<type>/<type>_part_bound.sv, binder4 kv41) and one or more of its
hard_cores[] it writes
  DIR/<module>/<module>.sv          module <module>: ports = the pins-file bases (core_pins_v37p naming: member-leaf port
                                     bit whose net reaches anything outside the core; '<rel>__<port>' for multi-leaf
                                     cores, the leaf port for single-leaf cores), instantiating the member leaves exactly
                                     as bound (parameters, intra-core nets, constants);
  DIR/<module>/<module>_core.json   port map, pin classes, kv39-pins vs kv41-boundary mismatches, straps, consistency
                                     of the module over every plan instance (kv41 rtl/<type>_part*.sv);
  DIR/split/<type>/<type>_part_bound.sv  (--split) the bound partition with the member leaves of the cores replaced by
                                     one instance each of the core module (black box in the partition kit);
  DIR/split/<type>/equiv.json       lint (verilator) + flattened bit-level connectivity diff, original vs split+cores.

Pin classes (every pin of the pins file is a core port; nothing is dropped silently):
  in      the net is driven outside the core: the pin drives its own member-leaf bits (as the pins file groups them)
  clk     the partition clock net: ONE pin (the first clock pin of the pins file, or an added 'ck') drives every
          member clock bit; the other clock pins of the pins file stay ports but are unused inside (clk_unused) and are
          left unconnected in the split partition (one clock tree per core)
  out     the net is driven by a member leaf: the connected output (driver's pin, else the first pin on the net)
  out_alias   another pin of an internally driven net (e.g. a sibling leaf's input on the same net): output assigned
          from the net, left unconnected in the split partition (no multi-driver)
  strap   a bound constant (S_* parameter) that differs between instances of the module: core input, tied to the
          S_ parameter in the split partition (pin ADDED: not in the pins file)
  added   a kv41 boundary bit with no pins-file pin (kv39 -> kv41 drift, or clock / reset of the astk pins which
          post_v38h excluded): one added pin per net (placed by gen_core_kit_kv.py on free tracks; REPORTED)
  stale   a pins-file pin with no kv41 boundary bit: port kept (input unused, or output assigned from the internal
          net and left unconnected); REPORTED
"""
import argparse
import json
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))          # physical/die_plan/qwen_kvsys (rtlnet.py)
from rtlnet import Net, split_concat  # noqa: E402

CLK_PORTS = re.compile(r'^clk(_t\d+|_\w+)?$')        # partition clock ports (bound: clk, clk_clk_hbm; kit wrapper: clk_t<i>)
RST_LEAF = re.compile(r'^(rst_n|arst_n|\w*_rst_n|rn)$')
DECLR = re.compile(r'^\s*(input|output|inout|wire|logic|reg)\s+(?:wire\s+|logic\s+)?(\[\d+:\d+\]\s*)?([A-Za-z_]\w*)')
PARAM = re.compile(r'^\s*parameter\s+(\[\d+:\d+\]\s*)?(S_\w+)\s*=\s*([^,]+?)\s*,?\s*$')


# ----------------------------------------------------------------------------------------------- plan / members
def members(t, hc):
    """(member plan insts, prefixes) of a hard core; prefixes None for a single-leaf core."""
    note = hc.get('note', '')
    m = re.match(r'(head_eighth|pv_pair|astk_core): ([^;(]+)', note)
    insts = [c['inst'] for c in t['contents']]
    if m:
        pre = [x.strip() for x in m.group(2).split('+')]
        return [i for i in insts if any(i == p or i.startswith(p + '__') for p in pre)], pre
    return [i for i in insts if i == hc['inst']], None


def rel(inst, pre, hc):
    if pre is None:
        return None
    if hc['module'] == 'kv3_pv_pair':
        k = pre.index(next(p for p in pre if inst == p or inst.startswith(p + '__')))
        return f's{k}'
    if hc['module'].startswith('kv3_astk_'):
        return re.sub(r'^astk_[EW][NS]__', '', inst).replace('__', '_')
    return re.sub(r'^head\d__', '', inst).replace('__', '_')


def bname(inst):
    return 'u_' + inst.replace('__', '_')


def canon(ri, mine, pre, hc):
    """instance name of a member inside the core: independent of the core's slot (head0/head1, kvpc1..15, pv pairs)."""
    r = rel(mine[ri], pre, hc)
    return f'u_{r}' if r else 'u_leaf'


def load_pins(path):
    pins = json.load(open(path))['pins']
    out = OrderedDict()
    for p in pins:
        m = re.match(r'^(.*)\[(\d+)\]$', p['name'])
        b, i = (m.group(1), int(m.group(2))) if m else (p['name'], None)
        out[(b, i)] = p
    return out


# ----------------------------------------------------------------------------------------------- netlist helpers
class Bound:
    """bound partition netlist + leaf port directions."""

    def __init__(self, path, ports_json):
        self.path = Path(path)
        self.text = self.path.read_text()
        self.net = Net(path)
        self.g = self.net.graph()
        self.ranged = set()
        self.params = OrderedDict()
        for ln in self.text.splitlines():
            m = PARAM.match(ln)
            if m:
                self.params[m.group(2)] = ((m.group(1) or '').strip(), m.group(3).strip())
                continue
            m = DECLR.match(ln)
            if m and m.group(2):
                self.ranged.add(m.group(3))
        self.mods = ports_json

    def pdir(self, mod, port):
        m = self.mods.get(mod)
        if m is None:
            raise KeyError(f'no port list for module {mod}')
        return m['ports'][port]['direction']

    def bittext(self, nb):
        n, i = nb
        return f'{n}[{i}]' if n in self.ranged or self.net.width.get(n, 1) > 1 else n

    def driver(self, root, exclude_core=None):
        """[(inst, port, bit) driving root] ('<port>', name, bit) for partition inputs."""
        out = []
        for e in self.g.get(root, []):
            if e[0] == '<port>':
                if self.net.ports.get(e[1]) == 'input':
                    out.append(e)
            else:
                mod = self.net.insts[e[0]][0]
                if self.pdir(mod, e[1]) == 'output':
                    out.append(e)
        return out


ANSI_PORT = re.compile(r'\b(input|output|inout)\b\s+(?:wire|logic|reg|signed|\s|\[[^\]]*\])*([A-Za-z_]\w*)')


def _regex_ports(path):
    """fallback port parser (ANSI headers): module -> {'ports': {name: {'direction'}}}."""
    txt = re.sub(r'//.*', '', Path(path).read_text())
    txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
    out = {}
    for m in re.finditer(r'\bmodule\s+(\w+)\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\);', txt, re.S):
        ports = {}
        for pm in re.finditer(r'(input|output|inout)\b([^,;]*?)([A-Za-z_]\w*)\s*(?=,|$)', m.group(3), re.S):
            ports[pm.group(3)] = dict(direction=pm.group(1))
        # continuation names after a direction (input wire [3:0] a, b)
        cur = None
        for item in m.group(3).split(','):
            mm = re.match(r'\s*(input|output|inout)\b', item)
            if mm:
                cur = mm.group(1)
            nm = re.findall(r'([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*$', item.strip())
            if cur and nm and nm[-1] not in ports:
                ports[nm[-1]] = dict(direction=cur)
        out[m.group(1)] = dict(ports=ports)
    return out


def port_dirs(files, defines=('SYNTHESIS',)):
    """module -> {'ports': {name: {'direction'}}} for every module of the files (yosys -lib, no elaboration; a file
    yosys -lib rejects (e.g. $fatal in a module body) falls back to an ANSI-header regex parse)."""
    import tempfile
    d = ' '.join(f'-D{x}' for x in defines)
    with tempfile.TemporaryDirectory() as td:
        j = Path(td) / 'p.json'
        cmd = f"read_verilog -sv -lib {d} {' '.join(str(f) for f in files)}; write_json {j}"
        r = subprocess.run(['yosys', '-q', '-p', cmd], capture_output=True, text=True)
        if not r.returncode:
            return json.loads(j.read_text())['modules']
        mods = {}
        for f in files:
            r = subprocess.run(['yosys', '-q', '-p', f"read_verilog -sv -lib {d} {f}; write_json {j}"],
                               capture_output=True, text=True)
            if not r.returncode:
                mods.update(json.loads(j.read_text())['modules'])
            else:
                for k, v in _regex_ports(f).items():
                    mods.setdefault(k, v)
        return mods


def const_bits(tok, params):
    """MSB-first constant bits of a token: '0'/'1'/'x' or ('S', name, i) for an S_ parameter (None if unknown)."""
    t = tok.strip()
    m = re.match(r'^(S_\w+)\[(\d+)\]$', t)
    if m:
        return [('S', m.group(1), int(m.group(2)))]
    m = re.match(r'^(S_\w+)(?:\[(\d+):(\d+)\])?$', t)
    if m:
        rng, _ = params.get(m.group(1), ('', None))
        mm = re.match(r'\[(\d+):(\d+)\]', rng or '')
        w = int(mm.group(1)) - int(mm.group(2)) + 1 if mm else 1
        hi, lo = (int(m.group(2)), int(m.group(3))) if m.group(2) else (w - 1, 0)
        return [('S', m.group(1), i) for i in range(hi, lo - 1, -1)]
    m = re.match(r"^(\d+)'([bdh])([0-9a-fA-FxXzZ_]+)$", t)
    if m:
        w, b, v = int(m.group(1)), m.group(2), m.group(3).replace('_', '')
        if b == 'b':
            s = v
        elif b == 'h':
            s = ''.join(format(int(c, 16), '04b') if c not in 'xXzZ' else 'xxxx' for c in v)
        else:
            s = format(int(v), 'b')
        s = s.rjust(w, '0')[-w:]
        return list(s)
    m = re.match(r'^(\d+)$', t)
    if m:
        return list(format(int(t), '032b'))
    return None


def ranges(bits):
    """[(name, i)] MSB-first -> compact concat text items."""
    out = []
    for b in bits:
        if out and isinstance(b, tuple) and isinstance(out[-1], list) and out[-1][0] == b[0] and out[-1][2] - 1 == b[1]:
            out[-1][2] = b[1]
        elif isinstance(b, tuple):
            out.append([b[0], b[1], b[1]])
        else:
            out.append(b)
    return out


def concat_text(items, scalar=lambda n: False):
    txt = []
    for it in items:
        if isinstance(it, list):
            n, hi, lo = it
            if scalar(n):
                txt.append(n)
            elif hi == lo:
                txt.append(f'{n}[{hi}]')
            else:
                txt.append(f'{n}[{hi}:{lo}]')
        else:
            txt.append(it)
    return txt[0] if len(txt) == 1 else '{' + ', '.join(txt) + '}'


# ----------------------------------------------------------------------------------------------- core analysis
def analyse(B, t, hc):
    """per core: member leaf bits, boundary classification (kv41)."""
    ms, pre = members(t, hc)
    mine = {bname(i): i for i in ms}
    miss = [b for b in mine if b not in B.net.insts]
    if miss:
        raise SystemExit(f"{hc['inst']}: member leaves missing in {B.path.name}: {miss[:5]}")
    leafbits = OrderedDict()          # (ri, port, bit) -> dict(nb, root, base)
    for ri in sorted(mine, key=lambda r: canon(r, mine, pre, hc)):
        mod, pm = B.net.insts[ri]
        rn = rel(mine[ri], pre, hc)
        for p, e in pm.items():
            bs = B.net.bits(e)
            n = len(bs)
            for k, nb in enumerate(bs):
                if nb is None:
                    continue
                root = B.net.find(nb)
                ends = B.g.get(root, [])
                others = [x for x in ends if x[0] not in mine]
                leafbits[(ri, p, n - 1 - k)] = dict(nb=nb, root=root, base=f'{rn}__{p}' if rn else p,
                                                    boundary=bool(others), dir=B.pdir(mod, p),
                                                    clock=next((x[1] for x in ends if x[0] == '<port>' and CLK_PORTS.match(x[1])), None))
    return ms, pre, mine, leafbits


def s_tokens(B, mine):
    """S_ parameter references of the member leaves: [(ri, port, token)]."""
    out = []
    for ri in sorted(mine):
        _, pm = B.net.insts[ri]
        for p, e in pm.items():
            for tk in split_concat(e):
                if re.match(r'^\s*S_\w+', tk):
                    out.append((ri, p, tk.strip()))
    return out


def s_value(B, tok):
    m = re.match(r'^(S_\w+)', tok)
    return B.params.get(m.group(1), (None, None))[1]


def build_core(B, t, hc, pins_file, straps=()):
    """core port model.  Returns dict with ports (ordered), leaf rewiring and the report."""
    ms, pre, mine, lb = analyse(B, t, hc)
    pins = load_pins(pins_file)
    # pin (base, bit) -> leaf bits (kv41)
    by_pin = defaultdict(list)
    for k, v in lb.items():
        if v['boundary']:
            by_pin[(v['base'], k[2])].append(k)
    nets = defaultdict(list)               # root -> boundary leaf bits
    for k, v in lb.items():
        if v['boundary']:
            nets[v['root']].append(k)
    rep = dict(pins_file=str(pins_file), pins=len(pins), kv41_boundary_pins=len(by_pin),
               stale=[], added=[], clk_unused=[], out_alias=[], straps=[])
    pin_class = OrderedDict()               # (base, bit) -> class
    leaf_src = {}                           # (ri, port, bit) -> ('pin', base, bit) | ('net', root)
    out_assign = {}                         # (base, bit) -> root  (outputs)
    part_conn = {}                          # (base, bit) -> nb (partition-side bit) or None (unconnected)
    # clock: one primary pin
    # clocks: one primary pin per clock net (core clock 'clk', HBM clock 'clk_clk_hbm' of the kvs_pc cores, ...)
    clk_nets = OrderedDict()
    for v in lb.values():
        if v['clock']:
            clk_nets.setdefault(v['root'], v['clock'])
    primary = {}
    for root, cport in clk_nets.items():
        cp = [pk for pk in pins if any(lb[k]['root'] == root for k in by_pin.get(pk, []))]
        primary[root] = cp[0] if cp else (('ck' if cport == 'clk' else 'ck_' + cport.replace('clk_', '', 1)), None)
    rep['clock_nets'] = {cport: f'{primary[r][0]}' + (f'[{primary[r][1]}]' if primary[r][1] is not None else '')
                         for r, cport in clk_nets.items()}
    for root, ks in nets.items():
        drv = [k for k in ks if lb[k]['dir'] == 'output']
        inside = bool(drv) or any(e[0] in mine and B.pdir(B.net.insts[e[0]][0], e[1]) == 'output'
                                  for e in B.g.get(root, []))
        pks = list(OrderedDict.fromkeys((lb[k]['base'], k[2]) for k in ks))
        inpins = [pk for pk in pks if pk in pins]
        if lb[ks[0]]['clock']:
            for pk in pks:
                if pk in pins and pk != primary[root]:
                    pin_class[pk] = 'clk_unused'
                    part_conn[pk] = None
                    rep['clk_unused'].append(f'{pk[0]}[{pk[1]}]')
            pc = primary[root]
            pin_class[pc] = 'clk'
            if pc not in pins:
                rep['added'].append(dict(pin=pc[0], bit=pc[1], why='clock net: no clock pin in the pins file',
                                         leaf_bits=len(ks)))
            part_conn[pc] = lb[ks[0]]['nb']
            for k in ks:
                leaf_src[k] = ('pin',) + pc
            continue
        if inside:
            d0 = drv[0] if drv else None
            dpk = (lb[d0]['base'], d0[2]) if d0 else None
            if dpk and dpk in pins:
                conn = dpk
            elif inpins:
                conn = inpins[0]
            else:
                conn = dpk or pks[0]
                rep['added'].append(dict(pin=conn[0], bit=conn[1], why='kv41 boundary net (internal driver) has no pin',
                                         leaf_bits=len(ks)))
            for pk in [conn] + [p for p in inpins if p != conn]:
                if pk == conn:
                    pin_class[pk] = 'out'
                    part_conn[pk] = lb[d0]['nb'] if d0 else lb[by_pin[pk][0]]['nb']
                else:
                    pin_class[pk] = 'out_alias'
                    part_conn[pk] = None
                    rep['out_alias'].append(f'{pk[0]}[{pk[1]}]')
                out_assign[pk] = root
            for k in ks:
                leaf_src[k] = ('net', root)
        else:
            # driven outside: every pins-file pin drives its own leaf bits; leaf bits without a pin take the net's
            # first pin (or one added pin)
            first = inpins[0] if inpins else None
            if first is None:
                isrst = all(RST_LEAF.match(k[1]) for k in ks)
                first = ('rst_n', None) if isrst and ('rst_n', None) not in pin_class and not any(
                    b == 'rst_n' for b, _ in pins) else pks[0]
                rep['added'].append(dict(pin=first[0], bit=first[1], why='kv41 boundary net (outside driver) has no pin',
                                         leaf_bits=len(ks), reset=isrst))
            for pk in OrderedDict.fromkeys([first] + inpins):
                pin_class[pk] = 'in'
                part_conn[pk] = lb[(by_pin.get(pk) or ks)[0]]['nb']
            for k in ks:
                pk = (lb[k]['base'], k[2])
                leaf_src[k] = ('pin',) + (pk if pk in pin_class else first)
    # stale pins (pins file, no kv41 boundary bit)
    for pk in pins:
        if pk in pin_class:
            continue
        ks = [k for k, v in lb.items() if (v['base'], k[2]) == pk]
        if ks and (lb[ks[0]]['dir'] == 'output' or B.driver(lb[ks[0]]['root'])):
            root = lb[ks[0]]['root']
            drv_in = [e for e in B.driver(root) if e[0] in mine]
            if drv_in:
                pin_class[pk] = 'stale_out'
                out_assign[pk] = root
                part_conn[pk] = None
                rep['stale'].append(dict(pin=f'{pk[0]}[{pk[1]}]', kind='internal net now (output assigned, unconnected)'))
                continue
        pin_class[pk] = 'stale_in'
        part_conn[pk] = None
        rep['stale'].append(dict(pin=f'{pk[0]}[{pk[1]}]', kind='no kv41 leaf bit' if not ks else 'internal net now (input unused)'))
    # straps (S_ constants that differ across instances of the module)
    strap_map = {}
    for ri, p, tok in s_tokens(B, mine):
        name = re.match(r'^(S_\w+)', tok).group(1)
        key = (rel(mine[ri], pre, hc), p)
        if key in straps:
            cb = const_bits(tok, B.params)
            base = f'{key[0]}__{p}' if key[0] else p
            strap_map[(ri, p)] = (base, len(cb), tok)
            for i in range(len(cb)):
                pin_class[(base, len(cb) - 1 - i)] = 'strap'
                part_conn[(base, len(cb) - 1 - i)] = cb[i]
            rep['straps'].append(dict(pin=base, width=len(cb), param=name, value=s_value(B, tok)))
    # ports
    ports = OrderedDict()
    order = {}
    for (b, i) in pins:
        order.setdefault(b, len(order))
    for (b, i), c in sorted(pin_class.items(), key=lambda kv: (order.get(kv[0][0], 10 ** 6), kv[0][0],
                                                               -1 if kv[0][1] is None else kv[0][1])):
        ports.setdefault(b, {})[i] = c
    pdecl = OrderedDict()
    for b, bits in ports.items():
        idx = [i for i in bits if i is not None]
        cls = set(bits.values())
        dirn = 'output' if cls <= {'out', 'out_alias', 'stale_out'} else 'input'
        if cls & {'out', 'out_alias', 'stale_out'} and cls - {'out', 'out_alias', 'stale_out'}:
            raise SystemExit(f"{hc['inst']}: port {b} mixes directions {cls}")
        if not idx:
            pdecl[b] = dict(dir=dirn, hi=None, lo=None, gaps=[])
            continue
        hi, lo = max(idx), min(idx)
        gaps = [i for i in range(lo, hi + 1) if i not in bits]
        for i in gaps:            # a gap inside a pins-file range: extra port bit (unused input / tied-off output)
            pin_class[(b, i)] = 'gap_' + ('out' if dirn == 'output' else 'in')
            part_conn[(b, i)] = None
            rep.setdefault('gap_bits', []).append(f'{b}[{i}]')
        pdecl[b] = dict(dir=dirn, hi=hi, lo=lo, gaps=gaps)
    return dict(hc=hc, ms=ms, pre=pre, mine=mine, lb=lb, pins=pins, pin_class=pin_class, leaf_src=leaf_src,
                out_assign=out_assign, part_conn=part_conn, pdecl=pdecl, strap_map=strap_map, rep=rep)


def pn(b):
    """escape a port base for Verilog (bases are identifiers already)."""
    return b


def emit_core(B, M):
    """core module text.  Member instances are named by their place in the core (canon), internal nets n<k> in order of
    first use, so two slots of one module (head0/head1, kvpc1..15, the pv pairs) must give identical text (comments
    aside): structural identity check of the master."""
    hc = M['hc']
    mod = hc['module']
    mine, pre = M['mine'], M['pre']
    order = sorted(mine, key=lambda r: canon(r, mine, pre, hc))
    L = [f"// GENERATED by physical/die_plan/qwen_kvsys/cores/harden/kv_core_rtl.py (KVG3-CORES): planned hard core {mod}",
         f"// = member leaves of {hc['inst']} in {B.path.name} (binder4 kv41), ports = {Path(M['rep']['pins_file']).name}",
         "// (+ added / strap pins, see <module>_core.json).  Do not edit.",
         "`timescale 1ns/1ps", "`default_nettype none", f"module {mod} ("]
    pl = []
    for b, d in M['pdecl'].items():
        rng = f"[{d['hi']}:{d['lo']}] " if d['hi'] is not None else ''
        pl.append(f"    {d['dir']} wire {rng}{pn(b)}")
    L.append(',\n'.join(pl))
    L.append(');')
    # S_ parameters used by members (not straps): inlined as literal values (slot-independent text)
    sval = {}
    for ri in order:
        for p, e in B.net.insts[ri][1].items():
            if (ri, p) in M['strap_map']:
                continue
            for sn in re.findall(r'\bS_\w+', e):
                sval[sn] = B.params[sn]
    # internal nets, numbered in order of first use
    wid = OrderedDict()

    def wire(root):
        if root[0] not in wid:
            wid[root[0]] = [f'n{len(wid)}', 0]
        wid[root[0]][1] = max(wid[root[0]][1], root[1] + 1)
        return wid[root[0]][0]
    inst_txt = []
    for ri in order:
        mod_, pm = B.net.insts[ri]
        hdr = re.search(rf'^\s*{re.escape(mod_)}\s*(#\(.*?\))?\s+{re.escape(ri)}\s*\(', B.text, re.M)
        par = hdr.group(1) if hdr and hdr.group(1) else ''
        cn = canon(ri, mine, pre, hc)
        inst_txt.append(f"    // member {mine[ri]} ({ri})")
        lm = mod_ + '__leaf' if mod_ == mod else mod_      # the core keeps the plan name, the leaf is renamed
        inst_txt.append(f"    {lm} {par + ' ' if par else ''}{cn} (")
        conns = []
        for p, e in pm.items():
            if (ri, p) in M['strap_map']:
                conns.append(f"        .{p}({M['strap_map'][(ri, p)][0]})")
                continue
            items = []
            n = len(B.net.bits(e))
            pos = 0
            for tk in split_concat(e):
                tb = B.net.bits(tk)
                for j, nb in enumerate(tb):
                    k = (ri, p, n - 1 - (pos + j))
                    if nb is None:
                        continue
                    src = M['leaf_src'].get(k)
                    if src is None or src[0] == 'net':
                        r = M['lb'][k]['root']
                        tb[j] = (wire(r), r[1])
                    else:
                        _, b, i = src
                        tb[j] = (b, i) if i is not None else (b, 0)
                if all(x is None for x in tb):
                    items.append(None)      # token boundary marker for constants
                    t2 = tk.strip()
                    mm = re.match(r'^(S_\w+)(\[(\d+):(\d+)\])?$', t2)
                    if mm:       # S_ literal, slot independent
                        rng, val = sval[mm.group(1)]
                        cb = const_bits(t2, B.params)
                        bits = const_bits(val, {})
                        if bits is None:
                            raise SystemExit(f'cannot inline {t2} = {val}')
                        full = const_bits(mm.group(1), B.params)
                        sel = [bits[-1 - full_i[2]] if len(bits) > full_i[2] else '0' for full_i in cb]
                        t2 = f"{len(sel)}'b{''.join(sel)}"
                    items.append(t2)
                else:
                    assert all(x is not None for x in tb), (ri, p, tk)
                    items += tb
                pos += len(tb)
            flat = []
            for x in items:
                if x is None:
                    continue
                flat.append(x)
            sc = lambda nm: nm in M['pdecl'] and M['pdecl'][nm]['hi'] is None
            conns.append(f"        .{p}({concat_text(ranges(flat), sc)})")
        inst_txt.append(',\n'.join(conns))
        inst_txt.append("    );")
    asg = []
    for (b, i), c in M['pin_class'].items():
        if c == 'gap_out':
            asg.append(f"    assign {b}[{i}] = 1'b0;")
    for pk, r in sorted(M['out_assign'].items(), key=lambda kv: (list(M['pdecl']).index(kv[0][0]), kv[0][1] or 0)):
        b, i = pk
        lhs = f'{b}[{i}]' if M['pdecl'][b]['hi'] is not None else b
        asg.append(f"    assign {lhs} = {wire(r)}[{r[1]}];")
    for orig, (nm, w) in wid.items():
        L.append(f"    wire [{w - 1}:0] {nm};   // {orig}")
    L += asg + inst_txt
    L.append("endmodule")
    L.append("`default_nettype wire")
    M['canon'] = {canon(ri, mine, pre, hc): ri for ri in mine}
    return '\n'.join(L) + '\n'


def body_key(txt):
    """core text without comments / header: the structural identity key of a master."""
    return '\n'.join(re.sub(r'\s*//.*$', '', l) for l in txt.split('\n')[3:])


def inst_blocks(text, names):
    """line spans [a, b] (inclusive) of the instances named `names` (+ their '// as-built' comment line)."""
    lines = text.split('\n')
    spans = {}
    i = 0
    pat = re.compile(r'^\s*([A-Za-z_]\w*)\s*(?:#\(.*?\))?\s+([A-Za-z_]\w*)\s*\(')
    while i < len(lines):
        m = pat.match(lines[i])
        if m and m.group(2) in names and m.group(1) not in ('module',):
            a = i - 1 if i > 0 and lines[i - 1].strip().startswith('// as-built') else i
            j = i
            if not lines[i].rstrip().endswith(');'):
                while not lines[j].strip().startswith(');'):
                    j += 1
            spans[m.group(2)] = (a, j)
            i = j + 1
            continue
        i += 1
    return lines, spans


def emit_split(B, models, out_module=None):
    names = set()
    for M in models:
        names |= set(M['mine'])
    lines, spans = inst_blocks(B.text, names)
    miss = names - set(spans)
    if miss:
        raise SystemExit(f'split: instance blocks not found: {sorted(miss)[:5]}')
    drop = set()
    for a, b in spans.values():
        drop |= set(range(a, b + 1))
    end = max(i for i, l in enumerate(lines) if l.strip() == 'endmodule')
    out, extra_w = [], []
    body = []
    for M in models:
        hc = M['hc']
        nm = f"u_core_{hc['inst']}"
        body.append(f"    // KVG3-CORES: planned hard core {hc['inst']} ({hc['module']}) = {len(M['mine'])} member leaves")
        conns = []
        for b, d in M['pdecl'].items():
            if d['hi'] is None:
                c = M['part_conn'].get((b, None))
                conns.append(f"        .{b}({B.bittext(c) if isinstance(c, tuple) else ''})")
                continue
            bits = []
            nc = 0
            for i in range(d['hi'], d['lo'] - 1, -1):
                c = M['part_conn'].get((b, i))
                if isinstance(c, tuple) and c[0] == 'S':
                    bits.append(f'{c[1]}[{c[2]}]')
                elif isinstance(c, tuple):
                    bits.append(c)
                elif isinstance(c, str):
                    bits.append(f"1'b{c}")
                else:
                    bits.append(None)
                    nc += 1
            if nc == len(bits):
                conns.append(f"        .{b}()")
                continue
            if nc:
                w = f'nc_{hc["inst"]}__{b}'
                extra_w.append(f"    wire [{d['hi']}:{d['lo']}] {w};   // KVG3-CORES: unconnected core pins (alias / unused)")
                bits = [x if x is not None else (w, d['hi'] - k) for k, x in enumerate(bits)]
            items = ranges([x if isinstance(x, tuple) else x for x in bits])
            # partition nets: scalar wires print bare
            sc = lambda nm: nm not in B.ranged and B.net.width.get(nm, 1) == 1 and not nm.startswith('nc_')
            conns.append(f"        .{b}({concat_text(items, sc)})")
        body.append(f"    {hc['module']} {nm} (")
        body.append(',\n'.join(conns))
        body.append("    );")
    for i, l in enumerate(lines):
        if i in drop:
            continue
        if i == end:
            out += extra_w + body
        out.append(l)
    txt = '\n'.join(out)
    hdr = ("// KVG3-CORES split (cores/harden/kv_core_rtl.py): member leaves of the planned hard cores " +
           ', '.join(M['hc']['inst'] for M in models) + " replaced by the core modules (black boxes in the partition kit).\n")
    return hdr + txt


# ----------------------------------------------------------------------------------------------- equivalence
class UF:
    def __init__(self):
        self.p = {}

    def f(self, x):
        p = self.p
        p.setdefault(x, x)
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def u(self, a, b):
        self.p[self.f(a)] = self.f(b)


def tok_nodes(net, e, scope, params):
    """MSB-first nodes of an expression: (scope, net, bit) or ('K', v) / ('S', name, i)."""
    out = []
    for tk in split_concat(e):
        nb = net.bits(tk)
        if all(x is None for x in nb):
            cb = const_bits(tk, params)
            if cb is None:
                out += [('?', tk.strip(), i) for i in range(len(nb))]
            else:
                for c in cb:
                    if isinstance(c, str):
                        out.append(('K', c))
                    else:          # S_ parameter bit -> its literal value (the core inlines the values)
                        v = const_bits(params[c[1]][1], {})
                        out.append(('K', v[-1 - c[2]] if v and len(v) > c[2] else '0'))
        else:
            out += [(scope, x[0], x[1]) if x else ('?', tk.strip(), 0) for x in nb]
    return out


def flat_groups(net, scope, uf, params, skip=()):
    """endpoint -> node: leaf port bits + partition ports; assigns merged into uf."""
    ends = {}
    for l, r in net.alias:
        for a, b in zip(net.bits(l), net.bits(r)):
            if a and b:
                uf.u((scope,) + a, (scope,) + b)
    for inst, (mod, pm) in net.insts.items():
        if inst in skip:
            continue
        for p, e in pm.items():
            nodes = tok_nodes(net, e, scope, params)
            n = len(nodes)
            for k, nd in enumerate(nodes):
                ends[(inst, p, n - 1 - k)] = nd
    for p in net.ports:
        for i in range(net.width[p]):
            ends[('<port>', p, i)] = (scope, p, i)
    return ends


def equiv(B, split_path, core_paths, models):
    """flattened bit-level connectivity: original partition vs split partition + core modules."""
    uf0 = UF()
    e0 = flat_groups(B.net, 'P', uf0, B.params)
    sn = Net(split_path)
    uf1 = UF()
    cores = {f"u_core_{M['hc']['inst']}": M for M in models}
    e1 = flat_groups(sn, 'P', uf1, B.params, skip=set(cores))
    for ci, M in cores.items():
        cn = Net(core_paths[M['hc']['module']])
        lp = dict(B.params)
        ce = flat_groups(cn, ci, uf1, lp)
        for k, nd in ce.items():
            if k[0] == '<port>':
                continue
            e1[(M['canon'][k[0]],) + k[1:]] = nd
        # core port bit <-> partition expression bit
        _, pm = sn.insts[ci]
        for p, e in pm.items():
            nodes = tok_nodes(sn, e, 'P', B.params)
            n = len(nodes)
            w = cn.width[p]
            lo = M['pdecl'][p]['lo'] or 0
            for k, nd in enumerate(nodes):
                if nd[0] == '?':
                    continue
                uf1.u((ci, p, n - 1 - k + lo), nd)
    # compare: group endpoints by root in each, canonical frozensets (constant / S_ roots keep their identity)
    def groups(ends, uf):
        g = defaultdict(set)
        for k, nd in ends.items():
            g[uf.f(nd)].add(k)
        canon = {}
        for r, s in g.items():
            tag = r if r[0] in ('K', 'S') else None
            canon[frozenset(s)] = tag
        return canon, g
    c0, g0 = groups(e0, uf0)
    c1, g1 = groups(e1, uf1)
    # original groups restricted to endpoints present in both (all of them should be)
    k0, k1 = set(e0), set(e1)
    only0 = sorted(k0 - k1)[:10]
    only1 = sorted(k1 - k0)[:10]
    s0, s1 = set(c0), set(c1)
    diff0 = [sorted(x)[:4] for x in list(s0 - s1)[:10]]
    diff1 = [sorted(x)[:4] for x in list(s1 - s0)[:10]]
    ok = not (k0 ^ k1) and s0 == s1
    return dict(verdict='PASS' if ok else 'FAIL', endpoints=len(k0), groups=len(s0),
                only_original=only0, only_split=only1, groups_only_original=len(s0 - s1), groups_only_split=len(s1 - s0),
                ex_original=[[list(map(str, y)) for y in x] for x in diff0], ex_split=[[list(map(str, y)) for y in x] for x in diff1])


def lint(files, top, defines=('SYNTHESIS',)):
    cmd = ['verilator', '--lint-only', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-MULTITOP', '--bbox-unsup',
           '--top-module', top] + [f'-D{d}' for d in defines] + [str(f) for f in files]
    r = subprocess.run(cmd, capture_output=True, text=True)
    errs = [l for l in r.stderr.splitlines() if l.startswith('%Error')]
    return dict(rc=r.returncode, errors=len(errs), first=errs[:5])


# ----------------------------------------------------------------------------------------------- main
def kv41_file(kv41, tn):
    f = Path(kv41) / f'{tn}_part.sv'
    if not f.exists():
        m = re.match(r'(.*)_(r\d+)$', tn)
        if m:
            f = Path(kv41) / f'{m.group(1)}_part_{m.group(2)}.sv'
    return f


_BOUND = {}


def consistency(plan, kv41, module, ports_json, plan_dir='.'):
    """the module over every plan instance (kv41 rtl/<type>_part.sv, base variant): boundary pin sets and S_ values."""
    T = plan['partition_types']
    sets, svals = {}, defaultdict(dict)
    insts = []
    for tn, t in T.items():
        for hc in t.get('hard_cores', []):
            if hc['module'] != module:
                continue
            f = kv41_file(kv41, tn)
            if not f.exists():
                sets[(tn, hc['inst'])] = None
                continue
            B = _BOUND.get(str(f)) or _BOUND.setdefault(str(f), Bound(f, ports_json))
            try:
                ms, pre, mine, lb = analyse(B, t, hc)
            except SystemExit as ex:
                sets[(tn, hc['inst'])] = str(ex)
                continue
            sets[(tn, hc['inst'])] = frozenset((v['base'], k[2]) for k, v in lb.items() if v['boundary'])
            for ri, p, tok in s_tokens(B, mine):
                svals[(rel(mine[ri], pre, hc), p)][(tn, hc['inst'])] = s_value(B, tok)
            insts.append((tn, t, hc, B))
    good = [s for s in sets.values() if isinstance(s, frozenset)]
    ref = good[0] if good else frozenset()
    union = frozenset().union(*good) if good else frozenset()
    straps = sorted(k for k, v in svals.items() if len(set(v.values())) > 1)
    # structural identity of the master over every slot (straps as pins, everything else must match byte for byte)
    keys = {}
    for tn, t, hc, B in insts:
        try:
            M = build_core(B, t, hc, Path(plan_dir) / hc['pins_file'], straps=set(straps))
            keys[f"{tn}.{hc['inst']}"] = body_key(emit_core(B, M))
        except SystemExit as ex:
            keys[f"{tn}.{hc['inst']}"] = 'ERR ' + str(ex)
    k0 = next(iter(keys.values()), None)
    struct_diff = [k for k, v in keys.items() if v != k0]
    return dict(structure_checked=len(keys), structure_differs=struct_diff,instances=len(sets), parsed=len(good),
                errors={f'{a}.{b}': v for (a, b), v in sets.items() if not isinstance(v, frozenset)},
                boundary_differs=[f'{a}.{b}' for (a, b), v in sets.items() if isinstance(v, frozenset) and v != ref],
                union_minus_ref=sorted(f'{b}[{i}]' for b, i in union - ref)[:40],
                straps=[dict(leaf=k[0], port=k[1], values=sorted(set(svals[k].values()))) for k in straps]), straps


def renamed_leaf_files(files, mods, outdir):
    """single-leaf cores whose leaf module has the core's plan name: copy the defining source with
    `module X` -> `module X__leaf` (the core instantiates X__leaf; X = the core / black box).  -> new file list, renames"""
    out, ren = [], []
    for f in files:
        txt = Path(f).read_text()
        hit = [m for m in mods if re.search(rf'^\s*module\s+{re.escape(m)}\b', txt, re.M)]
        if not hit:
            out.append(f)
            continue
        for m in hit:
            txt = re.sub(rf'^(\s*module\s+){re.escape(m)}\b', rf'\g<1>{m}__leaf', txt, flags=re.M)
        nf = Path(outdir) / (Path(f).stem + '__leaf' + Path(f).suffix)
        nf.write_text(f'// KVG3-CORES: copy of {f} with module(s) {hit} renamed *__leaf (core takes the plan name)\n' + txt)
        out.append(str(nf))
        ren.append(dict(src=f, copy=str(nf), modules=hit))
    return out, ren


# ----------------------------------------------------------------------------------------------- hr cores (opt-in)
HR_FAM = {'ck_core': 'ck', 'ck_host': 'ck', 'ck_ingest': 'ck', 'ck_phy_fam': 'ck_phy'}
HR_SAMECLK = ('ot_qwen_die_cdc_ch', 'qkd_host_native_qm_debt')       # members with an opt-in SAMECLK parameter
HR_FORKS = ('qkd_hr_native_qm_cdc', 'qkd_hr_qm_credit_pacer_cdc', 'qkd_hr_visibility_fence_cdc')  # KV-CDC2 forks
HR_R2 = Path(__file__).resolve().parents[4] / 'results/arch/qwen_split_1014/host_root_cluster/partition_r2.json'


def hr_header(txt, mod):
    m = re.search(r'\bmodule\s+' + re.escape(mod) + r'\s*\((.*?)\);', txt, re.S)
    if not m:
        raise SystemExit(f'{mod}: module header not found')
    order = [x.strip() for x in m.group(1).split(',') if x.strip()]
    decl = {}
    for d, rng, n in re.findall(r'^\s*(input|output|inout)\s+(?:wire\s+)?(\[\s*\d+\s*:\s*\d+\s*\]\s*)?([A-Za-z_]\w*)\s*;',
                                txt[m.end():], re.M):
        decl[n] = (d, re.sub(r'\s', '', rng) if rng else '')
    return order, decl


def hr_instances(body):
    """[(type, params text or None, inst name, conn text, span)] of the wrapper body (gen_cluster write_verilog form)."""
    out = []
    for m in re.finditer(r'^\s*([A-Za-z_]\w*)\s*(#\((.*?)\))?\s+\\?([A-Za-z_][\w\[\].$]*)\s*\((.*?)\);', body, re.S | re.M):
        if m.group(1) in ('module', 'input', 'output', 'wire', 'reg', 'assign', 'inout'):
            continue
        out.append((m.group(1), m.group(3), m.group(4), m.group(5), m.span()))
    return out


def hr_clock_alias(body, ports):
    """net -> family port it is an alias of (assign a = <family>; chains followed)."""
    al = {p: p for p in ports}
    for _ in range(4):
        for l, r in re.findall(r'^\s*assign\s+([A-Za-z_][\w$]*)\s*=\s*([A-Za-z_][\w$]*)\s*;', body, re.M):
            if r in al:
                al[l] = al[r]
    return al


def hr_core(hc, wdir, out, pdir, filelist, keep_fam):
    mod = hc['module']
    r2 = json.load(open(HR_R2))['children']
    rec = dict(schema='opentallas.kv.core_rtl_hr.v1', module=mod, inst=hc['inst'], wrappers=str(wdir),
               r2_members=r2.get(mod, {}).get('members'), sameclk=[], fork_blockers=[], notes=[])
    if mod in r2 and r2[mod].get('direct'):
        rec['notes'].append('r2 direct child: kit top = the member module itself; no wrapper emitted (its single '
                            'clock port is already the core clock pin)')
        return rec, None
    src = next((wdir / f'{mod}{e}' for e in ('.v', '.sv') if (wdir / f'{mod}{e}').exists()), None)
    if src is None:
        raise SystemExit(f'{mod}: no wrapper {mod}.v/.sv in {wdir} (plan module not an r2 child: re-pin not landed?)')
    txt = src.read_text()
    order, decl = hr_header(txt, mod)
    fams = [p for p in order if p in HR_FAM]
    fam = {} if keep_fam else {p: HR_FAM[p] for p in fams}
    body_start = txt.index('module ' + mod)
    body = txt[body_start:]
    al = hr_clock_alias(body, fams)
    # SAMECLK on member crossings whose clocks collapse onto one core pin
    edits = []
    for typ, par, inst, conn, span in hr_instances(body):
        cks = dict(re.findall(r'\.(wclk|rclk|ck|clk_h|clk_i|clk_i_out)\(\s*([A-Za-z_][\w$]*)\s*\)', conn))
        fset = {fam.get(al.get(n, n), al.get(n, n)) for n in cks.values()}
        if typ in HR_FORKS:
            rec['fork_blockers'].append(dict(inst=inst, type=typ, clocks=cks, why='KV-CDC2 CDC fork: regenerate the '
                                             'wrappers with gen_cluster.py --dieclk (no FORKS) so the original module '
                                             '(with SAMECLK) is instantiated'))
            continue
        if typ in HR_SAMECLK and cks and len(fset) == 1 and not keep_fam:
            if 'SAMECLK' in (par or ''):
                continue
            newpar = (par + ', ' if par else '') + '.SAMECLK(1)'
            edits.append((span, typ, par, newpar, inst))
            rec['sameclk'].append(dict(inst=inst, type=typ, clocks=cks, core_pin=fset.pop()))
    for (st, en), typ, par, newpar, inst in sorted(edits, key=lambda e: -e[0][0]):
        seg = body[st:en]
        seg = seg.replace(f'#({par})', f'#({newpar})', 1) if par else seg.replace(typ, f'{typ} #({newpar})', 1)
        body = body[:st] + seg + body[en:]
    body = body.replace('module ' + mod, 'module ' + mod + '__fam', 1)
    # top with the collapsed clock face
    tports, seen = [], set()
    for p in order:
        q = fam.get(p, p)
        if q not in seen:
            seen.add(q)
            tports.append((q, decl[p] if p not in fam else ('input', '')))
    lines = [f'// GENERATED by kv_core_rtl.py --hr-wrappers (KV-CORES2 10-25, BRIEFING 16a) from {src.name}; do not edit.',
             '`timescale 1ns/1ps', f'module {mod} ({", ".join(q for q, _ in tports)});']
    lines += [f'  {d} wire {r + " " if r else ""}{q};' for q, (d, r) in tports]
    lines.append(f'  {mod}__fam u_fam (' + ', '.join(f'.{p}({fam.get(p, p)})' for p in order) + ');')
    lines.append('endmodule')
    cdir = out / mod
    cdir.mkdir(parents=True, exist_ok=True)
    cp = cdir / f'{mod}.sv'
    cp.write_text('\n'.join(lines) + '\n\n' + txt[:body_start] + body)
    rec['clock_ports_before'] = fams
    rec['clock_ports_after'] = sorted({fam.get(p, p) for p in fams})
    rec['ports'] = {q: list(d) for q, d in tports}

    def width(r):
        m = re.match(r'\[(\d+):(\d+)\]', r or '')
        return abs(int(m.group(1)) - int(m.group(2))) + 1 if m else 1
    rec['port_bits'] = sum(width(r) for _, (d, r) in tports)
    if hc.get('pins_file') and (pdir / hc['pins_file']).exists():
        pins = load_pins(pdir / hc['pins_file'])
        pb = defaultdict(int)
        for (b, i) in pins:
            pb[b] += 1
        tb = {q: width(r) for q, (d, r) in tports}
        rec['pins_check'] = dict(pins_file=hc['pins_file'], pin_bits=len(pins), port_bits=rec['port_bits'],
                                 ports_without_pins=sorted(set(tb) - set(pb))[:40],
                                 n_ports_without_pins=len(set(tb) - set(pb)),
                                 pins_without_port=sorted(set(pb) - set(tb))[:40],
                                 n_pins_without_port=len(set(pb) - set(tb)),
                                 width_differs=sorted(b for b in set(tb) & set(pb) if tb[b] != pb[b])[:40],
                                 verdict='MATCH' if dict(tb) == dict(pb) else 'RE-PIN PENDING (plan pins are not '
                                         'the r2 wrapper face yet: run core_pins_hr.py on the r2 wrappers)')
    if filelist:
        fl = [l.strip() for l in open(filelist) if l.strip() and not l.startswith(('#', '//', '+', '-'))]
        rec['lint'] = lint([cp] + fl, mod)
    return rec, cp


def main_hr(a, plan, pdir, t):
    sel = [h for h in t.get('hard_cores', []) if h['module'].startswith('qkd_hr_')
           and (a.all_cores or h['inst'] in a.core)]
    if not sel:
        raise SystemExit('no qkd_hr_* cores selected (--core host__qkd_hr_<x> | --all-cores)')
    out, done = Path(a.out), set()
    for hc in sel:
        if hc['module'] in done:
            continue
        done.add(hc['module'])
        rec, cp = hr_core(hc, Path(a.hr_wrappers), out, pdir, a.hr_filelist, a.hr_keep_families)
        (out / hc['module']).mkdir(parents=True, exist_ok=True)
        (out / hc['module'] / f"{hc['module']}_core.json").write_text(json.dumps(rec, indent=1) + '\n')
        pc = rec.get('pins_check', {})
        print(json.dumps(dict(module=hc['module'], clocks=[rec.get('clock_ports_before'), rec.get('clock_ports_after')],
                              sameclk=[s['inst'] for s in rec['sameclk']], fork_blockers=len(rec['fork_blockers']),
                              port_bits=rec.get('port_bits'), pins=pc.get('verdict'), lint=rec.get('lint', {}).get('errors'),
                              notes=rec['notes'])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--type', required=True)
    ap.add_argument('--core', action='append', default=[])
    ap.add_argument('--all-cores', action='store_true')
    ap.add_argument('--kit-rtl', default=str(Path.home() / 'scratch/kv-g3/kit_rtl/g3'))
    ap.add_argument('--kv41', default=str(Path.home() / 'scratch/kv-g3/kv41/rtl'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', action='store_true')
    ap.add_argument('--no-consistency', action='store_true')
    ap.add_argument('--hr-wrappers', help='OPT-IN (KV-CORES2): host-cluster wrapper dir; selects the qkd_hr_* cores only')
    ap.add_argument('--hr-filelist', help='with --hr-wrappers: member sources for the lint')
    ap.add_argument('--hr-keep-families', action='store_true', help='with --hr-wrappers: no 16a clock collapse')
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    pdir = Path(a.plan).resolve().parent
    t = plan['partition_types'][a.type]
    if a.hr_wrappers:
        return main_hr(a, plan, pdir, t)
    kd = Path(a.kit_rtl) / a.type
    kj = json.load(open(kd / 'kit_rtl.json'))
    bound = kd / f"{kj['bound_module'].replace('_part_bound', '')}_part_bound.sv"
    files = [l.strip() for l in open(kd / 'kit_rtl.f') if l.strip()]
    leaf_files = [f for f in files if not re.search(r'_part(_bound)?\.sv$', f)]
    pj = port_dirs(files)
    B = Bound(bound, pj)
    hcs = [h for h in t.get('hard_cores', []) if (a.all_cores or h['inst'] in a.core)
           and not h['module'].startswith('qkd_hr_') and not h.get('lef')]
    if not hcs:
        raise SystemExit('no planned cores selected')
    out = Path(a.out)
    models, core_paths = [], {}
    for hc in hcs:
        mod = hc['module']
        cdir = out / mod
        cdir.mkdir(parents=True, exist_ok=True)
        cons, straps = (dict(skipped=True), []) if a.no_consistency else consistency(plan, a.kv41, mod, pj, pdir)
        M = build_core(B, t, hc, pdir / hc['pins_file'], straps=set(straps))
        models.append(M)
        cp = cdir / f'{mod}.sv'
        if mod in core_paths:          # same module twice in one type (head0/head1): one master, identical structure
            txt = emit_core(B, M)
            if body_key(txt) != body_key(Path(core_paths[mod]).read_text()):
                raise SystemExit(f"{a.type}.{hc['inst']}: {mod} differs structurally from its first slot in this type")
            continue
        cp.write_text(emit_core(B, M))
        core_paths[mod] = cp
        clash = {B.net.insts[ri][0] for ri in M['mine']} & {mod}
        cfiles, ren = renamed_leaf_files(leaf_files, clash, cdir) if clash else (leaf_files, [])
        M['files'] = cfiles
        M['rep']['leaf_renamed'] = ren
        lt = lint([cp] + cfiles, mod)
        cls = defaultdict(int)
        for c in M['pin_class'].values():
            cls[c] += 1
        rec = dict(schema='opentallas.kv.core_rtl.v1', module=mod, type=a.type, inst=hc['inst'], bound=str(bound),
                   members=M['ms'], member_bound=sorted(M['mine']), ports=len(M['pdecl']),
                   pin_bits=len(M['pin_class']), classes=dict(cls), report=M['rep'], consistency=cons, lint=lt,
                   files=[str(cp)] + cfiles, port_decl={b: [d['dir'], d['hi'], d['lo']] for b, d in M['pdecl'].items()},
                   pin_class={f'{b}[{i}]' if i is not None else b: c for (b, i), c in M['pin_class'].items()})
        (cdir / f'{mod}_core.json').write_text(json.dumps(rec, indent=1) + '\n')
        print(json.dumps(dict(module=mod, ports=rec['ports'], struct_differs=len(cons.get('structure_differs', [])), pin_bits=rec['pin_bits'], classes=rec['classes'],
                              added=len(M['rep']['added']), stale=len(M['rep']['stale']), straps=M['rep']['straps'],
                              lint=lt['errors'], cons_boundary_differs=len(cons.get('boundary_differs', [])))))
    if a.split:
        sd = out / 'split' / a.type
        sd.mkdir(parents=True, exist_ok=True)
        sp = sd / bound.name
        sp.write_text(emit_split(B, models))
        # black-box stubs of the cores for the partition kit
        stubs = []
        for M in models:
            if M['hc']['module'] in [s[0] for s in stubs]:
                continue
            pl = [f"    {d['dir']} wire {f'[{d['hi']}:{d['lo']}] ' if d['hi'] is not None else ''}{b}"
                  for b, d in M['pdecl'].items()]
            stubs.append((M['hc']['module'], f"(* blackbox *)\nmodule {M['hc']['module']} (\n" + ',\n'.join(pl) +
                          "\n);\nendmodule\n"))
        (sd / 'cores_bb.v').write_text("// KVG3-CORES: black boxes of the planned hard cores (port lists = core RTL)\n"
                                       "`default_nettype none\n" + ''.join(s for _, s in stubs) + "`default_nettype wire\n")
        eq = equiv(B, sp, core_paths, models)
        # partition-kit leaf list: a source that defines a core's plan-named leaf is replaced by its renamed copy
        kit_files = list(leaf_files)
        for M in models:
            for r in M['rep'].get('leaf_renamed', []):
                kit_files = [r['copy'] if f == r['src'] else f for f in kit_files]
        lt_split = lint([sp] + list(core_paths.values()) + kit_files, kj['bound_module'])
        lt_bb = lint([sp, sd / 'cores_bb.v'] + kit_files, kj['bound_module'])
        (sd / 'kit_rtl_split.f').write_text('\n'.join([str(kd / f"{kj['plan_module']}.sv"), str(sp), str(sd / 'cores_bb.v')]
                                                       + kit_files) + '\n')
        res = dict(type=a.type, cores=[M['hc']['inst'] for M in models], split=str(sp), equiv=eq,
                   lint_split_with_cores=lt_split, lint_split_with_bb=lt_bb)
        (sd / 'equiv.json').write_text(json.dumps(res, indent=1) + '\n')
        print(json.dumps(dict(split=str(sp), equiv=eq['verdict'], endpoints=eq['endpoints'], groups=eq['groups'],
                              lint_cores=lt_split['errors'], lint_bb=lt_bb['errors'])))


if __name__ == '__main__':
    main()
