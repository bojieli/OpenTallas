#!/usr/bin/env python3
"""S81-WQBP (10-20): consumer retirement + deadline check of the attn.wq_b row-batch (P126) pipeline on the real fullsix
RTL trace (TOK2 L16/E24 exe 63eccd91, Verilator 5.050), driven by the DIE COMPILER's calendar (xs_wqb_die.wqb_calendar
via retained_xs_program; images identical to the compiler emission) plus the 15 source-derived CAP descriptors
(codex/token-cap-contract-1020 compile_fullsix_cap_program.py).  Observational checks on monitors of the real RTL; no
check here can reschedule anything (static schedule rule).  Four rule groups, every one must PASS:

 R1 ELEMENT RETIRE (per tag, Q_LIFETIME of the 72 traced q elements; the 54 that capture are the active ones): each element's two configuration slots; a LIFE = gcnt of a
    slot > 0 (from the GO that loads it to the edge it returns to 0 = the retire).  Every element: lives == GOs (one per
    phase), each life retires before the trace ends and before the consumer deadline, consecutive phases alternate slot
    tag (double buffer, compiler tags 0/2), a slot is re-armed only after its previous life retired, fault == 0 on every
    observed edge.
 R2 CAP DESCRIPTOR RETIRE (per row domain, CAP_LIFETIME / ACTUAL_CAP_CFG): one CFG per phase, each descriptor window
    (open 0->1 .. 1->0) opens after its CFG and retires before the next CFG; windows disjoint; rbase domains rotate; all
    sticky causes / F5..F11 zero on every edge.
 R3 CONSUMER READ AT THE COMPILED DEADLINE: deadline D = first element capture + the compiler's predicted span
    ((n - 1) P + 223, xs_wqb_die) + the priced CAP/VP/wire tail (195) = the edge at which the die schedule starts the
    consumers of attn.wq_b (attn.q_rope / attention q reads; the composer charges exactly this node).  The VP SRAM state is
    rebuilt from every real VP commit (VP_ACTUAL_COMMIT, write port of the VP leaves) with t <= D and read at D: all 512
    head dims must equal the released-fixture golden (BF16 of the golden row, wqbp_golden_check); no collision; no
    later write to any consumed address until the end of the trace (the value is retained for the consumer window).
 R4 STATIC == RUNTIME: GO count == compiler phases, GO spacing == compiler period on every phase, CFG count == phases.

usage: check_wqbp_consumer.py --root SRC --fixture FIX --run RUN_DIR --golden-checker wqbp_golden_check.py
                              --calendar compiler_calendar.json --out OUT.json [--deadline-shift N] [--tail 195]
--deadline-shift N moves D by N edges (a negative N below the slack must FAIL R3: the mutant of the deadline check).
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

TAIL = 195            # priced CAP EDLY 24 + VP hand-off 28 + die wire 143 (the composer's attn.wq_b tail)
KV = re.compile(r'(\w+)=(\S+)')


def lines(run):
    p = Path(run) / 'diagnostic.log'
    if p.exists():
        with open(p, errors='replace') as f:
            yield from f
    else:
        with gzip.open(Path(run) / 'diagnostic.log.gz', 'rt', errors='replace') as f:
            yield from f


def parse(run):
    """one pass: Q_LIFETIME slot lives, CAP windows, CFG / GO / capture edges, VP commits"""
    q = {}                      # id -> state
    lives = defaultdict(list)   # id -> [dict(slot, tag, start, retire)]
    qfault = []
    cap_open, cap_win, cap_bad, cap_last = 0, [], [], None
    cfg, gos, caps, commits, collisions, terminal = [], [], [], [], [], []
    tmax = 0
    cap_ids = set()
    for ln in lines(run):
        k = ln.split(' ', 1)[0]
        if k not in ('Q_LIFETIME', 'CAP_LIFETIME', 'ACTUAL_CAP_CFG', 'ACTUAL_GO', 'ACTUAL_TAG_CAPTURE',
                     'VP_ACTUAL_COMMIT', 'FULLSIX_PREPARATORY_TRACE_END'):
            continue
        if k == 'FULLSIX_PREPARATORY_TRACE_END':
            terminal.append(ln.strip())
            continue
        d = dict(KV.findall(ln))
        t = int(d['t'])
        if t >= 1 << 63:
            t = -1                     # pre-reset monitor edge
        tmax = max(tmax, t)
        if k == 'Q_LIFETIME':
            i = d['id']
            g = [int(x) for x in d['gcnt'].split(',')]
            tg = [int(x) for x in d['otags'].split(',')]
            s = q.setdefault(i, dict(g=[0, 0], open=[None, None]))
            for j in (0, 1):
                if s['g'][j] == 0 and g[j] > 0:
                    s['open'][j] = dict(slot=j, tag=tg[j], start=t, retire=None)
                    lives[i].append(s['open'][j])
                elif s['g'][j] > 0 and g[j] == 0 and s['open'][j] is not None:
                    s['open'][j]['retire'] = t
                    s['open'][j] = None
            s['g'] = g
            if d.get('fault', '0') != '0':
                qfault.append((i, t, d['fault']))
        elif k == 'CAP_LIFETIME':
            o = int(d['open'])
            if o and not cap_open:
                cap_win.append(dict(open=t, close=None, rbase=d['rbase'], rcnt=int(d['rcnt'])))
            elif cap_open and not o and cap_win:
                cap_win[-1]['close'] = t
            cap_open = o
            bad = {x: d[x] for x in ('f5', 'f6', 'f7', 'f8', 'f9', 'f11', 'causes') if int(d[x], 16) != 0}
            if bad:
                cap_bad.append((t, bad))
        elif k == 'ACTUAL_CAP_CFG':
            cfg.append(t)
        elif k == 'ACTUAL_GO':
            gos.append((t, int(d['epoch'])))
        elif k == 'ACTUAL_TAG_CAPTURE':
            if d.get('captured') == '1':
                caps.append(t)
                cap_ids.add(d['id'])
        elif k == 'VP_ACTUAL_COMMIT':
            if d['collision'] != '0':
                collisions.append(t)
            if int(d['cwv'], 2) == 0:
                continue                # not a CW (capture) commit: the x-source rows of the qnorm stage
            mask, data = int(d['mask'], 16), int(d['data'], 16)
            leaf, bank, row = int(d['leaf']), int(d['bank']), int(d['row'])
            for w in range(4):
                wm = (mask >> (32 * w)) & 0xffffffff
                if wm:
                    commits.append((t, leaf, (row << 3) + (bank << 2) + w, (data >> (32 * w)) & 0xffffffff, wm))
    return dict(lives=lives, qfault=qfault, cap_win=cap_win, cap_bad=cap_bad, cfg=cfg, gos=gos, caps=caps,
                commits=commits, collisions=collisions, terminal=terminal, tmax=tmax, cap_ids=cap_ids,
                traced=set(q))


def golden_vp(root, fixture, checker):
    sys.argv = [str(checker), str(root), '/dev/null', str(fixture)]
    spec = importlib.util.spec_from_file_location('wqbp_fixture_golden', checker)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _, gold, selfcheck = m.build_golden()
    exp = {}
    for dim in range(512):
        off = m.storage_offset(dim)
        exp[((off >> 6) % 5, 64 * ((off >> 6) // 5) + (off & 63))] = (dim, int(gold[dim]['bf16']))
    return exp, selfcheck


def check(tr, cal, exp, shift=0, tail=TAIL):
    n, P = cal['nphases'], cal['period']
    out, bad = {}, {}

    def need(name, ok, detail):
        out[name] = bool(ok)
        if not ok:
            bad[name] = detail
    # ---------------------------------------------------------------- R4 static == runtime
    gos = sorted(tr['gos'])
    sp = [b[0] - a[0] for a, b in zip(gos, gos[1:])]
    need('R4_go_count_eq_phases', len(gos) == n, (len(gos), n))
    need('R4_go_spacing_eq_period', bool(sp) and all(x == P for x in sp), sorted(set(sp)))
    need('R4_cfg_count_eq_phases', len(tr['cfg']) == n, (len(tr['cfg']), n))
    # ---------------------------------------------------------------- deadline
    first_cap = min(tr['caps']) if tr['caps'] else None
    D = None if first_cap is None else first_cap + cal['predicted_span'] + tail + shift
    # ---------------------------------------------------------------- R1 element retire
    lv = tr['lives']
    per = {}
    r1 = dict(elements=len(lv), traced=len(tr['traced']), lives_ne_gos=[], open_at_end=[], retire_after_deadline=[], no_alternation=[],
              rearm_before_retire=[])
    for i, L in sorted(lv.items()):
        L = sorted(L, key=lambda x: x['start'])
        if len(L) != len(gos):
            r1['lives_ne_gos'].append((i, len(L)))
        for a in L:
            if a['retire'] is None:
                r1['open_at_end'].append((i, a['start']))
            elif D is not None and a['retire'] > D:
                r1['retire_after_deadline'].append((i, a['retire']))
        if any((a['slot'], a['tag']) == (b['slot'], b['tag']) for a, b in zip(L, L[1:])):
            r1['no_alternation'].append(i)
        for j in (0, 1):
            S = [a for a in L if a['slot'] == j]
            if any(a['retire'] is None or a['retire'] > b['start'] for a, b in zip(S, S[1:])):
                r1['rearm_before_retire'].append((i, j))
        per[i] = [(a['slot'], a['tag'], a['start'], a['retire']) for a in L]
    last_retire = max((a['retire'] for L in lv.values() for a in L if a['retire'] is not None), default=None)
    r1['last_element_retire'] = last_retire
    # the sid6 placement uses 54 of the 72 traced q elements (3 per frame idle: no GO, no capture, no life)
    need('R1_lives_on_exactly_the_capturing_elements', set(lv) == tr['cap_ids'] and len(lv) > 0,
         dict(lives=len(lv), capturing=len(tr['cap_ids']), traced=len(tr['traced'])))
    need('R1_one_life_per_go', not r1['lives_ne_gos'], r1['lives_ne_gos'][:6])
    need('R1_every_life_retires', not r1['open_at_end'], r1['open_at_end'][:6])
    need('R1_retire_before_deadline', D is not None and not r1['retire_after_deadline'], r1['retire_after_deadline'][:6])
    need('R1_tag_alternates_per_phase', not r1['no_alternation'], r1['no_alternation'][:6])
    need('R1_slot_rearmed_only_after_retire', not r1['rearm_before_retire'], r1['rearm_before_retire'][:6])
    need('R1_element_fault_zero', not tr['qfault'], (len(tr['qfault']), tr['qfault'][:4]))
    # ---------------------------------------------------------------- R2 CAP descriptor retire
    W, C = tr['cap_win'], sorted(tr['cfg'])
    r2_bad = []
    for k, w in enumerate(W):
        c = max((x for x in C if x <= w['open']), default=None)
        nxt = min((x for x in C if x > w['open']), default=None)
        if c is None or w['close'] is None or (nxt is not None and w['close'] >= nxt):
            r2_bad.append((k, w, c, nxt))
    need('R2_one_window_per_cfg', len(W) == len(C) == n, (len(W), len(C), n))
    need('R2_window_retires_before_next_cfg', not r2_bad, r2_bad[:4])
    need('R2_cap_causes_zero', not tr['cap_bad'], (len(tr['cap_bad']), tr['cap_bad'][:4]))
    need('R2_rbase_domains_rotate', all(a['rbase'] != b['rbase'] for a, b in zip(W, W[1:])), [w['rbase'] for w in W])
    # ---------------------------------------------------------------- R3 consumer read at D
    vp_at_D, written_after = {}, defaultdict(int)
    first_good = {}
    partial = [c for c in tr['commits'] if c[4] != 0xffffffff]
    for t, leaf, a, v, _ in sorted(tr['commits']):
        key = (leaf, a)
        if D is not None and t <= D:
            vp_at_D[key] = (t, v)
        if key in first_good:
            written_after[key] += 1
        elif key in exp and v == exp[key][1]:
            first_good[key] = t
    wrong = [(k, exp[k][0], vp_at_D.get(k)) for k in exp if vp_at_D.get(k, (None, None))[1] != exp[k][1]]
    late = sorted(t for k, t in first_good.items() if D is not None and t > D)
    last_commit = max((t for t, *_ in tr['commits']), default=None)
    need('R3_deadline_defined', D is not None, None)
    need('R3_consumer_reads_512_golden_at_deadline', not wrong, dict(n_wrong=len(wrong), first=wrong[:4]))
    need('R3_no_vp_collision', not tr['collisions'], tr['collisions'][:4])
    need('R3_full_word_commits', not partial, len(partial))
    need('R3_retained_no_overwrite_to_end', not written_after, dict(list(written_after.items())[:4]))
    need('R3_terminal_trace_present', len(tr['terminal']) == 1, tr['terminal'])
    res = dict(PASS=not bad, checks=out, failed=bad,
               calendar=dict(mode=cal['mode'], period=P, cfg_lead=cal.get('cfg_lead'), nphases=n,
                             predicted_span=cal['predicted_span'], tail=tail, deadline_shift=shift),
               first_capture=first_cap, deadline=D, last_vp_commit=last_commit, last_element_retire=last_retire,
               last_cap_retire=max((w['close'] for w in W if w['close'] is not None), default=None),
               slack_edges=None if (D is None or last_commit is None) else D - last_commit,
               go_edges=[g[0] for g in gos], cfg_edges=C,
               cap_windows=[(w['open'], w['close'], w['rbase']) for w in W],
               element_lives_example={i: per[i] for i in list(per)[:2]},
               vp_words=len(tr['commits']), consumed=len(exp), trace_end=tr['terminal'], tmax=tr['tmax'])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', required=True)
    ap.add_argument('--fixture', required=True)
    ap.add_argument('--run', required=True)
    ap.add_argument('--golden-checker', required=True)
    ap.add_argument('--calendar', required=True, help='compiler calendar record (contract.json compiler_calendar or '
                                                      'xs_wqb_die calendar.json)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--deadline-shift', type=int, default=0)
    ap.add_argument('--tail', type=int, default=TAIL)
    ap.add_argument('--expect', choices=('pass', 'fail'), default='pass')
    a = ap.parse_args(argv)
    c = json.loads(Path(a.calendar).read_text())
    cal = c.get('compiler_calendar', c)
    exp, selfcheck = golden_vp(a.root, a.fixture, a.golden_checker)
    tr = parse(a.run)
    res = check(tr, cal, exp, a.deadline_shift, a.tail)
    res.update(run=str(a.run), golden_self_check=selfcheck, expect=a.expect,
               verdict_as_expected=(res['PASS'] == (a.expect == 'pass')))
    Path(a.out).write_text(json.dumps(res, indent=1, default=str) + '\n')
    print('WQBP_CONSUMER', 'PASS' if res['PASS'] else 'FAIL', 'expect', a.expect,
          'as_expected' if res['verdict_as_expected'] else 'NOT_AS_EXPECTED', 'D', res['deadline'],
          'last_commit', res['last_vp_commit'], 'slack', res['slack_edges'], 'failed', sorted(res['failed']))
    return 0 if res['verdict_as_expected'] else 1


if __name__ == '__main__':
    sys.exit(main())
