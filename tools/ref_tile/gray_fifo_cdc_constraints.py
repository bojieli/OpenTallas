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
import shutil
import subprocess
import tempfile
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import cdc_sync_constraints as S

POLICY = 'reviewed_gray_fifos'
RELATIONSHIP_KIND = 'independent_clock_families'
CORE_PERIOD_PS = 833.333
FAMILIES = {'core': 833.333, 'host': 1000.0, 'ingest': 1666.667, 'phy': 1043.0,
            'hbm': 1024.0}    # HBM PHY CK/2 (RBH-STK 2026-10-18; cdc_sync_constraints ASYNC_RELATIONSHIP hbm_period_ps)
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
    # ROOT-0330-CDC review 2026-10-18: binary wbin/rbin, Gray wgray/rgray registered from the next binary value on
    # the pointer's own edge; async_reg 2-flop synchronisers wgray -> wg_r1 -> wg_r2 (read side), rgray -> rg_w1 ->
    # rg_w2 (write side); storage written at wbin under we && !full on the same edge as the Gray update (a word is
    # stable before its pointer is visible); full = (wgray == {~rg_w2[AW:AW-1], rg_w2[AW-2:0]}), empty = (rgray ==
    # wg_r2), rdata = mem[rbin] combinational (FWFT): read-valid = rgray != wg_r2, the ot_link_afifo 'link' form.
    # rd_freed is write-side (rg_w2 decode). AW >= 2 for the full encoding.
    'ot_hbm_accel_cdc_fifo': dict(
        path='rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
        sha256=('6b92d2ef1e24a526bd8f674d9aa696f61d4430b802155f35575d68efa439502b',),
        chains=(('wptr', 'wgray', ('wg_r1', 'wg_r2'), 'w2r'), ('rptr', 'rgray', ('rg_w1', 'rg_w2'), 'r2w')),
        valid='link', read_stage=None, min_ptr_bits=3),
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
    ext = extensions(spec)
    if spec.get('children') or (spec.get('macros') and ext is None):
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


EXTENSIONS = 'reviewed_gray_fifo_extensions'
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]*')
REF = re.compile(r'[A-Za-z_][A-Za-z0-9_.$\[\]]*')


def extensions(spec):
    """Opt-in extension mode (ROOT-0330-CDC 2026-10-18), absent = the original policy unchanged:

        "reviewed_gray_fifo_extensions": {
            "level_synchronizers": [{"name": "hbm_fault", "source": "u_wb.hbm_sticky", "chain": ["u_wb.hf1", "u_wb.hf2"]}],
            "die_constant_inputs": ["quad"],
            "why": "..."}

    enables (1) declared hard macros (spec.macros) clocked by exactly one declared root, every input cone in that
    family, outputs leaves of that family; (2) literal bus-bit clock roots; (3) declared 1-bit level synchronisers;
    (4) declared die-constant strap inputs bounded into every family; (5) storage consumers mixing several FIFOs or
    holding another role, each storage bit proved against its own FIFO's read-valid by an exact SAT miter."""
    ext = spec.get(EXTENSIONS)
    if ext is None:
        return None
    if not isinstance(ext, dict) or set(ext) - {'level_synchronizers', 'die_constant_inputs', 'why'}:
        raise GrayFifoError(f'reviewed_gray_fifos {EXTENSIONS} must be an object with level_synchronizers / '
                            'die_constant_inputs / why only (no false paths, groups or waivers)')
    levels = ext.get('level_synchronizers', [])
    if not isinstance(levels, list):
        raise GrayFifoError('reviewed_gray_fifos level_synchronizers must be a list')
    names, refs = set(), set()
    for g in levels:
        if not isinstance(g, dict) or set(g) - {'name', 'source', 'chain', 'why'}:
            raise GrayFifoError('reviewed_gray_fifos level synchroniser entries are {name, source, chain[, why]}')
        if not isinstance(g.get('name'), str) or not NAME.fullmatch(g['name']) or g['name'] in names:
            raise GrayFifoError('reviewed_gray_fifos level synchroniser names must be distinct identifiers')
        names.add(g['name'])
        chain = g.get('chain')
        if not isinstance(chain, list) or len(chain) < 2:
            raise GrayFifoError(f'reviewed_gray_fifos level synchroniser {g["name"]} needs >= 2 destination stages')
        for r in [g.get('source')] + chain:
            if not isinstance(r, str) or not REF.fullmatch(r) or r in refs:
                raise GrayFifoError(f'reviewed_gray_fifos level synchroniser {g["name"]}: register references are '
                                    f'distinct literal names: {r!r}')
            refs.add(r)
    straps = ext.get('die_constant_inputs', [])
    if not isinstance(straps, list) or len(set(straps)) != len(straps) or \
            any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for x in straps):
        raise GrayFifoError('reviewed_gray_fifos die_constant_inputs must be distinct literal input port names')
    return ext


def _macro_clock_pins(spec, root):
    """{master: clock pin} of the declared hard macros from their actual Liberty views: exactly one `clock : true`
    pin, every timing arc related to it, identical in every corner present."""
    out = {}
    root = Path(root).resolve()
    for item in spec.get('macros', []):
        if not isinstance(item, dict) or not isinstance(item.get('view'), str) or \
                not re.fullmatch(r'[A-Za-z0-9_./+-]+', item['view']):
            raise GrayFifoError('reviewed_gray_fifos macros need a literal view path')
        view = (root / item['view']).resolve()
        if not view.is_relative_to(root):
            raise GrayFifoError('reviewed_gray_fifos macro view outside the source root')
        master = view.name
        if f'{item["view"]}/{master}_bb.v' not in spec['sources']:
            raise GrayFifoError(f'reviewed_gray_fifos macro {master}: its blackbox {master}_bb.v must be a listed source')
        found = set()
        libs = sorted(view.glob(f'{master}_*.lib'))
        if not libs:
            raise GrayFifoError(f'reviewed_gray_fifos macro {master} has no Liberty view')
        for lib in libs:
            found.add(_liberty_clock(lib.read_text(), master))
        if len(found) != 1:
            raise GrayFifoError(f'reviewed_gray_fifos macro {master} clock pin differs between corners')
        out[master] = found.pop()
    return out


def _liberty_clock(text, master):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S).replace('\\\n', ' ')
    stack, clocks, related, in_cell = [], set(), set(), False
    for tok in re.finditer(r'(\w+)\s*\(([^()]*)\)\s*\{|\}|(\w+)\s*:\s*("[^"]*"|[^;{}]+);', text):
        if tok.group(1):
            stack.append((tok.group(1), tok.group(2).strip().strip('"')))
            continue
        if tok.group(0) == '}':
            if stack:
                stack.pop()
            continue
        groups = [g for g, _ in stack]
        if len(stack) < 2 or stack[1] != ('cell', master):
            continue
        pin = next((a for g, a in reversed(stack) if g in ('pin', 'bus')), None)
        key, value = tok.group(3), tok.group(4).strip().strip('"')
        if key == 'clock' and value == 'true' and pin is not None and groups[-1] in ('pin', 'bus'):
            clocks.add(pin)
        if key == 'related_pin' and 'timing' in groups:
            related.update(value.split())
    if len(clocks) != 1 or related - clocks:
        raise GrayFifoError(f'reviewed_gray_fifos macro {master} must have exactly one Liberty clock pin relating '
                            f'every arc (clocks {sorted(clocks)}, related {sorted(related)})')
    return next(iter(clocks))


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


def _netlist(document, spec, macros=None, extended=False):
    try:
        if extended:
            return S.Netlist(document, spec['top'], spec, macros=macros, extended=True)
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


def _extension_leaves(spec, ext, net, module, port_domain):
    """Extension mode: (macro cell -> family, strap input bit -> port name), after proving every declared hard macro is
    clocked directly by one declared root and every one of its input cones is in that family (or constant)."""
    declared = {}
    for item in spec.get('macros', []):
        n = item.get('count', 1)
        if type(n) is not int or n < 1:
            raise GrayFifoError('reviewed_gray_fifos macro count must be a positive integer')
        declared[Path(item['view']).name] = declared.get(Path(item['view']).name, 0) + n
    actual = {}
    for mc in net.macros.values():
        actual[mc['type']] = actual.get(mc['type'], 0) + 1
    if actual != declared:
        raise GrayFifoError(f'reviewed_gray_fifos elaborated macros {actual} differ from the declared macros {declared}')
    macro_domain = {}
    for cname, mc in sorted(net.macros.items()):
        name = cname.lstrip('\\')
        ck = mc['conn'].get(mc['clock'], [])
        if mc['dirs'].get(mc['clock']) != 'input' or len(ck) != 1 or ck[0] not in net.clock_domain:
            raise GrayFifoError(f'reviewed_gray_fifos macro {name} clock pin {mc["clock"]} is not tied directly to one '
                                'declared clock root')
        fam = macro_domain[cname] = net.clock_domain[ck[0]]
        for pin, bits in sorted(mc['conn'].items()):
            if pin == mc['clock'] or mc['dirs'][pin] != 'input':
                continue
            for b in bits:
                for leaf in net.cone(b):
                    if leaf in net.flops:
                        ldom = net.domain(leaf)
                    elif net.driver.get(leaf, ('',))[0] == 'macro':
                        ldom = net.clock_domain.get(net.macros[net.driver[leaf][1]]['conn'][
                            net.macros[net.driver[leaf][1]]['clock']][0])
                    else:
                        ldom = port_domain.get(leaf)
                    if ldom != fam:
                        what = net.key(leaf) if leaf in net.flops else (net.driver.get(leaf) or ('', str(leaf)))[1]
                        raise GrayFifoError(f'reviewed_gray_fifos macro {name} ({fam}) input {pin} reads {what} '
                                            f'({ldom}); a macro must sit in one clock family')
    straps = {}
    for p in ext.get('die_constant_inputs', []):
        if p not in module['ports'] or module['ports'][p]['direction'] != 'input':
            raise GrayFifoError(f'reviewed_gray_fifos die-constant input {p} is not an actual input port')
        bits = module['ports'][p]['bits']
        if any(b not in port_domain for b in bits):
            raise GrayFifoError(f'reviewed_gray_fifos die-constant input {p} must be a declared input of exactly one '
                                'family (its IO budget) and not a clock')
        for b in bits:
            straps[b] = p
    return macro_domain, straps


class Aig:
    """Structurally hashed and-inverter graph; literal 0/1 are constants, var v has literals 2v / 2v+1."""

    def __init__(self):
        self.nvars, self.ands, self.hash, self.inputs = 0, {}, {}, {}

    def inp(self, key):
        if key not in self.inputs:
            self.nvars += 1
            self.inputs[key] = 2 * self.nvars
        return self.inputs[key]

    def and_(self, a, b):
        if a == 0 or b == 0 or a == b ^ 1:
            return 0
        if a == 1 or a == b:
            return b
        if b == 1:
            return a
        if a < b:
            a, b = b, a
        lit = self.hash.get((a, b))
        if lit is None:
            self.nvars += 1
            lit = self.hash[(a, b)] = 2 * self.nvars
            self.ands[self.nvars] = (a, b)
        return lit

    def or_(self, a, b):
        return self.and_(a ^ 1, b ^ 1) ^ 1

    def xor(self, a, b):
        return self.or_(self.and_(a, b ^ 1), self.and_(a ^ 1, b))

    def mux(self, s, a, b):          # s ? b : a
        return self.or_(self.and_(s, b), self.and_(s ^ 1, a))

    def blif(self, po):
        """BLIF text of the cone of literal po (po not constant)."""
        seen, order, stack = set(), [], [po >> 1]
        while stack:
            v = stack[-1]
            if v in seen:
                stack.pop()
                continue
            if v in self.ands:
                kids = [x >> 1 for x in self.ands[v] if (x >> 1) not in seen]
                if kids:
                    stack.extend(kids)
                    continue
            seen.add(v)
            order.append(v)
            stack.pop()
        ins = [v for v in order if v not in self.ands]
        lines = ['.model miter', '.inputs ' + ' \\\n  '.join(' '.join(f'n{v}' for v in ins[i:i + 32])
                                                           for i in range(0, len(ins), 32)), '.outputs po']
        for v in order:
            if v in self.ands:
                a, b = self.ands[v]
                lines += [f'.names n{a >> 1} n{b >> 1} n{v}', f'{1 - (a & 1)}{1 - (b & 1)} 1']
        lines += [f'.names n{po >> 1} po', f'{1 - (po & 1)} 1', '.end', '']
        return '\n'.join(lines)


AIG_GATES = {
    '$_BUF_': lambda g, p: p['A'], '$_NOT_': lambda g, p: p['A'] ^ 1,
    '$_AND_': lambda g, p: g.and_(p['A'], p['B']), '$_NAND_': lambda g, p: g.and_(p['A'], p['B']) ^ 1,
    '$_OR_': lambda g, p: g.or_(p['A'], p['B']), '$_NOR_': lambda g, p: g.or_(p['A'], p['B']) ^ 1,
    '$_XOR_': lambda g, p: g.xor(p['A'], p['B']), '$_XNOR_': lambda g, p: g.xor(p['A'], p['B']) ^ 1,
    '$_ANDNOT_': lambda g, p: g.and_(p['A'], p['B'] ^ 1), '$_ORNOT_': lambda g, p: g.or_(p['A'], p['B'] ^ 1),
    '$_MUX_': lambda g, p: g.mux(p['S'], p['A'], p['B']), '$_NMUX_': lambda g, p: g.mux(p['S'], p['A'], p['B']) ^ 1,
    '$_AOI3_': lambda g, p: g.or_(g.and_(p['A'], p['B']), p['C']) ^ 1,
    '$_OAI3_': lambda g, p: g.and_(g.or_(p['A'], p['B']), p['C']) ^ 1,
    '$_AOI4_': lambda g, p: g.or_(g.and_(p['A'], p['B']), g.and_(p['C'], p['D'])) ^ 1,
    '$_OAI4_': lambda g, p: g.and_(g.or_(p['A'], p['B']), g.or_(p['C'], p['D'])) ^ 1,
}


def _aig_of(net, aig, bit, fresh, memo):
    """Literal of a netlist bit. Leaves (flop Q, input port, macro output) are shared variables, except the storage
    bits in `fresh` (the miter's second copy). A Yosys 'x' gate pin is one free variable per gate pin, shared by both
    copies, so the proof holds for every value synthesis may choose for it."""
    stack = [bit]
    while stack:
        b = stack[-1]
        if not isinstance(b, int):
            if b not in ('0', '1'):
                raise GrayFifoError(f'reviewed_gray_fifos undefined constant {b!r} in a storage-gating cone')
            memo[b] = int(b)
            stack.pop()
            continue
        if b in memo:
            stack.pop()
            continue
        if fresh and fresh.isdisjoint(net.cone(b)):
            memo[b] = _aig_of(net, aig, b, None, memo.setdefault('base', {}))
            stack.pop()
            continue
        drv = net.driver.get(b)
        if drv is None:
            raise GrayFifoError(f'reviewed_gray_fifos undriven bit {b} in a storage-gating cone')
        if drv[0] in ('flop', 'port', 'macro'):
            memo[b] = aig.inp(('fresh', b) if fresh and b in fresh else ('leaf', b))
            stack.pop()
            continue
        if drv[0] == 'unsupported':
            raise GrayFifoError(f'reviewed_gray_fifos unsupported cell {drv[2]} in a storage-gating cone')
        missing = [x for x in drv[3].values() if x != 'x' and x not in memo]
        if missing:
            stack.extend(missing)
            continue
        memo[b] = AIG_GATES[drv[2]](aig, {k: aig.inp(('x', drv[1], k)) if x == 'x' else memo[x]
                                          for k, x in drv[3].items()})
        stack.pop()
    return memo[bit]


def _abc():
    y = Path(_yosys())
    for c in (y.with_name('yosys-abc'), shutil.which('yosys-abc')):
        if c and Path(c).exists():
            return str(c)
    raise GrayFifoError('reviewed_gray_fifos extension storage proof requires yosys-abc next to Yosys')


def _unsat(aig, po, abc):
    if po == 0:
        return True
    if po == 1:
        return False
    with tempfile.TemporaryDirectory(prefix='ot-gray-fifo-miter-') as tmp:
        path = Path(tmp) / 'miter.blif'
        path.write_text(aig.blif(po))
        run = subprocess.run([abc, '-q', f'read_blif {path}; strash; iprove'], capture_output=True, text=True)
    verdicts = re.findall(r'^\s*(UNSATISFIABLE|SATISFIABLE)\b', run.stdout + run.stderr, re.M)
    if run.returncode or len(verdicts) != 1:
        raise GrayFifoError('reviewed_gray_fifos storage-gating SAT miter undecided: ' + (run.stdout + run.stderr)[-800:])
    return verdicts[0] == 'UNSATISFIABLE'


def _miter_storage_proof(net, consumers, fifos):
    """For every FIFO f and every consumer q reading f's storage S_f: no assignment with f's read-valid false makes
    D_q(X, S_f) differ from D_q(X, S_f') (S_f' a fresh copy, every other leaf shared). Equivalent to the per-bit
    BDD obligation (D|s=0 xor D|s=1) & !valid_f == 0 for every s in S_f (a function independent of each bit of a set
    under a condition that does not read the set is independent of the set). Exact: proved UNSAT by ABC iprove."""
    abc, aig, base = _abc(), Aig(), {}
    by_fifo = {}
    for q, owners in consumers.items():
        for fid in owners:
            by_fifo.setdefault(fid, []).append(q)
    for fid, qs in sorted(by_fifo.items()):
        fifo = fifos[fid]
        kind, terms = fifo['valid']
        if kind == 'neq':
            valid = 0
            for a, b in terms:
                valid = aig.or_(valid, aig.xor(_aig_of(net, aig, a, None, base), _aig_of(net, aig, b, None, base)))
        else:
            valid = 1
            for b, polarity in terms:
                x = _aig_of(net, aig, b, None, base)
                valid = aig.and_(valid, x if polarity else x ^ 1)
        fresh, memo = frozenset(fifo['storage']), {'base': base}
        diffs = [(q, aig.xor(_aig_of(net, aig, net.flops[q]['d'], None, base),
                             _aig_of(net, aig, net.flops[q]['d'], fresh, memo))) for q in sorted(qs)]

        def po(items):
            d = 0
            for _, x in items:
                d = aig.or_(d, x)
            return aig.and_(valid ^ 1, d)
        if _unsat(aig, po(diffs), abc):
            continue
        while len(diffs) > 1:        # name one actual failing consumer
            half = diffs[:len(diffs) // 2]
            diffs = diffs[len(diffs) // 2:] if _unsat(aig, po(half), abc) else half
        raise GrayFifoError(f'reviewed_gray_fifos consumer {net.key(diffs[0][0])} loads FIFO {fifo["scope"] or "<top>"} '
                            'storage while the FIFO read-valid is false (read not gated by the FIFO; exact SAT miter)')


def lint(spec, root):
    try:
        return _lint(spec, root)
    except S.CdcError as e:
        raise GrayFifoError(str(e).replace('cdc_synchronizers', 'reviewed_gray_fifos')) from None


def _lint(spec, root):
    relationship(spec)
    ext = extensions(spec)
    hashes, reviewed_files = _elaborate_sources(spec, root)
    document = elaborate(str(Path(root).resolve()), spec['top'], hashes,
                         tuple(sorted(spec.get('params', {}).items())), _yosys())
    net = _netlist(document, spec, _macro_clock_pins(spec, root), True) if ext is not None else _netlist(document, spec)
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
    macro_domain, strap_bits = {}, {}
    if ext is not None:
        macro_domain, strap_bits = _extension_leaves(spec, ext, net, m, port_domain)

    def leaf_domain(leaf):
        if leaf in net.flops:
            return net.domain(leaf)
        drv = net.driver.get(leaf)
        if drv and drv[0] == 'macro':
            return macro_domain[drv[1]]
        return port_domain.get(leaf)

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
            if len(src) < r.get('min_ptr_bits', 1):
                raise GrayFifoError(f'reviewed_gray_fifos {scope or "<top>"} ({base}) {cname} pointer has {len(src)} bits; '
                                    f'the reviewed source needs >= {r["min_ptr_bits"]}')
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
    levels = {}
    for g in (ext or {}).get('level_synchronizers', []):
        lid = f'l{len(levels)}'
        src, st = bits_of('', g['source']), [bits_of('', r) for r in g['chain']]
        if len(src) != 1 or any(len(x) != 1 for x in st):
            raise GrayFifoError(f'reviewed_gray_fifos level synchroniser {g["name"]}: source and every stage must be '
                                'one actual flop bit')
        src, st = src[0], [x[0] for x in st]
        sd, dds = net.domain(src), {net.domain(q) for q in st}
        if len(dds) != 1 or not all(net.flops[q]['pos'] for q in st):
            raise GrayFifoError(f'reviewed_gray_fifos level synchroniser {g["name"]} stages are not one posedge family')
        dd = dds.pop()
        if dd == sd:
            raise GrayFifoError(f'reviewed_gray_fifos level synchroniser {g["name"]} is a same-family path ({sd})')
        for j, q in enumerate(st):
            if net.flops[q]['d'] != (src if j == 0 else st[j - 1]):
                raise GrayFifoError(f'reviewed_gray_fifos level synchroniser {g["name"]} stage {j + 1} {net.key(q)} is '
                                    'not a direct flop of the previous stage (logic or bypass in the synchroniser)')
        if net.consumers.get(st[0], []) != [(net.flops[st[1]]['cell'], 'D')]:
            raise GrayFifoError(f'reviewed_gray_fifos level synchroniser {g["name"]} stage 1 {net.key(st[0])} drives '
                                'more than stage 2; a metastable stage must not be consumed')
        tag(src, ('lsrc', lid, 'lvl', 0))
        for j, q in enumerate(st):
            tag(q, ('lsync1' if j == 0 else 'lstage', lid, 'lvl', j))
        levels[lid] = dict(name=g['name'], src=sd, dst=dd, stages=len(st),
                           max_delay_ps=round(min(period[sd], period[dd]) - SETUP_UNCERTAINTY_PS, 3))
    straps_used = set()

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
                elif net.driver.get(leaf, ('',))[0] == 'macro':
                    ldom = macro_domain[net.driver[leaf][1]]
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
                if leaf in strap_bits:
                    straps_used.add((strap_bits[leaf], dom))
                    continue
                if leaf not in net.flops and leaf in port_domain:
                    raise GrayFifoError(f'reviewed_gray_fifos input {lname} ({ldom}) drives {net.key(q)} ({dom})')
                if leaf not in net.flops:
                    raise GrayFifoError(f'reviewed_gray_fifos macro output {lname} ({ldom}) drives {net.key(q)} ({dom}); '
                                        'a hard macro is a leaf of its own clock family')
                if lr and qr and lr[0] == 'src' and qr[0] == 'sync1' and lr[1:] == qr[1:]:
                    continue
                if lr and qr and lr[0] == 'lsrc' and qr[0] == 'lsync1' and lr[1] == qr[1]:
                    continue
                if lr and lr[0] == 'mem':
                    fifo = fifos[lr[1]]
                    if dom != fifo['reader']:
                        raise GrayFifoError(f'reviewed_gray_fifos storage {lname} read on {dom}, not reader {fifo["reader"]}')
                    if qr and qr[0] == 'rstage' and qr[1] == lr[1]:
                        continue
                    if qr is None or qr[0] == 'consumer' or ext is not None:
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
                    ldom = leaf_domain(leaf)
                    if ldom != name:
                        raise GrayFifoError(f'reviewed_gray_fifos output {p} ({name}) is combinational from '
                                            f'{net.key(leaf) if leaf in net.flops else leaf} ({ldom}); register it on {name}')
            outputs[p] = name
    gated = {}
    if ext is not None:
        # (b) storage gating, extension mode: every storage bit against ITS OWN FIFO's read-valid, exact SAT miter.
        _miter_storage_proof(net, consumers, fifos)
        for q, owners in sorted(consumers.items()):
            if q not in role and len(owners) == 1:
                tag(q, ('consumer', next(iter(owners)), 'mem', 0))
            else:
                gated[q] = sorted(owners)
        consumers = {}
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
    if ext is not None:
        for fid, f in record['fifos'].items():
            f['storage_read'] = f['storage_read'] or any(fid in o for o in gated.values())
        record['levels'] = levels
        record['gated'] = {}
        for q, owners in gated.items():
            for k in net.names.get(q, []):
                record['gated'][k] = owners
            cell = net.flops[q]['cell'].lstrip('\\')
            if not cell.startswith('$'):
                record['gated'].setdefault(cell, owners)
        record['straps'] = sorted({p for p, _ in straps_used})
        record['strap_crossings'] = sorted(f'{p}->{d}' for p, d in straps_used)
        record['macros'] = {c.lstrip('\\'): macro_domain[c] for c in sorted(macro_domain)}
        record['counts'].update(gated=len(gated), lsrc=len(levels), macro=len(macro_domain))
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
    text = (f'set ::ot_gf_roles [dict create {roles}]\nset ::ot_gf_fifos [dict create {fifos}]\n'
            f'set ::ot_gf_periods [dict create {periods}]\nset ::ot_gf_uncertainty {SETUP_UNCERTAINTY_PS!r}\n')
    if 'levels' not in record:
        return text
    levels = ' '.join('{' + lid + '} {src ' + v['src'] + ' dst ' + v['dst'] + ' bound ' + repr(v['max_delay_ps']) + '}'
                      for lid, v in sorted(record['levels'].items()))
    gated = ' '.join(_word(k) + ' {' + ' '.join(v) + '}' for k, v in sorted(record['gated'].items()))
    straps = ' '.join('{' + p + '} 1' for p in record['straps'])
    return text + (f'set ::ot_gf_levels [dict create {levels}]\nset ::ot_gf_gated [dict create {gated}]\n'
                   f'set ::ot_gf_straps [dict create {straps}]\n')


ASYNC_GUARD = '    if {[dict exists $async_pins [get_full_name $pin]]} continue'


def extend(body, spec, root):
    record = lint(spec, root)
    if body.count(S.CROSSING) != 1 or body.count(S.MARKER) != 1 or body.count(ASYNC_GUARD) != 1:
        raise GrayFifoError('reviewed_gray_fifos multi-root crossing gate changed; revalidate extension')
    body = body.replace(S.CROSSING, '          ot_gf_crossing $start $pin $source $cell $source_domain $expected\n'
                                    '          continue\n')
    body = body.replace(ASYNC_GUARD, '    if {[dict exists $async_pins [get_full_name $pin]]} {ot_gf_async $pin $cells $inputs; continue}')
    body = body.replace(S.MARKER, '  ot_gf_complete $cells\n' + S.MARKER)
    if 'levels' not in record:
        return bindings(record) + TCL + '\n' + body
    if body.count(STRAP_GUARD) != 1:
        raise GrayFifoError('reviewed_gray_fifos multi-root input ownership check changed; revalidate extension')
    body = body.replace(STRAP_GUARD, STRAP_GUARD.replace(
        '        set name [get_full_name $start]\n',
        '        set name [get_full_name $start]\n        if {[ot_gf_strap $start $pin $name $expected $inputs]} continue\n'))
    return bindings(record) + ext_tcl() + '\n' + body


STRAP_GUARD = ('        set name [get_full_name $start]\n'
               '        if {![dict exists $inputs $name] || [dict get $inputs $name] ne $expected} {\n')
EXT_SUBSTITUTIONS = (
    ('  if {$sk eq "" || $sf ne $tf || ![dict exists $::ot_gf_fifos $sf]} {\n',
     '  if {[ot_gf_ext_crossing $start $pin $source $target $source_domain $target_domain $sk $sf $tk $tf]} return\n'
     '  if {$sk eq "" || $sf ne $tf || ![dict exists $::ot_gf_fifos $sf]} {\n'),
    ('    lassign [ot_gf_role $cell] k f c i\n',
     '    lassign [ot_gf_role $cell] k f c i\n    if {[ot_gf_ext_complete $cell $domain $k $f]} continue\n'),
    ('  puts "OT_GF STRUCTURAL_PASS',
     '  ot_gf_ext_final\n  puts "OT_GF STRUCTURAL_PASS'),
)


def ext_tcl():
    """TCL of the extension mode: the original procs with three hooks, plus the extension procs."""
    text = TCL
    for old, new in EXT_SUBSTITUTIONS:
        if text.count(old) != 1:
            raise GrayFifoError('reviewed_gray_fifos crossing TCL changed; revalidate extension')
        text = text.replace(old, new)
    return text + TCL_EXT


TCL_EXT = r'''
# OT_GF extension mode (ROOT-0330-CDC 2026-10-18): declared 1-bit level synchronisers, storage consumers proved gated by
# each storage bit's own FIFO read-valid (several FIFOs, or a register with another role), die-constant strap inputs.
proc ot_gf_gated_fifos {cell} {
  set full [string map {\\ {}} [get_full_name [get_cells $cell]]]
  set names [list $full]
  if {[regexp {^([^$]+)\$} $full -> base]} {lappend names $base}
  foreach p [get_pins -quiet -of_objects [get_cells $cell]] {
    if {[get_property $p direction] ne "output"} continue
    foreach net [get_nets -quiet -of_objects $p] {lappend names [string map {\\ {}} [get_full_name $net]]}
  }
  set out {}
  foreach n $names {if {[dict exists $::ot_gf_gated $n]} {foreach f [dict get $::ot_gf_gated $n] {dict set out $f 1}}}
  return [dict keys $out]
}
proc ot_gf_ext_crossing {start pin source target source_domain target_domain sk sf tk tf} {
  if {$sk eq "lsrc" && $tk eq "lsync1" && $sf eq $tf && [dict exists $::ot_gf_levels $sf]} {
    set l [dict get $::ot_gf_levels $sf]
    if {[list $source_domain $target_domain] ne [list [dict get $l src] [dict get $l dst]]} {
      error "OT_GF: level crossing $source -> $target is $source_domain -> $target_domain, reviewed [dict get $l src] -> [dict get $l dst]"
    }
    ot_gf_bound $start $pin [dict get $l bound]
    dict incr ::ot_gf_seen [list $sf lsrc lvl 0]
    puts "OT_GF BOUNDED level $sf $source -> $target"
    return 1
  }
  if {$sk eq "mem" && [dict exists $::ot_gf_fifos $sf] && $sf in [ot_gf_gated_fifos $target]} {
    set f [dict get $::ot_gf_fifos $sf]
    if {$source_domain ne [dict get $f writer] || $target_domain ne [dict get $f reader]} {
      error "OT_GF: storage crossing $source -> $target is $source_domain -> $target_domain, reviewed [dict get $f writer] -> [dict get $f reader]"
    }
    ot_gf_bound $start $pin [dict get $f store]
    dict incr ::ot_gf_seen [list $sf mem mem 0]
    puts "OT_GF BOUNDED $sf mem mem -> gated $source -> $target"
    return 1
  }
  return 0
}
proc ot_gf_ext_complete {cell domain k f} {
  if {$k ni {lsrc lsync1 lstage}} {return 0}
  set l [dict get $::ot_gf_levels $f]
  set want [expr {$k eq "lsrc" ? [dict get $l src] : [dict get $l dst]}]
  if {$domain ne $want} {error "OT_GF: level synchroniser register $cell ($f $k) is in $domain, reviewed $want"}
  return 1
}
proc ot_gf_strap {start pin name expected inputs} {
  set base $name
  regexp {^([^\[]+)\[} $name -> base
  if {![dict exists $::ot_gf_straps $base]} {return 0}
  if {![dict exists $inputs $name]} {error "OT_GF: die-constant input $name has no declared IO family"}
  if {[dict get $inputs $name] eq $expected} {return 0}
  # (OpenSTA re-parses the calling command as a list: keep the bound a plain variable)
  set bound [expr {[dict get $::ot_gf_periods $expected] - $::ot_gf_uncertainty}]
  ot_gf_bound $start $pin $bound
  dict incr ::ot_gf_seen [list strap $name $expected]
  puts "OT_GF BOUNDED strap $name -> [get_full_name $pin] ($expected)"
  return 1
}
proc ot_gf_ext_final {} {
  dict for {l info} $::ot_gf_levels {
    if {![dict exists $::ot_gf_seen [list $l lsrc lvl 0]]} {error "OT_GF: missing actual level synchroniser crossing $l"}
  }
}
'''


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
