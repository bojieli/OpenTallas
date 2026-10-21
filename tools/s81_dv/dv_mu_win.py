#!/usr/bin/env python3
"""MU-DIE-S81/MUWIN (10-19): compiler-owned multi-user window / replay tables of the S81 MU die.

Gap (MU-DIE-S81/MUREPLAY 9fbc143b3): dv_layer_compile --mu / --mu-ctx emitted no dsdv_mu_hwin (mu2) / dsdv_mu_hslot
NEV > 0 (mu1) event rows, so the end-slice MU lanes (mu_c TX tag windows, mu_rc landing replays) stayed idle in every
replay and --mu-win runs were diagnostic.  This module is the compiler side (dv_layer_compile --mu-cal ... --mu-win):

  prog/mu_win.json   per layer, per end slice: event rows {kind tx | replay, ep, inst, lane, D} (D = edges after the
                     f_ks capture edge, the hwin / hslot contract: the event's output register takes its value on edge
                     capture + 1 + D), the user-0 landed edge at the slice pin (layer cycles), the per-slot attributes
                     {land, ab} of this die's copy (local slot order), the slot gap table, RL, and the static checks
  prog/mu_cfg.cfg    the boot config the die receives over the host lane, "IDX WORD" hex a line (the format of
                     rtl/dsrom_sys/s81_dv/unit/test/tb_dsdv_seq_host_mu.sv): CSR 0x15 = f_mc (sel 0 slot gaps, sel 1 RL),
                     CSR 0x16 = f_mw (hwin window rows: select / D / per-slot attributes) -- GEN mu2 (dsdv_seq_host_mux
                     = gap-table hslot + dsdv_mu_hwin, MU-S81-2 ac336f805 + 5dd45e769)
  prog/mu_cfg_mu1.cfg the same rows in the GEN mu1 format (dsdv_mu_hslot NEV 8, 908a67c18: window words on CSR 0x15
                     sel 1 d[23] = 1, ONE uniform slot period) -- only where the die's starts are on one uniform grid
  prog/mu_boot.memh  the CSR words as 515-b host words (appended after host_boot.memh, before the first start)

Event model (static, fixed cycles; the shift lemma: user k = user 0's schedule shifted by its calendar start):
  * the layer's stage h hand-offs are its substage_hop<i> ops (priced schedule).  Every end slice (s_7N, s_7S, s_0N,
    s_0S = hwin ep 0..3) sends its h share (NB 80 beats) on hop i and receives the peer's share.
  * TX window (kind 0) on ep: the window command lands at the lep mu_c pin LEAD_TX edges before the hop's first h
    beat can reach ro (ceil(hop.start)); the lep needs >= 2 (ot_s81sl_lep_core MU header).  Attributes {land, ab} of
    the slot: land = 1 for every user but the latency user (slot kind 'latency' is cut through), ab = copy B.
  * landing replay (kind 1) on ep: rc lands at the pin REPLAY_LAT edges before the user's h must be on ri
    (ceil(hop.end) - NB: the cut-through stream's first beat); dsdv_mu_land rc pin -> first rv 4 edges + lep replay pin
    flop -> ri 2 edges.  Fires only on slots with land = 1 (hwin eat[1]).
  * layer cycle c (schedule) = capture edge + c - layer_issue0 + 4 (dsdv_seq_host: f_ks capture t -> issuer t + 3 ->
    calendar age a leaves at t + 4 + a; job rows rebased by layer_issue0); a lane of age A lands a register value
    taken on edge e at e + A - 1 (dv_cut_replay word convention).  So D = (c_pin - layer_issue0 + 4) - A.
  * RL = job-0 KIT age + 7 (f_ks capture -> t_kd pin, the SEQHOST_MU_GATE contract); the gap table = this die's
    copy's starts in local order, last gap = period - span.
Status PRICED: the hop ops are not lowered yet (dv_layer_compile lowering GAP 'substage_hop': no h beats reach the lep
ro in any programme), so D is anchored on the priced hop op, not on a lowered beat edge.  The seq_host side (hwin
fires exactly ts + D with the slot's attributes) is exact and proven by the compiled-config bench
(rtl/dsrom_sys/s81_dv/unit/test/run_mu_win_prog_bench.sh); the slice side needs the hop lowering (see README).

  dv_mu_win.py cases --prog P --out DIR [--users 0,1,2] [--passes 2]   bench case files (+ mutants)
  dv_mu_win.py check --prog P --log RUN.log --mu CASE.mu [--fmt mu2]     tb_dsdv_seq_host_mu log vs the compiled table
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SCHEMA = 'opentallas.s81_dv.mu_win.v1'
EPS = (('7n', 'u_s_7N'), ('7s', 'u_s_7S'), ('0n', 'u_s_0N'), ('0s', 'u_s_0S'))   # hwin / hslot ep order (mux wiring)
NB = 80             # beats per end-slice h share (ot_s81sl_lep_mu NB, dsdv_mu_land NB)
LEAD_TX = 4         # window command at the lep pin -> first h beat at ro (lep needs >= 2)
REPLAY_LAT = 6      # rc at the lep pin -> first replayed beat on ri (dsdv_mu_land 4 + lep pin flop / ri 2)
NEV_HW = 8          # dsdv_seq_host_mux: dsdv_mu_hwin NEV 8 (and hslot NEV 8 on mu1)
NSLOT_HW = 47
CAP_TO_LAYER = 4    # layer cycle 0 = f_ks capture edge + 4 (dsdv_seq_host)


def mu_lanes(die):
    """ep -> {inst, lane, age} from the die build (compiler Die): the lane whose dst is (inst, mu_c)"""
    out = []
    for ep, (nm, inst) in enumerate(EPS):
        lk = next((k for k, L in die.links.items() if (inst, 'mu_c') in [tuple(x) for x in L['dst']]), None)
        if lk is None:
            raise SystemExit(f'mu_win: no lane drives {inst}.mu_c in this die build (not an MU die?)')
        L = die.links[lk]
        if (inst, 'mu_rc') not in [tuple(x) for x in L['dst']]:
            raise SystemExit(f'mu_win: {inst}.mu_rc is not on lane {lk} with mu_c')
        out.append(dict(ep=ep, name=nm, inst=inst, lane=lk, age=int(L['age_edges'])))
    return out


def gap_table(rows, period):
    st = [r['start'] for r in rows]
    gaps = [b - a for a, b in zip(st, st[1:])] + [period - (st[-1] - st[0])]
    return gaps


def build(sched, cal, slots, die, copy=None, nev=NEV_HW, nslot=NSLOT_HW):
    """the compiled MU window table of one layer programme on one die copy"""
    copy = copy or 'A'
    rows = sorted([r for r in slots['rows'] if r['copy'] == copy], key=lambda r: r['local'])
    if not rows:
        raise SystemExit(f'mu_win: no slot of copy {copy}')
    if [r['local'] for r in rows] != list(range(len(rows))):
        raise SystemExit(f'mu_win: copy {copy} local slots are not 0..{len(rows) - 1}')
    job0 = cal['job'][0] if cal.get('job') else dict(layer_issue0=0, rows=cal['rows'])
    t0 = job0.get('layer_issue0', 0)
    kit = next(r['issue'] for r in job0['rows'] if r.get('what') == 'KIT')
    RL = kit + 7
    period = slots['period']
    gaps = gap_table(rows, period)
    nw = len(gaps)
    lanes = mu_lanes(die)
    hops = sorted([o for o in sched['ops'] if re.fullmatch(r'substage_hop\d+', o['op'])], key=lambda o: o['start'])
    ev, checks = [], []
    # MU-DIE-S81/HOP: the hop is lowered (lower_vpx.lower_hop): each end slice's NB XB beats are 'out' events with
    # hop = op name at fixed ro edges -> the TX window anchors on the slice's FIRST lowered beat and closes after its
    # NB-th (the lep counts NB beats on its ro pin flop); without lowered beats the priced op start stays the anchor
    beats = {}
    for x in sched.get('events', []):
        if x.get('dir') == 'out' and x.get('hop') and x.get('kind') in ('XB', 'XQ'):
            beats.setdefault((x['hop'], x['inst']), []).append(x['cycle'])
    lowered = all((h['op'], L['inst']) in beats for h in hops for L in lanes) and bool(hops)
    for h in hops:
        hrx = math.ceil(h['end']) - NB
        for kind, lead in (('tx', LEAD_TX), ('replay', REPLAY_LAT)):
            for L in lanes:
                bc = sorted(beats.get((h['op'], L['inst']), []))
                if kind == 'tx' and bc:
                    anchor, what = bc[0], f'first of the {len(bc)} lowered XB beats on the lep ro (lower_vpx hop)'
                elif kind == 'tx':
                    anchor, what = math.ceil(h['start']), 'ceil(start): first h beat may reach ro (PRICED: not lowered)'
                else:
                    anchor, what = hrx, 'ceil(end) - NB: first h beat on ri (cut-through; receive side priced)'
                pin = anchor - lead                       # layer cycle the command lands at the slice pin (user 0)
                D = pin - t0 + CAP_TO_LAYER - L['age']
                ev.append(dict(i=len(ev), kind=kind, k=0 if kind == 'tx' else 1, ep=L['ep'], inst=L['inst'],
                               port='mu_c' if kind == 'tx' else 'mu_rc', lane=L['lane'], age=L['age'], D=D,
                               pin_layer=pin, out_layer=pin - L['age'] + 1, hop=h['op'],
                               **(dict(beats=len(bc), beat_first=bc[0], beat_last=bc[-1]) if kind == 'tx' and bc else {}),
                               anchor=dict(op=h['op'], edge=anchor, what=what)))
    att = [dict(slot=r['local'], user=r['user'], kind=r['kind'], land=int(r['kind'] != 'latency'),
                ab=int(r['copy'] == 'B'), start=r['start']) for r in rows]
    # ---- static checks (the hwin / hslot rules + the port-alone lemma)
    def chk(name, ok, why):
        checks.append(dict(check=name, verdict='PASS' if ok else 'FAIL', why=why))
    chk('nev', len(ev) <= nev, f'{len(ev)} event rows ({len(hops)} hops x 4 ends x 2), master NEV {nev}')
    chk('nslot', nw <= nslot, f'{nw} slots of copy {copy}, master NSLOT {nslot}')
    chk('gaps', all(g >= nw and g < 1 << 24 for g in gaps), f'gaps {sorted(set(gaps))} >= nw {nw}')
    chk('rl', nw < RL < 1 << 23, f'RL {RL} (job-0 KIT age {kit} + 7) > nw {nw}')
    bad = [e for e in ev if not (nw + 2 <= e['D'] <= RL - 2) or e['D'] >= 1 << 21]
    chk('d_range', not bad, f'every D in [nw + 2, RL - 2] = [{nw + 2}, {RL - 2}]'
        + (f'; out of range: {[(e["i"], e["kind"], e["ep"], e["D"]) for e in bad]}' if bad else ''))
    # two events of one start on one output port in one edge (hwin col_w), across all users of a period
    occ = {}
    coll = []
    for e in ev:
        for a in att:
            if e['kind'] == 'replay' and not a['land']:
                continue
            key = (e['port'], e['ep'], (a['start'] - rows[0]['start'] + e['out_layer']) % period)
            if key in occ:
                coll.append((occ[key], (e['i'], a['user'])))
            occ[key] = (e['i'], a['user'])
    chk('port_edge', not coll, f'one command per end-slice port per edge over the period ({len(occ)} commands)'
        + (f'; collisions {coll[:4]}' if coll else ''))
    # port alone: no other scheduled outbound lep traffic (RD / ring beats at the end slice's outward port) of ANY user
    # inside a TX window [pin, ceil(hop.end)] of any user (the lep faults a non-h beat inside a window)
    win = [(e, e['pin_layer'], e['beat_last'] if 'beat_last' in e else
            math.ceil(next(h['end'] for h in hops if h['op'] == e['hop']))) for e in ev if e['kind'] == 'tx']
    outs = [x for x in sched.get('events', []) if x.get('dir') == 'out' and x.get('inst') in {i for _, i in EPS}
            and 'lep' in str(x.get('port', ''))]
    hit = []
    for e, lo, hi in win:
        for x in outs:
            if x['inst'] != e['inst']:
                continue
            for a in att:
                c = (x['cycle'] + a['start'] - rows[0]['start']) % period
                for b in att:
                    if a is b and x.get('hop') == e['hop']:
                        continue                          # the window's own h beats
                    w0 = (lo + b['start'] - rows[0]['start']) % period
                    if 0 <= (c - w0) % period <= hi - lo:
                        hit.append((e['i'], b['user'], x['kind'], x['tag'], a['user']))
    chk('port_alone', not hit, f'{len(outs)} scheduled outbound lep events of {len(att)} users vs {len(win)} TX windows'
        + (f'; inside a window: {hit[:4]}' if hit else ''))
    chk('hops', bool(hops), f'{len(hops)} substage hop ops in the programme' + ('' if hops else ': no MU event'))
    # MU-DIE-S81/HOP: a lowered hop puts exactly NB beats on each end slice's ro, after its window command
    nbad = [(e['i'], e['inst'], e.get('beats')) for e in ev if e['kind'] == 'tx' and lowered and
            (e.get('beats') != NB or e['beat_first'] - e['pin_layer'] < 2)]
    chk('hop_beats', lowered and not nbad, (f'every TX window covers exactly NB {NB} lowered XB beats, command >= 2 '
        f'edges before the first' if lowered else 'hop not lowered (no XB hop beats in the schedule events)')
        + (f'; bad {nbad}' if nbad else ''))
    ok = all(c['verdict'] == 'PASS' for c in checks)
    # a uniform grid (mu1 hslot: ONE slot period) only when every gap is equal
    uni = len(set(gaps)) == 1
    return dict(schema=SCHEMA, layer=slots['layer'], group=slots['group'], copy=copy, mode=slots['mode'],
                period=period, nw=nw, gaps=gaps, RL=RL, kit_age=kit, layer_issue0=t0, NB=NB, LEAD_TX=LEAD_TX,
                REPLAY_LAT=REPLAY_LAT, cap_to_layer=CAP_TO_LAYER, lanes=lanes, hops=[dict(op=h['op'], start=h['start'],
                end=h['end']) for h in hops], events=ev, slots=att, checks=checks,
                verdict='PASS' if ok else 'FAIL', mu1_uniform=uni,
                lowered=lowered,
                status=('TX LOWERED: window D anchored on the lowered XB hop beats (lower_vpx hop); replay D on the '
                        'priced hop end (receive side elastic, off-die)') if lowered else
                       'PRICED: D anchored on the priced substage_hop ops (hop not lowered)')


# ------------------------------------------------------------------------------------------------ boot config words
def w15(sel, d):
    return 0x15, (1 << 25) | (sel << 24) | d


def w16(sub, d):
    return 0x16, (1 << 25) | (sub << 21) | d


def cfg_words(T, fmt='mu2', mutant=None):
    """the host CSR stream: gap table + RL on 0x15, window rows on 0x16 (mu2) / 0x15 sel 1 d[23] (mu1).
    mutant: ('shift', event i, n) moves one event's D by n edges; ('drop', event i) leaves one event row unloaded"""
    mut = mutant or ()
    out = []
    if fmt == 'mu2':
        out += [w15(0, g) for g in T['gaps']]
    else:
        if not T['mu1_uniform']:
            raise SystemExit('mu1 format: the copy\'s starts are not on one uniform period (the record calendar needs '
                             'the gap-table hslot of GEN mu2)')
        out.append(w15(0, T['gaps'][0]))
    out.append(w15(1, T['RL']))
    win = (lambda sub, d: w16(sub, d)) if fmt == 'mu2' else (lambda sub, d: w15(1, (1 << 23) | (sub << 21) | d))
    for e in T['events']:
        if mut[:1] == ('drop',) and mut[1] == e['i']:
            continue
        D = e['D'] + (mut[2] if mut[:1] == ('shift',) and mut[1] == e['i'] else 0)
        out.append(win(0, e['i'] | e['k'] << 8 | e['ep'] << 9))
        out.append(win(1, D))
        for s in T['slots']:
            out.append(win(2, s['slot'] | s['ab'] << 10 | s['land'] << 11))
    return out


def host_words(cfg):
    """CSR words as 515-b host words {h_cls 0, h_d[57:32] word, h_d[7:0] index, h_v} (dsdv_seq_host_mux decode)"""
    return [(w << 33) | (i << 1) | 1 for i, w in cfg]


def write_prog(out, T):
    out = Path(out)
    (out / 'prog/mu_win.json').write_text(json.dumps(T, indent=1) + '\n')
    cfg = cfg_words(T, 'mu2')
    (out / 'prog/mu_cfg.cfg').write_text(''.join(f'{i:02x} {w:07x}\n' for i, w in cfg))
    (out / 'prog/mu_boot.memh').write_text(''.join(f'{x:0129x}\n' for x in host_words(cfg)))
    files = ['prog/mu_win.json', 'prog/mu_cfg.cfg', 'prog/mu_boot.memh']
    if T['mu1_uniform']:
        c1 = cfg_words(T, 'mu1')
        (out / 'prog/mu_cfg_mu1.cfg').write_text(''.join(f'{i:02x} {w:07x}\n' for i, w in c1))
        files.append('prog/mu_cfg_mu1.cfg')
    return files


# ------------------------------------------------------------------------------------------------ expected traces
def expected(T, starts):
    """starts: [(t_ks capture edge, user, pos, local slot)] -> the hwin output lines tb_dsdv_seq_host_mu prints:
    'MC<ep>' / 'MR<ep>' at log cycle t_ks + 1 + D (the output register takes the value on posedge t_ks + 1 + D and the
    tb displays it on the next posedge with the pre-increment cycle label = t_ks + 1 + D), payload as the RTL builds it"""
    out = []
    att = {s['slot']: s for s in T['slots']}
    for t, user, pos, slot in starts:
        a = att[slot]
        if a['user'] != user:
            raise SystemExit(f'start user {user} on local slot {slot} whose user is {a["user"]}')
        for e in T['events']:
            c = t + 1 + e['D']
            if e['kind'] == 'tx':
                out.append((f'MC{e["ep"]}', c, (pos & 0x1FFFFF) << 13 | user << 3 | a['land'] << 2 | a['ab'] << 1 | 1))
            elif a['land']:
                out.append((f'MR{e["ep"]}', c, user << 1 | 1))
    return sorted(out, key=lambda x: (x[1], x[0]))


def cases(a):
    T = json.loads((Path(a.prog) / 'prog/mu_win.json').read_text())
    d = Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    users = [int(x) for x in a.users.split(',')] if a.users else [s['user'] for s in T['slots']]
    by_u = {s['user']: s for s in T['slots']}
    s0 = T['slots'][0]['start']
    mu = []
    for p in range(a.passes):
        for u in users:
            s = by_u[u]
            mu.append((p * T['period'] + s['start'] - s0, u, 3 + 100 * u + p, 1000 + 7 * u + p, s['slot']))
    mu.sort()
    (d / 'mu.mu').write_text(''.join(f'{x[0]} {x[1]} {x[2]} {x[3]} {x[4]}\n' for x in mu))
    tx = next(e for e in T['events'] if e['kind'] == 'tx')
    rp = next(e for e in T['events'] if e['kind'] == 'replay')
    info = {}
    for name, m in (('base', None), ('mut_winshift', ('shift', tx['i'], 1)), ('mut_replaydrop', ('drop', rp['i']))):
        cfg = cfg_words(T, a.fmt, m)
        (d / f'{name}.cfg').write_text(''.join(f'{i:02x} {w:07x}\n' for i, w in cfg))
        info[name] = dict(words=len(cfg), mutant=m)
    info['starts'] = len(mu)
    info['users'] = users
    (d / 'cases.json').write_text(json.dumps(info, indent=1) + '\n')
    print(json.dumps(info))


EVL = re.compile(r'^PROG (MC\d|MR\d) (\d+) ([0-9a-fA-F]+)\s*$', re.M)


def check(a):
    T = json.loads((Path(a.prog) / 'prog/mu_win.json').read_text())
    t = Path(a.log).read_text()
    ks = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in
          re.finditer(r'^PROG KS (\d+) user (\d+) pos (\d+)', t, re.M)]
    mu = [l.split() for l in Path(a.mu).read_text().split('\n') if l.strip()]
    if len(ks) != len(mu):
        return report(a, False, [f'{len(ks)} starts in the log, {len(mu)} in {a.mu}'], 0, 0)
    starts = [(c, u, p, int(m[4])) for (c, u, p), m in zip(ks, mu)]
    exp = expected(T, starts)
    got = [(m.group(1), int(m.group(2)), int(m.group(3), 16)) for m in EVL.finditer(t)]
    last = max(c for c, *_ in starts) + max(e['D'] for e in T['events']) + 2
    got = [g for g in got if g[1] <= last]
    errs = []
    es, gs = set(exp), set(got)
    for x in sorted(es - gs, key=lambda x: x[1])[:10]:
        errs.append(f'missing {x[0]} at {x[1]} value {x[2]:x}')
    for x in sorted(gs - es, key=lambda x: x[1])[:10]:
        errs.append(f'unexpected {x[0]} at {x[1]} value {x[2]:x}')
    mf = re.search(r'^PROG TMF ([01]{4})', t, re.M)
    if 'PROG END' not in t:
        errs.append('run incomplete (no PROG END)')
    if mf is None or mf.group(1) != '0000':
        errs.append(f't_mf {mf.group(1) if mf else "?"} (want 0000)')
    note = None
    fl = [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r'^PROG FAULT (\d+) code (\d+)', t, re.M)]
    if fl:
        # the bench has no svc_rs model: the compiled svc job's done (engine 4 row) never returns on s_jd, so the issuer
        # raises run fault 8 (done row not matched) once, svc done age + 6 edges after the first start's capture.
        # ot_dsdv_fixed_issue: run_fault is status only (no issue / KIT / END edge depends on it), so the windows and
        # the KIT returns are unaffected.  Any other fault (code, edge) is an error.
        cal = json.loads((Path(a.prog) / 'prog/calendar.json').read_text())
        svc = [r['done'] for r in (cal['job'][0]['rows'] if cal.get('job') else cal['rows']) if r['engine'] == 4
               and r['done']]
        ok8 = len(fl) == 1 and fl[0][1] == 8 and svc and fl[0][0] == starts[0][0] + min(svc) + 6
        if ok8:
            note = f'issuer fault code 8 at {fl[0][0]} = first start {starts[0][0]} + svc done age {min(svc)} + 6: ' \
                   f'no svc_rs responder in this bench (status only)'
        else:
            errs.append(f'issuer fault {fl} (svc done ages {svc})')
    return report(a, not errs, errs, len(exp), len(es & gs), note)


def report(a, ok, errs, nexp, nmatch, note=None):
    r = dict(verdict='PASS' if ok else 'FAIL', expected=nexp, matched=nmatch, errors=errs, log=str(a.log), note=note)
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print(f'MUWIN_PROG {"PASS" if ok else "FAIL"} {nmatch}/{nexp} compiled events on their edge' +
          ('' if ok else '; ' + '; '.join(errs[:6])) + (f' [{note}]' if note else ''))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('cases')
    c.add_argument('--prog', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--users', default=None)
    c.add_argument('--passes', type=int, default=2)
    c.add_argument('--fmt', default='mu2', choices=('mu2', 'mu1'))
    k = sp.add_parser('check')
    k.add_argument('--prog', required=True)
    k.add_argument('--log', required=True)
    k.add_argument('--mu', required=True)
    k.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    return cases(a) if a.cmd == 'cases' else check(a)


if __name__ == '__main__':
    raise SystemExit(main() or 0)
