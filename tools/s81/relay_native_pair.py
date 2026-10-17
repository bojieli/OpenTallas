#!/usr/bin/env python3
"""Composed NATIVE relay-pair reach bench (S-DIE H-REACH 2026-10-16, after the stnv566 electrical failure, 1f9ab4788).

The ETM pair bench (relay_reach_bench.py) times a same-phase ideal-clock pair through scalar ETMs: it cannot see the
real forwarded clock (ot_fwd_link_stage captures on negedge fi0 and INVERTS fo0, so a fo0 -> fi0 hop is a half cycle)
and it cannot see the electrical limit at the first native input cell (stnv566: 298 ps slew at 225 um vs 260 ps).

This bench composes, per sweep point, ONE FLAT netlist of the two CLOSED native station/relay netlists (driver A,
receiver B; every cell, its own routed 6_final.spef) joined by the bench's measured GRT wires (relay_reach_bench.py run
with --fwd-clock: every data bit, and the forwarded clock A.fo0 -> B.fi0 where the class has one).  Each joined net is
one SPEF D_NET = A's routed port net + the GRT top wire + B's routed port net (coupling caps grounded on their own node).
OpenSTA then times the real thing:

  fwd  (class has fo0 + fi0): one ideal clock at A's fi0 port, set_propagated_clock; B's clock = A's native clock tree ->
       fo0 driver -> routed clock wire -> B's native tree, i.e. the actual phase (inversion included) -- no neighbour-skew
       term (the skew is computed).  Base sign-off uncertainty 60 setup / 25 hold.
  tree (relay / hub station with a die-delivered ck): one clock at A's ck and B's ck ports (die delivers phase-aligned
       roots), propagated inside each view; base 60 / 25 PLUS the 80 ps neighbour skew adversely (coordinator model).

Corners: TT setup at 833.33 (stream) and 1111.1 (serial), FF hold, SS 833 setup sensitivity.  Electrical: the native
SDC's set_max_transition (260 ps) and the library max_capacitance on EVERY pin of both instances
(report_check_types -violators); a sweep point is electrically valid only with zero violations.

Measured reach (per period) = the largest swept d at which the pair has setup >= 0, FF hold >= 0 and zero
max-slew / max-cap violations, at that and every shorter swept d; reported with the worst-bit pin-to-pin Manhattan
length there (no margin; planning = 0.9 x).  UNBUFFERED: the bench inserts nothing; the wire is the hop.

Driver variants (structural comparison): --variant NAME=NETLIST substitutes A's (and B's) netlist by a native netlist
whose pin-local output buffers were swapped (relay_driver_sensitivity.py); the routed SPEF of the closed view is kept
(sensitivity: larger cells are not re-placed / re-routed), so a variant row is NOT a closed view.

    relay_native_pair.py stage --cls M --archive DIR --bench-run B --stage STAGE --out OUT [--variant N=V.v ...]
    (OUT/run.sh on ot-run)        relay_native_pair.py collect --out OUT
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

IMAGE = 'openroad/orfs:asap7lock'
T_STREAM, T_SERIAL = 833.333, 1111.111
U_SETUP, U_HOLD, SKEW = 60.0, 25.0, 80.0
CORNERS = (('tt833', 'tt', T_STREAM, 'max'), ('tt1111', 'tt', T_SERIAL, 'max'), ('ff_hold', 'ff', T_STREAM, 'min'),
           ('ss833', 'ss', T_STREAM, 'max'))
CLOCK_PORTS = ('fi0', 'ck', 'cw')
ASAP7_NLDM = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'
RVT_LIBS = ('asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz', 'asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz',
            'asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz', 'asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib',
            'asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz')
CONST_RE = re.compile(r"^\d+'[bhd]")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def san(x):
    x = x.strip().replace('\\', '').strip()
    return re.sub(r'[^A-Za-z0-9_]', '_', x)


# ------------------------------------------------------------------------------------------------ netlist
def parse_verilog(text):
    """OpenROAD write_verilog flat module -> (module, ports{name: (dir, msb, lsb) }, cells[(cell, inst, [(pin, net)])])"""
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    mod = re.search(r'\bmodule\s+(\S+)\s*\(', text).group(1)
    body = text[text.index(';', text.index('module')) + 1:text.rindex('endmodule')]
    ports = {}
    for m in re.finditer(r'\b(input|output|inout)\s*(?:\[(\d+):(\d+)\])?\s*([^;]+);', body):
        for n in m.group(4).split(','):
            ports[n.strip()] = (m.group(1), int(m.group(2)) if m.group(2) else None, int(m.group(3)) if m.group(3) else None)
    alias = {}
    for m in re.finditer(r'\bassign\s+(\\\S+|[^=\s]+)\s*=\s*(\\\S+|[^;\s]+)\s*;', body):
        alias[m.group(2).strip()] = m.group(1).strip()      # assign PORT = NET: NET is the port's net
    body = re.sub(r'\bassign\b[^;]*;', '', body)
    cells = []
    stmts = body.split(';')
    for s in stmts:
        s = s.strip()
        if not s or re.match(r'^(input|output|inout|wire)\b', s):
            continue
        m = re.match(r'^(\S+)\s+(\\\S+|\S+)\s*\((.*)\)\s*$', s, re.S)
        if not m:
            raise ValueError(f'unparsed statement: {s[:120]}')
        conns = [(p, n.strip()) for p, n in re.findall(r'\.(\w+)\s*\(\s*((?:\\\S+\s*)|[^()]*?)\s*\)', m.group(3))]
        if not conns:          # physical-only cells (fillers / decaps written from an ODB): no timing role
            continue
        cells.append((m.group(1), m.group(2).strip(), conns))
    if alias:
        # OpenROAD write_verilog: `assign dq[8] = \\dq[8]9 ;` makes \\dq[8]9 the PORT net, while a bare dq[8] in a cell
        # connection is the INTERNAL net literally named "dq[8]" (its SPEF D_NET has no *P).  Keep them apart: the bare
        # name becomes the escaped internal net, the alias becomes the port bit.
        assigned = set(alias.values())
        cells = [(c, i, [(p, alias.get(n, '\\' + n if n in assigned else n)) for p, n in conns]) for c, i, conns in cells]
    return mod, ports, cells


def port_bits(ports):
    out = {}
    for n, (d, hi, lo) in ports.items():
        if hi is None:
            out[n] = d
        else:
            for i in range(min(hi, lo), max(hi, lo) + 1):
                out[f'{n}[{i}]'] = d
    return out


# ------------------------------------------------------------------------------------------------ spef
def parse_spef(text):
    """-> dict(cu, ru, nets{name: dict(conn[(kind, node, dir, cell)], caps[(n1, n2|None, c)], res[(n1, n2, r)])})
    with names resolved through *NAME_MAP; cu / ru = multipliers to FF / KOHM"""
    hdr, _, rest = text.partition('*D_NET')
    cu = {'PF': 1000.0, 'FF': 1.0}[re.search(r'\*C_UNIT\s+1\s+(\w+)', hdr).group(1).upper()]
    ru = {'OHM': 0.001, 'KOHM': 1.0}[re.search(r'\*R_UNIT\s+1\s+(\w+)', hdr).group(1).upper()]
    nm = {}
    if '*NAME_MAP' in hdr:
        sec = hdr.split('*NAME_MAP', 1)[1].split('*PORTS', 1)[0]
        for line in sec.splitlines():
            s = line.split(None, 1)
            if len(s) == 2 and s[0].startswith('*'):
                nm[s[0]] = s[1].strip()

    def res_name(tok):
        if tok.startswith('*'):
            if ':' in tok:
                a, b = tok.split(':', 1)
                return nm.get(a, a) + ':' + b
            return nm.get(tok, tok)
        return tok
    nets = {}
    for blk in ('*D_NET' + rest).split('*D_NET ')[1:]:
        lines = blk.splitlines()
        name = res_name(lines[0].split()[0])
        conn, caps, res, sec = [], [], [], None
        for line in lines[1:]:
            s = line.split()
            if not s:
                continue
            if s[0] in ('*CONN', '*CAP', '*RES', '*END'):
                sec = s[0]
                continue
            if sec == '*CONN' and s[0] in ('*P', '*I'):
                cell = s[s.index('*D') + 1] if '*D' in s else None
                conn.append((s[0], res_name(s[1]), s[2], cell))
            elif sec == '*CAP':
                if len(s) == 3:
                    caps.append((res_name(s[1]), None, float(s[2]) * cu))
                else:
                    caps.append((res_name(s[1]), res_name(s[2]), float(s[3]) * cu))
            elif sec == '*RES':
                res.append((res_name(s[1]), res_name(s[2]), float(s[3]) * ru))
        nets[name] = dict(conn=conn, caps=caps, res=res)
    return nets


class Merged:
    """one merged flat D_NET: node renaming into a common namespace"""

    def __init__(self, name):
        self.name, self.conn, self.caps, self.res, self.n = name, {}, [], [], 0
        self.alias = {}

    def node(self, key):
        if key not in self.alias:
            self.n += 1
            self.alias[key] = f'{self.name}:{self.n}'
        return self.alias[key]

    def add(self, net, inst_map, port_map, tag):
        """inst_map(inst) -> flat inst name; port_map(port) -> ('port', top port) | ('node', junction key) | None"""
        own = set()
        conn_nodes = {}
        for kind, node, d, cell in net['conn']:
            if kind == '*I':
                inst, pin = node.rsplit(':', 1)
                fn = f'{inst_map(inst)}:{pin}'
                self.conn[fn] = ('*I', d, cell)
                conn_nodes[node] = fn
            else:
                pm = port_map(node)
                if pm is None:
                    conn_nodes[node] = self.node((tag, 'port', node))
                elif pm[0] == 'port':
                    self.conn[pm[1]] = ('*P', d, None)
                    conn_nodes[node] = pm[1]
                else:
                    conn_nodes[node] = self.node(pm[1])
            own.add(node)

        def map_node(tok):
            if tok in conn_nodes:
                return conn_nodes[tok]
            return self.node((tag, tok))

        def is_own(tok, netname):
            return tok in own or tok.startswith(netname + ':')
        netname = net.get('_name')
        for a, b, c in net['caps']:
            if b is None:
                self.caps.append((map_node(a), c))
            elif is_own(a, netname):
                self.caps.append((map_node(a), c))
            elif is_own(b, netname):
                self.caps.append((map_node(b), c))
        for a, b, r in net['res']:
            self.res.append((map_node(a), map_node(b), r))

    def text(self):
        tot = sum(c for _, c in self.caps)
        out = [f'*D_NET {self.name} {tot:.6g}', '*CONN']
        for n, (k, d, cell) in self.conn.items():
            out.append(f'{k} {n} {d}' + (f' *D {cell}' if cell else ''))
        caps = collections.defaultdict(float)
        for n, c in self.caps:
            caps[n] += c
        out.append('*CAP')
        out += [f'{i + 1} {n} {c:.6g}' for i, (n, c) in enumerate(sorted(caps.items()))]
        out.append('*RES')
        out += [f'{i + 1} {a} {b} {r:.6g}' for i, (a, b, r) in enumerate(self.res)]
        out.append('*END\n')
        return '\n'.join(out)


# ------------------------------------------------------------------------------------------------ stage
def extract_archive(archive, cell, binding_tt_sha, binding_job=None):
    man = json.loads((archive / 'manifest.json').read_text())
    got = {}
    for f in man['files']:
        name = Path(f['path']).name
        if '/base/' not in f['path'] or name not in ('6_final.spef', '6_final.v', '6_final.sdc'):
            continue
        p = archive / 'run' / f['stored']
        raw = subprocess.run(['zstd', '-dc', str(p)], check=True, stdout=subprocess.PIPE).stdout \
            if f.get('compression') == 'zstd' else p.read_bytes()
        if sha(raw) != f['sha256']:
            raise ValueError(f'archive checksum mismatch {p}')
        got[name] = (raw.decode(), f['sha256'])
    if len(got) != 3:
        raise ValueError(f'{archive}: 6_final spef/v/sdc incomplete ({sorted(got)})')
    def rd(p):
        if p.exists():
            return p.read_bytes()
        z = Path(str(p) + '.zst')
        return subprocess.run(['zstd', '-dc', str(z)], check=True, stdout=subprocess.PIPE).stdout
    vdir = archive / 'run' / 'record' / 'views' / cell
    if not vdir.is_dir():
        # older closure-loop archives keep no record/views export: identity by the bound job id only (recorded),
        # standard ASAP7 RVT NLDM libraries (the closure flow's set) for each corner
        if man.get('job') != binding_job:
            raise ValueError(f'{cell}: archive job {man.get("job")} != bound job {binding_job}')
        heads = {c: ''.join(f'read_liberty {ASAP7_NLDM}/{f.format(C=c.upper())}\n' for f in RVT_LIBS)
                 for c in ('tt', 'ff', 'ss')}
        man['_identity'] = 'job id only (archive has no record/views ETM export to hash)'
        return man, got, heads
    tt = rd(vdir / f'{cell}_tt.lib')
    if sha(tt) != binding_tt_sha:
        raise ValueError(f'{cell}: archived ETM differs from the bound view (die binding sha256)')
    heads = {c: rd(vdir / f'export_{c}.tcl').decode().split('read_db ', 1)[0] for c in ('tt', 'ff', 'ss')}
    man['_identity'] = 'archived ETM sha256 == bound view sha256'
    return man, got, heads


def cmd_stage(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    srec = json.loads((Path(a.stage) / 'stage.json').read_text())['classes'][a.cls]
    model = json.loads((Path(a.stage) / 'views' / a.cls / 'model.json').read_text())
    man, got, heads = extract_archive(Path(a.archive), a.cls, srec['files']['tt']['sha256'], srec.get('job'))
    spef_txt, spef_sha = got['6_final.spef']
    v_txt, v_sha = got['6_final.v']
    sdc_txt = got['6_final.sdc'][0]
    mt = re.search(r'set_max_transition\s+([\d.]+)', sdc_txt)
    max_tr = float(mt.group(1)) if mt else None
    native = parse_spef(spef_txt)
    for k_, n_ in native.items():
        n_['_name'] = k_
    port_net = {}
    for name, n in native.items():
        for kind, node, d, cell in n['conn']:
            if kind == '*P':
                port_net[node] = name
    variants = {'native': (v_txt, v_sha)}
    for spec in a.variant or []:
        nm, path = spec.split('=', 1)
        raw = Path(path).read_bytes()
        variants[nm] = (raw.decode(), sha(raw))
    bench = Path(a.bench_run)
    mp = json.loads((bench / 'map.json').read_text())
    sp = bench / 'reach.spef.gz'
    btxt = gzip.decompress(sp.read_bytes()).decode() if sp.exists() else (bench / 'reach.spef').read_text()
    bnets = parse_spef(btxt)
    for k_, n_ in bnets.items():
        n_['_name'] = k_
    pin2net, net_bufin = {}, collections.defaultdict(list)
    bcell = {}
    for nn, n_ in bnets.items():
        for kind, node, d_, cell in n_['conn']:
            if kind != '*I':
                continue
            inst, pin = node.rsplit(':', 1)
            pin2net[(inst, pin)] = nn
            if not re.match(r'^P\d+_[AB]$', inst):
                bcell[inst] = cell
                if d_ == 'I':
                    net_bufin[nn].append(inst)

    def chain(bA, op, bB, ip, start_name):
        """bench nets and repeaters from bA.op to bB.ip (repair_design repeaters; one net when unbuffered)"""
        net = pin2net.get((bA, op)) or (start_name if start_name in bnets else None)
        if net is None:
            raise ValueError(f'bench SPEF lacks the net of {bA}:{op}')
        nets, bufs = [net], []
        while (bB, ip) not in [tuple(c[1].rsplit(':', 1)) for c in bnets[net]['conn'] if c[0] == '*I']:
            nxt = net_bufin.get(net, [])
            if len(nxt) != 1:
                raise ValueError(f'repeater chain {bA}:{op} -> {bB}:{ip} breaks at {net} ({nxt})')
            b_ = nxt[0]
            net = pin2net[(b_, 'Y')]
            bufs.append(b_)
            nets.append(net)
            if len(nets) > 200:
                raise ValueError('repeater chain loop')
        return nets, bufs
    pairs = sorted((i for i in mp['insts'] if i['cls'] == a.cls), key=lambda i: i['d'])
    if a.d_max:
        pairs = [i for i in pairs if i['d'] <= a.d_max]
    if not pairs:
        raise ValueError(f'{bench}: no pair of {a.cls}')
    fwd = bool(mp.get('fclk')) and any(f['cls'] == a.cls for f in mp['fclk'].values())
    clocks = [c for c in CLOCK_PORTS if any(p.split('[')[0] == c for p in port_bits(parse_verilog(v_txt)[1]))]
    rec = dict(schema='opentallas.s81.relay_native_pair_stage.v1', cls=a.cls, archive=str(a.archive), job=man['job'],
               consumed={'6_final.spef': spef_sha, '6_final.v': v_sha}, etm_tt_sha256=srec['files']['tt']['sha256'],
               bench_run=str(bench), identity=man.get('_identity'), clock_mode='fwd' if fwd else 'tree', clock_ports=clocks, max_transition_ps=max_tr,
               variants={k: s for k, (_, s) in variants.items()}, points={})
    for vn, (vt, _) in variants.items():
        vd = out / vn
        vd.mkdir(exist_ok=True)
        mod, ports, cells = parse_verilog(vt)
        pb = port_bits(ports)
        V, S, top_ports, wires = [], [], {}, set()
        for pr in pairs:
            k = pr['k']
            joins = {}           # (inst side, port bit) -> junction net name
            jl = []
            for p in model['pairs']:
                if p['dir'] == 'skip':
                    continue
                src, dst = ('a', 'b') if p['dir'] == 'fwd' else ('b', 'a')
                for bit, op in p['out_pins'].items():
                    ip = p['in_pins'][bit]
                    bn = f'n{k}_{p["out"]}' + ('' if bit == 'None' or p['width'] == 1 else f'[{bit}]')
                    jl.append((f'k{k}_w_{san(op)}', bn, src, op, dst, ip))
            if fwd:
                jl.append((f'k{k}_fck', f'n{k}_fck[0]' if f'n{k}_fck[0]' in bnets else f'n{k}_fck', 'a', 'fo0[0]', 'b', 'fi0[0]'))
            chains = []
            for jn, bn, src, op, dst, ip in jl:
                bA = f'P{k}_A' if src == 'a' else f'P{k}_B'
                bB = f'P{k}_B' if dst == 'b' else f'P{k}_A'
                nets_, bufs_ = chain(bA, _bench_pin(op, bA, pin2net), bB, _bench_pin(ip, bB, pin2net), bn)
                names = [jn] if len(nets_) == 1 else [jn] + [f'{jn}_r{i_}' for i_ in range(1, len(nets_) - 1)] + [f'{jn}_z']
                joins[(src, op)] = names[0]
                joins[(dst, ip)] = names[-1]
                chains.append((names, nets_, bufs_, src, op, dst, ip, bA, bB))
            netname = {}

            def flat_net(side, x):
                x = x.strip()
                if x in pb:
                    if (side, x) in joins:
                        return joins[(side, x)]
                    base = x.split('[')[0]
                    if base in clocks and (side == 'a' or not fwd):
                        pn = f'k{k}_ck{side}' if not fwd else f'k{k}_ck'
                        top_ports[pn] = 'input'
                        return pn
                    nmx = f'k{k}{side}_p_{san(x)}'
                    if pb[x] == 'input':
                        top_ports[nmx] = 'input'
                    else:
                        wires.add(nmx)
                    return nmx
                nmx = f'k{k}{side}_{san(x)}'
                wires.add(nmx)
                return nmx
            for side in ('a', 'b'):
                for cell, inst, conns in cells:
                    cs = ', '.join('.%s(%s)' % (pn, flat_net(side, n) if n and not CONST_RE.match(n) else n)
                                   for pn, n in conns)
                    V.append(f' {cell} k{k}{side}_{san(inst)} ({cs});')
            nrep = 0
            for names, nets_, bufs_, *_ in chains:
                wires.update(names)
                for i_, b_ in enumerate(bufs_):
                    V.append(f' {bcell[b_]} k{k}_rb_{san(b_)} (.A({names[i_]}), .Y({names[i_ + 1]}));')
                nrep += len(bufs_)
            # SPEF: every native net of both sides; port nets that join are merged with the bench wire
            merged = {}
            imap = lambda i: i if re.match(r'^P\d+_[AB]$', i) else f'k{k}_rb_{san(i)}'  # noqa: E731
            for names, nets_, bufs_, src, op, dst, ip, bA, bB in chains:
                for i_, (fn_, bn_) in enumerate(zip(names, nets_)):
                    M = Merged(fn_)
                    merged[fn_] = M
                    M.add(bnets[bn_], imap, lambda p_: None, 'w')
                    for key in list(M.conn):     # the view-instance pins become the native junction nodes
                        if key.startswith(bA + ':') or key.startswith(bB + ':'):
                            del M.conn[key]
                    if i_ == 0:
                        _rekey(M, f'{bA}:{_bench_pin(op, bA, pin2net)}', M.node(('j', src, op)))
                    if i_ == len(nets_) - 1:
                        _rekey(M, f'{bB}:{_bench_pin(ip, bB, pin2net)}', M.node(('j', dst, ip)))
            done = set()
            for side in ('a', 'b'):
                for name, n in native.items():
                    ports_here = [node for kind, node, d, c in n['conn'] if kind == '*P']
                    jn = next((joins[(side, pt)] for pt in ports_here if (side, pt) in joins), None)
                    if jn:
                        M = merged[jn]
                        pt = next(pt for pt in ports_here if (side, pt) in joins)
                        M.add(n, lambda i, s=side: f'k{k}{s}_{san(i)}',
                              lambda p, s=side, pt=pt: ('node', ('j', s, pt)) if p == pt else None, side)
                        continue
                    fname = None
                    for pt in ports_here:
                        fname = flat_net(side, pt)
                    if fname is None:
                        fname = f'k{k}{side}_{san(name)}'
                    if fname in done:
                        continue
                    done.add(fname)
                    M = Merged(fname)
                    M.add(n, lambda i, s=side: f'k{k}{s}_{san(i)}',
                          lambda p, f=fname: ('port', f) if f in top_ports else None, side)
                    S.append(M.text())
            S += [M.text() for M in merged.values()]
            rec['points'][str(k)] = dict(d=pr['d'], bits=len(jl) - (1 if fwd else 0), repeaters=nrep,
                                         L_max=max((s['L'] for pin, s in mp['sinks'].items()
                                                    if pin.startswith(f'P{k}_')), default=None))
        hdr = ['*SPEF "ieee 1481-1999"', '*DESIGN "pair_top"', '*DATE "-"', '*VENDOR "OpenTallas"',
               '*PROGRAM "relay_native_pair.py"', '*VERSION "1"', '*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"',
               '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER []', '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 KOHM',
               '*L_UNIT 1 HENRY', '', '*PORTS'] + [f'{p} I' for p in sorted(top_ports)] + ['']
        (vd / 'pair.spef').write_text('\n'.join(hdr) + '\n' + '\n'.join(S))
        vl = ['module pair_top (' + ', '.join(sorted(top_ports)) + ');']
        vl += [f' input {p};' for p in sorted(top_ports)]
        vl += [f' wire {w};' for w in sorted(wires - set(top_ports))]
        (vd / 'pair.v').write_text('\n'.join(vl + V + ['endmodule']) + '\n')
        for name, corner, per, chk in CORNERS:
            unc_s = U_SETUP + (0 if fwd else SKEW)
            unc_h = U_HOLD + (0 if fwd else SKEW)
            clk_ports = sorted(p for p in top_ports if re.match(r'^k\d+_ck', p))
            ks = sorted(int(x) for x in rec['points'])
            tcl = heads[corner].replace('read_lef', '#read_lef') + f"""
read_verilog /work/pair.v
link_design pair_top
read_spef /work/pair.spef
create_clock -name clk -period {per} [get_ports {{{' '.join(clk_ports)}}}]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup {unc_s} [all_clocks]
set_clock_uncertainty -hold {unc_h} [all_clocks]
{f'set_max_transition {max_tr} [current_design]' if max_tr else ''}
foreach k {{{' '.join(map(str, ks))}}} {{
  puts "OT_PAIR $k"
  report_checks -through [get_nets -quiet k${{k}}_w_*] -path_delay {chk} -format end -group_path_count 100000 -endpoint_path_count 1 -digits 2
  puts "OT_PAIR_END $k"
}}
set mid [lindex {{{' '.join(map(str, ks))}}} [expr {{{len(ks)} / 2}}]]
report_checks -through [get_nets k${{mid}}_w_*] -path_delay {chk} -format full_clock_expanded -fields {{slew cap}} -digits 1
report_check_types -max_slew -max_capacitance -violators > /work/{name}.drv
puts OT_NATIVE_PAIR_DONE
"""
            (vd / f'sta_{name}.tcl').write_text(tcl)
    (out / 'stage.json').write_text(json.dumps(rec, indent=1))
    (out / 'run.sh').write_text(f"""#!/bin/bash
# relay_native_pair: one sta session per variant x corner (flat composed native pair, merged SPEF).
# DECLARE 24 GB to ot-heavy (ot-run --mem 24): at most 4 sessions at a time, each docker --memory=6g; peak RSS logged.
set -u
B=$(cd "$(dirname "$0")" && pwd)
for v in {' '.join(variants)}; do [ -f $B/$v/pair.spef ] || gunzip -kf $B/$v/pair.spef.gz; done
one() {{ v=$1; c=$2; docker run --rm --name npair_$(basename $B)_${{v}}_$c --cpus=1 --memory=6g -v $B/$v:/work -w /work {IMAGE} \\
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v sta -no_init -exit /work/sta_$c.tcl > /work/sta_$c.log 2>&1; chmod -R a+rwX /work"; }}
export -f one; export B
for v in {' '.join(variants)}; do for c in {' '.join(c[0] for c in CORNERS)}; do echo "$v $c"; done; done | xargs -P 4 -L 1 bash -c 'one $0 $1'
rc=0
for v in {' '.join(variants)}; do for c in {' '.join(c[0] for c in CORNERS)}; do grep -q OT_NATIVE_PAIR_DONE $B/$v/sta_$c.log || {{ echo STA_FAIL $v $c; rc=1; }}; done; done
for v in {' '.join(variants)}; do rm -f $B/$v/pair.spef; done
[ $rc = 0 ] && echo NATIVE_PAIR_DONE
exit $rc
""")
    (out / 'run.sh').chmod(0o755)
    print(f'{a.cls}: {len(pairs)} points, variants {list(variants)}, clock {rec["clock_mode"]} -> {out}')


def _bench_pin(pin, inst, pin2net):
    """bench pin name of a view pin: the bench may have scalarized a 1-bit bus (dq[0] -> dq)"""
    if (inst, pin) in pin2net:
        return pin
    b = pin.split('[')[0]
    return b if (inst, b) in pin2net else pin


def _rekey(M, old, new):
    """replace node `old` (a bench view-port pin) by junction node `new` in M's caps / res"""
    M.caps = [(new if n == old else n, c) for n, c in M.caps]
    M.res = [(new if a == old else a, new if b == old else b, r) for a, b, r in M.res]


# ------------------------------------------------------------------------------------------------ collect
def parse_end_report(text):
    """OT_PAIR k / report_checks -format end blocks -> {k: dict(slack, end, fails, n)} (worst endpoint per pair)"""
    out = {}
    for m in re.finditer(r'OT_PAIR (\d+)\n(.*?)OT_PAIR_END \1', text, re.S):
        rows = []
        for line in m.group(2).splitlines():
            s = [t for t in line.split() if not t.startswith('(')]
            if len(s) >= 4 and re.match(r'^k\d+[ab]_', s[0]):
                try:
                    rows.append((float(s[-1]), s[0]))
                except ValueError:
                    pass
        k = int(m.group(1))
        out[k] = None if not rows else dict(slack=min(rows)[0], end=min(rows)[1], start=None,
                                            fails=sum(1 for r in rows if r[0] < 0), n=len(rows))
    return out


def parse_drv(p):
    """report_check_types -max_slew -max_capacitance -violators -> {k: dict(slew_n, slew_max, cap_n, cap_worst)}
    slew_max = the largest violating transition (ps) of pair k; cap_worst = worst max-cap slack (fF)"""
    if not p.exists():
        return None
    out = collections.defaultdict(lambda: dict(slew_n=0, slew_max=0.0, cap_n=0, cap_worst=0.0))
    sec = None
    for line in p.read_text().splitlines():
        if line.startswith('max slew'):
            sec = 'slew'
        elif line.startswith('max capacitance'):
            sec = 'cap'
        s = line.split()
        if sec and len(s) >= 4 and 'VIOLATED' in line and re.match(r'^k\d+[ab]_', s[0]):
            k = int(re.match(r'^k(\d+)', s[0]).group(1))
            if sec == 'slew':
                out[k]['slew_n'] += 1
                out[k]['slew_max'] = max(out[k]['slew_max'], float(s[2]))
            else:
                out[k]['cap_n'] += 1
                out[k]['cap_worst'] = min(out[k]['cap_worst'], float(s[3]))
    return out


SLEW_LIMITS = (260.0, 320.0)    # native block SDC set_max_transition (gate) / ASAP7 library default_max_transition


def cmd_collect(a):
    out = Path(a.out)
    rec = json.loads((out / 'stage.json').read_text())
    res = dict(schema='opentallas.s81.relay_native_pair.v1', cls=rec['cls'], job=rec['job'],
               clock_mode=rec['clock_mode'], max_transition_ps=rec['max_transition_ps'], variants={})
    for vn in rec['variants']:
        vd = out / vn
        rows = {}
        for name, *_ in CORNERS:
            log = vd / f'sta_{name}.log'
            if not log.exists() or 'OT_NATIVE_PAIR_DONE' not in log.read_text(errors='ignore'):
                rows[name] = None
                continue
            rows[name] = parse_end_report(log.read_text(errors='ignore'))
        drv = {name: parse_drv(vd / f'{name}.drv') for name, *_ in CORNERS}
        pts = []
        for k, pt in sorted(rec['points'].items(), key=lambda kv: kv[1]['d']):
            k = int(k)
            g = lambda c: (rows.get(c) or {}).get(k)  # noqa: E731
            z = dict(slew_n=0, slew_max=0.0, cap_n=0, cap_worst=0.0)
            e_tt = (drv['tt833'] or {}).get(k, z)
            e_ff = (drv['ff_hold'] or {}).get(k, z)
            pts.append(dict(d=pt['d'], L_max=pt['L_max'],
                            tt833=g('tt833') and g('tt833')['slack'], tt1111=g('tt1111') and g('tt1111')['slack'],
                            ff_hold=g('ff_hold') and g('ff_hold')['slack'], ss833=g('ss833') and g('ss833')['slack'],
                            worst_end_tt833=g('tt833') and g('tt833')['end'],
                            slew_viol_tt=e_tt['slew_n'], max_slew_tt_ps=e_tt['slew_max'] or None,
                            slew_viol_ff=e_ff['slew_n'], max_slew_ff_ps=e_ff['slew_max'] or None,
                            cap_viol_tt=e_tt['cap_n'], cap_viol_ff=e_ff['cap_n'],
                            drv_tt=e_tt['slew_n'] + e_tt['cap_n'], drv_ff=e_ff['slew_n'] + e_ff['cap_n']))

        def electrical_ok(p, lim):
            if p['cap_viol_tt'] or p['cap_viol_ff']:
                return False
            return max(p['max_slew_tt_ps'] or 0.0, p['max_slew_ff_ps'] or 0.0) <= lim

        def reach(key, lim=SLEW_LIMITS[0]):
            """ceiling: last swept d of the initial run with setup >= 0 and zero TT/FF electrical violations; floor:
            smallest d from which FF hold >= 0 at every point up to the ceiling (None: hold fails at the ceiling)"""
            best, first_fail = None, None
            for p in pts:
                if p[key] is not None and p[key] >= 0 and electrical_ok(p, lim):
                    best = p
                else:
                    first_fail = p
                    break
            floor = None
            if best is not None:
                upto = [p for p in pts if p['d'] <= best['d']]
                for i_ in range(len(upto) - 1, -1, -1):
                    if upto[i_]['ff_hold'] is None or upto[i_]['ff_hold'] < 0:
                        break
                    floor = upto[i_]
            return best, first_fail, floor
        r = {}
        for key, lab in (('tt833', 'stream'), ('tt1111', 'serial')):
            b, ff, fl = reach(key)
            ok = b is not None and fl is not None
            r[lab] = dict(reach_d_um=b and b['d'], reach_L_um=b and b['L_max'], slack_at_reach_ps=b and b[key],
                          hold_floor_d_um=fl and fl['d'], hold_floor_L_um=fl and fl['L_max'],
                          window_valid=ok, first_fail_d_um=ff and ff['d'], first_fail_reason=_why(ff, key))
            b2, ff2, fl2 = reach(key, SLEW_LIMITS[1])
            r[lab]['sensitivity_slew320'] = dict(reach_d_um=b2 and b2['d'], reach_L_um=b2 and b2['L_max'],
                                                 window_valid=b2 is not None and fl2 is not None)
        res['variants'][vn] = dict(sha256=rec['variants'][vn], points=pts, **r)
    (out / 'result.json').write_text(json.dumps(res, indent=1))
    for vn, v in res['variants'].items():
        print(vn, 'stream', v['stream'], 'serial', v['serial'])


def _why(p, key):
    if p is None:
        return None
    w = []
    if p[key] is None or p[key] < 0:
        w.append(f'setup {p[key]}')
    if p['ff_hold'] is None or p['ff_hold'] < 0:
        w.append(f'hold {p["ff_hold"]}')
    if p['drv_tt'] or p['drv_ff']:
        w.append(f'electrical: slew>260 {p["slew_viol_tt"]}/{p["slew_viol_ff"]} pins (TT/FF) max '
                 f'{max(p["max_slew_tt_ps"] or 0, p["max_slew_ff_ps"] or 0):.1f} ps, max-cap {p["cap_viol_tt"]}/{p["cap_viol_ff"]}')
    return '; '.join(w)


def cmd_stage_many(a):
    """stage every class of the given bench batches whose bound job has a closed archive under --archive-root"""
    srec = json.loads((Path(a.stage) / 'stage.json').read_text())['classes']
    for b in a.bench_run:
        cls = sorted({i['cls'] for i in json.loads((Path(b) / 'map.json').read_text())['insts']})
        for m in cls:
            if a.only and m not in a.only:
                continue
            out = Path(a.out_root) / m
            arch = Path(a.archive_root) / m / str(srec[m].get('job'))
            if not (arch / 'manifest.json').exists():
                print(f'{m}: NOT STAGED (no closed archive {arch})')
                continue
            try:
                cmd_stage(argparse.Namespace(cls=m, archive=str(arch), bench_run=b, stage=a.stage, out=str(out),
                                             variant=None, d_max=a.d_max))
            except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as e:
                print(f'{m}: NOT STAGED ({type(e).__name__}: {e})')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('stage')
    s.add_argument('--cls', required=True)
    s.add_argument('--archive', required=True)
    s.add_argument('--bench-run', required=True, help='relay_reach_bench batch dir (map.json + reach.spef[.gz])')
    s.add_argument('--stage', required=True)
    s.add_argument('--out', required=True)
    s.add_argument('--variant', action='append', help='NAME=netlist.v (native netlist with swapped output drivers)')
    s.add_argument('--d-max', type=float)
    s2 = sp.add_parser('stage-many')
    s2.add_argument('--bench-run', action='append', required=True)
    s2.add_argument('--stage', required=True)
    s2.add_argument('--archive-root', default='/home/ubuntu/closed_archive')
    s2.add_argument('--out-root', required=True)
    s2.add_argument('--only', nargs='*')
    s2.add_argument('--d-max', type=float)
    c = sp.add_parser('collect')
    c.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    {'stage': cmd_stage, 'stage-many': cmd_stage_many, 'collect': cmd_collect}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
