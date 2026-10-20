#!/usr/bin/env python3
"""KV-HEALTH 10-19: install the continuous registered health plane into the laned KV die netlist (prep step).

Owner 10-19 12:41: PER-LAYER health retirement accepted (+7,680 edges/token, 2.985 %).  STATUS sits after the complete
closed fault path from every source; continuous sticky global health stays live (never gated / cleared / masked) and
later health blocks subsequent admission.  The 357-source contract (kv_retirement_contract.py, claude/kv-retire-1019):
STATUS = cutoff 1785 + DMAX (worst source -> AFR edges, incl. the 36 AHUB hf -> ufh edges of the existing ufh source) +
the 15-edge AFR / face / TX / link / consumer suffix; reserved here at a fixed 1998 (see STATUS_RESERVED: same padded
token period as the accepted 1982).  This pass makes that plane die source.

  kv_health_plane.py install --run RUN [--strict]      (kvsys_prep.sh, OT_KV_HEALTH=1, after the forwarded lanes)

Sources (generic rules on the laned case_kv/die.v + elements.lef; every rule names its owner when absent):
  * every landing qkd_landsh_<W> / qkd_landsh0_<W> `fault` (sticky ring-epoch fault, cleared by its receiving rs);
  * kc_<st>.kf (qkd_ctrl_kc, NOT sticky -> an explicit sticky latch beside it) once the die KC master exposes `kf`;
  * dcal fault (`flt` / `fault`) unless already consumed (OT_KV_DCAL_FLT: dcal flt -> afr d[8], priced by the contract);
  * every other OUTPUT pin named fault / flt / kf / pcf / hfault / *_fault of a die master that has no reader is
    reported as an UNADMITTED source (never silently dropped);
  * existing_ufh: the old kvs_attn.ufh net (AHUB hf) becomes one leaf; the final sticky sink drives kvs_attn.ufh.
Topology: kv_fault_topology.propose (codex 1f4241db0 / a1c24018d lineage, logically benched on 356/357 sources):
per clock root a geometric fold of neighbour pairs (<= 405 um a hop), cross-root via spare payload bits of the existing
stack -> core forwarded lanes (no new crossing; the bit rides every station and the landed ring), final sticky beside
kvs_attn.  Cell masters (structural safety: NO reset fanout added except at sticky cells):
  join   -> qkd_hp_or2            q <= a | b, no reset (pure pipeline OR; flushes by data after source clear)
  pipe   -> qkd_rlys_1            closed 1-bit relay standard, no reset
  sticky -> qkd_astk_fault_join   q <= a | q, async reset = the source's / consumer's own regional reset
The sink's region is held >= 273 edges after a re-assert (qkd_rst_region_pr_h273), covering source clear + plane depth.

Outputs: case_kv/{die.v, place.tcl, elements.lef, die.v.pads.json} rewritten (originals *.prehealth), libs + views.json
+ expand.json leaves for the three masters, RUN/health_plane.json (inventory, plan, emitted cells, leaf latencies,
reach audit, STATUS budget) and RUN/health_successor.json (kv_retirement_contract --successor input).
A missing source family / a plane deeper than the reserved DMAX writes RUN/HEALTH_DIAGNOSTIC (NOT a die result) or,
with --strict, fails.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import die_port_bind as P          # noqa: E402
import kv_fault_topology as T      # noqa: E402

REACH = 405.0
# STATUS reservation.  kv_retirement_contract (claude/kv-retire-1019): STATUS = cutoff 1785 + DMAX + suffix 15; its model
# plane gave DMAX 182 -> STATUS 1982, per-layer price +7,680 padded edges/token (owner-accepted 2.985 %).  The padded
# period has room: unpadded tail 256,553 + 36 x (delay - 197) <= 257,280 for delay <= 217 (price.json token_period_pad),
# so any STATUS <= 2002 costs exactly the accepted 257,280.  KV-HEALTH reserves a FIXED STATUS 1998 (delay 213,
# compiled_end 1999): DMAX budget 198 for the actual plane (v4 floorplan: 183) with 15 edges for the KC / DCAL / PC
# sources still to be exported -- one compiled constant, no per-floorplan image churn, zero extra token edges.
STATUS_RESERVED = 1998
DMAX_RESERVED = STATUS_RESERVED - 1785 - 15
AHUB_UFH_EDGES = 36                # AHUB hf -> attention.ufh (34 plain + hub u_core rn[3] 2), kv_retirement_contract
CORNERS = ('tt', 'ff', 'ss')
NETLIST_ONLY = False
MASTERS = dict(
    join=dict(master='qkd_hp_or2', rtl='rtl/qwen_sys/kv_health_20261019/qkd_hp_or2.sv',
              view='physical/ref_tile/qkd_hp_or2/views/qkd_hp_or2'),
    pipe=dict(master='qkd_rlys_1', rtl='rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv',
              view='physical/ref_tile/qkd_rlys_1/views/qkd_rlys_1'),
    sticky=dict(master='qkd_astk_fault_join', rtl='rtl/qwen_sys/split_20261014/qkd_astk_phys.sv',
                view='physical/ref_tile/qkd_astk_fault_join/views/qkd_astk_fault_join'))
LAND = re.compile(r'qkd_landsh0?_(1|36|296|528)$')
FAMILY = re.compile(r'qkd_(rlysh0?|landsh0?)_(1|36|296|528)$')
FAULT_PORT = re.compile(r'^(fault|flt|kf|pcf|hfault|\w+_fault)$')
INST = re.compile(r'^(\s*)(\w+)\s+(\\?\S+)\s*\((.*)\);\s*$')
PLACE = re.compile(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_lef(text):
    macros = {}
    for m in re.finditer(r'^MACRO (\S+)\s*$(.*?)^END \1\s*$', text, re.M | re.S):
        name, body = m.groups()
        size = re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)', body)
        pins = {}
        for pm in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$', body, re.M | re.S):
            d = re.search(r'DIRECTION (\w+)', pm.group(2))
            r = re.search(r'RECT\s+([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)', pm.group(2))
            xy = None
            if r:
                x0, y0, x1, y1 = map(float, r.groups())
                xy = [(x0 + x1) / 2, (y0 + y1) / 2]
            pins[pm.group(1)] = dict(dir=(d.group(1).upper() if d else None), xy=xy)
        macros[name] = dict(size=list(map(float, size.groups())) if size else None, pins=pins, text=m.group(0))
    return macros


# port directions / approximate pin offsets of the plane masters when their LEF is not in the case (--netlist-only)
HP_DIRS = dict(qkd_hp_or2=dict(ck='INPUT', a='INPUT', b='INPUT', q='OUTPUT'),
               qkd_rlys_1=dict(ck='INPUT', a='INPUT', b='OUTPUT'),
               qkd_astk_fault_join=dict(ck='INPUT', rst_n='INPUT', a='INPUT', b='INPUT', q='OUTPUT'))
HP_PIN = dict(a=[0.042, 10.812], b=[0.042, 10.956], q=[21.558, 10.812])
# KV-BIND4 10-19: exported health sources (kv_static_die HEALTH_SRC buses) whose die-frame pin is INOUT / group-named: the RTL
# direction (qkd_ctrl_strip.sv qkd_ctrl_kc `output kf`; qkd_d2d_cal_seq_bc4.sv `output reg fault` = die group flt, kv_die
# dcal_binding) overrides the frame so the source's own pin is never counted as its reader; PIN_ALIAS = the LEF pin name.
SRC_DIRS = dict(qkd_ctrl_kc=dict(kf='OUTPUT'), qkd_dcal=dict(flt='OUTPUT'))
PIN_ALIAS = dict(qkd_dcal=dict(flt='fault'))


def port_dirs(die, m):
    d = {p: {v['dir'] for v in pv} for p, pv in base_ports(die.macros.get(m, {}).get('pins', {})).items()}
    for p, v in HP_DIRS.get(m, {}).items():
        d.setdefault(p, {v})
    for p, v in SRC_DIRS.get(m, {}).items():
        d[p] = {v}
    return d


def base_ports(pins):
    out = defaultdict(list)
    for p, v in pins.items():
        out[re.sub(r'\[\d+\]$', '', p)].append(v)
    return out


class Die:
    def __init__(self, run):
        self.run, self.case = run, run / 'case_kv'
        self.path = self.case / 'die.v'
        self.nets, _, _, insts = P.parse_die(str(self.path))
        self.cells = {}
        for m, i, p, c in insts:
            if i in self.cells:
                raise ValueError('duplicate instance ' + i)
            self.cells[i] = (m, p, c)
        self.places = {m.group(1): dict(x=float(m.group(2)), y=float(m.group(3)), orient=m.group(4))
                       for m in PLACE.finditer((self.case / 'place.tcl').read_text())}
        self.macros = parse_lef((self.case / 'elements.lef').read_text())

    def point(self, i, port):
        m = self.macros.get(self.cells[i][0])
        if m is None and self.cells[i][0] in HP_DIRS and i in self.places:
            if self.cells[i][0] == 'qkd_rlys_1' and port == 'b':
                return None
            pl, off = self.places[i], HP_PIN.get(port.split('[')[0])
            return None if off is None else [round(pl['x'] + off[0], 4), round(pl['y'] + off[1], 4)]
        if m is None or i not in self.places:
            return None
        pin = m['pins'].get(port) or m['pins'].get(port + '[0]')
        al = PIN_ALIAS.get(self.cells[i][0], {}).get(port)
        if (pin is None or pin['xy'] is None) and al:
            pin = m['pins'].get(al) or m['pins'].get(al + '[0]')
        if pin is None or pin['xy'] is None:
            return None
        (x, y), (w, h), pl = pin['xy'], m['size'], self.places[i]
        o = pl['orient']
        if o == 'MX':
            y = h - y
        elif o == 'MY':
            x = w - x
        elif o == 'R180':
            x, y = w - x, h - y
        elif o != 'R0':
            raise ValueError(f'{i}: unsupported orientation {o}')
        return [round(pl['x'] + x, 4), round(pl['y'] + y, 4)]

    def bits(self, expr):
        return P.expr_bits(expr, self.nets)

    def scalar(self, expr):
        b = self.bits(expr)
        if b is None or len(b) != 1 or b[0][0] in ('CONST', 'Z'):
            raise ValueError('expected one die signal bit: ' + str(expr))
        return f'{b[0][0]}[{b[0][1]}]'


def readers(die):
    """net bit -> [(inst, port)] for every input-direction connection (by the master LEF), conservative otherwise"""
    rd = defaultdict(list)
    for i, (m, _p, c) in die.cells.items():
        pd = port_dirs(die, m)
        for port, expr in c.items():
            dirs = pd.get(port, set())
            if dirs == {'OUTPUT'}:
                continue
            b = die.bits(expr)
            for bit in (b or []):
                if bit[0] not in ('CONST', 'Z'):
                    rd[bit].append((i, port))
    return rd


def inventory(die):
    rd = readers(die)
    sources, unadmitted, blockers, covered = [], [], [], []

    def add(i, port, clock, reset, sticky, **kw):
        m, p, c = die.cells[i]
        if port not in c:
            blockers.append(dict(source=f'{i}.{port}', master=m, reason='output pin not connected in the generated case',
                                 owner=kw.get('owner')))
            return
        bit = die.bits(c[port])
        if bit is None or len(bit) != 1 or bit[0][0] in ('CONST', 'Z'):
            raise ValueError(f'{i}.{port}: not one die signal bit')
        r = rd.get(bit[0], [])
        if r:
            covered.append(dict(source=f'{i}.{port}', readers=[f'{a}.{b}' for a, b in r]))
            return
        sources.append(dict(id=f'{i}.{port}', instance=i, master=m, port=port, signal=list(bit[0]),
                            clock=die.scalar(c[clock]), reset=die.scalar(c[reset]), sticky=sticky,
                            requires_sticky_latch=not sticky, placement=die.places.get(i), pin_xy=die.point(i, port),
                            **{k: v for k, v in kw.items() if k != 'owner'}))
    for i, (m, p, c) in sorted(die.cells.items()):
        if m.startswith(('qkd_landsh_', 'qkd_landsh0_')) and not LAND.fullmatch(m):
            raise ValueError('new landing family requires exact fault admission ' + m)
        if LAND.fullmatch(m):
            add(i, 'fault', 'ck', 'rs', True)
    for st in ('WS', 'WN', 'ES', 'EN'):
        i = 'kc_' + st
        if i not in die.cells:
            continue
        m = die.cells[i][0]
        if 'kf' in base_ports(die.macros.get(m, {}).get('pins', {})):
            add(i, 'kf', 'ck', 'rsi', False, owner='KV-PC2 (qkd_ctrl_kc kf)')
        else:
            blockers.append(dict(source=f'{i}.kf', master=m, owner='KV-PC2/KV-GEN9',
                                 reason='die KC master exposes no kf pin (closed qkd_ctrl_kc view has kf; kv_die binding '
                                        'group kf + view bind owed); KC fi -> kf is not sticky: sticky latch planned'))
    if 'dcal' in die.cells:
        m, p, c = die.cells['dcal']
        port = 'flt' if 'flt' in c else ('fault' if 'fault' in c else None)
        if port is None:
            blockers.append(dict(source='dcal.fault', master=m, owner='KV-DCAL2/KV-GEN9',
                                 reason='DCAL sticky fault not exported (OT_KV_DCAL_BC4=1 binds the bc4 view with group '
                                        'flt; OT_KV_DCAL_FLT=1 routes it to afr d[8])'))
        else:
            add('dcal', port, 'ck', 'rst_n', True, owner='KV-DCAL2')
    # every other unread fault-like OUTPUT on any die master: reported, never dropped
    known = {s['id'] for s in sources} | {c['source'] for c in covered} | {b['source'] for b in blockers}
    known |= {f"{s['instance']}.{PIN_ALIAS[s['master']][s['port']]}" for s in sources
              if s.get('port') in PIN_ALIAS.get(s.get('master'), {})}      # the same pin under its LEF name
    for i, (m, p, c) in sorted(die.cells.items()):
        if LAND.fullmatch(m) or i.startswith('hp_'):
            continue
        for port, pv in base_ports(die.macros.get(m, {}).get('pins', {})).items():
            if not FAULT_PORT.match(port) or {v['dir'] for v in pv} != {'OUTPUT'} or f'{i}.{port}' in known:
                continue
            b = die.bits(c[port]) if port in c else None
            if b and any(rd.get(x) for x in b if x[0] not in ('CONST', 'Z')):
                continue
            unadmitted.append(dict(source=f'{i}.{port}', master=m, connected=port in c))
    m, p, c = die.cells['kvs_attn']
    if m != 'qkd_kvs_attn':
        raise ValueError('unexpected final consumer ' + m)
    sources.append(dict(id='existing_ufh', instance='kvs_attn', port='ufh', signal=list(die.bits(c['ufh'])[0]),
                        clock=die.scalar(c['ck']), reset=die.scalar(c['rst_n']), sticky=False, requires_sticky_latch=False,
                        placement=die.places['kvs_attn'], pin_xy=die.point('kvs_attn', 'ufh'),
                        extra_edges=AHUB_UFH_EDGES,
                        note='AHUB hf path (pulse-capable) kept on core c; the final sticky sink retains it'))
    consumer = dict(pin_xy=die.point('kvs_attn', 'ufh'), instance='kvs_attn', port='ufh', clock=die.scalar(c['ck']),
                    reset=die.scalar(c['rst_n']), placement=die.places['kvs_attn'])
    return dict(sources=sources, blockers=blockers, unadmitted=unadmitted, covered=covered, consumer=consumer,
                lanes=spare_lanes(die, rd))


def spare_lanes(die, rd):
    """stack -> core forwarded lanes with a payload bit that is constant 0 at the lane input and read by nothing but
    the next station along the whole lane (kv_fault_plane.py lane rule, on the laned netlist)"""
    fwd = json.loads((die.run / 'fwd_lanes.json').read_text())
    drivers = Counter()
    for i, (m, p, c) in die.cells.items():
        if FAMILY.fullmatch(m) and 'b' in c:
            drivers.update(x for x in (die.bits(c['b']) or []) if x[0] not in ('CONST', 'Z'))
    lanes = []
    for n, lane in enumerate(fwd['lanes']):
        chain, width = lane['stations'], lane['S']
        if lane['src_tree'] == 'c' or lane['dst_tree'] != 'c':
            continue
        if any(s not in die.cells for s in chain):
            continue
        pairs = []
        for i in chain:
            m, p, c = die.cells[i]
            mm = FAMILY.fullmatch(m)
            if not mm or int(mm.group(2)) != width:
                raise ValueError('unexpected forwarded station ' + i)
            a, b = die.bits(c['a']), die.bits(c['b'])
            if a is None or b is None or len(a) != width or len(b) != width:
                raise ValueError('station width ' + i)
            pairs.append((list(reversed(a)), list(reversed(b))))
        free = []
        for bit in range(width):
            if pairs[0][0][bit] != ('CONST', 0):
                continue
            good = True
            for k, (aa, bb) in enumerate(pairs):
                out = bb[bit]
                if out[0] in ('CONST', 'Z') or drivers[out] != 1:
                    good = False
                    break
                exp = []
                if k + 1 < len(chain):
                    nxt = pairs[k + 1][0][bit]
                    if nxt == out:
                        exp = [(chain[k + 1], 'a')]
                    elif nxt != ('CONST', 0):
                        good = False
                        break
                if sorted(rd.get(out, [])) != exp:
                    good = False
                    break
            if good:
                free.append(bit)
        if not free:
            continue
        m0, _, c0 = die.cells[chain[0]]
        lanes.append(dict(id=f'lane_{n}', src_tree=lane['src_tree'], dst_tree=lane['dst_tree'], stations=chain,
                          free_bits=free, width=width,
                          source_clock=die.scalar(c0['ck_s' if m0.startswith('qkd_landsh0_') else 'ck']),
                          destination_clock=die.scalar(die.cells[chain[-1]][2]['ck']),
                          destination_reset=die.scalar(die.cells[chain[-1]][2]['rs']) if 'rs' in die.cells[chain[-1]][2] else None,
                          input_pin_xy={str(b): die.point(chain[0], f'a[{b}]') for b in free},
                          output_pin_xy={str(b): die.point(chain[-1], f'b[{b}]') for b in free},
                          physical_price_cycles=lane['landed'] + lane.get('post_stages', 0),
                          conservative_model_cycles=math.ceil(lane['landed'] + lane.get('post_stages', 0)) + 2,
                          timing_basis='fwd_lanes.json landed + post stages (+2 conservative)'))
    return lanes


def obstacles(die):
    out = []
    for i, pl in die.places.items():
        m = die.macros.get(die.cells[i][0]) if i in die.cells else None
        if m and m['size']:
            w, h = m['size']
            out.append([pl['x'], pl['y'], pl['x'] + w, pl['y'] + h])
    return out


def pack_msb(bits):
    """MSB-first [(net, i) | ('CONST', v)] -> Verilog expression (runs of one net, sized constants)"""
    runs = []
    for b in bits:
        if b[0] == 'CONST':
            if runs and runs[-1][0] == 'CONST' and runs[-1][2] == b[1]:
                runs[-1][1] += 1
            else:
                runs.append(['CONST', 1, b[1]])
        elif runs and runs[-1][0] == b[0] and runs[-1][2] == b[1] + 1:
            runs[-1][2] = b[1]
        else:
            runs.append([b[0], b[1], b[1]])
    parts = []
    for r in runs:
        if r[0] == 'CONST':
            parts.append(f"{r[1]}'b{str(r[2]) * r[1]}" if r[1] <= 64 else f"{{{r[1]}{{1'b{r[2]}}}}}")
        else:
            parts.append(f'{r[0]}[{r[1]}:{r[2]}]' if r[1] != r[2] else f'{r[0]}[{r[1]}]')
    return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'


def install(run, strict=False, dry=False):
    die = Die(run)
    inv = inventory(die)
    tinv = dict(sources=inv['sources'], physical_obstacles=obstacles(die), consumer=inv['consumer'],
                spare_transport_candidates=inv['lanes'], requirements=[], physical_blockers=inv['blockers'])
    plan = T.propose(tinv)
    # leaf latency to the sink (plan graph), + the existing ufh's AHUB edges
    lat = {}
    prev = {}
    for n in plan['nodes']:
        prev[n['id']] = n
    tr = {t['id']: t for t in plan['transports']}
    memo = {}

    def depth(x):            # edges from signal x to the sink output, through the unique fan-out path
        return memo[x]
    consumers = defaultdict(list)
    for n in plan['nodes']:
        consumers[n['a']].append(n['id'])
        if n['b'] not in (n['a'], n['id']):
            consumers[n['b']].append(n['id'])
    for t in plan['transports']:
        consumers[t['source']].append(t['id'])
    sink = plan['sink']

    def walk(x, seen=()):
        if x == sink:
            return 0
        nxt = [c for c in consumers.get(x, []) if c != x]
        if len(nxt) != 1:
            raise ValueError(f'health plane signal {x}: {len(nxt)} consumers (expected exactly one tree parent)')
        c = nxt[0]
        e = tr[c]['latency_cycles'] if c in tr else 1
        return e + walk(c)
    for s in inv['sources']:
        lat[s['id']] = walk(s['id']) + s.get('extra_edges', 0)   # edges source pin -> sink q (= ufh input), contract leaf
    dmax = max(lat.values())
    rep = dict(schema='opentallas.kv_health_plane.v1', run=str(run),
               inputs={f: sha(run / f) for f in ('case_kv/die.v', 'case_kv/place.tcl', 'case_kv/elements.lef',
                                                  'fwd_lanes.json')},
               sources=len(inv['sources']), sources_by_clock=dict(Counter(s['clock'] for s in inv['sources'])),
               blockers=inv['blockers'], unadmitted=inv['unadmitted'], covered=inv['covered'],
               spare_lanes=len(inv['lanes']), spare_bits=sum(len(l['free_bits']) for l in inv['lanes']),
               cells=dict(Counter(n['kind'] for n in plan['nodes'])), transports=len(plan['transports']),
               leaf_latency=lat, dmax=dmax, worst=sorted(((v, k) for k, v in lat.items()), reverse=True)[:12], dmax_reserved=DMAX_RESERVED,
               status=dict(cutoff=1785, suffix=15, required_status_age=1785 + dmax + 15, reserved=STATUS_RESERVED,
                           status_delay=STATUS_RESERVED - 1785, compiled_end=STATUS_RESERVED + 1,
                           token_period_padded=257280, fits_reserved=dmax <= DMAX_RESERVED))
    if dry:
        return rep, plan, None
    emitted = emit(die, inv, plan)
    rep['emitted'] = emitted
    return rep, plan, emitted


def emit(die, inv, plan):
    case, run = die.case, die.run
    lines = die.path.read_text().split('\n')
    sig = {}
    for s in inv['sources']:
        sig[s['id']] = f"{s['signal'][0]}[{s['signal'][1]}]"
    for n in plan['nodes']:
        sig[n['id']] = f"n_hp_{n['id']}[0]"
    # transports: rewire the free bit through every station of the lane
    edits = defaultdict(dict)        # inst -> port -> MSB-first bit list
    padfree = defaultdict(lambda: defaultdict(set))

    def cur(i, port):
        if port not in edits[i]:
            edits[i][port] = list(die.bits(die.cells[i][2][port]))
        return edits[i][port]
    for t in plan['transports']:
        lane = next(l for l in inv['lanes'] if l['id'] == t['lane_id'])
        chain, w, k = lane['stations'], lane['width'], t['payload_bit']
        src = sig[t['source']]
        nm, bi = re.fullmatch(r'(\S+)\[(\d+)\]', src).groups()
        a0 = cur(chain[0], 'a')
        if a0[w - 1 - k] != ('CONST', 0):
            raise ValueError(f'{chain[0]}.a[{k}] is not a constant-0 spare')
        a0[w - 1 - k] = (nm, int(bi))
        for j in range(1, len(chain)):
            out = cur(chain[j - 1], 'b')[w - 1 - k]
            aj = cur(chain[j], 'a')
            if aj[w - 1 - k] == ('CONST', 0):
                aj[w - 1 - k] = out
            elif aj[w - 1 - k] != out:
                raise ValueError(f'{chain[j]}.a[{k}] carries another signal')
        for i in chain:
            padfree[i]['a'].add(k)
            padfree[i]['b'].add(k)
        last = cur(chain[-1], 'b')[w - 1 - k]
        sig[t['id']] = f'{last[0]}[{last[1]}]'
    # the sink drives kvs_attn.ufh; the old ufh net is the existing_ufh leaf
    sink_net = sig[plan['sink']]
    out_lines, seen = [], set()
    for ln in lines:
        m = INST.match(ln)
        if m and m.group(3) in edits:
            ind, mst, nm_, body = m.groups()
            conns = re.findall(r'\.(\w+)\(((?:[^()]|\([^()]*\))*)\)', body)
            txt = ', '.join(f'.{p}({pack_msb(edits[nm_][p]) if p in edits[nm_] else e})' for p, e in conns)
            ln = f'{ind}{mst} {nm_} ({txt});'
            seen.add(nm_)
        elif m and m.group(3) == 'kvs_attn':
            ind, mst, nm_, body = m.groups()
            body2, cnt = re.subn(r'\.ufh\(([^()]*)\)', f'.ufh({sink_net})', body)
            if cnt != 1:
                raise ValueError('kvs_attn.ufh connection not found exactly once')
            ln = f'{ind}{mst} {nm_} ({body2});'
            seen.add('kvs_attn')
        out_lines.append(ln)
    if seen != set(edits) | {'kvs_attn'}:
        raise ValueError(f'instances not rewritten: {sorted(set(edits) | {"kvs_attn"} - seen)}')
    # new cells + wires before endmodule
    clock, reset = {}, {}
    for s in inv['sources']:
        clock[s['id']], reset[s['id']] = s['clock'], s['reset']
    new, wires, place = [], [], []
    for n in plan['nodes']:
        ck = n['clock']
        a, b = sig[n['a']], sig[n['b']]
        q = sig[n['id']]
        wires.append(f'  wire [0:0] n_hp_{n["id"]};')
        if n['kind'] == 'join':
            new.append(f'  qkd_hp_or2 hp_{n["id"]} (.ck({ck}), .a({a}), .b({b}), .q({q}));')
        elif n['kind'] == 'pipe':
            new.append(f'  qkd_rlys_1 hp_{n["id"]} (.a({a}), .b({q}), .ck({ck}));')
        elif n['kind'] == 'sticky':
            if n['b'] != n['id']:
                raise ValueError('sticky without self feedback ' + n['id'])
            new.append(f'  qkd_astk_fault_join hp_{n["id"]} (.ck({ck}), .rst_n({n["reset"]}), .a({a}), .b({q}), .q({q}));')
        else:
            raise ValueError('node kind ' + n['kind'])
        p = n['placement']
        place.append(f'ot_mts::place [$_blk findInst hp_{n["id"]}] {p["x"]:.3f} {p["y"]:.3f} R0')
    end = max(j for j, ln in enumerate(out_lines) if ln.strip() == 'endmodule')
    mod = next(j for j, ln in enumerate(out_lines) if re.match(r'\s*module\b', ln))
    first_inst = next(j for j, ln in enumerate(out_lines) if j > mod and (m_ := INST.match(ln)) and m_.group(2) != 'module'
                      and not re.match(r'\s*(input|output|inout|wire|reg|assign)\b', ln))
    out_lines = out_lines[:first_inst] + wires + out_lines[first_inst:end] + \
        ['  // KV-HEALTH 10-19: continuous registered health plane (kv_health_plane.py)'] + new + out_lines[end:]
    for f in ('die.v', 'place.tcl', 'elements.lef', 'die.v.pads.json'):
        if (case / f).exists() and not (case / (f + '.prehealth')).exists():
            shutil.copy(case / f, case / (f + '.prehealth'))
    (case / 'die.v').write_text('\n'.join(out_lines))
    pt = (case / 'place.tcl').read_text().rstrip('\n') + '\n# KV-HEALTH 10-19 health plane cells\n' + '\n'.join(place) + '\n'
    (case / 'place.tcl').write_text(pt)
    # pads: a functional health bit keeps no padding declaration
    pf = case / 'die.v.pads.json'
    removed = 0
    if pf.exists():
        pj = json.loads(pf.read_text())
        for i, ports in padfree.items():
            ent = pj.get('instances', {}).get(i)
            if not ent:
                continue
            for port, ks in ports.items():
                rngs = ent['ports'].get(port, [])
                new_r = []
                for lo, hi in rngs:
                    cur_lo = lo
                    for b in range(lo, hi + 1):
                        if b in ks:
                            removed += 1
                            if cur_lo <= b - 1:
                                new_r.append([cur_lo, b - 1])
                            cur_lo = b + 1
                    if cur_lo <= hi:
                        new_r.append([cur_lo, hi])
                ent['ports'][port] = new_r
            ent['reason'] = ent['reason'] + ' | KV-HEALTH: health-plane transport bits removed from the pad set'
        pf.write_text(json.dumps(pj, indent=1) + '\n')
    # masters: LEF, libs, views, expand leaves
    elef = (case / 'elements.lef').read_text()
    add = []
    used = sorted({MASTERS[n['kind']]['master'] for n in plan['nodes']})
    views, missing_views = {}, []
    for kind, d in MASTERS.items():
        if d['master'] not in used:
            continue
        lef = ROOT / d['view'] / f"{d['master']}.lef"
        if not lef.exists():
            if NETLIST_ONLY:
                missing_views.append(d['master'])
                continue
            raise SystemExit(f'kv_health_plane: no closed view for {d["master"]} at {d["view"]} (close the kit first, '
                             'or --netlist-only: never a physical run)')
        views[d['master']] = d
        if not re.search(rf'^MACRO {d["master"]}\s*$', elef, re.M):
            t = lef.read_text()
            mm = re.search(rf'^MACRO {d["master"]}\s*$.*?^END {d["master"]}\s*$', t, re.M | re.S)
            add.append(mm.group(0))
    if add:
        t = elef.rstrip()
        e = re.search(r'^END LIBRARY\s*$', t, re.M)
        t = (t[:e.start()] + '\n'.join(add) + '\n' + t[e.start():]) if e else t + '\n' + '\n'.join(add)
        (case / 'elements.lef').write_text(t + '\n')
    libs = run / 'libs'
    if (libs / 'views.json').exists():
        vj = json.loads((libs / 'views.json').read_text())
        for mst, d in views.items():
            for c in CORNERS:
                src = ROOT / d['view'] / f'{mst}_{c}.lib'
                if src.exists() and not (libs / f'qfd_etm_{mst}_{c}.lib').exists():
                    txt = re.sub(r'library\s*\(\s*"?[^")]+"?\s*\)', f'library (qfd_etm_{mst}_{c})', src.read_text(), count=1)
                    (libs / f'qfd_etm_{mst}_{c}.lib').write_text(txt)
            vj['views'].setdefault(mst, dict(bound=True, view=d['view'], module=mst, cls='health_plane'))
        (libs / 'views.json').write_text(json.dumps(vj, indent=1) + '\n')
    ex = run / 'expand.json'
    ej = json.loads(ex.read_text()) if ex.exists() else dict(schema='opentallas.qwen_kvsys_expand.v1', frames={})
    for mst, d in views.items():
        ej.setdefault('leaves', {}).setdefault(mst, dict(view=d['view'], rtl=d['rtl'], rtl_deps=[]))
    ex.write_text(json.dumps(ej, indent=1) + '\n')
    if missing_views:
        (case / 'HEALTH_NETLIST_ONLY').write_text('kv_health_plane --netlist-only: masters without closed views: '
                                                  + ' '.join(missing_views) + '\n')
    return dict(cells=len(new), wires=len(wires), rewired_instances=len(edits), pad_bits_freed=removed,
                masters=sorted(views), missing_views=missing_views, sink_net=sink_net)


def audit(run):
    """independent check on the EMITTED netlist: every source bit reaches kvs_attn.ufh through hp_* cells and lane
    stations only; every new cell input wire <= REACH; reset loads added only at sticky cells"""
    die = Die(run)
    drv = {}
    for i, (m, p, c) in die.cells.items():
        dirs = port_dirs(die, m)
        for port, expr in c.items():
            if dirs.get(port) == {'OUTPUT'}:
                for k, b in enumerate(reversed(die.bits(expr) or [])):
                    if b[0] not in ('CONST', 'Z'):
                        drv[b] = (i, port, k)
    rd = readers(die)
    hp = {i: v for i, v in die.cells.items() if i.startswith('hp_')}
    far, resets = [], Counter()
    for i, (m, p, c) in hp.items():
        for port in ('a', 'b'):
            b = die.bits(c[port])[0]
            if b[0] in ('CONST', 'Z'):
                raise ValueError(f'{i}.{port} tied')
            d = drv.get(b)
            if d is None:
                raise ValueError(f'{i}.{port}: undriven {b}')
            if d[0] == i:
                continue
            dm = die.macros.get(die.cells[d[0]][0], {}).get('pins', {})
            p0 = die.point(d[0], d[1] if (d[1] in dm or not dm) else f'{d[1]}[{d[2]}]')
            p1 = die.point(i, port)
            if p0 and p1:
                um = abs(p0[0] - p1[0]) + abs(p0[1] - p1[1])
                if um > REACH:
                    far.append(dict(cell=i, port=port, driver=f'{d[0]}.{d[1]}', um=round(um, 1)))
        if 'rst_n' in c:
            resets[die.scalar(c['rst_n'])] += 1
    ufh = die.bits(die.cells['kvs_attn'][2]['ufh'])[0]
    root = drv.get(ufh)
    ok = bool(root and root[0].startswith('hp_') and die.cells[root[0]][0] == 'qkd_astk_fault_join')
    # backward cone of ufh through hp cells + lane stations
    cone, stack, leaves = set(), [ufh], set()
    while stack:
        b = stack.pop()
        d = drv.get(b)
        if d is None:
            continue
        i, port, k = d
        m = die.cells[i][0]
        if i.startswith('hp_'):
            if i in cone:
                continue
            cone.add(i)
            for p_ in ('a', 'b'):
                stack.append(die.bits(die.cells[i][2][p_])[0])
        elif FAMILY.fullmatch(m) and port == 'b':
            a = list(reversed(die.bits(die.cells[i][2]['a'])))
            cone.add(f'{i}#{k}')
            stack.append(a[k])
        else:
            leaves.add(f'{i}.{port}')
    return dict(sink_is_sticky=ok, cone_cells=sum(1 for x in cone if x.startswith('hp_')), hp_cells=len(hp),
                lane_bits=sum(1 for x in cone if '#' in x), leaves=sorted(leaves), far_inputs=far,
                reset_loads_added=sum(resets.values()), reset_nets=dict(resets.most_common(8)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    i = sp.add_parser('install')
    i.add_argument('--run', type=Path, required=True)
    i.add_argument('--strict', action='store_true')
    i.add_argument('--dry-run', action='store_true')
    i.add_argument('--netlist-only', action='store_true', help='masters without closed views keep no LEF/libs (bench / '
                   'bind checks only, never a physical run)')
    a = ap.parse_args(argv)
    global NETLIST_ONLY
    NETLIST_ONLY = a.netlist_only
    rep, plan, emitted = install(a.run, a.strict, a.dry_run)
    if emitted is not None:
        rep['audit'] = au = audit(a.run)
        expect = {s for s in rep['leaf_latency'] if s != 'existing_ufh'} | {'kvs_attn.ufh_old'}
        got = set(au['leaves'])
        rep['audit']['source_coverage'] = dict(
            missing=sorted(s for s in rep['leaf_latency'] if s != 'existing_ufh' and s not in got),
            extra=sorted(got - {s for s in rep['leaf_latency']}))
    (a.run / 'health_plane.json').write_text(json.dumps(dict(rep, plan=plan), indent=1) + '\n')
    succ = dict(schema='opentallas.kv_health_successor.v1', sources=[dict(id=s, clock=None) for s in rep['leaf_latency']],
                leaf_latencies={s: v - (AHUB_UFH_EDGES if s == 'existing_ufh' else 0) for s, v in rep['leaf_latency'].items()})
    (a.run / 'health_successor.json').write_text(json.dumps(succ, indent=1) + '\n')
    bad = []
    if rep['blockers']:
        bad.append(f"{len(rep['blockers'])} required sources not exported: " +
                   ', '.join(sorted({b['source'] for b in rep['blockers']}))[:300])
    if rep['unadmitted']:
        bad.append(f"{len(rep['unadmitted'])} unread fault-like outputs not admitted")
    if not rep['status']['fits_reserved']:
        bad.append(f"plane DMAX {rep['dmax']} > reserved {DMAX_RESERVED}: STATUS {rep['status']['required_status_age']} > "
                   f"{STATUS_RESERVED}")
    if emitted is not None:
        au = rep['audit']
        if not au['sink_is_sticky'] or au['far_inputs'] or au['source_coverage']['missing']:
            bad.append(f"audit: sticky sink {au['sink_is_sticky']}, far inputs {len(au['far_inputs'])}, "
                       f"uncovered {len(au['source_coverage']['missing'])}")
    summ = {k: rep[k] for k in ('sources', 'sources_by_clock', 'cells', 'transports', 'dmax', 'dmax_reserved', 'status', 'worst')}
    summ['blockers'] = len(rep['blockers'])
    summ['unadmitted'] = len(rep['unadmitted'])
    if emitted is not None:
        summ['audit'] = {k: rep['audit'][k] for k in ('sink_is_sticky', 'cone_cells', 'hp_cells', 'lane_bits',
                                                     'reset_loads_added')}
    print('KV_HEALTH ' + json.dumps(summ))
    if bad:
        (a.run / 'HEALTH_DIAGNOSTIC').write_text('\n'.join(bad) + '\n')
        print('KV_HEALTH DIAGNOSTIC: ' + ' | '.join(bad))
        return 1 if a.strict else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
