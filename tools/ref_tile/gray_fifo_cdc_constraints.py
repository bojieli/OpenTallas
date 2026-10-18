"""Reviewed Gray-pointer FIFO CDC admission for multi-family native leaf tiles (KV-HOSTCL-CDC 2026-10-17).

Opt-in policy ``clock_data_paths: "reviewed_gray_fifos"`` on a ``multiple_cts_roots`` leaf tile, with

    "clock_relationship": {"kind": "independent_clock_families",
                           "periods_ps": {"core": 833.333, "host": 1000.0, ...}}

Domains are clock FAMILIES (fixture tools/qwen_native_host/host_owner.hpp): core 833.333, host 1000, ingest 1666.667,
phy 1043 ps; core is required, any two or more families may share one leaf (core|host|ingest works). Families are
asynchronous to each other: no ratio or phase relationship is assumed. Each family domain declares the exact ratio
of its period to core (``FAMILIES[name] * 1000 / 833333``), may expose several actual CTS roots (ordinary STA inside
a family) and owns literal IO base names.

Only fingerprinted FIFO sources (REVIEWED) and ot_reset_sync carry crossings. The generator elaborates the actual leaf
sources with Yosys (flattened, SYNTHESIS, no defines), binds every reviewed instance to its reviewed file through the
Yosys scope metadata, and refuses unless every cross-family dependence of every register is one of:

  (a) pointer: reviewed Gray/online publication bit i -> stage 1 bit i of the same FIFO's synchroniser on the other
      side; stage 1 D is exactly that flop (no logic), stage 1 Q drives only stage 2, the chain has >= 2 stages, and
      writer/reader sides are the actual domains of the reviewed registers (writer != reader);
  (b) storage: FIFO storage (mem) -> a read-side register that is either the reviewed FIFO's own registered read
      stage (ot_qwen_async_fifo_w RSEL2 rs_q, sampled for the pop edge by the reviewed source) or a consumer whose
      next state provably does not depend on any storage bit while the FIFO's own read-valid predicate is false
      (ot_link_afifo: !rempty; ot_qwen_async_fifo_w / ot_async_fifo: rd_valid). The proof is an exact BDD check
      over the actual elaborated cone: for every storage bit s, (D|s=0 xor D|s=1) & !valid == 0;
  (c) asynchronous reset: an ot_reset_sync pipe register's asynchronous control (assert asynchronously, deassert
      through its own >= 2-stage pipe whose stage 0 D is constant 1 and drives only stage 1).

Everything else is refused: an unsynchronised crossing, a 1-stage synchroniser, logic in a synchroniser, a storage
read not gated by the FIFO's valid, cross-family asynchronous control of any other register, a cross-family input
port, and a combinational cross-family output.

The generated SDC replaces the multi-root crossing gate. Each actual mapped crossing must match the generator's role
tags and receives, from the actual launch register (or input port, for (c)) to the actual D/async pin only,
``set_max_delay -ignore_clock_latency`` (pointer: faster family period - 60 ps; storage and reset: destination
period - 60 ps) and ``set_min_delay -ignore_clock_latency 0``, with a finite-path proof. No false path, clock group,
multicycle or same-family exception is generated; every tagged register must sit in its tagged family, and every
pointer bit crossing must be seen in the mapped graph. Not a physical-closure or metastability-MTBF claim.
"""
import hashlib
import json
import re
import subprocess
import tempfile
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import cdc_sync_constraints as S

POLICY = 'reviewed_gray_fifos'
RELATIONSHIP_KIND = 'independent_clock_families'
CORE_PERIOD_PS = 833.333
FAMILIES = {'core': 833.333, 'host': 1000.0, 'ingest': 1666.667, 'phy': 1043.0}
SETUP_UNCERTAINTY_PS = 60.0
RESET_SYNC = ('ot_reset_sync', 'rtl/lib/ot_reset_sync.sv',
              ('489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd',))
# Reviewed FIFO sources. A chain is (name, source register, stage registers, direction); a stage pattern with {k}
# enumerates k = 0, 1, ... while the register exists. w2r: source on the writer side, stages on the reader side.
REVIEWED = {
    'ot_link_afifo': dict(
        path='rtl/link/ot_link_afifo.sv',
        sha256=('fd295cdf0e41d47ebd9a231b4ee505bb21da72cae8efd2de35af96d123816a68',),
        chains=(('wptr', 'wgray', 'wgray_s[{k}]', 'w2r'), ('rptr', 'rgray', 'rgray_s[{k}]', 'r2w')),
        valid='link', read_stage=None),
    'ot_qwen_async_fifo_w': dict(
        path='rtl/physical/ot_qwen_async_fifo_w.sv',
        sha256=('6352f90f3f6caa5f69e56b256a191e250971ff0ce039499eea141e611921e76a',),
        chains=(('wptr', 'wr_gray_pub', ('wr_gray_r1', 'wr_gray_r2'), 'w2r'),
                ('rptr', 'rd_gray', ('rd_gray_w1', 'rd_gray_w2'), 'r2w'),
                ('wonl', 'wr_online', ('wr_online_r1', 'wr_online_r2'), 'w2r'),
                ('ronl', 'rd_online', ('rd_online_w1', 'rd_online_w2'), 'r2w')),
        valid='conditioned',
        read_stage=re.compile(r'g_rs\[\d+\]\.(?:genblk\d+\.)?g_s2\.rs_q\[\d+\](?:\[\d+\])?')),
    'ot_async_fifo': dict(
        path='rtl/lib/ot_async_fifo.sv',
        sha256=('22c5e15fc205c1585be1a3cf1cefa58550ddf546e3fe56945ec3282f276948bc',),
        chains=(('wptr', 'wr_gray', ('wr_gray_r1', 'wr_gray_r2'), 'w2r'),
                ('rptr', 'rd_gray', ('rd_gray_w1', 'rd_gray_w2'), 'r2w'),
                ('wonl', 'wr_online', ('wr_online_r1', 'wr_online_r2'), 'w2r'),
                ('ronl', 'rd_online', ('rd_online_w1', 'rd_online_w2'), 'r2w')),
        valid='conditioned', read_stage=None),
}
STORAGE = re.compile(r'mem\[\d+\](?:\[\d+\])?')
RESERVED_ATTRIBUTE = re.compile(rb'\b(?:src|hdlname|module\w*|cell_\w*|keep_hierarchy)\s*=')
BDD_NODE_LIMIT = 2_000_000


class GrayFifoError(ValueError):
    pass


def family_ratio(name):
    r = Fraction(round(FAMILIES[name] * 1000), round(CORE_PERIOD_PS * 1000))
    return [r.numerator, r.denominator]


def relationship(spec):
    """Schema of the opt-in policy. Cheap; the structural lint runs in lint()."""
    if spec.get('clock') != 'multiple_cts_roots' or spec.get('kind') != 'tile':
        raise GrayFifoError('reviewed_gray_fifos requires a multiple_cts_roots leaf tile')
    if any(spec.get(k) for k in ('defines', 'hard_define', 'hard_defines', 'orfs_vars')):
        raise GrayFifoError('reviewed_gray_fifos elaborates SYNTHESIS sources only; build defines/ORFS overrides are unsupported')
    if any(spec.get(k) for k in ('sdc_extra', 'boundary_tcl', 'pre_cts_extra', 'forwarded_clock')):
        raise GrayFifoError('reviewed_gray_fifos owns all clock/crossing constraints; custom timing hooks are unsupported')
    if spec.get('cdc_synchronizers') is not None:
        raise GrayFifoError('reviewed_gray_fifos cannot be combined with cdc_synchronizers')
    if spec.get('children') or spec.get('macros'):
        raise GrayFifoError('reviewed_gray_fifos supports soft native leaves only; no hard children/macros')
    declared = spec.get('clock_entry_domains')
    if not isinstance(declared, dict) or 'core' not in declared or len(declared) < 2 or set(declared) - set(FAMILIES):
        raise GrayFifoError(f'reviewed_gray_fifos domains must be core plus >= 1 of the clock families {sorted(FAMILIES)}')
    expected = dict(kind=RELATIONSHIP_KIND, periods_ps={n: FAMILIES[n] for n in declared})
    if spec.get('clock_relationship') != expected:
        raise GrayFifoError('reviewed_gray_fifos requires clock_relationship ' + json.dumps(expected, sort_keys=True))
    if float(spec.get('route', {}).get('signoff_period_ps', CORE_PERIOD_PS)) != CORE_PERIOD_PS:
        raise GrayFifoError('reviewed_gray_fifos must retain the actual core 833.333 ps primary period')
    for name, d in declared.items():
        if not isinstance(d, dict) or d.get('ratio') != family_ratio(name):
            raise GrayFifoError(f'reviewed_gray_fifos {name} ratio must be {family_ratio(name)} ({FAMILIES[name]} ps family period)')


def _elaborate_sources(spec, root):
    root = Path(root)
    hashes, reviewed_files = [], {}
    for path in spec['sources']:
        p = (root / path).resolve()
        if not p.is_relative_to(root.resolve()) or not re.fullmatch(r'[A-Za-z0-9_./+-]+', str(p)):
            raise GrayFifoError('reviewed_gray_fifos unsafe source path')
        content = p.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        hashes.append((path, digest))
        reviewed = [(m, r) for m, r in REVIEWED.items() if r['path'] == path] + \
                   ([(RESET_SYNC[0], dict(path=RESET_SYNC[1], sha256=RESET_SYNC[2]))] if path == RESET_SYNC[1] else [])
        if reviewed:
            module, r = reviewed[0]
            if digest not in r['sha256']:
                raise GrayFifoError(f'reviewed_gray_fifos reviewed source changed: {path}')
            reviewed_files[module] = str(p)
            continue
        for attribute in re.findall(rb'\(\*(.*?)\*\)', content, re.S):
            if RESERVED_ATTRIBUTE.search(attribute):
                raise GrayFifoError('reviewed_gray_fifos reserved source/scope metadata attributes are unsupported')
        if b'$paramod' in content or b'$scopeinfo' in content:
            raise GrayFifoError('reviewed_gray_fifos reserved Yosys module identities are unsupported')
        if re.search(rb'`include\b', content):
            raise GrayFifoError('reviewed_gray_fifos includes require explicit source closure; unsupported')
    if len(set(spec['sources'])) != len(spec['sources']):
        raise GrayFifoError('reviewed_gray_fifos duplicate sources')
    return tuple(hashes), reviewed_files


@lru_cache(maxsize=16)
def elaborate(root, top, sources, params, yosys):
    # Byte hashes are part of the key; no caller-supplied graph or receipt can stand in for this elaboration.
    root = Path(root)
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', top):
        raise GrayFifoError('reviewed_gray_fifos invalid top')
    paths = []
    for path, digest in sources:
        p = (root / path).resolve()
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise GrayFifoError('reviewed_gray_fifos source changed during elaboration')
        paths.append(str(p))
    args = ''
    for name, value in params:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) or type(value) is not int:
            raise GrayFifoError('reviewed_gray_fifos requires literal integer parameters')
        args += f' -chparam {name} {value}'
    with tempfile.TemporaryDirectory(prefix='ot-gray-fifo-') as tmp:
        out = Path(tmp) / 'netlist.json'
        cmd = (f'read_verilog -sv -DSYNTHESIS {" ".join(paths)}; hierarchy -check -top {top}{args}; '
               f'proc; flatten; memory; opt; dffunmap; techmap; opt_expr; opt_clean; write_json {out}')
        run = subprocess.run([yosys, '-Q', '-T', '-p', cmd], capture_output=True, text=True)
        if run.returncode:
            raise GrayFifoError('reviewed_gray_fifos source elaboration failed: ' + (run.stdout + run.stderr)[-1500:])
        return json.loads(out.read_text())


class Bdd:
    """Minimal reduced ordered BDD: node 0/1 are terminals; a node is (level, lo, hi)."""

    def __init__(self):
        self.nodes = [(1 << 62, 0, 0), (1 << 62, 1, 1)]
        self.unique, self.memo, self.vars = {}, {}, {}

    def var(self, level):
        if level not in self.vars:
            self.vars[level] = self.mk(level, 0, 1)
        return self.vars[level]

    def mk(self, level, lo, hi):
        if lo == hi:
            return lo
        key = (level, lo, hi)
        n = self.unique.get(key)
        if n is None:
            if len(self.nodes) >= BDD_NODE_LIMIT:
                raise GrayFifoError('reviewed_gray_fifos storage-gating proof exceeds the BDD node limit; keep the '
                                    'FIFO read consumer local')
            n = len(self.nodes)
            self.nodes.append(key)
            self.unique[key] = n
        return n

    def ite(self, f, g, h):
        if f == 1:
            return g
        if f == 0:
            return h
        if g == h:
            return g
        if g == 1 and h == 0:
            return f
        key = (f, g, h)
        if key in self.memo:
            return self.memo[key]
        top = min(self.nodes[f][0], self.nodes[g][0], self.nodes[h][0])
        cof = lambda x, b: (self.nodes[x][2] if b else self.nodes[x][1]) if self.nodes[x][0] == top else x
        r = self.mk(top, self.ite(cof(f, 0), cof(g, 0), cof(h, 0)), self.ite(cof(f, 1), cof(g, 1), cof(h, 1)))
        self.memo[key] = r
        return r

    def neg(self, f):
        return self.ite(f, 0, 1)

    def restrict(self, f, level, value, memo=None):
        memo = {} if memo is None else memo
        if f in memo:
            return memo[f]
        lv, lo, hi = self.nodes[f]
        if f < 2 or lv > level:
            r = f
        elif lv == level:
            r = hi if value else lo
        else:
            r = self.mk(lv, self.restrict(lo, level, value, memo), self.restrict(hi, level, value, memo))
        memo[f] = r
        return r


GATES = {
    '$_BUF_': lambda b, p: p['A'], '$_NOT_': lambda b, p: b.neg(p['A']),
    '$_AND_': lambda b, p: b.ite(p['A'], p['B'], 0), '$_NAND_': lambda b, p: b.neg(b.ite(p['A'], p['B'], 0)),
    '$_OR_': lambda b, p: b.ite(p['A'], 1, p['B']), '$_NOR_': lambda b, p: b.neg(b.ite(p['A'], 1, p['B'])),
    '$_XOR_': lambda b, p: b.ite(p['A'], b.neg(p['B']), p['B']), '$_XNOR_': lambda b, p: b.ite(p['A'], p['B'], b.neg(p['B'])),
    '$_ANDNOT_': lambda b, p: b.ite(p['A'], b.neg(p['B']), 0), '$_ORNOT_': lambda b, p: b.ite(p['A'], 1, b.neg(p['B'])),
    '$_MUX_': lambda b, p: b.ite(p['S'], p['B'], p['A']), '$_NMUX_': lambda b, p: b.neg(b.ite(p['S'], p['B'], p['A'])),
    '$_AOI3_': lambda b, p: b.neg(b.ite(b.ite(p['A'], p['B'], 0), 1, p['C'])),
    '$_OAI3_': lambda b, p: b.neg(b.ite(b.ite(p['A'], 1, p['B']), p['C'], 0)),
    '$_AOI4_': lambda b, p: b.neg(b.ite(b.ite(p['A'], p['B'], 0), 1, b.ite(p['C'], p['D'], 0))),
    '$_OAI4_': lambda b, p: b.neg(b.ite(b.ite(p['A'], 1, p['B']), b.ite(p['C'], 1, p['D']), 0)),
}


def _bdd_of(net, bdd, bit, level, cache):
    """Exact BDD of a netlist bit over its leaf (flop Q / input port) variables. Iterative (deep cones).

    A Yosys 'x' gate input (e.g. an out-of-range read-mux arm) is an unconstrained free variable of its own per gate
    pin, so every proof holds for every value synthesis may choose for it."""
    xlevel = cache.setdefault('xlevel', {})
    stack = [bit]
    while stack:
        b = stack[-1]
        if not isinstance(b, int):
            if b not in ('0', '1'):
                raise GrayFifoError(f'reviewed_gray_fifos undefined constant {b!r} in a storage-gating cone')
            cache[b] = int(b)
            stack.pop()
            continue
        if b in cache:
            stack.pop()
            continue
        drv = net.driver.get(b)
        if drv is None:
            raise GrayFifoError(f'reviewed_gray_fifos undriven bit {b} in a storage-gating cone')
        if drv[0] in ('flop', 'port'):
            cache[b] = bdd.var(level(b))
            stack.pop()
            continue
        if drv[0] == 'unsupported':
            raise GrayFifoError(f'reviewed_gray_fifos unsupported cell {drv[2]} in a storage-gating cone')
        missing = [x for x in drv[3].values() if x != 'x' and x not in cache]
        if missing:
            stack.extend(missing)
            continue
        args = {}
        for k, x in drv[3].items():
            if x == 'x':
                key = (drv[1], k)
                xlevel.setdefault(key, (1 << 41) + len(xlevel))
                args[k] = bdd.var(xlevel[key])
            else:
                args[k] = cache[x]
        cache[b] = GATES[drv[2]](bdd, args)
        stack.pop()
    return cache[bit]


def _yosys():
    try:
        return S._yosys()
    except S.CdcError as e:
        raise GrayFifoError(str(e).replace('cdc_synchronizers', 'reviewed_gray_fifos')) from None


def _netlist(document, spec):
    try:
        return S.Netlist(document, spec['top'], spec)
    except S.CdcError as e:
        raise GrayFifoError(str(e).replace('cdc_synchronizers', 'reviewed_gray_fifos')) from None


def _scopes(document, spec, reviewed_files):
    """(scope, module) of every reviewed FIFO / reset-synchroniser instance, bound to its reviewed file."""
    module = document['modules'][spec['top']]
    found = []
    top_src = module.get('attributes', {}).get('src', '')
    if spec['top'] in REVIEWED or spec['top'] == RESET_SYNC[0]:
        found.append(('', spec['top'], top_src))
    for name, cell in module['cells'].items():
        if cell['type'] != '$scopeinfo':
            continue
        a = cell.get('attributes', {})
        base = a.get('module_hdlname') or a.get('module', '')
        if base.startswith('$paramod'):
            base = base.rsplit('\\', 1)[-1]
        if base in REVIEWED or base == RESET_SYNC[0]:
            found.append((name.lstrip('\\'), base, a.get('module_src', '')))
    out = []
    for scope, base, src in found:
        if base not in reviewed_files or src.rsplit(':', 1)[0] != reviewed_files[base]:
            raise GrayFifoError(f'reviewed_gray_fifos instance {scope or "<top>"} of {base} does not bind its reviewed '
                                'source file (fingerprinted sources must be listed and supply the module)')
        out.append((scope, base))
    return out


def lint(spec, root):
    try:
        return _lint(spec, root)
    except S.CdcError as e:
        raise GrayFifoError(str(e).replace('cdc_synchronizers', 'reviewed_gray_fifos')) from None


def _lint(spec, root):
    relationship(spec)
    hashes, reviewed_files = _elaborate_sources(spec, root)
    document = elaborate(str(Path(root).resolve()), spec['top'], hashes,
                         tuple(sorted(spec.get('params', {}).items())), _yosys())
    net = _netlist(document, spec)
    ds = spec['clock_entry_domains']
    period = {n: FAMILIES[n] for n in ds}
    port_domain = {}
    m = document['modules'][spec['top']]
    for name, d in ds.items():
        for p in d.get('inputs', []):
            if p not in m['ports'] or m['ports'][p]['direction'] != 'input':
                raise GrayFifoError(f'reviewed_gray_fifos declared input {p} is not an actual input port')
            for b in m['ports'][p]['bits']:
                port_domain[b] = name
    for b in net.clock_domain:
        port_domain.pop(b, None)

    def bits_of(scope, reg):
        prefix = scope + '.' if scope else ''
        keys = [k for k in net.bit_of if k == prefix + reg or re.fullmatch(re.escape(prefix + reg) + r'\[\d+\]', k)]
        keys.sort(key=lambda k: int(k[k.rfind('[') + 1:-1]) if k != prefix + reg else -1)
        out = []
        for k in keys:
            b = net.bit_of[k]
            if b not in net.flops:
                raise GrayFifoError(f'reviewed_gray_fifos {k} is not a single flop Q')
            out.append(b)
        return out

    role = {}

    def tag(q, r):
        if q in role and role[q] != r:
            raise GrayFifoError(f'reviewed_gray_fifos {net.key(q)} carries two roles {role[q]} / {r} (merged registers)')
        role[q] = r

    fifos, resets, scopes = {}, [], _scopes(document, spec, reviewed_files)
    for scope, base in scopes:
        if base == RESET_SYNC[0]:
            pipe = bits_of(scope, 'reset_pipe')
            if len(pipe) < 2:
                raise GrayFifoError(f'reviewed_gray_fifos reset synchroniser {scope} has fewer than 2 stages')
            doms = {net.domain(q) for q in pipe}
            if len(doms) != 1 or not all(net.flops[q]['pos'] for q in pipe):
                raise GrayFifoError(f'reviewed_gray_fifos reset synchroniser {scope} is not one posedge domain')
            if net.flops[pipe[0]]['d'] != '1' or any(net.flops[pipe[i]]['d'] != pipe[i - 1] for i in range(1, len(pipe))):
                raise GrayFifoError(f'reviewed_gray_fifos reset synchroniser {scope} pipe is not 1 -> stage -> stage')
            if len({net.flops[q]['r'] for q in pipe}) != 1:
                raise GrayFifoError(f'reviewed_gray_fifos reset synchroniser {scope} stages do not share one async control')
            if net.consumers.get(pipe[0], []) != [(net.flops[pipe[1]]['cell'], 'D')]:
                raise GrayFifoError(f'reviewed_gray_fifos reset synchroniser {scope} stage 0 drives more than stage 1')
            for i, q in enumerate(pipe):
                tag(q, ('rst', f'r{len(resets)}', 'pipe', i))
            resets.append(dict(scope=scope, domain=doms.pop(), stages=len(pipe)))
            continue
        r = REVIEWED[base]
        fid = f'f{len(fifos)}'
        chains = []
        for cname, src_reg, stages, direction in r['chains']:
            src = bits_of(scope, src_reg)
            if isinstance(stages, str):
                names, k = [], 0
                while bits_of(scope, stages.format(k=k)):
                    names.append(stages.format(k=k))
                    k += 1
            else:
                names = list(stages)
            st = [bits_of(scope, s) for s in names]
            if not src:
                raise GrayFifoError(f'reviewed_gray_fifos {scope or "<top>"} ({base}) lost its {src_reg} publication register')
            if len(st) < 2 or any(len(s) != len(src) for s in st):
                raise GrayFifoError(f'reviewed_gray_fifos {scope or "<top>"} ({base}) {cname} synchroniser has '
                                    f'{len(st)} full-width stage(s); >= 2 destination stages are required')
            chains.append((cname, src_reg, names, direction, src, st))
        w_dom = {net.domain(q) for c in chains for q in (c[4] if c[3] == 'w2r' else c[5][0])}
        r_dom = {net.domain(q) for c in chains for q in (c[4] if c[3] == 'r2w' else c[5][0])}
        if len(w_dom) != 1 or len(r_dom) != 1:
            raise GrayFifoError(f'reviewed_gray_fifos {scope or "<top>"} ({base}) pointer registers span several families')
        writer, reader = w_dom.pop(), r_dom.pop()
        if writer == reader:
            raise GrayFifoError(f'reviewed_gray_fifos {scope or "<top>"} ({base}) writer and reader are one family '
                                f'({writer}); no CDC exception on a same-family path')
        for cname, src_reg, names, direction, src, st in chains:
            sd, dd = (writer, reader) if direction == 'w2r' else (reader, writer)
            for q in src:
                if net.domain(q) != sd:
                    raise GrayFifoError(f'reviewed_gray_fifos {net.key(q)} is not on the {sd} side')
            for j, s in enumerate(st):
                for i, q in enumerate(s):
                    if net.domain(q) != dd or not net.flops[q]['pos']:
                        raise GrayFifoError(f'reviewed_gray_fifos synchroniser {net.key(q)} is not a posedge {dd} flop')
                    if net.flops[q]['d'] != (src[i] if j == 0 else st[j - 1][i]):
                        raise GrayFifoError(f'reviewed_gray_fifos synchroniser stage {j + 1} {net.key(q)} is not a '
                                            'direct flop of the previous stage (logic or bypass in the synchroniser)')
            for i, q in enumerate(st[0]):
                if net.consumers.get(q, []) != [(net.flops[st[1][i]]['cell'], 'D')]:
                    raise GrayFifoError(f'reviewed_gray_fifos synchroniser stage 1 {net.key(q)} drives more than '
                                        'stage 2; a metastable stage must not be consumed')
            for i, q in enumerate(src):
                tag(q, ('src', fid, cname, i))
            for j, s in enumerate(st):
                for i, q in enumerate(s):
                    tag(q, ('sync1' if j == 0 else 'stage', fid, cname, i))
        prefix = scope + '.' if scope else ''
        storage = sorted({b for k, b in net.bit_of.items() if k.startswith(prefix) and
                          STORAGE.fullmatch(k[len(prefix):]) and b in net.flops})
        for q in storage:
            if net.domain(q) != writer:
                raise GrayFifoError(f'reviewed_gray_fifos storage {net.key(q)} is not on the writer side {writer}')
            tag(q, ('mem', fid, 'mem', 0))
        if r['read_stage'] is not None:
            for k, b in net.bit_of.items():
                if k.startswith(prefix) and r['read_stage'].fullmatch(k[len(prefix):]) and b in net.flops:
                    if net.domain(b) != reader:
                        raise GrayFifoError(f'reviewed_gray_fifos read stage {net.key(b)} is not on the reader side')
                    tag(b, ('rstage', fid, 'mem', 0))
        # The FIFO's own read-valid, as the reviewed source defines it, over the actual tagged registers:
        #   ot_link_afifo:  !rempty = (rgray != wgray_s[SYNC-1])
        #   ot_qwen_async_fifo_w / ot_async_fifo: rd_valid = rd_domain_rst_n && wr_online_r2 && !rd_empty
        stage = {c[0]: c for c in chains}
        if r['valid'] == 'link':
            valid = ('neq', tuple(zip(stage['rptr'][4], stage['wptr'][5][-1])))
        else:
            empty = bits_of(scope, 'rd_empty')
            # rd_domain_rst_n: the reviewed source's own wire; if synthesis dropped the name, the reviewed
            # rd_reset_conditioner output (ot_async_fifo EXT_RST 0 places it in a generate block).
            rst = [net.bit_of.get(prefix + 'rd_domain_rst_n')]
            if not isinstance(rst[0], int):
                conditioner = [c for c, b in scopes if b == RESET_SYNC[0] and
                               re.fullmatch(re.escape(prefix) + r'(?:[A-Za-z_]\w*\.)?rd_reset_conditioner', c)]
                rst = bits_of(conditioner[0], 'reset_pipe')[-1:] if len(conditioner) == 1 else [None]
            if len(empty) != 1 or not isinstance(rst[0], int) or len(stage['wonl'][5][-1]) != 1:
                raise GrayFifoError(f'reviewed_gray_fifos {scope or "<top>"} lost its read-valid registers')
            if net.domain(empty[0]) != reader:
                raise GrayFifoError(f'reviewed_gray_fifos {net.key(empty[0])} is not on the reader side')
            valid = ('and', ((rst[0], 1), (stage['wonl'][5][-1][0], 1), (empty[0], 0)))
        fifos[fid] = dict(scope=scope, module=base, writer=writer, reader=reader, valid=valid,
                          storage=set(storage), chains={c[0]: len(c[4]) for c in chains},
                          pointer_max_delay_ps=round(min(period[writer], period[reader]) - SETUP_UNCERTAINTY_PS, 3),
                          storage_max_delay_ps=round(period[reader] - SETUP_UNCERTAINTY_PS, 3))
    if not fifos:
        raise GrayFifoError('reviewed_gray_fifos requires at least one actual reviewed FIFO instance')
    storage_owner = {q: fid for fid, f in fifos.items() for q in f['storage']}

    # Census of every actual cross-family dependence (flop D and asynchronous control, and output ports).
    consumers = {}
    for q, f in net.flops.items():
        dom = net.domain(q)
        for pin, bit in (('D', f['d']), ('R', f['r'])):
            for leaf in net.cone(bit):
                if leaf in net.flops:
                    ldom = net.domain(leaf)
                elif leaf in port_domain:
                    ldom = port_domain[leaf]
                else:
                    raise GrayFifoError(f'reviewed_gray_fifos {net.key(q)} {pin} reads an undeclared input or a clock '
                                        f'as data (bit {leaf})')
                if ldom == dom:
                    continue
                lr, qr = role.get(leaf), role.get(q)
                lname = net.key(leaf) if leaf in net.flops else net.driver[leaf][1]
                if pin == 'R':
                    if lr and lr[0] != 'rst':
                        raise GrayFifoError(f'reviewed_gray_fifos FIFO publication {lname} ({lr[0]}) drives asynchronous '
                                            f'control of {net.key(q)}')
                    if qr and qr[0] == 'rst':
                        continue
                    raise GrayFifoError(f'reviewed_gray_fifos cross-family asynchronous control {lname} ({ldom}) -> '
                                        f'{net.key(q)} ({dom}); only an ot_reset_sync pipe may take it')
                if leaf not in net.flops:
                    raise GrayFifoError(f'reviewed_gray_fifos input {lname} ({ldom}) drives {net.key(q)} ({dom})')
                if lr and qr and lr[0] == 'src' and qr[0] == 'sync1' and lr[1:] == qr[1:]:
                    continue
                if lr and lr[0] == 'mem':
                    fifo = fifos[lr[1]]
                    if dom != fifo['reader']:
                        raise GrayFifoError(f'reviewed_gray_fifos storage {lname} read on {dom}, not reader {fifo["reader"]}')
                    if qr and qr[0] == 'rstage' and qr[1] == lr[1]:
                        continue
                    if qr is None or qr[0] == 'consumer':
                        consumers.setdefault(q, set()).add(lr[1])
                        continue
                raise GrayFifoError(f'reviewed_gray_fifos unapproved crossing {lname} ({ldom}) -> {net.key(q)} ({dom})'
                                    f'{" " + str(lr[:3]) + " -> " + str(qr[:3]) if lr or qr else ""}')
    outputs = {}
    for name, d in ds.items():
        for p in d.get('outputs', []):
            if p not in m['ports'] or m['ports'][p]['direction'] != 'output':
                raise GrayFifoError(f'reviewed_gray_fifos declared output {p} is not an actual output port')
            for b in m['ports'][p]['bits']:
                for leaf in net.cone(b):
                    ldom = net.domain(leaf) if leaf in net.flops else port_domain.get(leaf)
                    if ldom != name:
                        raise GrayFifoError(f'reviewed_gray_fifos output {p} ({name}) is combinational from '
                                            f'{net.key(leaf) if leaf in net.flops else leaf} ({ldom}); register it on {name}')
            outputs[p] = name
    # (b) storage gating: exact BDD proof over the actual cone.
    bdd, cache = Bdd(), {}
    level = lambda b: (1 << 40) + b if b in storage_owner else b
    for q, owners in sorted(consumers.items()):
        if len(owners) != 1:
            raise GrayFifoError(f'reviewed_gray_fifos consumer {net.key(q)} mixes storage of several FIFOs')
        fid = next(iter(owners))
        fifo = fifos[fid]
        kind, terms = fifo['valid']
        if kind == 'neq':
            v = 0
            for a, b in terms:
                x, y = _bdd_of(net, bdd, a, level, cache), _bdd_of(net, bdd, b, level, cache)
                v = bdd.ite(v, 1, bdd.ite(x, bdd.neg(y), y))
        else:
            v = 1
            for b, polarity in terms:
                x = _bdd_of(net, bdd, b, level, cache)
                v = bdd.ite(v, x if polarity else bdd.neg(x), 0)
        invalid = bdd.neg(v)
        fn = _bdd_of(net, bdd, net.flops[q]['d'], level, cache)
        for s in sorted(net.cone(net.flops[q]['d']) & fifo['storage']):
            dep = bdd.ite(bdd.restrict(fn, level(s), 0), bdd.neg(bdd.restrict(fn, level(s), 1)),
                          bdd.restrict(fn, level(s), 1))
            if bdd.ite(dep, invalid, 0) != 0:
                raise GrayFifoError(f'reviewed_gray_fifos consumer {net.key(q)} loads FIFO {fifo["scope"] or "<top>"} '
                                    f'storage {net.key(s)} while the FIFO read-valid is false (read not gated by the FIFO)')
        tag(q, ('consumer', fid, 'mem', 0))
    record = dict(source_sha256=dict(hashes), roles={}, resets=resets,
                  fifos={fid: dict(scope=f['scope'], module=f['module'], writer=f['writer'], reader=f['reader'],
                                   chains=f['chains'], storage_bits=len(f['storage']),
                                   storage_read=any(r[1] == fid and r[0] in ('rstage', 'consumer') for r in role.values()),
                                   pointer_max_delay_ps=f['pointer_max_delay_ps'],
                                   storage_max_delay_ps=f['storage_max_delay_ps'])
                         for fid, f in fifos.items()},
                  periods_ps=period)
    for q, r in role.items():
        for k in net.names.get(q, []):
            record['roles'][k] = list(r)
        cell = net.flops[q]['cell'].lstrip('\\')
        if not cell.startswith('$'):
            record['roles'].setdefault(cell, list(r))
    record['counts'] = {k: sum(1 for x in role.values() if x[0] == k)
                        for k in ('src', 'sync1', 'stage', 'mem', 'rstage', 'consumer', 'rst')}
    return record


def _word(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.$\[\]]*', value):
        raise GrayFifoError('reviewed_gray_fifos unsupported identifier ' + repr(value))
    return '{' + value + '}'


def bindings(record):
    roles = ' '.join(_word(k) + ' {' + ' '.join(str(x) for x in r) + '}' for k, r in sorted(record['roles'].items()))
    fifos = ' '.join('{' + fid + '} {writer ' + f['writer'] + ' reader ' + f['reader'] + ' ptr '
                     + repr(f['pointer_max_delay_ps']) + ' store ' + repr(f['storage_max_delay_ps'])
                     + ' store_read ' + str(int(f['storage_read'])) + ' chains {'
                     + ' '.join(f'{c} {n}' for c, n in sorted(f['chains'].items())) + '}}'
                     for fid, f in sorted(record['fifos'].items()))
    periods = ' '.join(f'{n} {p!r}' for n, p in sorted(record['periods_ps'].items()))
    return (f'set ::ot_gf_roles [dict create {roles}]\nset ::ot_gf_fifos [dict create {fifos}]\n'
            f'set ::ot_gf_periods [dict create {periods}]\nset ::ot_gf_uncertainty {SETUP_UNCERTAINTY_PS!r}\n')


ASYNC_GUARD = '    if {[dict exists $async_pins [get_full_name $pin]]} continue'


def extend(body, spec, root):
    record = lint(spec, root)
    if body.count(S.CROSSING) != 1 or body.count(S.MARKER) != 1 or body.count(ASYNC_GUARD) != 1:
        raise GrayFifoError('reviewed_gray_fifos multi-root crossing gate changed; revalidate extension')
    body = body.replace(S.CROSSING, '          ot_gf_crossing $start $pin $source $cell $source_domain $expected\n'
                                    '          continue\n')
    body = body.replace(ASYNC_GUARD, '    if {[dict exists $async_pins [get_full_name $pin]]} {ot_gf_async $pin $cells $inputs; continue}')
    body = body.replace(S.MARKER, '  ot_gf_complete $cells\n' + S.MARKER)
    return bindings(record) + TCL + '\n' + body


TCL = r'''
# OT_GF (gray_fifo_cdc_constraints.py): reviewed Gray-pointer FIFO crossings between asynchronous clock families.
# The generator elaborated the fingerprinted sources and proved every cross-family dependence is a reviewed pointer
# synchroniser, a FIFO-valid-gated storage read or an ot_reset_sync input. Each actual mapped crossing must match a
# tagged pair; no other path receives an exception and no false path or clock group exists.
set ::ot_gf_seen {}
proc ot_gf_role {cell} {
  set full [string map {\\ {}} [get_full_name [get_cells $cell]]]
  set names [list $full]
  if {[regexp {^([^$]+)\$} $full -> base]} {lappend names $base}
  set roles {}
  foreach n $names {if {[dict exists $::ot_gf_roles $n]} {dict set roles [dict get $::ot_gf_roles $n] 1}}
  if {![dict size $roles]} {
    foreach p [get_pins -quiet -of_objects [get_cells $cell]] {
      if {[get_property $p direction] ne "output"} continue
      foreach net [get_nets -quiet -of_objects $p] {
        set n [string map {\\ {}} [get_full_name $net]]
        if {[dict exists $::ot_gf_roles $n]} {dict set roles [dict get $::ot_gf_roles $n] 1}
      }
    }
  }
  if {[dict size $roles] > 1} {error "OT_GF: ambiguous FIFO role for $cell: [dict keys $roles]"}
  if {![dict size $roles]} {return {}}
  return [lindex [dict keys $roles] 0]
}
proc ot_gf_launch {start} {
  if {[sta::object_type $start] eq "Port" || ([sta::object_type $start] eq "Pin" && [$start is_top_level_port])} {
    return [get_ports [get_full_name $start]]
  }
  set launch [get_cells -quiet -of_objects $start]
  if {[llength $launch] != 1} {error "OT_GF: missing unique launch register"}
  return $launch
}
proc ot_gf_bound {start target bound} {
  set launch [ot_gf_launch $start]
  set_max_delay -ignore_clock_latency $bound -from $launch -to $target
  set_min_delay -ignore_clock_latency 0.0 -from $launch -to $target
  foreach kind {max min} {
    set paths [find_timing_paths -from $launch -to $target -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" && ![info exists ::ot_mm_active]} {
      puts "OT_GF PATH_DEFERRED [get_full_name $start] -> [get_full_name $target] $kind (strict at sign-off)"
      continue
    }
    if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
      error "OT_GF: missing finite bounded $kind path [get_full_name $start] -> [get_full_name $target]"
    }
  }
}
proc ot_gf_crossing {start pin source target source_domain target_domain} {
  if {[lindex [split [get_full_name $pin] /] end] ne "D" || [get_property $pin direction] ne "input"} {
    error "OT_GF: cross-family control pin [get_full_name $pin]"
  }
  lassign [ot_gf_role $source] sk sf sc si
  lassign [ot_gf_role $target] tk tf tc ti
  if {$sk eq "" || $sf ne $tf || ![dict exists $::ot_gf_fifos $sf]} {
    error "OT_GF: unapproved actual crossing $source -> $target ($sk $sf $sc -> $tk $tf $tc)"
  }
  set f [dict get $::ot_gf_fifos $sf]
  set writer [dict get $f writer]; set reader [dict get $f reader]
  if {$sk eq "src" && $tk eq "sync1" && $sc eq $tc && $si == $ti} {
    set side [expr {[lsearch -exact {wptr wonl} $sc] >= 0 ? [list $writer $reader] : [list $reader $writer]}]
    if {[list $source_domain $target_domain] ne $side} {
      error "OT_GF: pointer crossing $source -> $target is $source_domain -> $target_domain, reviewed $side"
    }
    ot_gf_bound $start $pin [dict get $f ptr]
  } elseif {$sk eq "mem" && $tk in {rstage consumer}} {
    if {$source_domain ne $writer || $target_domain ne $reader} {
      error "OT_GF: storage crossing $source -> $target is $source_domain -> $target_domain, reviewed $writer -> $reader"
    }
    ot_gf_bound $start $pin [dict get $f store]
  } else {
    error "OT_GF: unapproved actual crossing $source -> $target ($sk $sf $sc $si -> $tk $tc $ti)"
  }
  dict incr ::ot_gf_seen [list $sf $sk $sc $si]
  puts "OT_GF BOUNDED $sf $sk $sc -> $tk $source -> $target"
}
proc ot_gf_async {pin cells inputs} {
  # Recovery/removal stays timed. A cross-family asynchronous control is admitted only into an ot_reset_sync pipe.
  set cell [get_full_name [get_cells -of_objects $pin]]
  set domain [dict get $cells $cell]
  foreach start [get_fanin -flat -startpoints_only -to $pin] {
    set name [get_full_name $start]
    if {[sta::object_type $start] eq "Port" || ([sta::object_type $start] eq "Pin" && [$start is_top_level_port])} {
      if {![dict exists $inputs $name]} {error "OT_GF: undeclared input $name drives asynchronous control [get_full_name $pin]"}
      set source_domain [dict get $inputs $name]
    } else {
      set source [get_full_name [get_cells -quiet -of_objects $start]]
      if {![dict exists $cells $source]} {
        if {[ot_ce_constant_cone $start]} continue
        error "OT_GF: unowned asynchronous control $source -> [get_full_name $pin]"
      }
      set source_domain [dict get $cells $source]
    }
    if {$source_domain eq $domain} continue
    lassign [ot_gf_role $cell] tk
    if {$tk ne "rst"} {error "OT_GF: cross-family asynchronous control $name ($source_domain) -> [get_full_name $pin] ($domain)"}
    set bound [expr {[dict get $::ot_gf_periods $domain] - $::ot_gf_uncertainty}]
    ot_gf_bound $start $pin $bound
    dict incr ::ot_gf_seen [list rst $cell]
    puts "OT_GF BOUNDED reset $name -> [get_full_name $pin]"
  }
}
proc ot_gf_complete {cells} {
  # Every tagged register sits in its tagged family (a tag on a same-family path is refused here).
  dict for {cell domain} $cells {
    lassign [ot_gf_role $cell] k f c i
    if {$k eq "" || $k eq "rst"} continue
    set info [dict get $::ot_gf_fifos $f]
    set w [dict get $info writer]; set r [dict get $info reader]
    set wside [expr {[lsearch -exact {wptr wonl} $c] >= 0}]
    switch -- $k {
      src {set want [expr {$wside ? $w : $r}]}
      sync1 - stage {set want [expr {$wside ? $r : $w}]}
      mem {set want $w}
      default {set want $r}
    }
    if {$domain ne $want} {error "OT_GF: FIFO register $cell ($f $k $c) is in $domain, reviewed $want; no exception on a same-family path"}
  }
  dict for {f info} $::ot_gf_fifos {
    dict for {c width} [dict get $info chains] {
      for {set i 0} {$i < $width} {incr i} {
        if {![dict exists $::ot_gf_seen [list $f src $c $i]]} {error "OT_GF: missing actual synchronised pointer crossing $f $c bit $i"}
      }
    }
    if {[dict get $info store_read] && ![dict exists $::ot_gf_seen [list $f mem mem 0]]} {error "OT_GF: missing actual storage crossing $f"}
  }
  puts "OT_GF STRUCTURAL_PASS [dict size $::ot_gf_seen] crossing classes (bounded reviewed FIFO crossings only; no physical closure claim)"
}
'''
