#!/usr/bin/env python3
"""dv_cut_replay.py -- neighbour-traffic replay for the S81-DV slice cuts (LB2-S81/REPLAY, TOK.DS.BENCH, 10-18).

A cut (dv_slice_cut.py) is a set of die instances with every lane that crosses its boundary cut at the NEIGHBOUR
master's output register: an input port i__w_<link>_src is the outside producer's register (the cut holds the relay
stations, forwarded clock and landing), an output port o__w_<link>_lnd (or _dst for an unlanded lane) is the landed
word at the outside consumer's pin.  This tool turns the compiled layer programme (dv_layer_compile.py schedule.json +
prog/ctl_templates.json) into the traffic the cut's outside neighbours send it, at the compiler-scheduled cycles, and
into the words the cut must deliver to them, and checks / composes the runs.  No simulation runs here (the benches run
on the fleet: run_dv_slice.sh via ot-run, Verilator 5.050).

Landing ages are read from the DIE BUILD, never hard-coded: die.v[.gz] relay stations st_<link>_<i> (half-cycle
dsfd_dvrlyh_*, T/2 each) and landing ld_<link> (dsfd_dvland_*, its .k strap): age = ceil(N / 2) + k + 1 edges for a
landed lane (ot_s81_land: last station -> o = K + 1), N / 2 for an unlanded one.  A port whose bits span several lanes
(a 1,104-b line beat = 4 x 276-b lanes) is whole when its SLOWEST lane lands (the compiler's line model): the
producer launches every lane at ONE edge = landed cycle - max age; a lane with a smaller age lands earlier and tears
the word -- a schedule fault the checks catch (S81-LBGAP G8).  The tool refuses (verdict STALE) a programme whose
compiled link ages differ from the die build's (recompile on the build), and records a die.v sha mismatch.

Traffic encoded from the programme (every other scheduled boundary event is listed as UNENCODED and makes the replay
partial -- dv_layer_record never counts a partial replay as a layer measurement):
  CTL  at <slice>.ri_e / ri_w: the template beat as the slice receives it on the line (ot_s81sl_rstop hdr: hops field
       [8:4] = remaining stops, E-bound 8 - col, W-bound col + 1; src [12:9] = the line injector's sid strap, the
       column-4 slice of the tier: dv_layer_compile ctl_path) landed at the slice pin at e - RSTOP_HOP (the compiler's
       event cycle e is the beat's line-out edge at the slice).  The same beat passes every stop between the injector
       and the slice: it is DERIVED at each intermediate slice c at e - sum(bundle age + RSTOP_HOP) over the stops (die
       ages), with the hops field of that stop, so a cut on the line path sees it on both of its line faces.
  SVCJ at <svc entry>.j: the job word (payload hex) on the j pin at the event cycle.
Word timing: every encoded word is a ONE-cycle pulse of the producer register (the line / job registers are cleared
the next edge); several words on one port in one cycle are OR'ed (a bit set twice with different values is an error).

Sources of a boundary input lane (replay.json records which one fed each port):
  schedule  the words above;
  trace     COMPOSE: the producer cut's own run (its trace.txt of o__w_<link>_lnd), shifted back by the lane age --
            the neighbour is then the real RTL, not the programme's model of it (--trace PRODUCER_REPLAY_DIR=RUN_DIR);
  idle      no word scheduled on the lane: held 0.
Bench convention (dv_slice_tb / dv_slice_replay, S81-LBGAP 10-18 18:10): a word put on <lane>_src at bench cycle k is
the neighbour register launched at edge k - 1 and lands at k - 1 + age; checks sample at the falling edge after rising
edge k; cycles are layer cycles + --t0.

  dv_cut_replay.py ages    --die-v die.v.gz [--prog DIR] [--out ages.json]
  dv_cut_replay.py gen     --die-v die.v.gz --prog DIR --cut CUTDIR --out DIR [--t0 100] [--trace PDIR=RUN ...]
                           [--mutant shift:<link>:<n> | corrupt:<link>[:<bit>]] [--lane-age] [--allow-stale]
  dv_cut_replay.py check   --replay DIR --run RUN [--out check.json]      (trace vs every encoded word, no extras)
  dv_cut_replay.py compose --cut NAME=REPLAY_DIR:RUN_DIR ... --out compose.json   (cross-cut lane consistency)
Mutants (negative controls; replay.json verdict_kind MUTANT): shift moves every word of ONE boundary input lane by n
cycles, corrupt flips one bit of its first word -- the bench must FAIL (commit the run as the fail witness).
--lane-age is a DIAGNOSTIC: each output lane is checked at its own landing (tear-tolerant), never a schedule verdict.
"""
import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA = 'opentallas.s81_dv.cut_replay.v1'
RSTOP_HOP = 2                       # ot_s81sl_rstop: line in pin -> line out pin 2 edges a stop
LINE_INJECT_COL = 4                 # dv_layer_compile ctl_path: seq_host V -> column-4 slice -> line both ways
ENCODED = ('CTL', 'SVCJ')
PIN_OFFSET = {'CTL': -RSTOP_HOP, 'SVCJ': 0}   # landed-pin cycle = event cycle + offset

INST_RE = re.compile(r'^\s*(\w+)\s+(?:#\((.*?)\)\s+)?(\w+)\s*\((.*)\);\s*(?://.*)?$')
WIRE_RE = re.compile(r'^\s*(?:wire|input wire|output wire|reg)\s*(?:\[(\d+):(\d+)\])?\s*([^;]+);')
SEG_RE = re.compile(r"^\s*(?:(\w+)\s*(?:\[(\d+)(?::(\d+))?\])?|(\d+)'[dhb]([0-9a-fA-F_]+))\s*$")


# ================================================================================================= die build model
def read_text(p):
    p = Path(p)
    b = p.read_bytes()
    return (gzip.decompress(b) if p.suffix == '.gz' else b).decode()


def split_conns(body):
    """'.a(x), .b({y[3:0], z})' -> {a: 'x', b: '{y[3:0], z}'} (balanced parentheses)"""
    out, i = {}, 0
    while True:
        j = body.find('.', i)
        if j < 0:
            return out
        k = body.find('(', j)
        name = body[j + 1:k].strip()
        d, m = 0, k
        while m < len(body):
            if body[m] == '(':
                d += 1
            elif body[m] == ')':
                d -= 1
                if d == 0:
                    break
            m += 1
        out[name] = body[k + 1:m].strip()
        i = m + 1


class DieBuild:
    """die.v of a die build: instances, wire widths, relay / landing links with their ages, port bit maps"""

    def __init__(self, die_v):
        self.path = str(die_v)
        raw = read_text(die_v)
        self.sha256 = hashlib.sha256(raw.encode()).hexdigest()
        self.inst, self.width = {}, {}
        for line in raw.splitlines():
            w = WIRE_RE.match(line)
            if w:
                hi = int(w.group(1)) if w.group(1) else 0
                for n in w.group(3).split(','):
                    self.width[n.strip()] = hi + 1
                continue
            m = INST_RE.match(line)
            if not m or m.group(1) in ('module', 'wire', 'input', 'output', 'assign', 'reg'):
                continue
            master, params, name, body = m.groups()
            self.inst[name] = dict(master=master, params=params or '', conns=split_conns(body))
        self._links()

    def bits(self, expr):
        """port expression -> LSB-first list of (net, bit) / None (constant bit)"""
        e = expr.strip()
        if e.startswith('{') and e.endswith('}'):
            e = e[1:-1]
        out = []
        for seg in reversed([s for s in e.split(',') if s.strip()]):
            m = SEG_RE.match(seg)
            if not m:
                raise ValueError(f'port expression segment not understood: {seg!r}')
            if m.group(4):
                out += [None] * int(m.group(4))
                continue
            net, hi, lo = m.group(1), m.group(2), m.group(3)
            if hi is None:
                hi, lo = self.width.get(net, 1) - 1, 0
            else:
                hi, lo = int(hi), int(lo if lo is not None else hi)
            out += [(net, b) for b in range(lo, hi + 1)]
        return out

    def port_bits(self, inst, port):
        e = self.inst.get(inst, {}).get('conns', {}).get(port)
        return self.bits(e) if e else []

    def strap(self, inst, port):
        v = self.inst.get(inst, {}).get('conns', {}).get(port, '')
        m = re.fullmatch(r"(\d+)'([dh])([0-9a-fA-F]+)", v)
        return int(m.group(3), 16 if m.group(2) == 'h' else 10) if m else None

    def _links(self):
        st, ld = defaultdict(dict), {}
        for n, i in self.inst.items():
            m = re.fullmatch(r'st_(.+)_(\d+)', n)
            if m and i['master'].startswith('dsfd_dvrlyh'):
                st[m.group(1)][int(m.group(2))] = n
            m = re.fullmatch(r'ld_(.+)', n)
            if m and i['master'].startswith('dsfd_dvland'):
                ld[m.group(1)] = n
        users = defaultdict(list)
        for n, i in self.inst.items():
            if n.startswith(('st_', 'ld_', 'fwd_', 'rsg_')):
                continue
            for p, e in i['conns'].items():
                for w in set(re.findall(r'\bw_(\w+?)_(src|lnd|dst)\b', e)):
                    users[w].append((n, p))
        self.links = {}
        for lk in set(st) | set(ld):
            n = len(st.get(lk, {}))
            k = self.strap(ld[lk], 'k') if lk in ld else None
            if lk in ld and k is None:
                raise ValueError(f'landing {ld[lk]} has no .k strap')
            age = (math.ceil(n / 2) + k + 1) if lk in ld else n / 2
            first = st[lk][min(st[lk])] if n else ld.get(lk)
            src_bits = self.port_bits(first, 'i') if first else []
            out_net = f'w_{lk}_lnd' if lk in ld else f'w_{lk}_dst'
            self.links[lk] = dict(stations=n, landing=ld.get(lk), K=k, age=age, out_net=out_net,
                                  src=sorted(users.get((lk, 'src'), [])),
                                  dst=sorted(users.get((lk, 'lnd'), []) + users.get((lk, 'dst'), [])),
                                  src_bits=src_bits)
        self.by_out = {L['out_net']: lk for lk, L in self.links.items()}

    def sid(self, inst):
        return self.strap(inst, 'sid')


# ================================================================================================= cut model
class Cut:
    def __init__(self, d):
        d = Path(d)
        self.dir = str(d)
        self.ports = {p['port']: p for p in json.loads((d / 'tb_ports.json').read_text())}
        sp = json.loads((d / 'slice_ports.json').read_text())['ports']
        for n, p in self.ports.items():
            p['net'] = sp[n]['net']
            p['peers'] = sp[n].get('peers', [])
        self.insts = set(json.loads((d / 'slice_insts.json').read_text())['how'])
        self.in_by_net = {p['net']: p for p in self.ports.values() if p['dir'] == 'input'}
        self.out_by_net = {p['net']: p for p in self.ports.values() if p['dir'] == 'output'}


# ================================================================================================= programme -> words
def ctl_beat(T, ev, die, inst):
    """the template beat as <inst> receives it on its line face (hops / src rewritten as ot_s81sl_rstop delivers it)"""
    ti = int(ev['payload'].split()[1].rstrip(';'))
    beat = int(T[ti]['beat'], 16)
    if (beat >> 4) & 0x1F:
        raise ValueError(f'template {ti} carries hops {(beat >> 4) & 0x1F}: only line-default (0) beats are modelled')
    col, tier = int(inst[4]), inst[5]
    hops = col + 1 if ev['port'] == 'ri_e' else 8 - col
    src = die.sid(f'u_s_{LINE_INJECT_COL}{tier}')
    return (beat & ~(0x1F << 4) & ~(0xF << 9)) | (hops & 0x1F) << 4 | (src & 0xF) << 9, ti, hops, src


def line_link_age(die, a, b):
    """bundle age of the line a -> b (max over its lanes) and the lanes"""
    ls = [k for k, L in die.links.items() if any(x[0] == a for x in L['src']) and any(x[0] == b for x in L['dst'])]
    if not ls:
        raise ValueError(f'no line lanes {a} -> {b} in the die build')
    return max(die.links[k]['age'] for k in ls), sorted(ls)


def derive_line_events(S, die):
    """every CTL line beat seen at a schedule slice passes EVERY stop of its line direction (ot_s81sl_rstop forwards a
    non-NX beat with hops > 1; a template beat carries hops 0 = the injector's line default, so a W-bound beat reaches
    column 0 and an E-bound one column 7): derive its arrival at each other stop from the die's bundle ages (the
    compiler's line model -- a stop is 2 edges, a hop is the slowest lane of the bundle), on the build"""
    have = {(e['inst'], e['port'], e['cycle'], e['payload']) for e in S['events'] if e['kind'] == 'CTL'}
    out = []
    for e in S['events']:
        if e['kind'] != 'CTL' or e['dir'] != 'in' or e['port'] not in ('ri_e', 'ri_w'):
            continue
        col, tier = int(e['inst'][4]), e['inst'][5]
        path = list(range(LINE_INJECT_COL - 1, -1, -1)) if e['port'] == 'ri_e' else list(range(LINE_INJECT_COL + 1, 8))
        if col not in path:
            raise ValueError(f'CTL event {e["tag"]} at {e["inst"]}.{e["port"]} is not on a line from column '
                             f'{LINE_INJECT_COL}')
        t, i, arr = e['cycle'], path.index(col), {}
        for j in range(i - 1, -1, -1):                   # upstream stops (toward the injector)
            age, _ = line_link_age(die, f'u_s_{path[j]}{tier}', f'u_s_{path[j + 1]}{tier}')
            t -= age + RSTOP_HOP
            arr[path[j]] = t
        t = e['cycle']
        for j in range(i + 1, len(path)):                # downstream stops (toward the line end)
            age, _ = line_link_age(die, f'u_s_{path[j - 1]}{tier}', f'u_s_{path[j]}{tier}')
            t += age + RSTOP_HOP
            arr[path[j]] = t
        for c, t in arr.items():
            d = dict(e, cycle=t, inst=f'u_s_{c}{tier}', derived_from=f'{e["inst"]}@{e["cycle"]}')
            if (d['inst'], d['port'], d['cycle'], d['payload']) not in have:
                have.add((d['inst'], d['port'], d['cycle'], d['payload']))
                out.append(d)
    return out


def landed_words(S, T, die):
    """(consumer inst, port) words at the consumer pin: [{event, inst, port, cycle_land, bits {(net, bit): v}}]"""
    words, unenc = [], []
    evs = S['events'] + derive_line_events(S, die)
    for e in evs:
        if e['dir'] != 'in':
            continue
        if e.get('plan_only') or e['kind'] not in ENCODED:
            unenc.append(e)
            continue
        inst = e['inst']
        pb = die.port_bits(inst, e['port'])
        if not pb:
            unenc.append(dict(e, why=f'no port {inst}.{e["port"]} in the die build'))
            continue
        if e['kind'] == 'CTL':
            val, ti, hops, src = ctl_beat(T, e, die, inst)
            meta = dict(template=ti, hops=hops, src_sid=src)
        else:
            val, meta = int(e['payload'], 16), {}
        bits = {nb: (val >> i) & 1 for i, nb in enumerate(pb) if nb is not None}
        words.append(dict(event=dict((k, v) for k, v in e.items() if k != 'payload') | {'payload': e['payload']},
                          inst=inst, port=e['port'], cycle_land=e['cycle'] + PIN_OFFSET[e['kind']], bits=bits, **meta))
    for e in S['events']:
        if e['dir'] == 'out':
            unenc.append(e)       # the programme states what a unit sends, not the word (fixture payloads)
    return words, unenc


def stale_check(S, die, manifest):
    diffs = []
    for lk, L in S.get('links', {}).items():
        D = die.links.get(lk)
        if D is None:
            diffs.append(dict(link=lk, compiled_age=L['age_edges'], die_age=None, why='lane not in the die build'))
        elif abs(float(L['age_edges']) - float(D['age'])) > 1e-9:
            diffs.append(dict(link=lk, compiled_age=L['age_edges'], die_age=D['age'], compiled_K=L.get('K'),
                              die_K=D['K'], stations=D['stations']))
    sha_ok = manifest.get('die_v_sha256') == die.sha256
    return dict(link_age_diffs=diffs, die_v_sha256_build=die.sha256, die_v_sha256_compiled=manifest.get('die_v_sha256'),
                die_sha_match=sha_ok, stale=bool(diffs))


# ================================================================================================= gen
def gen(a):
    die = DieBuild(a.die_v)
    prog = Path(a.prog)
    S = json.loads((prog / 'schedule.json').read_text())
    T = {t['i']: t for t in json.loads((prog / 'prog/ctl_templates.json').read_text())['templates']}
    man = json.loads((prog / 'manifest.json').read_text()) if (prog / 'manifest.json').exists() else {}
    cut = Cut(a.cut)
    st = stale_check(S, die, man)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if st['stale'] and not a.allow_stale:
        (out / 'replay.json').write_text(json.dumps(dict(schema=SCHEMA, verdict_kind='STALE', stale=st,
            why='the programme was compiled on lane ages the die build does not have: recompile on this build'),
            indent=1) + '\n')
        print(f'dv_cut_replay: STALE -- {len(st["link_age_diffs"])} lane ages differ from the die build '
              f'(e.g. {st["link_age_diffs"][:3]}); recompile the programme on {a.die_v}')
        return 2
    words, unenc = landed_words(S, T, die)
    host = None
    if a.host_boot is not None:
        words, host = host_boot_words(a, die, prog, S, words)
    traces = {}
    for spec in a.trace:
        pdir, run = spec.split('=', 1)
        traces[pdir] = run
    tsrc = trace_sources(die, cut, traces)
    mut = parse_mutant(a.mutant)

    drive = defaultdict(lambda: defaultdict(int))      # in port -> cycle -> value (schedule words: 1-cycle pulses)
    setm = defaultdict(lambda: defaultdict(int))       # in port -> cycle -> mask of bits already set
    checks = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # out port -> cycle -> [mask, value]
    rec_in, rec_out, internal, outside = [], [], 0, 0
    if mut and mut['kind'] == 'corrupt':
        firsts = [w['cycle_land'] for w in words if w['inst'] in cut.insts and
                  any(die.by_out.get(n) == mut['link'] for n, _ in w['bits'])]
        if not firsts:
            raise SystemExit(f'mutant {a.mutant}: no scheduled word enters the cut on {mut["link"]}')
        mut['at'] = min(firsts)
        mut['bit'] = 13 if mut['bit'] is None else mut['bit']

    def put(port, c, bit, v, why):
        m = 1 << bit
        if setm[port][c] & m and ((drive[port][c] >> bit) & 1) != v:
            raise SystemExit(f'conflict: {port} bit {bit} at {c} set twice with different values ({why})')
        setm[port][c] |= m
        if v:
            drive[port][c] |= m

    for w in words:
        by_link = defaultdict(dict)
        for (net, bit), v in w['bits'].items():
            lk = die.by_out.get(net)
            if lk is not None:
                by_link[lk][bit] = v
        if not by_link:
            continue
        bage = max(die.links[lk]['age'] for lk in by_link)     # the port is whole when its slowest lane lands
        for lk, lb in by_link.items():
            L = die.links[lk]
            src_in = bool({i for i, _ in L['src']} & cut.insts)
            dst_in = w['inst'] in cut.insts
            if dst_in == src_in:
                internal += dst_in
                outside += not dst_in
                continue
            if dst_in:                                  # neighbour -> cut: drive the producer register
                if src_ports_of(cut, L) & set(tsrc):
                    continue                            # the lane is fed from the producer cut's trace
                k = w['cycle_land'] - bage + 1 + a.t0
                hit = set()
                for bit, v in lb.items():
                    sb = L['src_bits'][bit] if bit < len(L['src_bits']) else None
                    if sb is None:
                        continue
                    pin = cut.in_by_net.get(sb[0])
                    if pin is None:
                        raise SystemExit(f'lane {lk} bit {bit}: source net {sb[0]} is not a cut input port')
                    kk, vv = k, v
                    if mut and mut['link'] == lk:
                        if mut['kind'] == 'shift':
                            kk = k + mut['n']
                        elif w['cycle_land'] == mut['at'] and bit == mut['bit']:
                            vv = 1 - v
                    put(pin['port'], kk, sb[1], vv, f'{w["event"]["tag"]} {lk}')
                    hit.add(pin['port'])
                if w.get('hold') and w['cycle_land'] != w['hold']:
                    continue
                rec_in.append(dict(lane=lk, tag=w['event']['tag'], kind=w['event']['kind'], at=f'{w["inst"]}.{w["port"]}',
                                   cycle_land=w['cycle_land'], drive_cycle=k, lane_age=L['age'], bundle_age=bage,
                                   ports=sorted(hit), derived=w['event'].get('derived_from'),
                                   **{x: w[x] for x in ('template', 'hops', 'src_sid') if x in w}))
            else:                                       # cut -> neighbour: check the landed word
                op = cut.out_by_net.get(L['out_net'])
                if op is None:
                    raise SystemExit(f'lane {lk}: {L["out_net"]} is not a cut output port')
                tc = w['cycle_land'] + a.t0 - ((bage - L['age']) if a.lane_age else 0)
                m = v = 0
                for bit, b in lb.items():
                    m |= 1 << bit
                    v |= b << bit
                checks[op['port']][tc][0] |= m
                checks[op['port']][tc][1] |= v
                rec_out.append(dict(lane=lk, tag=w['event']['tag'], kind=w['event']['kind'], at=f'{w["inst"]}.{w["port"]}',
                                    cycle_land=w['cycle_land'], check_cycle=tc, lane_age=L['age'], bundle_age=bage,
                                    port=op['port'], derived=w['event'].get('derived_from')))
    ins = []
    for port, cyc in setm.items():                      # schedule words: a pulse, 0 the next cycle unless set again
        idx = cut.ports[port]['index']
        prev = 0
        for c in sorted(set(cyc) | {c + 1 for c in cyc}):
            v = drive[port][c] if c in cyc else 0
            if v != prev:
                ins.append((c, idx, v))
                prev = v
    # trace-fed lanes: the producer cut's landed lane values, shifted back by the lane age (values hold)
    tchg = defaultdict(lambda: defaultdict(lambda: [0, 0]))     # in port -> cycle -> [mask, value]
    for lk, (pdir, run, pport, prp) in tsrc_lanes(tsrc).items():
        L = die.links[lk]
        pidx = Cut(prp['cut']).ports[pport]['index']
        for c, v in read_trace(run).get(pidx, []):
            k = c - prp['t0'] + a.t0 - L['age'] + 1
            for bit, sb in enumerate(L['src_bits']):
                if sb is None or sb[0] not in cut.in_by_net:
                    continue
                port = cut.in_by_net[sb[0]]['port']
                tchg[port][k][0] |= 1 << sb[1]
                tchg[port][k][1] |= ((v >> bit) & 1) << sb[1]
    for port, cc in tchg.items():
        cur = 0
        for c in sorted(cc):
            m, v = cc[c]
            cur = (cur & ~m) | v
            ins.append((c, cut.ports[port]['index'], cur))
    neg = [r for r in ins if r[0] < 0]
    if neg:
        raise SystemExit(f'{len(neg)} producer drives before bench cycle 0 (first {neg[0][:2]}): raise --t0 / --host-boot '
                         f'(a lane of age A needs its first landed word at >= A - 1)')
    halves = {c for c, *_ in ins if c != int(c)}
    outs = sorted((c, cut.ports[p]['index'], mv[0], mv[1]) for p, cc in checks.items() for c, mv in cc.items())
    ins.sort(key=lambda r: (r[0], r[1]))
    fmt = lambda c: (f'{c:.1f}' if c != int(c) else str(int(c)))
    (out / 'in.txt').write_text(''.join(f'{fmt(c)} {i} {v:x}\n' for c, i, v in ins))
    (out / 'out.txt').write_text(''.join(f'{fmt(c)} {i} {m:x} {v:x}\n' for c, i, m, v in outs))
    # boundary accounting: every boundary lane, its source and its scheduled traffic
    bnd = []
    for p in cut.ports.values():
        lk = None
        m = re.fullmatch(r'w_(\w+?)_(src|lnd|dst)', p['net'])
        if m:
            lk = m.group(1)
        if not lk or lk not in die.links:
            continue
        L = die.links[lk]
        if p['dir'] == 'input':
            src = 'trace' if p['port'] in tsrc else ('schedule' if p['port'] in setm else 'idle')
        else:
            src = 'checked' if p['port'] in checks else 'unchecked'
        bnd.append(dict(port=p['port'], dir=p['dir'], lane=lk, age=L['age'], K=L['K'], stations=L['stations'],
                        source=src, peers=p['peers']))
    bnd_insts = {x for b in bnd for x in b['peers']} | cut.insts
    unenc_here = [dict((k, v) for k, v in e.items()) for e in unenc
                  if str(e.get('inst', '')).split('.')[0] in bnd_insts]
    kind = 'MUTANT' if mut else ('DIAGNOSTIC' if (a.lane_age or st['stale']) else 'SCHEDULE')
    ncyc = int(max([c for c, *_ in outs] + [c for c, *_ in ins] + [a.t0]) + 50)
    doc = dict(schema=SCHEMA, tool='tools/s81_dv/dv_cut_replay.py', die_v=str(a.die_v), die_v_sha256=die.sha256,
               prog=str(prog), prog_manifest_sha256=hashlib.sha256((prog / 'manifest.json').read_bytes()).hexdigest()
               if (prog / 'manifest.json').exists() else None, cut=cut.dir, layer=S.get('layer'), t0=a.t0,
               mutant=a.mutant or None, lane_age=a.lane_age, host_boot=host, verdict_kind=kind, stale=st,
               traces=traces, boundary=bnd, in_words=rec_in, out_checks=rec_out, internal_words=internal,
               unencoded=unenc_here, unencoded_total=len(unenc), partial=bool(unenc_here),
               in_events=len(ins), out_check_lines=len(outs), half_cycle_inputs=len(halves), ncyc=ncyc,
               expected_out={p: {fmt(c): [f'{mv[0]:x}', f'{mv[1]:x}'] for c, mv in sorted(cc.items())}
                             for p, cc in checks.items()})
    (out / 'replay.json').write_text(json.dumps(doc, indent=1) + '\n')
    print(f'dv_cut_replay gen {Path(cut.dir).name}: {kind}; {len(rec_in)} lane words in ({len(ins)} events), '
          f'{len(rec_out)} lane words checked ({len(outs)} check lines); boundary {len(bnd)} lanes '
          f'({sum(b["source"] == "trace" for b in bnd)} trace-fed); unencoded boundary events {len(unenc_here)}; '
          f'stale {st["stale"]} die sha match {st["die_sha_match"]}; ncyc {ncyc}')
    return 0


def word_at(die, inst, port, val, cycle_land, kind, tag, hold=None):
    pb = die.port_bits(inst, port)
    if not pb:
        raise SystemExit(f'no port {inst}.{port} in the die build')
    w = dict(event=dict(kind=kind, tag=tag, inst=inst, port=port, cycle=cycle_land, dir='in', payload=f'{val:x}'),
             inst=inst, port=port, cycle_land=cycle_land, bits={nb: (val >> i) & 1 for i, nb in enumerate(pb) if nb})
    if hold is not None:
        w['hold'] = hold
    return w


def host_boot_words(a, die, prog, S, words):
    """--host-boot B: the compiled host boot stream (prog/host_boot.memh, 515-b host words, the dsdv_seq_host L0
    format) delivered on u_seqhost.f_host one word every 5th edge from bench cycle B (tb_dv_prog_seqhost's host slots),
    the lane-live flags f_lf = 4'b0101 held from cycle 0, and ONE job start on f_ks at bench cycle --ks (word
    --ks-word, default the seqhost bench's {v, user 37, pos 1000, tok 5000}).  The calendar accepts the start only on its
    start phase (ot_dsdv_fixed_issue), a reset-tree artefact of the cut: give --ks, and sweep its residue mod 4 once per
    build if the first run misses (record the accepted residue).  Layer cycle 0 = KS + 4 (the compiled V command leaves
    vo at KS + issue + 11 = issue + 7 in layer cycles: dsdv_seq_host header, check_seqhost.py), so --t0 is set to KS + 4."""
    hs = [int(x, 16) for x in (prog / 'prog/host_boot.memh').read_text().split()]
    ks = a.ks if a.ks is not None else a.host_boot + 5 * len(hs) + 64
    a.t0 = ks + 4
    ksw = int(a.ks_word, 16)
    end = int(max([w['cycle_land'] for w in words] + [0]) + a.t0 + 64)
    out = list(words)
    out += [word_at(die, 'u_seqhost', 'f_host', h, a.host_boot + 5 * i - a.t0, 'HOST', f'host_boot[{i}]')
            for i, h in enumerate(hs)]
    out.append(word_at(die, 'u_seqhost', 'f_ks', ksw, ks - a.t0, 'KS', 'job start'))
    lf_age = max(die.links[die.by_out[n]]['age'] for n, _ in die.port_bits('u_seqhost', 'f_lf') if n in die.by_out)
    c0 = math.ceil(lf_age - 1)                        # the first landed cycle the producer can reach from bench 0
    out += [word_at(die, 'u_seqhost', 'f_lf', 0b0101, c - a.t0, 'LF', 'lane live', hold=c0 - a.t0)
            for c in range(c0, end)]
    return out, dict(boot_start=a.host_boot, words=len(hs), last_word=a.host_boot + 5 * (len(hs) - 1), ks=ks,
                     ks_word=f'{ksw:x}', t0=a.t0, f_lf=f'0101 held from landed bench cycle {c0}',
                     memh_sha256=hashlib.sha256((prog / 'prog/host_boot.memh').read_bytes()).hexdigest())


def src_ports_of(cut, L):
    return {cut.in_by_net[sb[0]]['port'] for sb in L['src_bits'] if sb and sb[0] in cut.in_by_net}


def parse_mutant(s):
    if not s:
        return None
    f = s.split(':')
    if f[0] == 'shift' and len(f) == 3:
        return dict(kind='shift', link=f[1], n=int(f[2]))
    if f[0] == 'corrupt' and len(f) in (2, 3):
        return dict(kind='corrupt', link=f[1], bit=int(f[2]) if len(f) == 3 else None)
    raise SystemExit(f'bad --mutant {s!r}: shift:<link>:<n> | corrupt:<link>[:<bit>]')


def trace_sources(die, cut, traces):
    """cut input port -> (producer replay dir, run dir, producer output port, lane) for lanes whose producer cut ran"""
    out = {}
    for pdir, run in traces.items():
        pc = Cut(json.loads((Path(pdir) / 'replay.json').read_text())['cut'])
        for net, p in cut.in_by_net.items():
            m = re.fullmatch(r'w_(\w+?)_src', net)
            if not m or m.group(1) not in die.links:
                continue
            lk = m.group(1)
            po = pc.out_by_net.get(die.links[lk]['out_net'])
            if po is not None:
                out[p['port']] = (pdir, run, po['port'], lk)
    return out


def tsrc_lanes(tsrc):
    out = {}
    for port, (pdir, run, pport, lk) in tsrc.items():
        out[lk] = (pdir, run, pport, json.loads((Path(pdir) / 'replay.json').read_text()))
    return out


# ================================================================================================= trace / check
def read_trace(run):
    """trace.txt (`<cycle> <port index> <hex>`, value changes of every output port) -> {index: [(cycle, value)]}"""
    t = Path(run) / 'trace.txt' if Path(run).is_dir() else Path(run)
    out = defaultdict(list)
    for ln in t.read_text().splitlines():
        f = ln.split()
        if len(f) == 3:
            out[int(f[1])].append((int(f[0]), int(f[2], 16)))
    return out


def value_at(changes, c):
    v = 0
    for cc, vv in changes:
        if cc > c:
            break
        v = vv
    return v


def check(a):
    rp = json.loads((Path(a.replay) / 'replay.json').read_text())
    cut = Cut(rp['cut'])
    tr = read_trace(a.run)
    t0 = rp['t0']
    status = (Path(a.run) / 'status').read_text() if (Path(a.run) / 'status').exists() else ''
    res, bad = [], 0
    for b in rp['boundary']:
        if b['dir'] != 'output':
            continue
        p = cut.ports[b['port']]
        ch = tr.get(p['index'], [])
        exp = {float(c): (int(m, 16), int(v, 16)) for c, (m, v) in rp['expected_out'].get(b['port'], {}).items()}
        miss = [c for c, (m, v) in exp.items() if (value_at(ch, c) & m) != (v & m)]
        # strict (no unencoded boundary traffic in the programme): the lane carries nothing but the encoded words
        extra = [c for c, v in ch if v and float(c) not in exp]
        strict = not rp['partial']
        n_bad = len(miss) + (len(extra) if strict else 0)
        bad += n_bad
        res.append(dict(port=b['port'], lane=b['lane'], expected=len(exp), missed=sorted(miss)[:20],
                        unscheduled=extra[:20], n_unscheduled=len(extra), strict=strict, ok=n_bad == 0))
    sim_pass = 'TB_DV_SLICE PASS' in status
    doc = dict(schema=SCHEMA + '.check', replay=str(a.replay), run=str(a.run), verdict_kind=rp['verdict_kind'],
               sim_pass=sim_pass, trace_mismatches=bad, partial=rp['partial'],
               verdict='PASS' if (sim_pass and bad == 0) else 'FAIL', ports=res)
    Path(a.out or (Path(a.replay) / 'check.json')).write_text(json.dumps(doc, indent=1) + '\n')
    print(f'dv_cut_replay check: {doc["verdict"]} (sim {"PASS" if sim_pass else "FAIL"}, trace mismatches {bad}, '
          f'{rp["verdict_kind"]}, partial {rp["partial"]})')
    return 0 if doc['verdict'] == 'PASS' else 1


def compose(a):
    """cross-cut lane consistency: for every lane leaving cut A into cut B, B's replayed input (shifted forward by the
    lane age) must equal A's landed trace over the replay window"""
    cuts = {}
    for spec in a.cut:
        name, rest = spec.split('=', 1)
        rdir, run = rest.split(':', 1)
        rp = json.loads((Path(rdir) / 'replay.json').read_text())
        cuts[name] = dict(rp=rp, rdir=rdir, run=run, cut=Cut(rp['cut']))
    die = DieBuild(next(iter(cuts.values()))['rp']['die_v'])
    rows, bad = [], 0
    for an, A in cuts.items():
        trA = read_trace(A['run'])
        for bn, B in cuts.items():
            if an == bn:
                continue
            ins = defaultdict(list)
            for ln in (Path(B['rdir']) / 'in.txt').read_text().splitlines():
                c, i, v = ln.split()
                ins[int(i)].append((float(c), int(v, 16)))
            for net, pb in B['cut'].in_by_net.items():
                m = re.fullmatch(r'w_(\w+?)_src', net)
                if not m or m.group(1) not in die.links:
                    continue
                lk = m.group(1)
                L = die.links[lk]
                pa = A['cut'].out_by_net.get(L['out_net'])
                if pa is None:
                    continue
                shift = L['age'] - 1 - B['rp']['t0'] + A['rp']['t0']
                got = [(c + shift, v) for c, v in ins.get(pb['index'], [])]
                ref = trA.get(pa['index'], [])
                lo, hi = 0, min(A['rp']['ncyc'], B['rp']['ncyc'] + shift)
                cyc = sorted({c for c, _ in got} | {c for c, _ in ref})
                mism = [c for c in cyc if lo <= c <= hi and value_at(ref, c) != value_at(sorted(got), c)]
                bad += len(mism)
                rows.append(dict(lane=lk, producer=an, consumer=bn, consumer_source=next(
                    (b['source'] for b in B['rp']['boundary'] if b['port'] == pb['port']), None),
                    words_producer=sum(1 for _, v in ref if v), words_consumer=sum(1 for _, v in got if v),
                    mismatch_cycles=mism[:20], ok=not mism))
    doc = dict(schema=SCHEMA + '.compose', cuts={k: dict(replay=v['rdir'], run=v['run']) for k, v in cuts.items()},
               lanes=rows, mismatches=bad, verdict='PASS' if bad == 0 else 'FAIL')
    Path(a.out).write_text(json.dumps(doc, indent=1) + '\n')
    print(f'dv_cut_replay compose: {doc["verdict"]} ({len(rows)} cross-cut lanes, {bad} mismatching cycles)')
    return 0 if bad == 0 else 1


def ages(a):
    die = DieBuild(a.die_v)
    doc = dict(schema=SCHEMA + '.ages', die_v=str(a.die_v), die_v_sha256=die.sha256,
               links={k: dict((x, v) for x, v in L.items() if x != 'src_bits') for k, L in sorted(die.links.items())})
    if a.prog:
        prog = Path(a.prog)
        S = json.loads((prog / 'schedule.json').read_text())
        man = json.loads((prog / 'manifest.json').read_text()) if (prog / 'manifest.json').exists() else {}
        doc['stale'] = stale_check(S, die, man)
        print(f"ages: {len(die.links)} lanes; programme stale {doc['stale']['stale']} "
              f"({len(doc['stale']['link_age_diffs'])} age diffs), die sha match {doc['stale']['die_sha_match']}")
    if a.out:
        Path(a.out).write_text(json.dumps(doc, indent=1) + '\n')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('ages')
    g.add_argument('--die-v', required=True)
    g.add_argument('--prog')
    g.add_argument('--out')
    g = sp.add_parser('gen')
    g.add_argument('--die-v', required=True)
    g.add_argument('--prog', required=True)
    g.add_argument('--cut', required=True)
    g.add_argument('--out', required=True)
    g.add_argument('--t0', type=int, default=100)
    g.add_argument('--trace', action='append', default=[], help='PRODUCER_REPLAY_DIR=RUN_DIR (compose: trace-fed lanes)')
    g.add_argument('--mutant', default='')
    g.add_argument('--lane-age', action='store_true')
    g.add_argument('--allow-stale', action='store_true')
    g.add_argument('--host-boot', type=int, default=None, help='bench cycle of the first host boot word (cuts with u_seqhost)')
    g.add_argument('--ks', type=int, default=None)
    g.add_argument('--ks-word', default=f'{(1 << 52) | (37 << 42) | (1000 << 21) | 5000:x}')
    g = sp.add_parser('check')
    g.add_argument('--replay', required=True)
    g.add_argument('--run', required=True)
    g.add_argument('--out')
    g = sp.add_parser('compose')
    g.add_argument('--cut', action='append', required=True, help='NAME=REPLAY_DIR:RUN_DIR')
    g.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    return dict(ages=ages, gen=gen, check=check, compose=compose)[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
