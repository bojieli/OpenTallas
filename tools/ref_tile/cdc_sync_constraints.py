"""Reviewed CDC-exception mode for multi-root leaf tiles: Gray-event synchronisers (COLSU-2 2026-10-17).

Spec key ``cdc_synchronizers`` (only with ``clock: multiple_cts_roots`` on a tile, never with async_gray_fifo):

    [{"name": "xser_event", "src_domain": "core", "dst_domain": "serial",
      "source": "g_xser.h_seq",                                  # Gray event counter (source domain flops)
      "chain": ["g_xser.x1_seq", "g_xser.x2_seq", "g_xser.x3_seq"],  # >= 2 destination-clock stages
      "payload": ["g_xser.h_cd", ...],                           # optional held payload (source domain flops)
      "sync_max_delay_ps": 250, "payload_max_delay_ps": 833}]

A reference is an RTL register ``name`` (every bit) or one bit ``name[i]`` of the elaborated, flattened design.

Admission is a structural lint on the actual sources elaborated by Yosys (names or receipts never grant it):
  * the source register is a Gray counter: over every reachable-or-not assignment of its next-state cone, at most one
    bit changes per source edge (a 1-bit level is trivially Gray);
  * the chain is >= 2 posedge flops on the destination clock; stage 1 D is exactly the source bit (no logic), every
    later stage D is exactly the previous stage Q, and stage 1 Q drives nothing but stage 2;
  * every payload bit holds whenever the Gray counter holds (payload and count are published on the same edge);
  * every destination register whose D cone contains payload is a capture register: its cone uses no source bit, no
    stage-1 bit and at least one chain stage >= 2, and while those stages agree bit-for-bit (no event in flight) its
    next state does not depend on any payload bit (capture gated by the synchronised count);
  * every other cross-domain data or asynchronous-control dependence in the design is refused, and a group whose two
    domains are the same domain (declared or actual clock) is refused.

The generated SDC replaces the multi-root crossing gate: each actual mapped crossing must be source bit i -> stage-1
bit i (bounded ``sync_max_delay_ps``) or payload -> capture register (bounded ``payload_max_delay_ps``), each with
``set_min_delay 0`` and ``-ignore_clock_latency``, from the actual launch register to the actual D pin only, with a
finite-path proof. No false path, clock group or same-domain exception is generated; every tagged register is checked
to sit in its declared domain and every declared bit must be seen crossing. Not a physical-closure claim.

With the existing ``seam_windows`` schema, a related 3:4 leaf may also have static bank crossings. The lint admits
each remaining dependence only from one literal bank source on the declared launch/capture domains. CDC-tagged
registers cannot use that fallback. Mapped ownership applies both exact CDC bounds and the existing seam bounds,
requires every group/window to be seen, and leaves negative setup/hold slack visible to signoff. A window declaration
does not prove its calendar: the tile's behavioural minimum-age and overwrite tests remain required.
"""
import hashlib
import fnmatch
import itertools
import json
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

KEY = 'cdc_synchronizers'
SETUP_UNCERTAINTY_PS = 60.0
MAX_CONE_VARS = 16
REF = re.compile(r'([A-Za-z_][A-Za-z0-9_.$]*)(?:\[(\d+)\])?')
COMB = {
    '$_BUF_': lambda p: p['A'], '$_NOT_': lambda p: 1 - p['A'],
    '$_AND_': lambda p: p['A'] & p['B'], '$_NAND_': lambda p: 1 - (p['A'] & p['B']),
    '$_OR_': lambda p: p['A'] | p['B'], '$_NOR_': lambda p: 1 - (p['A'] | p['B']),
    '$_XOR_': lambda p: p['A'] ^ p['B'], '$_XNOR_': lambda p: 1 - (p['A'] ^ p['B']),
    '$_ANDNOT_': lambda p: p['A'] & (1 - p['B']), '$_ORNOT_': lambda p: p['A'] | (1 - p['B']),
    '$_MUX_': lambda p: p['B'] if p['S'] else p['A'], '$_NMUX_': lambda p: 1 - (p['B'] if p['S'] else p['A']),
    '$_AOI3_': lambda p: 1 - ((p['A'] & p['B']) | p['C']), '$_OAI3_': lambda p: 1 - ((p['A'] | p['B']) & p['C']),
    '$_AOI4_': lambda p: 1 - ((p['A'] & p['B']) | (p['C'] & p['D'])),
    '$_OAI4_': lambda p: 1 - ((p['A'] | p['B']) & (p['C'] | p['D'])),
}
FLOP = re.compile(r'\$_DFF_([PN])(?:([PN])([01]))?_$')


class CdcError(ValueError):
    pass


# Asynchronous stream/HBM pair (RBH-STK 2026-10-18): the same HBM PHY periods as async_gray_fifo, but the crossings are
# the linted synchroniser structure below instead of the reviewed FIFO primitive. No other crossing is admitted.
ASYNC_POLICY = 'cdc_synchronizers_async'
ASYNC_RELATIONSHIP = dict(kind='hbm_phy_async_synchronizers', stream_period_ps=833.333, hbm_period_ps=1024.0)
ASYNC_RATIO = [3072000, 2499999]


def async_relationship(spec):
    """clock_data_paths cdc_synchronizers_async: core = stream 833.333, every other domain = HBM 1024, one root each."""
    if spec.get(KEY) is None:
        raise CdcError(f'{ASYNC_POLICY} requires cdc_synchronizers (the only admitted crossings)')
    if spec.get('clock') != 'multiple_cts_roots' or spec.get('kind') != 'tile':
        raise CdcError(f'{ASYNC_POLICY} requires a multiple_cts_roots leaf tile')
    if spec.get('clock_relationship') != ASYNC_RELATIONSHIP:
        raise CdcError(f'{ASYNC_POLICY} requires clock_relationship ' + json.dumps(ASYNC_RELATIONSHIP, sort_keys=True))
    if float(spec.get('route', {}).get('signoff_period_ps', 833.333)) != 833.333:
        raise CdcError(f'{ASYNC_POLICY} must retain the actual stream833.333 primary period')
    declared = spec.get('clock_entry_domains')
    if not isinstance(declared, dict) or set(declared) != {'core', 'hbm'}:
        raise CdcError(f'{ASYNC_POLICY} requires exactly core (stream) and hbm domains')
    for name, d in declared.items():
        want = [1, 1] if name == 'core' else ASYNC_RATIO
        if not isinstance(d, dict) or d.get('ratio') != want or len(d.get('ports', [])) != 1:
            raise CdcError(f'{ASYNC_POLICY} {name}: ratio must be {want} with exactly one actual root port')


def periods(spec):
    import clock_entry_constraints as C
    base = C.signoff_period(spec)
    return {n: base * d['ratio'][0] / d['ratio'][1] for n, d in spec['clock_entry_domains'].items()}


def validate(spec):
    """Schema and bounds. Cheap; the structural lint runs in load()."""
    groups = spec.get(KEY)
    if groups is None:
        return []
    if spec.get('clock') != 'multiple_cts_roots' or spec.get('kind') != 'tile':
        raise CdcError('cdc_synchronizers requires a multiple_cts_roots leaf tile')
    if spec.get('clock_data_paths') == 'async_gray_fifo':
        raise CdcError('cdc_synchronizers cannot be combined with async_gray_fifo')
    if any(spec.get(k) for k in ('sdc_extra', 'boundary_tcl', 'pre_cts_extra', 'forwarded_clock')):
        raise CdcError('cdc_synchronizers owns the crossing constraints; custom timing hooks are unsupported')
    if any(spec.get(k) for k in ('defines', 'hard_define', 'hard_defines')):
        raise CdcError('cdc_synchronizers lint elaborates SYNTHESIS sources only; build defines are unsupported')
    if not isinstance(groups, list) or not groups:
        raise CdcError('cdc_synchronizers must be a nonempty list')
    per = periods(spec)
    names, refs = set(), set()
    for g in groups:
        if not isinstance(g, dict):
            raise CdcError('cdc_synchronizers entries must be objects')
        allowed = {'name', 'src_domain', 'dst_domain', 'source', 'chain', 'payload', 'sync_max_delay_ps',
                   'payload_max_delay_ps', 'why'}
        if set(g) - allowed:
            raise CdcError(f'cdc_synchronizers unsupported keys {sorted(set(g) - allowed)} (no false paths/groups)')
        n = g.get('name')
        if not isinstance(n, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', n) or n in names:
            raise CdcError('cdc_synchronizers group names must be distinct identifiers')
        names.add(n)
        s, d = g.get('src_domain'), g.get('dst_domain')
        if s not in per or d not in per:
            raise CdcError(f'{n}: src_domain/dst_domain must be declared clock_entry_domains')
        if s == d:
            raise CdcError(f'{n}: same-domain path; a synchronizer exception needs two different clock domains')
        chain = g.get('chain')
        if not isinstance(chain, list) or len(chain) < 2:
            raise CdcError(f'{n}: chain needs >= 2 destination-clock stages')
        payload = g.get('payload', [])
        if not isinstance(payload, list):
            raise CdcError(f'{n}: payload must be a list')
        for r in [g.get('source')] + chain + payload:
            if not isinstance(r, str) or not REF.fullmatch(r):
                raise CdcError(f'{n}: register references are literal names or name[bit]: {r!r}')
            if r in refs:
                raise CdcError(f'{n}: register {r} named twice')
            refs.add(r)
        bound = g.get('sync_max_delay_ps')
        cap = min(per[s], per[d]) - SETUP_UNCERTAINTY_PS
        if isinstance(bound, bool) or not isinstance(bound, (int, float)) or not 0 < bound <= cap:
            raise CdcError(f'{n}: sync_max_delay_ps must be in (0, {cap:.3f}] (faster period minus setup uncertainty)')
        pb = g.get('payload_max_delay_ps')
        if payload:
            cap = per[d] - SETUP_UNCERTAINTY_PS
            if isinstance(pb, bool) or not isinstance(pb, (int, float)) or not 0 < pb <= cap:
                raise CdcError(f'{n}: payload_max_delay_ps must be in (0, {cap:.3f}] (destination period minus setup)')
        elif pb is not None:
            raise CdcError(f'{n}: payload_max_delay_ps without payload')
    return groups


def _yosys():
    modern = Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'
    y = os.environ.get('YOSYS', str(modern) if modern.exists() else shutil.which('yosys'))
    if not y:
        raise CdcError('cdc_synchronizers requires actual Yosys source elaboration')
    return y


@lru_cache(maxsize=16)
def elaborate(root, top, sources, params, yosys):
    root = Path(root)
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', top):
        raise CdcError('cdc_synchronizers invalid top')
    paths = []
    for path, digest in sources:
        p = (root / path).resolve()
        if not p.is_relative_to(root.resolve()) or not re.fullmatch(r'[A-Za-z0-9_./+-]+', str(p)):
            raise CdcError('cdc_synchronizers unsafe source path')
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise CdcError('cdc_synchronizers source changed during elaboration')
        paths.append(str(p))
    args = ''
    for name, value in params:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) or type(value) is not int:
            raise CdcError('cdc_synchronizers requires literal integer parameters')
        args += f' -chparam {name} {value}'
    with tempfile.TemporaryDirectory(prefix='ot-cdc-sync-') as tmp:
        out = Path(tmp) / 'netlist.json'
        # LH-PGVM2 10-19: the lint is a LOGICAL census, so kept hierarchy (keep_hierarchy region / replica cells, kept for
        # placement and fanout) is flattened too; otherwise a kept cell is an 'unexpected unmapped cell'.  Kept replicas
        # of one register are logically one register here (opt merges them); synthesis still keeps them apart.
        cmd = (f'read_verilog -sv -DSYNTHESIS {" ".join(paths)}; hierarchy -check -top {top}{args}; '
               f'setattr -mod -unset keep_hierarchy; '
               f'proc; flatten; memory; opt; dffunmap; techmap; opt_expr; opt_clean; write_json {out}')
        run = subprocess.run([yosys, '-Q', '-T', '-p', cmd], capture_output=True, text=True)
        if run.returncode:
            raise CdcError('cdc_synchronizers source elaboration failed: ' + (run.stdout + run.stderr)[-1500:])
        return json.loads(out.read_text())


class Netlist:
    def __init__(self, document, top, spec, macros=None, extended=False):
        """``extended`` (opt-in, gray_fifo_cdc_constraints extensions only): literal bus-bit clock roots, ``macros``
        {master: clock pin} of declared hard-macro cells whose outputs become leaves (driver 'macro'), and an iterative
        cone walk for deep cones. Without it every unmapped cell / non-scalar clock port is refused as before."""
        self.extended = extended
        m = document['modules'][top]
        self.driver, self.flops, self.consumers = {}, {}, {}
        self.clock_domain = {}
        self.macros = {}
        macros = macros or {}
        port_bits = {}
        for name, p in m['ports'].items():
            for b in p['bits']:
                if isinstance(b, int):
                    port_bits[b] = name
                    if p['direction'] == 'input':
                        self.driver[b] = ('port', name)
        for name, d in spec['clock_entry_domains'].items():
            for port in d['ports']:
                bits = m['ports'].get(port, {}).get('bits', [])
                bus = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]', port)
                if not bits and extended and bus and bus.group(1) in m['ports'] and not m['ports'][bus.group(1)].get('upto'):
                    # literal bus-bit root (extension mode only): bit i of an actual input bus port
                    p, i = m['ports'][bus.group(1)], int(bus.group(2)) - m['ports'][bus.group(1)].get('offset', 0)
                    bits = [p['bits'][i]] if p['direction'] == 'input' and 0 <= i < len(p['bits']) else []
                if len(bits) != 1:
                    raise CdcError(f'cdc_synchronizers clock port {port} is not one actual scalar input')
                self.clock_domain[bits[0]] = name
        for cname, c in m['cells'].items():
            t, conn = c['type'], c['connections']
            if t == '$scopeinfo':      # yosys >= 0.40 flatten: hierarchy-name metadata, no connections
                continue
            for pin, bits in conn.items():
                if c.get('port_directions', {}).get(pin) == 'input':
                    for b in bits:
                        if isinstance(b, int):
                            self.consumers.setdefault(b, []).append((cname, pin))
            f = FLOP.fullmatch(t)
            if f:
                q = conn['Q'][0]
                self.flops[q] = dict(cell=cname, d=conn['D'][0], c=conn['C'][0], pos=f.group(1) == 'P',
                                     r=conn.get('R', [None])[0], t=t)
                self.driver[q] = ('flop', cname)
            elif t in COMB:
                self.driver[conn['Y'][0]] = ('comb', cname, t, {k: v[0] for k, v in conn.items() if k != 'Y'})
            elif t.startswith('$_'):
                for pin, bits in conn.items():
                    if c.get('port_directions', {}).get(pin) == 'output':
                        for b in bits:
                            self.driver[b] = ('unsupported', cname, t)
            elif t in macros:
                dirs = c.get('port_directions', {})
                if set(dirs) != set(conn) or any(v not in ('input', 'output') for v in dirs.values()):
                    raise CdcError(f'cdc_synchronizers macro {cname} ({t}) lacks actual port directions')
                self.macros[cname] = dict(type=t, clock=macros[t], conn=conn, dirs=dirs)
                for pin, bits in conn.items():
                    if dirs[pin] == 'output':
                        for b in bits:
                            if isinstance(b, int):
                                self.driver[b] = ('macro', cname)
            else:
                raise CdcError(f'cdc_synchronizers unexpected unmapped cell {t}')
        for b, name in port_bits.items():
            if m['ports'][name]['direction'] == 'output':
                self.consumers.setdefault(b, []).append(('port', name))
        self.names = {}
        self.bit_of = {}
        for name, n in m['netnames'].items():
            if n.get('hide_name') or name.startswith('$'):
                continue
            off, bits = n.get('offset', 0), n['bits']
            if n.get('upto'):
                raise CdcError(f'cdc_synchronizers unsupported [lo:hi] declaration {name}')
            for i, b in enumerate(bits):
                key = name if len(bits) == 1 and off == 0 else f'{name}[{off + i}]'
                self.bit_of[key] = b
                if isinstance(b, int):
                    self.names.setdefault(b, []).append(key)
        self._cone = {}

    def resolve(self, ref, what):
        name, idx = REF.fullmatch(ref).groups()
        keys = [ref] if idx is not None else [k for k in self.bit_of if k == name or re.fullmatch(re.escape(name) + r'\[\d+\]', k)]
        keys = sorted(keys, key=lambda k: int(k[k.rfind('[') + 1:-1]) if k.endswith(']') else -1)
        if not keys or any(k not in self.bit_of for k in keys):
            raise CdcError(f'cdc_synchronizers {what} register {ref} not found in the elaborated design')
        out = []
        for k in keys:
            b = self.bit_of[k]
            if b not in self.flops:
                raise CdcError(f'cdc_synchronizers {what} {k} is not a single flop Q (constant or logic)')
            out.append(b)
        return keys, out

    def domain(self, q):
        f = self.flops[q]
        if f['c'] not in self.clock_domain:
            raise CdcError(f'cdc_synchronizers flop {self.key(q)} is not clocked directly by a declared clock port')
        return self.clock_domain[f['c']]

    def key(self, q):
        return '/'.join(sorted(self.names.get(q) or [self.flops[q]['cell'] if q in self.flops else str(q)]))

    def cone(self, bit):
        """Leaf bits (flop Q / input port) of the combinational fan-in of `bit`."""
        if not isinstance(bit, int):
            return frozenset()
        if bit in self._cone:
            return self._cone[bit]
        if self.extended:
            return self._cone_iterative(bit)
        drv = self.driver.get(bit)
        if drv is None or drv[0] in ('flop', 'port', 'macro'):
            res = frozenset([bit]) if drv else frozenset()
        elif drv[0] == 'unsupported':
            raise CdcError(f'cdc_synchronizers unsupported cell {drv[2]} in a crossing cone')
        else:
            self._cone[bit] = frozenset()  # combinational loop guard
            res = frozenset().union(*(self.cone(b) for b in drv[3].values()))
        self._cone[bit] = res
        return res

    def _cone_iterative(self, bit):
        """cone() without recursion (deep real cones); a combinational loop contributes nothing, as the guard above."""
        stack, active = [bit], set()
        while stack:
            b = stack[-1]
            if b in self._cone:
                stack.pop()
                continue
            drv = self.driver.get(b)
            if drv is None or drv[0] in ('flop', 'port', 'macro'):
                self._cone[b] = frozenset([b]) if drv else frozenset()
                stack.pop()
                continue
            if drv[0] == 'unsupported':
                raise CdcError(f'cdc_synchronizers unsupported cell {drv[2]} in a crossing cone')
            ins = [x for x in drv[3].values() if isinstance(x, int)]
            if b not in active:
                active.add(b)
                todo = [x for x in ins if x not in self._cone and x not in active]
                if todo:
                    stack.extend(todo)
                    continue
            active.discard(b)
            self._cone[b] = frozenset().union(*(self._cone.get(x, frozenset()) for x in ins))
            stack.pop()
        return self._cone[bit]

    def evaluate(self, bit, env, memo):
        if not isinstance(bit, int):
            if bit in ('0', '1'):
                return int(bit)
            raise CdcError(f'cdc_synchronizers undefined constant {bit!r} in a crossing cone')
        if bit in env:
            return env[bit]
        if bit in memo:
            return memo[bit]
        drv = self.driver[bit]
        v = COMB[drv[2]]({k: self.evaluate(b, env, memo) for k, b in drv[3].items()})
        memo[bit] = v
        return v


def _assignments(vars_):
    if len(vars_) > MAX_CONE_VARS:
        raise CdcError(f'cdc_synchronizers cone of {len(vars_)} variables exceeds the exhaustive-lint limit '
                       f'{MAX_CONE_VARS}; keep the synchroniser logic local')
    for values in itertools.product((0, 1), repeat=len(vars_)):
        yield dict(zip(vars_, values))


def lint(spec, root):
    groups = validate(spec)
    files = spec['sources']
    hashes = tuple((f, hashlib.sha256((Path(root) / f).read_bytes()).hexdigest()) for f in files)
    document = elaborate(str(Path(root).resolve()), spec['top'], hashes, tuple(sorted(spec.get('params', {}).items())),
                         _yosys())
    net = Netlist(document, spec['top'], spec)
    role = {}      # flop Q bit -> (group, role, index)
    record = dict(groups={}, roles={}, source_sha256=dict(hashes))
    # Mixed mode admits only the existing related-clock bank windows alongside exact CDC groups.
    # It never falls back to the general related-clock exemption for an unclassified dependence.
    import clock_entry_constraints as C
    windows = C.seam_windows(spec) or []
    port_domain = {p: n for n, d in spec['clock_entry_domains'].items() for p in d['ports']}
    seam_role, seam_seen = {}, set()
    resolved = []
    for g in groups:
        n, sd, dd = g['name'], g['src_domain'], g['dst_domain']
        skeys, src = net.resolve(g['source'], 'source')
        stages = [net.resolve(r, 'chain') for r in g['chain']]
        pay = [net.resolve(r, 'payload') for r in g.get('payload', [])]
        for q in src + [b for _, p in pay for b in p]:
            if net.domain(q) != sd:
                raise CdcError(f'{n}: {net.key(q)} is not on the declared source domain {sd}')
        for keys, bits in stages:
            if len(bits) != len(src):
                raise CdcError(f'{n}: chain stage {keys[0]} width differs from the source width {len(src)}')
            for q in bits:
                if net.domain(q) != dd:
                    raise CdcError(f'{n}: chain flop {net.key(q)} is not on the destination clock {dd}')
        for q in [b for _, bits in stages for b in bits] + src + [b for _, p in pay for b in p]:
            if not net.flops[q]['pos']:
                raise CdcError(f'{n}: {net.key(q)} is not a posedge flop')
            if q in role:
                raise CdcError(f'{n}: {net.key(q)} already has synchronizer role {role[q]}')
        if net.flops[src[0]]['c'] == net.flops[stages[0][1][0]]['c']:
            raise CdcError(f'{n}: same-domain path; source and stage 1 share one actual clock')
        for i, q in enumerate(src):
            role[q] = (n, 'source', i)
        for j, (_, bits) in enumerate(stages):
            for i, q in enumerate(bits):
                role[q] = (n, 'sync1' if j == 0 else f'stage{j + 1}', i)
        for _, bits in pay:
            for q in bits:
                role[q] = (n, 'payload', 0)
        # Gray: at most one source bit changes per source edge, over every assignment of the next-state cone.
        # A 1-bit level is trivially Gray (no enumeration, so its next-state cone may be any size).
        vars_ = [] if len(src) == 1 else sorted(set(src).union(*(net.cone(net.flops[q]['d']) for q in src)))
        for env in (_assignments(vars_) if vars_ else ()):
            memo = {}
            if sum(net.evaluate(net.flops[q]['d'], env, memo) != env[q] for q in src) > 1:
                raise CdcError(f'{n}: source {g["source"]} is not a Gray counter (more than one bit changes per edge)')
        # Chain: stage 1 D is the source bit, stage k+1 D is stage k Q, stage 1 Q drives only stage 2.
        prev = src
        for j, (keys, bits) in enumerate(stages):
            for i, q in enumerate(bits):
                if net.flops[q]['d'] != prev[i]:
                    raise CdcError(f'{n}: chain stage {j + 1} bit {i} ({net.key(q)}) is not a direct flop of '
                                   f'{"the source" if j == 0 else "the previous stage"} (logic in the synchroniser)')
            prev = bits
        for i, q in enumerate(stages[0][1]):
            sinks = net.consumers.get(q, [])
            if sinks != [(net.flops[stages[1][1][i]]['cell'], 'D')]:
                raise CdcError(f'{n}: stage-1 flop {net.key(q)} drives more than stage 2 ({len(sinks)} sinks); '
                               'a metastable stage must not be consumed')
        # Payload holds whenever the Gray count holds (same publishing edge).
        sdeps = set(src).union(*(net.cone(net.flops[q]['d']) for q in src))
        for _, bits in pay:
            for p in bits:
                vars_ = sorted(sdeps | net.cone(net.flops[p]['d']) | {p})
                for env in _assignments(vars_):
                    memo = {}
                    if all(net.evaluate(net.flops[q]['d'], env, memo) == env[q] for q in src) and \
                            net.evaluate(net.flops[p]['d'], env, memo) != env[p]:
                        raise CdcError(f'{n}: payload {net.key(p)} changes while the Gray count holds '
                                       '(payload not published with the event)')
        resolved.append((g, src, stages, [b for _, p in pay for b in p]))
        record['groups'][n] = dict(src_domain=sd, dst_domain=dd, width=len(src), payload_bits=sum(len(p) for _, p in pay),
                                   sync_max_delay_ps=float(g['sync_max_delay_ps']),
                                   payload_max_delay_ps=float(g.get('payload_max_delay_ps') or 0.0))
    # Census of every actual cross-domain dependence.
    captures = {}
    for q, f in net.flops.items():
        dom = net.domain(q)
        for pin, bit in (('D', f['d']), ('R', f['r'])):
            for leaf in net.cone(bit):
                if leaf not in net.flops or net.domain(leaf) == dom:
                    continue
                lr, qr = role.get(leaf), role.get(q)
                if pin == 'R':
                    raise CdcError(f'cdc_synchronizers cross-domain asynchronous control {net.key(leaf)} -> '
                                   f'{net.key(q)}; synchronise the reset per domain')
                if lr and qr and lr[0] == qr[0] and lr[1] == 'source' and qr[1] == 'sync1' and lr[2] == qr[2]:
                    continue
                if lr and lr[1] == 'payload' and qr is None:
                    g = next(x for x in resolved if x[0]['name'] == lr[0])
                    if dom != g[0]['dst_domain']:
                        raise CdcError(f'{lr[0]}: payload {net.key(leaf)} captured on {dom}, not {g[0]["dst_domain"]}')
                    captures.setdefault(q, set()).add(lr[0])
                    continue
                if windows and not lr and not qr:
                    names = net.names.get(leaf, []) + [net.flops[leaf]['cell'].lstrip('\\')]
                    matches = [w for w in windows
                               if port_domain[w['launch']] == net.domain(leaf)
                               and port_domain[w['capture']] == dom
                               and any(fnmatch.fnmatchcase(n, pat) for n in names for pat in w['from'])]
                    if len(matches) != 1:
                        raise CdcError(f'cdc_synchronizers seam crossing {net.key(leaf)} -> {net.key(q)} '
                                       f'matches {len(matches)} windows; exactly one required')
                    w = matches[0]
                    if leaf in seam_role and seam_role[leaf] != w['name']:
                        raise CdcError(f'cdc_synchronizers seam source {net.key(leaf)} belongs to several windows')
                    seam_role[leaf] = w['name']
                    seam_seen.add(w['name'])
                    continue
                raise CdcError(f'cdc_synchronizers undeclared crossing {net.key(leaf)} ({net.domain(leaf)}) -> '
                               f'{net.key(q)} ({dom})')
    # Gated capture: no source / stage-1 bit, >= one stage >= 2, and payload-independent while no event is in flight.
    for q, gs in captures.items():
        if len(gs) != 1:
            raise CdcError(f'cdc_synchronizers capture {net.key(q)} mixes payload of several groups')
        g, src, stages, pbits = next(x for x in resolved if x[0]['name'] in gs)
        n = g['name']
        leaves = net.cone(net.flops[q]['d'])
        banned = set(src) | set(stages[0][1])
        if leaves & banned:
            raise CdcError(f'{n}: capture {net.key(q)} reads the Gray source or the metastable stage 1')
        late = {b: i for _, bits in stages[1:] for i, b in enumerate(bits) if b in leaves}
        if not late:
            raise CdcError(f'{n}: capture {net.key(q)} is not gated by the synchronised count (no chain stage >= 2)')
        if any(leaf in net.flops and role.get(leaf, (None,))[0] not in (None, n) for leaf in leaves):
            raise CdcError(f'{n}: capture {net.key(q)} reads another synchroniser group')
        payload_leaves = sorted(leaves & set(pbits))
        others = sorted(leaves - set(payload_leaves))
        if len(leaves) > MAX_CONE_VARS:
            raise CdcError(f'{n}: capture cone of {net.key(q)} exceeds {MAX_CONE_VARS} variables')
        for env in _assignments(others):
            if any(env[a] != env[b] for a in late for b in late if late[a] == late[b]):
                continue       # an event is in flight on the synchronised count: capture may load
            seen = set()
            for penv in _assignments(payload_leaves):
                seen.add(net.evaluate(net.flops[q]['d'], {**env, **penv}, {}))
            if len(seen) > 1:
                raise CdcError(f'{n}: capture {net.key(q)} loads payload with no event on the synchronised count '
                               '(capture not gated)')
        role[q] = (n, 'capture', 0)
    for g, src, stages, pbits in resolved:
        if pbits and not any(r[0] == g['name'] and r[1] == 'capture' for r in role.values()):
            raise CdcError(f'{g["name"]}: payload has no capture register')
    for q, r in role.items():
        for k in net.names.get(q, []):
            record['roles'][k] = list(r)
        cell = net.flops[q]['cell'].lstrip('\\')
        if not cell.startswith('$'):
            record['roles'].setdefault(cell, list(r))
    record['counts'] = {r: sum(1 for x in role.values() if x[1] == r) for r in ('source', 'sync1', 'payload', 'capture')}
    if windows:
        if seam_seen != {w['name'] for w in windows}:
            raise CdcError('cdc_synchronizers seam windows without actual crossings: '
                           + str(sorted({w['name'] for w in windows} - seam_seen)))
        record['seam_roles'] = {}
        for q, name in seam_role.items():
            for key in net.names.get(q, []) + [net.flops[q]['cell'].lstrip('\\')]:
                if not key.startswith('$'):
                    record['seam_roles'][key] = [name, 'seam', 0]
        record['seam_windows'] = {w['name']: dict(src=port_domain[w['launch']], dst=port_domain[w['capture']],
                                                setup=w['setup_q'], hold=w['hold_q']) for w in windows}
    return record


def _word(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.$\[\]]*', value):
        raise CdcError('cdc_synchronizers unsupported identifier ' + repr(value))
    return '{' + value + '}'


def bindings(record):
    roles = ' '.join(_word(k) + ' {' + ' '.join(str(x) for x in r) + '}' for k, r in sorted(record['roles'].items()))
    groups = ' '.join('{' + n + '} {src ' + g['src_domain'] + ' dst ' + g['dst_domain'] + ' width ' + str(g['width'])
                      + ' payload ' + str(g['payload_bits']) + ' sync ' + repr(g['sync_max_delay_ps'])
                      + ' pay ' + repr(g['payload_max_delay_ps']) + '}' for n, g in sorted(record['groups'].items()))
    return f'set ::ot_cdc_roles [dict create {roles}]\nset ::ot_cdc_groups [dict create {groups}]\n'


CROSSING = ('          if {!$::ot_ce_related_data} {error "OT_MULTI_ROOT: cross-domain data path $source -> $cell requires '
            'explicit related profile"}\n          dict set crossing_pairs [list $source_domain $expected] 1\n')
MARKER = '  puts "OT_MULTI_ROOT OWNERSHIP PASS roots='


def extend(body, spec, root):
    # kit generation binds a receipt-cached lint (lint_receipt.py): never re-elaborated on localhost per gen/gate/submit
    import lint_receipt
    record = lint_receipt.record(KEY, lint, CdcError, spec, root, _yosys())
    if body.count(CROSSING) != 1 or body.count(MARKER) != 1:
        raise CdcError('cdc_synchronizers multi-root crossing gate changed; revalidate extension')
    body = body.replace(CROSSING, '          ot_cdc_crossing $start $pin $source $cell $source_domain $expected\n'
                                  '          continue\n')
    body = body.replace(MARKER, '  ot_cdc_complete $cells\n' + MARKER)
    extra = ''
    tcl = TCL
    if spec.get('seam_windows') is not None:
        if not record.get('seam_windows'):
            raise CdcError('mixed seam/CDC requires a fresh structurally linted seam receipt')
        roles = ' '.join(_word(k) + ' {' + ' '.join(map(str, r)) + '}'
                         for k, r in sorted(record['seam_roles'].items()))
        windows = ' '.join('{' + n + '} {' + ' '.join(f'{k} {v}' for k, v in w.items()) + '}'
                           for n, w in sorted(record['seam_windows'].items()))
        extra = f'set ::ot_cdc_seam_roles [dict create {roles}]\nset ::ot_cdc_seams [dict create {windows}]\n'
        # Use exactly the same mapped-register identity resolver as CDC; keep the namespaces disjoint.
        resolver = TCL[TCL.index('proc ot_cdc_role '):TCL.index('proc ot_cdc_bound ')]
        extra += resolver.replace('ot_cdc_role', 'ot_cdc_seam_role').replace('::ot_cdc_roles', '::ot_cdc_seam_roles')
        extra += MIXED_TCL
        tcl = tcl.replace('  if {$sg eq "" || $sg ne $tg}',
                          '  if {$sg eq "" && $tg eq ""} {\n'
                          '    ot_cdc_seam_crossing $start $pin $source $target $source_domain $target_domain\n'
                          '    return\n  }\n  if {$sg eq "" || $sg ne $tg}')
        body = body.replace('  ot_cdc_complete $cells\n', '  ot_cdc_complete $cells\n  ot_cdc_seam_complete\n')
    # The flow's sole top wrapper (ref_tile.pin_wrapper / ot_pin_regs.tcl) adds this exact namespace once.
    # The original RTL lint has no wrapper, so admit its identities after stripping ONLY that known prefix.
    wrapped = any(isinstance(spec.get(k), dict) and spec[k].get('enable') is True
                  for k in ('pin_regs', 'reset_landing'))
    if wrapped:
        for key in ('pin_regs', 'reset_landing'):
            if isinstance(spec.get(key), dict) and spec[key].get('enable') not in (True, False, None):
                raise CdcError('CDC flow wrapper enable must be a boolean')
        def normalize(text):
            text = text.replace('  set names [list $full]\n',
                                '  set names [ot_cdc_flow_names $full]\n')
            text = text.replace('        if {[dict exists $::ot_cdc_roles $n]} {dict set roles [dict get $::ot_cdc_roles $n] 1}',
                                '        foreach name [ot_cdc_flow_names $n] {\n'
                                '          if {[dict exists $::ot_cdc_roles $name]} {dict set roles [dict get $::ot_cdc_roles $name] 1}\n        }')
            text = text.replace('        if {[dict exists $::ot_cdc_seam_roles $n]} {dict set roles [dict get $::ot_cdc_seam_roles $n] 1}',
                                '        foreach name [ot_cdc_flow_names $n] {\n'
                                '          if {[dict exists $::ot_cdc_seam_roles $name]} {dict set roles [dict get $::ot_cdc_seam_roles $name] 1}\n        }')
            return text
        extra = FLOW_WRAPPER_TCL + normalize(extra)
        tcl = normalize(tcl)
    return bindings(record) + extra + tcl + '\n' + body


FLOW_WRAPPER_TCL = r'''
proc ot_cdc_flow_names {name} {
  set names [list $name]
  if {[regsub {^u_ot_pr_core[./]} $name {} core]} {
    lappend names $core
    if {[regexp {^([^$]+)\$} $core -> base]} {lappend names $base}
  }
  # LH-PGVM2 10-19: contents of kept-hierarchy instances (keep_hierarchy region / replica cells) are named with '/'
  # in the routed netlist; the lint flattens them with '.' (cdc_sync_constraints.elaborate)
  foreach n $names {if {[string first / $n] >= 0} {lappend names [string map {/ .} $n]}}
  return $names
}
'''


MIXED_TCL = r'''
# Every non-CDC dependence is an exact linted bank-source / domain pair; ordinary related data is not exempted.
set ::ot_cdc_seam_seen {}
proc ot_cdc_seam_crossing {start pin source target source_domain target_domain} {
  lassign [ot_cdc_seam_role $source] name role index
  if {$name eq "" || ![dict exists $::ot_cdc_seams $name]} {
    error "OT_CDC_SEAM: undeclared crossing $source -> $target"
  }
  set w [dict get $::ot_cdc_seams $name]
  if {$source_domain ne [dict get $w src] || $target_domain ne [dict get $w dst]} {
    error "OT_CDC_SEAM: wrong clock domains $source -> $target"
  }
  set launch [get_cells -quiet -of_objects $start]
  if {[llength $launch] != 1} {error "OT_CDC_SEAM: missing unique bank register"}
  set q [expr {[get_property [get_clocks core_clk] period] / 3.0}]
  # Same latency-inclusive semantics as seam_window_sdc, narrowed to this actual launch and capture D pin.
  set max_bound [expr {[dict get $w setup] * $q}]
  set min_bound [expr {-[dict get $w hold] * $q}]
  set_max_delay $max_bound -from $launch -to $pin
  set_min_delay $min_bound -from $launch -to $pin
  foreach kind {max min} {
    set paths [find_timing_paths -from $launch -to $pin -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" && ![info exists ::ot_mm_active]} continue
    if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
      error "OT_CDC_SEAM: missing finite bounded $kind path $source -> $target"
    }
  }
  dict incr ::ot_cdc_seam_seen $name
  puts "OT_CDC_SEAM BOUNDED $name $source -> $target"
}
proc ot_cdc_seam_complete {} {
  dict for {name window} $::ot_cdc_seams {
    if {![dict exists $::ot_cdc_seam_seen $name]} {error "OT_CDC_SEAM: missing actual bank window $name"}
  }
  puts "OT_CDC_SEAM STRUCTURAL_PASS $::ot_cdc_seam_seen (finite bounded paths, physical slack checked at signoff)"
}
'''


TCL = r'''
# OT_CDC (cdc_sync_constraints.py): reviewed synchroniser crossings only. The generator linted the elaborated
# sources (Gray source, >= 2-stage destination chain, payload published with the count, capture gated by the
# synchronised count). Every actual crossing must match a tagged pair; no other path receives an exception.
set ::ot_cdc_seen {}
proc ot_cdc_role {cell} {
  set full [string map {\\ {}} [get_full_name [get_cells $cell]]]
  set names [list $full]
  if {[regexp {^([^$]+)\$} $full -> base]} {lappend names $base}
  set roles {}
  foreach n $names {if {[dict exists $::ot_cdc_roles $n]} {dict set roles [dict get $::ot_cdc_roles $n] 1}}
  if {![dict size $roles]} {
    foreach p [get_pins -quiet -of_objects [get_cells $cell]] {
      if {[get_property $p direction] ne "output"} continue
      foreach net [get_nets -quiet -of_objects $p] {
        set n [string map {\\ {}} [get_full_name $net]]
        if {[dict exists $::ot_cdc_roles $n]} {dict set roles [dict get $::ot_cdc_roles $n] 1}
      }
    }
  }
  if {[dict size $roles] > 1} {error "OT_CDC: ambiguous synchronizer role for $cell: [dict keys $roles]"}
  if {![dict size $roles]} {return {}}
  return [lindex [dict keys $roles] 0]
}
proc ot_cdc_bound {start target bound} {
  set launch [get_cells -quiet -of_objects $start]
  if {[llength $launch] != 1} {error "OT_CDC: missing unique launch register"}
  set_max_delay -ignore_clock_latency $bound -from $launch -to $target
  set_min_delay -ignore_clock_latency 0.0 -from $launch -to $target
  foreach kind {max min} {
    set paths [find_timing_paths -from $launch -to $target -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" && ![info exists ::ot_mm_active]} {
      puts "OT_CDC PATH_DEFERRED [get_full_name $start] -> [get_full_name $target] $kind (strict at sign-off)"
      continue
    }
    if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
      error "OT_CDC: missing finite bounded $kind path [get_full_name $start] -> [get_full_name $target]"
    }
  }
}
proc ot_cdc_crossing {start pin source target source_domain target_domain} {
  if {[lindex [split [get_full_name $pin] /] end] ne "D" || [get_property $pin direction] ne "input"} {
    error "OT_CDC: cross-domain control pin [get_full_name $pin]"
  }
  lassign [ot_cdc_role $source] sg sr si
  lassign [ot_cdc_role $target] tg tr ti
  if {$sg eq "" || $sg ne $tg} {error "OT_CDC: unapproved actual crossing $source -> $target ($sg $sr -> $tg $tr)"}
  set g [dict get $::ot_cdc_groups $sg]
  if {$source_domain ne [dict get $g src] || $target_domain ne [dict get $g dst]} {
    error "OT_CDC: crossing $source -> $target is $source_domain -> $target_domain, declared [dict get $g src] -> [dict get $g dst]"
  }
  if {$sr eq "source" && $tr eq "sync1" && $si == $ti} {
    ot_cdc_bound $start $pin [dict get $g sync]
  } elseif {$sr eq "payload" && $tr eq "capture"} {
    ot_cdc_bound $start $pin [dict get $g pay]
  } else {
    error "OT_CDC: unapproved actual crossing $source -> $target ($sg $sr $si -> $tr $ti)"
  }
  dict incr ::ot_cdc_seen [list $sg $sr $si]
  puts "OT_CDC BOUNDED $sg $sr -> $tr $source -> $target"
}
proc ot_cdc_complete {cells} {
  # Every tagged register sits in its declared domain (a tag on a same-domain path is refused here).
  dict for {cell domain} $cells {
    lassign [ot_cdc_role $cell] g r i
    if {$g eq ""} continue
    set want [expr {$r in {source payload} ? [dict get $::ot_cdc_groups $g src] : [dict get $::ot_cdc_groups $g dst]}]
    if {$domain ne $want} {error "OT_CDC: synchronizer register $cell ($g $r) is in $domain, declared $want; no exception on a same-domain path"}
  }
  dict for {g info} $::ot_cdc_groups {
    for {set i 0} {$i < [dict get $info width]} {incr i} {
      if {![dict exists $::ot_cdc_seen [list $g source $i]]} {error "OT_CDC: missing actual synchronised crossing $g bit $i"}
    }
    if {[dict get $info payload] && ![dict exists $::ot_cdc_seen [list $g payload 0]]} {error "OT_CDC: missing actual payload crossing $g"}
  }
  puts "OT_CDC STRUCTURAL_PASS $::ot_cdc_seen (bounded synchroniser crossings only; no physical closure claim)"
}
'''
