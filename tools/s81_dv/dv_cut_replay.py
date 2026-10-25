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
       ages), with the hops field of that stop, so a cut on the line path sees it on both of its line faces; the column-4
       injector re-injects every V CTL beat BOTH ways (ot_s81sl_xr), so the copy on the other line side is derived too.
  SVCJ at <svc entry>.j: the job word (payload hex) on the j pin at the event cycle.
  WORDS (LB2-S81/EVENTS, 10-18): every event that carries `words` [[edge, value hex, mask hex]] on `ports` (the
       compiler's word encoders: QF q frames at the svc entry q pins, PV P.V stream and SVCDONE jd pulses at the svc
       entries' output registers, ...).  dir in: edge = the consumer pin's landed edge; dir out: edge = the producer
       output register's edge, the word lands at each consumer at edge + the slowest lane age of its bundle.  The mask
       selects the checked bits (data the cut cannot reproduce -- engine values without the HBM image, fixture rows --
       is masked and named in the event's data_masked); a consumer cut is driven with the full value.  valid_bit names
       the lane's valid bit: the strict check counts extra words on it only (data lanes may hold stale bits).
       `width` (TOK-DS-GAPS 10-24) limits the word to the low bits of its ports (an xfin NX flit is one 276-b lane word
       on a 1,104-b line port): bundle age and checked bits are those of the lanes under the width.  A CTL event with
       `payload186` (layer-entry target-5 row writes) is driven as the seq_host line beat of that payload (no template).
  Not cut words: boundary 'offdie' events (beyond the die's elastic link layer: the end-slice RD beats leave through
       the reliable link lanes, bench_vpx checks them) and dir 'internal' events (inside one instance: the vs command
       rides the CTL beat of its calendar row, `ctl_at`) are listed apart and do not make a replay partial.
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
                           [--mutant shift:<link>:<n> | corrupt:<link>[:<bit>] | shift-kind:<KIND>:<n> |
                            expect-shift:<KIND>:<n>] [--lane-age] [--allow-stale]
  dv_cut_replay.py check   --replay DIR --run RUN [--out check.json]      (trace vs every encoded word, no extras)
  dv_cut_replay.py compose --cut NAME=REPLAY_DIR:RUN_DIR ... --out compose.json   (cross-cut lane consistency)
Mutants (negative controls; replay.json verdict_kind MUTANT): shift moves every word of ONE boundary input lane by n
cycles, corrupt flips one bit of its first word, shift-kind:<KIND>:<n> moves every driven word of one event class,
expect-shift:<KIND>:<n> moves every check of one event class (the RTL trace must then miss it) -- the bench / check
must FAIL (commit the run as the fail witness).
--lane-age is a DIAGNOSTIC: each output lane is checked at its own landing (tear-tolerant), never a schedule verdict.
"""
import argparse
import gzip
import hashlib
import json
import os
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

from xr_timing import inject_cycles, check_run_source

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

    def __init__(self, die_v, plan=None):
        self.path = str(die_v)
        # TOK-FUNC-S81 (10-21): the 72-frame die abuts neighbour slices (0-station plan links): their direction comes
        # from the plan (sibling ../p4l/plan.json of a dv_layer_compile die tree, or OT_DV_DIE_PLAN); none -> as before
        if plan is None:
            sib = Path(die_v).resolve().parent.parent / 'p4l/plan.json'
            plan = os.environ.get('OT_DV_DIE_PLAN') or (str(sib) if sib.exists() else None)
        self.plan_path = plan
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
            # TOK-S81-GAPS/INT 10-19: an x_frame lane without a die-top ld_ lands INSIDE its receiving frame (crs4 with the
            # receiver's lk strap, 3 b per lane; G8R2 frame_lk derived from the land plan K) -- same model as
            # dv_layer_compile Die._links (internal_landing), else every frame lane reads STALE against the compiler
            internal = None
            mi = re.fullmatch(r'x_f_.+_l(\d+)', lk)
            if lk not in ld and mi:
                for dn, _ in users.get((lk, 'dst'), []):
                    sv = self.strap(dn, 'lk')
                    if sv is not None:
                        k, internal = (sv >> (3 * int(mi.group(1)))) & 7, dn
                        break
            age = (math.ceil(n / 2) + k + 1) if (lk in ld or internal) else n / 2
            first = st[lk][min(st[lk])] if n else ld.get(lk)
            src_bits = self.port_bits(first, 'i') if first else []
            out_net = f'w_{lk}_lnd' if lk in ld else f'w_{lk}_dst'
            self.links[lk] = dict(stations=n, landing=ld.get(lk), internal_landing=internal, K=k, age=age, out_net=out_net,
                                  src=sorted(users.get((lk, 'src'), [])),
                                  dst=sorted(users.get((lk, 'lnd'), []) + users.get((lk, 'dst'), [])),
                                  src_bits=src_bits)
        if self.plan_path:
            plan = json.loads(Path(self.plan_path).read_text())
            B = plan['blocks']
            for pl in plan['links']:
                lk = pl['i'].replace('-', '_')
                if lk in self.links or pl.get('s', 0) > 0:
                    continue
                a, b = 'u_' + B[pl['e'][0][0]]['name'], 'u_' + B[pl['e'][1][0]]['name']
                us = users.get((lk, 'src'), []) + users.get((lk, 'dst'), []) + users.get((lk, 'lnd'), [])
                src = sorted(u for u in us if u[0] == a)
                dst = sorted(u for u in us if u[0] == b)
                if src and dst:
                    self.links[lk] = dict(stations=0, landing=None, internal_landing=None, K=None, age=0,
                                          out_net=f'w_{lk}_src', src=src, dst=dst, src_bits=[], abutted=True)
        self.by_out = {L['out_net']: lk for lk, L in self.links.items() if not L.get('abutted')}

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
    if ev.get('payload186') is not None:
        # TOK-DS-GAPS 10-24: an explicit-payload CTL beat (layer-entry target-5 row writes, layer_prog/norm_nx.py): not a
        # calendar template; the line beat is the seq_host packer's (dv_layer_compile.ctl_line_beat, src 4, hops 0)
        ti, beat = None, 1 | 4 << 9 | int(ev['payload186'], 16) << 21
    else:
        ti = int(ev['payload'].split()[1].rstrip(';'))
        beat = int(T[ti]['beat'], 16)
    if (beat >> 4) & 0x1F:
        raise ValueError(f'template {ti} carries hops {(beat >> 4) & 0x1F}: only line-default (0) beats are modelled')
    if ev['port'] == 'vi':
        # TOKd-S81 10-23 (c14/G9 entry job22, u_s_4N.vi on w_tvN_seqhost_lnd): a V-rung beat is the seq_host packer's
        # word itself (hops 0, src 4); the stop rewrites hops / src only when it re-injects the beat on its line.
        return beat, ti, (beat >> 4) & 0x1F, (beat >> 9) & 0xF
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
    """every CTL line beat seen at a schedule slice passes EVERY stop of BOTH line directions: the column-4 injector's
    control plane re-injects a V CTL beat on its tier line both ways (ot_s81sl_xr ci_dir 3'b011 for every V CTL beat,
    whatever its slice mask; hops 0 = each side's line default, so the W copy reaches column 0 and the E copy column 7),
    and ot_s81sl_rstop forwards a non-NX beat with hops > 1.  From the compiled arrival at the event's slice, derive the
    injector's line-out edge, then the arrival at each other stop of both directions from the die's bundle ages (the
    compiler's line model -- a stop is RSTOP_HOP edges, a hop is the slowest lane of the bundle), on the build.
    TOK-S81-GAPS/CTL 10-19: the G8 cut_3S_ctl L0 run shows every W-bound beat on xrE_4S and every E-bound one on xrW_2S."""
    have = {(e['inst'], e['port'], e['cycle'], e['payload']) for e in S['events'] if e['kind'] == 'CTL'}
    out = []
    W = list(range(LINE_INJECT_COL - 1, -1, -1))      # W-bound stops (arrive on ri_e)
    E = list(range(LINE_INJECT_COL + 1, 8))           # E-bound stops (arrive on ri_w)
    for e in S['events']:
        if e['kind'] != 'CTL' or e['dir'] != 'in' or e['port'] not in ('ri_e', 'ri_w', 'vi'):
            continue
        col, tier = int(e['inst'][4]), e['inst'][5]
        hop = lambda a, b: line_link_age(die, f'u_s_{a}{tier}', f'u_s_{b}{tier}')[0] + RSTOP_HOP
        if e['port'] == 'vi':
            if col != LINE_INJECT_COL:
                raise ValueError(f'CTL event {e["tag"]} at {e["inst"]}.vi is not the column-{LINE_INJECT_COL} injector')
            t_out = e['cycle'] - RSTOP_HOP + inject_cycles(S)
        else:
            path = W if e['port'] == 'ri_e' else E
            if col not in path:
                raise ValueError(f'CTL event {e["tag"]} at {e["inst"]}.{e["port"]} is not on a line from column '
                                 f'{LINE_INJECT_COL}')
            t_out, prev = e['cycle'], LINE_INJECT_COL
            for c in path[:path.index(col) + 1]:
                t_out -= hop(prev, c)
                prev = c
            # TOKj-S81 10-23 (fc30 entry job17: 51 u_s_3N.ri_e rows, w_tvN_seqhost_lnd 51 words unscheduled): a line
            # beat compiled at a stop is the seq_host V rung beat re-injected by the column-4 slice, so the rung word
            # on <u_s_4T>.vi is derived too (inverse of the vi branch above; ctl_beat leaves a vi beat unrewritten).
            v = dict(e, cycle=t_out + RSTOP_HOP - inject_cycles(S), inst=f'u_s_{LINE_INJECT_COL}{tier}', port='vi',
                     derived_from=f'{e["inst"]}@{e["cycle"]}')
            if (v['inst'], 'vi', v['cycle'], v['payload']) not in have:
                have.add((v['inst'], 'vi', v['cycle'], v['payload']))
                out.append(v)
        for path, port in ((W, 'ri_e'), (E, 'ri_w')):
            t, prev = t_out, LINE_INJECT_COL
            for c in path:
                t += hop(prev, c)
                prev = c
                d = dict(e, cycle=t, inst=f'u_s_{c}{tier}', port=port, derived_from=f'{e["inst"]}@{e["cycle"]}')
                if (d['inst'], d['port'], d['cycle'], d['payload']) not in have:
                    have.add((d['inst'], d['port'], d['cycle'], d['payload']))
                    out.append(d)
    return out


def derive_vctl_line_events(S, die):
    """TOK-S81-GAPS 10-19 (G8R2 cut_3S L0: 15 unscheduled line words on xrW_2S_l0 / xrE_3S_l0): a CTL beat the G-unit
    sends on vo_s / vo_n lands on the V face of the slice its lane reaches (u_s_3S / u_s_3N), and ot_s81sl_xr re-injects
    EVERY V CTL beat on the tier line both ways (ci_dir 3'b011, hops 0 = line default) -- the same path as the column-4
    seq_host V injection in derive_line_events, from the receiving slice's column.  The beat on each stop's line face is
    the G-unit word with the hops / src fields rewritten as ctl_beat does (hops = col + 1 W-bound on ri_e, 8 - col
    E-bound on ri_w; src = the injecting slice's sid).  Timing = derive_line_events: line out = V landed edge
    - RSTOP_HOP + V_CTL_INJECT, then line_link_age + RSTOP_HOP per stop (measured: row 1000 lands 3S 1489, 2S / 4S 1505)."""
    out = []
    for e in S['events']:
        if e.get('inst') != 'u_gunit' or e.get('dir') != 'out' or e.get('kind') != 'CTL' or not e.get('words'):
            continue
        try:
            lw = event_words(e, die)
        except ValueError:
            continue
        for w in lw:
            m = re.fullmatch(r'u_s_(\d)([NS])', w['inst'])
            if not m:
                continue
            col, tier = int(m.group(1)), m.group(2)
            src = die.sid(w['inst'])
            hop = lambda a, b: line_link_age(die, f'u_s_{a}{tier}', f'u_s_{b}{tier}')[0] + RSTOP_HOP
            t_out = w['cycle_land'] - RSTOP_HOP + inject_cycles(S)
            for path, port in ((range(col - 1, -1, -1), 'ri_e'), (range(col + 1, 8), 'ri_w')):
                t, prev = t_out, col
                for c in path:
                    t += hop(prev, c)
                    prev = c
                    hops = c + 1 if port == 'ri_e' else 8 - c
                    ws = []
                    for edge, v, mk in e['words']:
                        v = int(v, 16)
                        v = (v & ~(0x1F << 4) & ~(0xF << 9)) | (hops & 0x1F) << 4 | (src & 0xF) << 9
                        ws.append([t, f'{v:x}', mk])
                    out.append(dict(e, cycle=t, inst=f'u_s_{c}{tier}', port=port, ports=[port], dir='in', words=ws,
                                    derived_from=f'u_gunit.{e["port"]}@{e["cycle"]} via {w["inst"]}'))
    return out


def lane_of_net(die, net):
    m = re.fullmatch(r'w_(\w+?)_(src|lnd|dst)', net)
    return m.group(1) if m and m.group(1) in die.links else None


def event_words(e, die):
    """LB2-S81/EVENTS: an event with `words` [[edge, value hex, mask hex]] on `ports` (LSB-first concatenation) ->
    consumer-pin words.  dir in: the ports are the consumer's, the edge is the landed edge.  dir out: the ports are the
    producer's output registers (w_<lane>_src nets), the edge is the register's; each consumer instance gets one word
    on its landed nets at edge + the slowest lane age of its bundle (the line / port model).  bits = the full value
    (what a consumer cut is driven with), chk = the bits the mask checks; valid = the consumer bit of `valid_bit`."""
    pb = []
    for p in e.get('ports') or [e['port']]:
        b = die.port_bits(e['inst'], p)
        if not b:
            raise ValueError(f'event {e["kind"]} {e["tag"]}: no port {e["inst"]}.{p} in the die build')
        pb += b
    if e.get('width') is not None:
        # TOK-DS-GAPS 10-24: a word narrower than its port bundle (an xfin NX flit = one 276-b lane word on a 1,104-b
        # line port) occupies only the low `width` bits: it is whole when ITS lanes land (the receiving rstop reads
        # nothing above), so the bundle age and the checked bits are those of the lanes under the width
        pb = pb[:int(e['width'])]
    vb = e.get('valid_bit')
    out = []
    if e['dir'] == 'in':
        groups = {e['inst']: [(i, nb) for i, nb in enumerate(pb)]}
    else:
        groups = defaultdict(list)
        for i, nb in enumerate(pb):
            lk = lane_of_net(die, nb[0]) if nb else None
            if lk is None or not nb[0].endswith('_src'):
                continue                                # a constant / unconnected producer bit leaves nothing
            L = die.links[lk]
            for inst in sorted({x[0] for x in L['dst']}):
                groups[inst].append((i, (L['out_net'], nb[1])))
    for inst, ib in groups.items():
        bage = 0
        if e['dir'] == 'out':
            bage = max(die.links[die.by_out[nb[0]]]['age'] for _, nb in ib)
        for edge, v, m in e['words']:
            v, m = int(v, 16), int(m, 16)
            bits = {nb: (v >> i) & 1 for i, nb in ib if nb is not None}
            chk = {nb for i, nb in ib if nb is not None and (m >> i) & 1}
            valid = {nb for i, nb in ib if nb is not None and i == vb}
            out.append(dict(event=dict((k, x) for k, x in e.items() if k != 'words'), inst=inst, port=e['port'],
                            cycle_land=edge + bage, bits=bits, chk=chk, valid=valid))
    return out


def valid_refs(S, die):
    """consumer landed bit -> the landed bit of its bundle's valid flag, from the programme's port_valid declarations
    and every event's valid_bit (producer ports map through their lanes to the consumer's landed nets)"""
    decl = list(S.get('port_valid', []))
    for e in S['events']:
        if e.get('valid_bit') is not None:
            decl.append(dict(inst=e['inst'], ports=e.get('ports') or [e['port']], bit=e['valid_bit']))
    ref = {}
    for d in decl:
        pb = []
        for p in d['ports']:
            pb += die.port_bits(d['inst'], p)
        if d['bit'] >= len(pb) or pb[d['bit']] is None:
            continue
        land = lambda nb: (die.links[lane_of_net(die, nb[0])]['out_net'], nb[1]) \
            if nb and nb[0].endswith('_src') and lane_of_net(die, nb[0]) else nb
        v = land(pb[d['bit']])
        for nb in pb:
            if nb is not None and land(nb) != v:
                ref[land(nb)] = v
    return ref


HP_PRODUCER_GAP = ('the slices\' HC partial roots (hc.fn / hc.sumsq chunk sums, kind-7 HP send on tv to the G-unit) are '
                   'not lowered (lowering PARTIAL: ot_s81sl_xr / frames cfg7 / ot_s81sl_vn send config): the HP words '
                   'are fixture-model values, so a cut holding the producer slice cannot be checked for them (a cut '
                   'holding the G-unit is driven with them)')


SC_PRODUCER_GAP = ('the router scores the slices send the G-unit (sqrt(softplus) of the ffn.router gate rows after '
                   'ffn.router_allgather) have no compiled producer (ffn.router / ffn.router_allgather GAP on this '
                   'programme): the SC words are fixture values, so a cut holding the producer slice cannot be checked '
                   'for them (a cut holding the G-unit is driven with them)')


def hp_gap(evs):
    """TOK-S81-GAPS 10-19 (G8R2 cut_3S L0: 827 tvN_s_3S words all-zero): HP beats into the G-unit come from the slices'
    unlowered HC send (lower_gu payload 'fixture slice model') -> producer_gap, like the svc QF q stream; SC (router
    scores, fixture) likewise (27 tvN_s_3S words)"""
    for e in evs:
        if e.get('inst') == 'u_gunit' and e.get('dir') == 'in' and not e.get('producer_gap'):
            if e.get('kind') == 'HP':
                e['producer_gap'] = HP_PRODUCER_GAP
            elif e.get('kind') == 'SC':
                e['producer_gap'] = SC_PRODUCER_GAP


def landed_words(S, T, die):
    """(consumer inst, port) words at the consumer pin: [{event, inst, port, cycle_land, bits {(net, bit): v}}];
    the events no cut can check at a fixed cycle (offdie) and the slice-internal ones are returned apart"""
    words, unenc, offdie, internal = [], [], [], []
    evs = S['events'] + derive_line_events(S, die) + derive_vctl_line_events(S, die)
    hp_gap(evs)
    for e in evs:
        if e.get('boundary') == 'offdie':
            offdie.append(e)
            continue
        if e['dir'] == 'internal':
            (internal if e.get('ctl_at') is not None else unenc).append(e)
            continue
        if e.get('words') and not e.get('plan_only'):
            try:
                words += event_words(e, die)
            except ValueError as x:
                unenc.append(dict(e, why=str(x), words=None))
            continue
        if e['dir'] != 'in':
            unenc.append(e)       # the programme states what a unit sends, not the word (fixture payloads)
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
    return words, unenc, offdie, internal


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
def bk_drain_sink_filter(S, T, spec):
    """--bk-drain-sink UID[,UID] (TOK-DS 10-24, opt-in candidate dsdv_bk_g/ot_dsdv_vstop BK_DRAIN_SINK=1, Codex 51ae2e4cef):
    the BK rung stop consumes a CTL beat whose payload is a drain command addressed to its uid (payload186 [7:0] = BK uid,
    [10:8] = op 1; on the beat [28:21] / [31:29]), so the beat never reaches the column-4 slice and is never re-injected on
    the tier line.  The compiler still schedules it as a slice CTL beat (vi + both line directions); drop exactly those
    events (and so their derived line copies) for the listed uids and record them.  Only valid on a build with the sink ON;
    default (no option) keeps the legacy transparent-forwarding model."""
    if not spec:
        return None
    uids = {int(x, 16) for x in str(spec).split(',')}
    drop, keep = [], []
    for e in S['events']:
        t = None
        if e.get('kind') == 'CTL' and str(e.get('payload', '')).startswith('template '):
            t = T.get(int(str(e['payload']).split()[1]))
        p = int(t['payload186'], 16) if t and t.get('payload186') else None
        if p is not None and (p >> 8) & 7 == 1 and (p & 0xff) in uids:
            drop.append(dict(tag=e['tag'], inst=e['inst'], port=e['port'], cycle=e['cycle'], payload186=t['payload186']))
        else:
            keep.append(e)
    S['events'] = keep
    return dict(uids=sorted(hex(u) for u in uids), consumed_events=drop, n=len(drop))


def gen(a):
    die = DieBuild(a.die_v)
    prog = Path(a.prog)
    S = json.loads((prog / 'schedule.json').read_text())
    T = {t['i']: t for t in json.loads((prog / 'prog/ctl_templates.json').read_text())['templates']}
    man = json.loads((prog / 'manifest.json').read_text()) if (prog / 'manifest.json').exists() else {}
    bk_sunk = bk_drain_sink_filter(S, T, a.bk_drain_sink)
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
    words, unenc, offdie, internal_ev = landed_words(S, T, die)
    host = None
    if a.host_boot is not None or a.idle_run:
        words, host = host_boot_words(a, die, prog, S, words, cut)
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
    pgap, gap_lanes = set(), set()
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
        if w.get('bundle_age') is not None:                   # a part-word of a wider port bundle (held KS payload /
            bage = w['bundle_age']                            # start pulse): launched with the whole bundle
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
                if any(lk.startswith(x) for x in a.equalize):
                    # TOK-S81-GAPS/GU: --equalize models a die-gap fix (the bundle's lanes land together, as an equal
                    # station count / per-lane K would make them): the lane is launched at its own age -> DIAGNOSTIC
                    k = w['cycle_land'] - L['age'] + 1 + a.t0
                hit = set()
                for bit, v in lb.items():
                    sb = L['src_bits'][bit] if bit < len(L['src_bits']) else None
                    if sb is None:
                        continue
                    pin = cut.in_by_net.get(sb[0])
                    if pin is None:
                        raise SystemExit(f'lane {lk} bit {bit}: source net {sb[0]} is not a cut input port')
                    kk, vv = k, v
                    if mut and mut['kind'] == 'shift-kind' and w['event']['kind'] == mut['ev']:
                        kk = k + mut['n']
                    if mut and mut.get('link') == lk:
                        if mut['kind'] == 'shift':
                            kk = k + mut['n']
                        elif w['cycle_land'] == mut['at'] and bit == mut['bit']:
                            vv = 1 - v
                    put(pin['port'], kk, sb[1], vv, f'{w["event"]["tag"]} {lk}')
                    hit.add(pin['port'])
                if w.get('hold') is not None and w['cycle_land'] != w['hold']:
                    continue
                rec_in.append(dict(lane=lk, tag=w['event']['tag'], kind=w['event']['kind'], at=f'{w["inst"]}.{w["port"]}',
                                   cycle_land=w['cycle_land'], drive_cycle=k, lane_age=L['age'], bundle_age=bage,
                                   ports=sorted(hit), derived=w['event'].get('derived_from'),
                                   **{x: w[x] for x in ('template', 'hops', 'src_sid') if x in w}))
            else:                                       # cut -> neighbour: check the landed word
                if w['event'].get('producer_gap'):
                    key = (w['event']['kind'], w['event']['tag'], w['inst'])
                    gap_lanes.add(lk)
                    if key not in pgap:
                        pgap.add(key)
                        unenc.append(dict(w['event'], why='producer not programmed: ' + w['event']['producer_gap']))
                    continue
                op = cut.out_by_net.get(L['out_net'])
                if op is None:
                    raise SystemExit(f'lane {lk}: {L["out_net"]} is not a cut output port')
                tc = w['cycle_land'] + a.t0 - ((bage - L['age']) if a.lane_age else 0)
                if mut and mut['kind'] == 'expect-shift' and w['event']['kind'] == mut['ev']:
                    tc += mut['n']
                m = v = 0
                chk = w.get('chk')
                for bit, b in lb.items():
                    if chk is not None and (L['out_net'], bit) not in chk:
                        continue
                    m |= 1 << bit
                    v |= b << bit
                if not m:
                    continue
                if checks[op['port']][tc][0] & m & (checks[op['port']][tc][1] ^ v):
                    raise SystemExit(f'conflict: check {op["port"]} at {tc} expects two values ({w["event"]["tag"]})')
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
    vref = valid_refs(S, die)
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
        vr = {}
        if p['dir'] == 'output':
            own = sorted({v for (n, _), v in vref.items() if n == p['net']})
            if own and own[0][0] in cut.out_by_net:
                vr = dict(valid_ref=dict(port=cut.out_by_net[own[0][0]]['port'], bit=own[0][1]))
        bnd.append(dict(port=p['port'], dir=p['dir'], lane=lk, age=L['age'], K=L['K'], stations=L['stations'],
                        source=src, peers=p['peers'], **vr))
    bnd_insts = {x for b in bnd for x in b['peers']} | cut.insts
    here = lambda evs: [dict((k, v) for k, v in e.items() if k != 'words') for e in evs
                        if str(e.get('inst', '')).split('.')[0] in bnd_insts]
    unenc_here, offdie_here, internal_here = here(unenc), here(offdie), here(internal_ev)
    # strict per output lane: no unencoded traffic can be on it (a producer-gap lane, or a lane whose producer /
    # consumer instance has an unencoded event of unknown lanes)
    loose = {str(e.get('inst', '')).split('.')[0] for e in unenc_here if not e.get('producer_gap')}
    # u_seqhost.t_host (alive / status / host read words toward the host PHY) is the off-die host face: elastic, not on
    # the compiled timeline (dsdv_seq_host header), so its lane is never strict (TOK-S81-GAPS/CTL 10-19)
    th = {nb for nb in die.port_bits('u_seqhost', 't_host') if nb} if 'u_seqhost' in die.inst else set()
    for b in bnd:
        if b['dir'] == 'output':
            L = die.links[b['lane']]
            b['strict'] = b['lane'] not in gap_lanes and not ({x[0] for x in L['src'] + L['dst']} & loose)
            if th and th & {tuple(x) for x in L['src_bits'] if x}:
                b['strict'], b['loose_why'] = False, 'host status lane (u_seqhost.t_host): off-die elastic face'
    by_kind = defaultdict(lambda: defaultdict(int))
    for r in rec_in:
        by_kind[r['kind']]['in_words'] += 1
    for r in rec_out:
        by_kind[r['kind']]['out_checks'] += 1
    for x, n in ((unenc_here, 'unencoded'), (offdie_here, 'offdie'), (internal_here, 'internal')):
        for e in x:
            by_kind[e['kind']][n] += 1
    kind = 'MUTANT' if mut else ('DIAGNOSTIC' if (a.lane_age or st['stale'] or a.equalize) else 'SCHEDULE')
    ncyc = int(max([c for c, *_ in outs] + [c for c, *_ in ins] + [a.t0]) + 50)
    doc = dict(schema=SCHEMA, tool='tools/s81_dv/dv_cut_replay.py', die_v=str(a.die_v), die_v_sha256=die.sha256,
               prog=str(prog), prog_manifest_sha256=hashlib.sha256((prog / 'manifest.json').read_bytes()).hexdigest()
               if (prog / 'manifest.json').exists() else None, cut=cut.dir, layer=S.get('layer'), t0=a.t0,
               timing_contract=S.get('timing_contract'),
               mutant=a.mutant or None, lane_age=a.lane_age, equalize=a.equalize, host_boot=host, verdict_kind=kind, stale=st,
               bk_drain_sink=bk_sunk,
               traces=traces, boundary=bnd, in_words=rec_in, out_checks=rec_out, internal_words=internal,
               unencoded=unenc_here, unencoded_total=len(unenc), partial=bool(unenc_here),
               offdie=offdie_here, internal_events=internal_here, by_kind={k: dict(v) for k, v in sorted(by_kind.items())},
               in_events=len(ins), out_check_lines=len(outs), half_cycle_inputs=len(halves), ncyc=ncyc,
               expected_out={p: {fmt(c): [f'{mv[0]:x}', f'{mv[1]:x}'] for c, mv in sorted(cc.items())}
                             for p, cc in checks.items()})
    (out / 'replay.json').write_text(json.dumps(doc, indent=1) + '\n')
    print(f'dv_cut_replay gen {Path(cut.dir).name}: {kind}; {len(rec_in)} lane words in ({len(ins)} events), '
          f'{len(rec_out)} lane words checked ({len(outs)} check lines); boundary {len(bnd)} lanes '
          f'({sum(b["source"] == "trace" for b in bnd)} trace-fed); unencoded boundary events {len(unenc_here)} '
          f'({sorted({e["kind"] for e in unenc_here})}), offdie {len(offdie_here)}, internal {len(internal_here)}; '
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


KS_START_BIT = 52     # f_ks = {start, user 10, tok 21, pos 21}


def ks_source_words(die, ksw, ks_land, end):
    """S81-P10 10-24 (fc30 entry, every job: the KS word lands TORN on eks_7N, bits of hf_7N_l1 (age 38) one edge before
    those of hf_7N_l2 (age 39)): model the REAL f_ks producer, not a one-edge pulse of the whole word.  The producer is
    the host RX of u_s_7N (ot_s81sl_lep g_hrx): fk_d = f_ks[51:0] is a register loaded only on a KS frame and HELD,
    fk_s = f_ks[52] (start) is a one-edge pulse; both launch on the same source edge.  Every consumer (dsdv_seq_host
    ks_q, dsdv_eng_rr ks) samples the payload on the start edge, so a bundle whose lanes differ in age is whole at the
    start's landed edge as long as start rides the slowest lane or the payload is held (KS frames >= skew + 1 apart).
    Returns the start pulse word (landed at ks_land) + the payload held from ks_land to end, all launched with the whole
    f_ks bundle (bundle_age = its slowest lane)."""
    pb = die.port_bits('u_seqhost', 'f_ks')
    if not pb:
        raise SystemExit('no port u_seqhost.f_ks in the die build')
    lanes = {lane_of_net(die, nb[0]) for nb in pb if nb}
    bage = max(die.links[lk]['age'] for lk in lanes if lk in die.links) if lanes - {None} else None
    w0 = word_at(die, 'u_seqhost', 'f_ks', ksw, ks_land, 'KS', 'job start')
    pulse = dict(w0, bits={nb: v for nb, v in w0['bits'].items() if nb == pb[KS_START_BIT]}, bundle_age=bage)
    pay = ksw & ((1 << KS_START_BIT) - 1)
    out = [pulse]
    for c in range(math.floor(ks_land), math.ceil(end)):
        w = word_at(die, 'u_seqhost', 'f_ks', pay, c, 'KS', 'job start payload (held)', hold=math.floor(ks_land))
        w['bits'] = {nb: v for nb, v in w['bits'].items() if nb != pb[KS_START_BIT]}
        w['bundle_age'] = bage
        out.append(w)
    return out


def ks_engram_words(die, ksw, ks_land):
    """TOKj-S81 10-23 (fc30 entry, every job: 2 unscheduled words on the strict lane eks_7N at 2307 / 2308): with
    HOSTB_ENABLE 0, dsdv_hostb_seqhost_mux forwards the landed f_ks pins combinationally on engram_f_ks (hostb_landing
    `assign engram_f_ks = legacy_f_ks`) to u_eng.f_ks.  The engram engine must receive the job-start word WHOLE, at
    the f_ks landed edge + the forward bundle's slowest lane age (the port model: a port is whole when its slowest lane
    lands).  Encoded as the u_eng.f_ks pin word, so a cut holding u_seqhost CHECKS it (a torn f_ks bundle -- lanes of
    unequal age -- then fails here instead of passing as two unexpected words).  Any other seqhost master (hostb
    landing / starter in the path) has its own latency: the forward is then not encoded (returns none)."""
    sh = die.inst.get('u_seqhost')
    if not sh or sh['master'] != 'dsdv_hostb_seqhost_mux' or not re.search(r'\.HOSTB_ENABLE\(\s*0\s*\)', sh['params']):
        return []
    fb = die.port_bits('u_seqhost', 'engram_f_ks')
    lanes = {lane_of_net(die, nb[0]) for nb in fb if nb}
    if not fb or None in lanes or not die.port_bits('u_eng', 'f_ks'):
        return []
    age = max(die.links[lk]['age'] for lk in lanes)
    return [word_at(die, 'u_eng', 'f_ks', ksw, ks_land + age, 'KS', 'job start -> engram f_ks (u_seqhost forward)')]


def seqhost_live(die, cut, idle_run):
    """TOK-S81-GAPS/CTL: the bench cycle from which u_seqhost captures host words.  dsdv_sh_lk gates the host valid with
    its relayed reset (fi[0] <= rn & f_host[0]) and t_host <= rn ? {alive 1, ...} : 0, so the first edge t_host's alive bit
    (bit 76) leaves the unit = rn release + 1.  Read from an idle run of THIS build (trace.txt of the cut's landed
    t_host lane): live = alive landed cycle - lane age - 1.  A boot word landing before that is silently dropped
    (10-18 G8 cut_3S_ctl L0: header words at 64/69 dropped, rn up at ~80 -> issuer fault code 4, no job)."""
    pb = die.port_bits('u_seqhost', 't_host')
    nb = pb[76] if len(pb) > 76 else None
    # t_host's alive bit fans out to several lanes (c14: ht_7N age 38 and hbc_reverse_l0 age 22) and die.links is built
    # from a set, so next() picked either one run to run (live 99 or 98, alive landed 138 or 121).  Take the host
    # return lane ht_* (it lands beside the forward host lanes hf_*, whose landing gates the boot stream; its age gives
    # the measured unit edge: t_host alive at the pin at 100 = live 99 + 1), then the name order: deterministic.
    lks = sorted((k for k, L in die.links.items() if nb and nb in L['src_bits'] and cut.out_by_net.get(L['out_net'])),
                 key=lambda k: (not k.startswith('ht_'), k))
    lk = lks[0] if lks else next((k for k, L in die.links.items() if nb and nb in L['src_bits']), None)
    if lk is None:
        raise SystemExit('--idle-run: u_seqhost.t_host alive bit has no lane in this build')
    L = die.links[lk]
    port = cut.out_by_net.get(L['out_net'])
    if port is None:
        raise SystemExit(f'--idle-run: the cut does not observe {L["out_net"]} (t_host lane {lk})')
    bit = L['src_bits'].index(nb) - port.get('lo', 0)
    tr = Path(idle_run) / 'trace.txt'
    for line in tr.read_text().split('\n'):
        f = line.split()
        if len(f) == 3 and int(f[1]) == port['index'] and (int(f[2], 16) >> bit) & 1:
            return dict(lane=lk, age=L['age'], alive_landed=int(f[0]), live=int(f[0]) - L['age'] - 1, trace=str(tr))
    raise SystemExit(f'--idle-run: t_host alive never seen on {port["port"]} in {tr}')


def calendar_start_phase(hs):
    """start_phase pw_d[8:7] of the calendar header (CSR 0x10 word with pw_d[27:26] == 3, begin form pw_d[25] == 0)."""
    for w in hs:
        d = w >> 1
        if w & 1 and (w >> 513) & 3 == 0 and d & 0xFF == 0x10:
            p = (d >> 32) & ((1 << 28) - 1)
            if p >> 26 == 3 and not (p >> 25) & 1:
                return (p >> 7) & 3
    return None


def host_boot_words(a, die, prog, S, words, cut=None):
    """--host-boot B: the compiled host boot stream (prog/host_boot.memh, 515-b host words, the dsdv_seq_host L0
    format) delivered on u_seqhost.f_host one word every 5th edge from bench cycle B (tb_dv_prog_seqhost's host slots),
    the lane-live flags f_lf = 4'b0101 held from cycle 0, and ONE job start on f_ks at bench cycle --ks (word
    --ks-word, default the seqhost bench's {v, user 37, tok 1000, pos 5000}).  The calendar accepts the start only on its
    start phase (ot_dsdv_fixed_issue), a reset-tree artefact of the cut: derive --ks from the actual reset/phase
    contract. The default is a diagnostic estimate, not a production launch. Layer cycle 0 = KS + 5: KS is the f_ks LANDED edge (the
    lane's last flop), u_seqhost's pin flop captures it one edge later (t = KS + 1), and the compiled V command leaves vo
    at t + issue + 11 = issue + 7 in layer cycles (dsdv_seq_host header, check_seqhost.py).  TOK-S81-GAPS/CTL 10-19,
    measured on G8 cut_3S_ctl (ks 2547): vo_n of row 8 (issue 1141) at 3700 = KS + 12 + issue; SVCJ on jw_E / jw_W one
    edge after a KS + 4 anchor."""
    hs = [int(x, 16) for x in (prog / 'prog/host_boot.memh').read_text().split()]
    live = seqhost_live(die, cut, a.idle_run) if getattr(a, 'idle_run', None) else None
    if live is not None:
        # TOKd-S81 10-23 (cap14 c14fx cut_3S_ctl, job15 CTL monitor): u_seqhost's own rn (live 99) is NOT the binding
        # edge.  The forward host lane's landing (ld_hf_7N_l*, on the receiving frame's landing reset, released later
        # since the chained-frame calendar fix v2) dropped every word landing before ~139 while t_host alive landed at
        # 138: the 0x11 length + calendar header were lost -> walk_issue code 4, no job, no V CTL.  The boot stream
        # therefore starts after BOTH edges: seqhost live + 8 and the landed t_host alive edge + 8.
        floor = max(live['live'] + 8, live['alive_landed'] + 8)
        if a.host_boot is None:
            a.host_boot = floor
        if a.host_boot < live['live'] + 2:
            raise SystemExit(f'--host-boot {a.host_boot} lands before u_seqhost leaves reset (live at {live["live"]}, '
                             f'idle run {a.idle_run}): the boot header would be dropped; use >= {live["live"] + 2}')
        if a.host_boot < live['alive_landed'] + 4:
            raise SystemExit(f'--host-boot {a.host_boot} lands before the host lane landing is live (t_host alive '
                             f'landed {live["alive_landed"]}): the boot header would be dropped; use >= {floor}')
    ks = a.ks if a.ks is not None else a.host_boot + 5 * len(hs) + 64
    # walk_issue accepts a start only when (phase_q + 1) == start_phase at its sampling edge (else code 5, no job);
    # phase_q = edges since the issuer's own relayed reset, mod 4, which the lane-age model does not pin (measured
    # 10-23: c14 accepts (KS - live) % 4 == 3, G9 == 0).  The default KS is therefore phase-blind: callers measure
    # it (run_entry_replay --ks-probe) and pass --ks.
    sp = calendar_start_phase(hs)
    a.t0 = ks + 5
    from ks_descriptor import encode as encode_ks, fixture_word
    meta_path = getattr(a, 'ks_fixture_meta', None)
    if S.get('input_sources') and not meta_path:
        raise ValueError('native entry programme requires --ks-fixture-meta and --ks-user; an opaque word is not fixture provenance')
    supplied = int(a.ks_word, 16) if a.ks_word is not None else None
    if meta_path:
        if getattr(a, 'ks_user', None) is None:
            raise ValueError('fixture descriptor requires explicit --ks-user from incoming HOST context')
        raw = Path(meta_path).read_bytes(); meta = json.loads(raw)
        meta_sha = hashlib.sha256(raw).hexdigest()
        if S.get('fixture_meta_sha256') and S['fixture_meta_sha256'] != meta_sha:
            raise ValueError('KS fixture metadata differs from native entry programme')
        if S.get('input_sources'):
            files = json.loads((Path(meta_path).parent/'files.json').read_text())
            if any(files.get(name, {}).get('sha256') != spec.get('sha256')
                   for name, spec in S['input_sources'].items()):
                raise ValueError('KS fixture input identity differs from native entry programme')
        ksw = fixture_word(meta, user=a.ks_user, supplied=supplied)
        provenance = dict(status='SOURCE_METADATA_ONLY_NO_RUNTIME_PRODUCER', fixture_meta_sha256=meta_sha,
                          user=a.ks_user, token=meta['token'], position=meta['position'],
                          runtime_provenance_qualified=False)
    else:
        # Preserve the existing opaque legal-bench wire value while naming its
        # fields according to the real RTL, rather than reversing tok/pos.
        ksw = supplied if supplied is not None else encode_ks(user=37, token=1000, position=5000)
        provenance = dict(status='DIAGNOSTIC_OPAQUE_OR_SYNTHETIC', runtime_provenance_qualified=False)
    end = int(max([w['cycle_land'] for w in words] + [0]) + a.t0 + 64)
    out = list(words)
    out += [word_at(die, 'u_seqhost', 'f_host', h, a.host_boot + 5 * i - a.t0, 'HOST', f'host_boot[{i}]')
            for i, h in enumerate(hs)]
    if getattr(a, 'ks_payload', 'hold') == 'pulse':      # legacy (10-21..10-23): the whole word a one-edge pulse
        out.append(word_at(die, 'u_seqhost', 'f_ks', ksw, ks - a.t0, 'KS', 'job start'))
    else:
        out += ks_source_words(die, ksw, ks - a.t0, end - a.t0)
    eng = ks_engram_words(die, ksw, ks - a.t0)
    if eng and getattr(a, 'ks_payload', 'hold') != 'pulse':
        # u_eng.f_ks carries the held payload between starts: a value change is a new word only with start [52] set
        S.setdefault('port_valid', []).append(dict(inst='u_eng', ports=['f_ks'], bit=KS_START_BIT))
    out += eng
    # Host CSR 0x14 emits a real G-unit configuration beat seven producer
    # edges after the host lane lands (one pin capture plus six internal edges). Include those bytes in strict boundary checks.
    for i, h in enumerate(hs):
        d = h >> 1
        if not h & 1 or h >> 513 or (d & 255) != 0x14:
            continue
        value = 1 | ((d >> 8) & 1023) << 1 | ((d >> 32) & ((1 << 256)-1)) << 11
        cycle = a.host_boot + 5 * i + 7 - a.t0
        event = dict(cycle=cycle, inst='u_seqhost', port='cw_v', ports=['cw_v','cw_a','cw_d'],
                     dir='out', kind='HOST_CW', tag=f'host_boot[{i}] CSR14', valid_bit=0,
                     words=[[cycle, f'{value:x}', f'{(1 << 267)-1:x}']])
        out += event_words(event, die)
        S.setdefault('port_valid', []).append(dict(inst='u_seqhost', ports=['cw_v','cw_a','cw_d'], bit=0))
    lf_age = max(die.links[die.by_out[n]]['age'] for n, _ in die.port_bits('u_seqhost', 'f_lf') if n in die.by_out)
    c0 = math.ceil(lf_age - 1)                        # the first landed cycle the producer can reach from bench 0
    out += [word_at(die, 'u_seqhost', 'f_lf', 0b0101, c - a.t0, 'LF', 'lane live', hold=c0 - a.t0)
            for c in range(c0, end)]
    return out, dict(boot_start=a.host_boot, seqhost_live=live, words=len(hs), last_word=a.host_boot + 5 * (len(hs) - 1), ks=ks,
                     start_phase=sp, ks_explicit=a.ks is not None,
                     ks_word=f'{ksw:x}', ks_provenance=provenance, t0=a.t0, f_lf=f'0101 held from landed bench cycle {c0}',
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
    if f[0] in ('shift-kind', 'expect-shift') and len(f) == 3:
        return dict(kind=f[0], ev=f[1], n=int(f[2]))
    raise SystemExit(f'bad --mutant {s!r}: shift:<link>:<n> | corrupt:<link>[:<bit>] | shift-kind:<KIND>:<n> | '
                     f'expect-shift:<KIND>:<n>')


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
    xrt_proof = check_run_source(rp.get('timing_contract'), a.run,
                                 a.xrt_runtime_proof or os.environ.get('OT_S81_XRT_RUNTIME_PROOF'))
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
        # a lane of a bundle with a valid flag: a value change is an extra word only while the flag is set
        vr = b.get('valid_ref')
        if vr:
            vch = tr.get(cut.ports[vr['port']]['index'], [])
            live = lambda c: (value_at(vch, c) >> vr['bit']) & 1
        else:
            live = lambda c: True
        extra = [c for c, v in ch if v and live(c) and float(c) not in exp]
        strict = b.get('strict', not rp['partial'])
        n_bad = len(miss) + (len(extra) if strict else 0)
        bad += n_bad
        res.append(dict(port=b['port'], lane=b['lane'], expected=len(exp), missed=sorted(miss)[:20],
                        unscheduled=extra[:20], n_unscheduled=len(extra), strict=strict, ok=n_bad == 0))
    sim_pass = 'TB_DV_SLICE PASS' in status
    doc = dict(schema=SCHEMA + '.check', replay=str(a.replay), run=str(a.run), verdict_kind=rp['verdict_kind'],
               sim_pass=sim_pass, trace_mismatches=bad, partial=rp['partial'], xrt_runtime_proof=xrt_proof,
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
    g.add_argument('--bk-drain-sink', default=None, help='UID[,UID] hex: build has BK_DRAIN_SINK=1; addressed BK drain CTL '
                   'beats are consumed at the BK stop (no slice/line events). Candidate profile only')
    g.add_argument('--lane-age', action='store_true')
    g.add_argument('--allow-stale', action='store_true')
    g.add_argument('--equalize', action='append', default=[], help='LANE_PREFIX: drive each lane of the bundle at its '
                   'own age (models a die-gap fix, e.g. G8 residual hf_7N); the verdict becomes DIAGNOSTIC')
    g.add_argument('--host-boot', type=int, default=None, help='bench cycle of the first host boot word (cuts with u_seqhost)')
    g.add_argument('--idle-run', default=None, help='idle run dir of this cut build (trace.txt): derives u_seqhost reset '
                   'release; --host-boot defaults to it + 8 and is refused below it + 2')
    g.add_argument('--ks', type=int, default=None)
    g.add_argument('--ks-payload', choices=('hold', 'pulse'), default='hold',
                   help='f_ks producer model: hold (default, S81-P10 10-24: the u_s_7N host RX holds the payload fk_d and '
                        'pulses start fk_s) or pulse (legacy: the whole word for one edge; a torn bundle then misses)')
    g.add_argument('--ks-word', default=None, help='opaque diagnostic word, or exact fixture descriptor checked against --ks-fixture-meta/--ks-user')
    g.add_argument('--ks-fixture-meta', help='fixture meta.json; native entry replay requires this descriptor provenance')
    g.add_argument('--ks-user', type=int, help='explicit incoming HOST user; not inferred from fixture rank')
    g = sp.add_parser('check')
    g.add_argument('--replay', required=True)
    g.add_argument('--run', required=True)
    g.add_argument('--out')
    g.add_argument('--xrt-runtime-proof', default=None,
                   help="selected-XRT HOST/control runtime proof: 'self-entry' (only run_entry_replay.py: this run is "
                        "the proof) or a PASS_CUT_COMPONENT entry_replay.json (env OT_S81_XRT_RUNTIME_PROOF)")
    g = sp.add_parser('compose')
    g.add_argument('--cut', action='append', required=True, help='NAME=REPLAY_DIR:RUN_DIR')
    g.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    return dict(ages=ages, gen=gen, check=check, compose=compose)[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
