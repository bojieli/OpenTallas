#!/usr/bin/env python3
"""OWNERS-SWEEP (OWNER r710): hourly table of unsigned types/cores on S81, HEAD, QC, KV (HBM skipped) with the lane that owns each.
Run on the hub:  python3 -I ~/coord/bin/owners_sweep.py [--agent-ids FILE|-] [--out lanes/OWNERS-SWEEP.tsv] [--hours 6] [--alive-hours 2]
  --agent-ids  lane<TAB>agent-id file from the rtx-pro localhost (pipe it in with '-': ssh intel2 '... --agent-ids -' < agent_ids.tsv)
Rows come from tools/failure_breakdown.py (same label()/signed logic) over autopilot/kit_wave_stages.tsv; owners from lane mentions
in lanes/posts/*.md entries (stamp in the last --hours) and lanes/handoff/*.md (mtime in the last --hours), plus the registry owner in
autopilot/OWNERS.tsv when it names a lane.  Flags: UNOWNED, DEAD-OWNER, FAILED-NO-RELAUNCH (>1 h), STALE (>3 h), UNCLASSIFIED (failure no rule names),
CBC-FALLBACK (COORD r713 fallback, CBC-RULES-1119: the type's family failed on >= 2 plan events with a DESIGN failure -- timing,
route, place, CTS, structural stop -- i.e. 2 normal fix rounds; the family's next event takes the close-by-construction form:
tools/die_plan/cbc_pass.py rows).  --cbc-post prints one post line of the CBC-FALLBACK families (hourly cron posts it as CBC-RULES-1119).  stdlib only, read-only
except the output file.  Prints per-die/flag counts.  Stamps are America/Los_Angeles."""
import argparse, collections, csv, glob, json, os, re, sys, time

os.environ['TZ'] = 'America/Los_Angeles'; time.tzset()
COORD = os.path.expanduser('~/coord')
sys.path.insert(0, os.path.join(COORD, 'tools'))
import failure_breakdown as fb

DIES = [d for d in fb.DIES if d[0] != 'hbm']
EXCLUDE_LANES = {'COORD', 'OWNERS-SWEEP', 'KIT-WAVE-1', 'KIT-WAVE-3', 'KIT-WAVE-5', 'KIT-WAVE-12'}
NOT_FAILED = {'running', 'running (lint advisory)', 'running (>150k advisory)', 'waits on child core', 'signed (count pending)',
              'cancelled (superseded)', 'duplicate (twin running)', 'needs parent receipt (re-sign)', 'withdrawn (lane form)',
              'placed, route held', 'held by die owner (plan event pending)', 'dedup orphan'}
RUNNING = {'running', 'running (lint advisory)', 'running (>150k advisory)', 'waits on child core', 'duplicate (twin running)'}
STAMP = re.compile(r'^- (\d{4}-\d\d-\d\d \d\d:\d\d)')
TOK = re.compile(r'[A-Za-z0-9_]{4,}')


def ts(s):
    try:
        return time.mktime(time.strptime(s[:16], '%Y-%m-%d %H:%M'))
    except ValueError:
        return 0.0


def fmt_t(t):
    return time.strftime('%m-%d %H:%M', time.localtime(t)) if t else ''


def load_lanes(now, win):
    """index token -> {lane: (time, snippet)}; last post per lane"""
    idx = collections.defaultdict(dict)
    last = {}
    def add(lane, t, text):
        snip = re.sub(r'\s+', ' ', text)[:90]
        for tk in set(TOK.findall(text)):
            cur = idx[tk].get(lane)
            if cur is None or t > cur[0]:
                idx[tk][lane] = (t, snip)
    for f in glob.glob(os.path.join(COORD, 'lanes/posts/*.md')):
        lane = os.path.basename(f)[:-3]
        ent = None
        try:
            lines = open(f, errors='replace').read().split('\n')
        except OSError:
            continue
        def flush():
            if ent and ent[0] >= now - win:
                add(lane, ent[0], ent[1])
        for l in lines:
            m = STAMP.match(l)
            if m:
                flush()
                ent = [ts(m.group(1)), l]
                last[lane] = max(last.get(lane, 0), ent[0])
            elif ent is not None:
                ent[1] += '\n' + l
        flush()
    for f in glob.glob(os.path.join(COORD, 'lanes/handoff/*.md')):
        lane = os.path.basename(f)[:-3]
        try:
            mt = os.path.getmtime(f)
        except OSError:
            continue
        last.setdefault(lane + '#handoff', mt)
        if mt >= now - win:
            add(lane, mt, open(f, errors='replace').read(60000))
    for k in [k for k in last if k.endswith('#handoff')]:
        lane = k[:-8]; last[lane] = max(last.get(lane, 0), last.pop(k))
    return idx, last


def keys(item):
    name = item.split('#')[0]
    ks = [(3, name)]
    if name.startswith('ot_'):
        ks.append((3, name[3:]))
    m = re.search(r'__(cl[0-9a-f]{8})', name)
    if m:
        ks.append((2, m.group(1)))
        ks.append((2, re.sub(r'__pv[0-9a-f]+$', '', name)))
    base = re.split(r'__', name)[0]
    base = re.sub(r'^ot_', '', base)
    b2 = re.sub(r'_v\d+\w*$', '', base)
    for b in {base, b2}:
        if len(b) >= 5:
            ks.append((1, b))
    return ks


CBC_FAMILY = re.compile(r'__(?:t\d+|cl[0-9a-f]{6,}|pv[0-9a-f]{6,})')
CBC_DESIGN = re.compile(r'TIMING|ROUTING|ROUTE|PLACE|CTS|GRT|DRC|STRUCT|setup|hold|overflow|wns|tns|-\d+(?:\.\d+)? ?(?:ps|ns)|congest', re.I)
CBC_NOT = re.compile(r'INFRA|FLOW|SOURCE|SRC_MANIFEST|KIT_NOT_SELF|kit-RTL|bind: ERROR|missing|LINT|queue|drained|LEAK-CANCEL|SUPERSEDED by attempt', re.I)
CBC_EVENT = re.compile(r'FAIL on event (\S+)')


def cbc_family(item):
    return CBC_FAMILY.split(item.split('#')[0])[0]


def cbc_failed_rounds(rows, since=0.0):
    """(die, family) -> sorted plan events on which a type of the family had a DESIGN failure (current FAIL row, a FAIL row
    superseded by a later event, or a STRUCT-STOP); infra / flow / source / lint / queue failures are not fix rounds."""
    ev = collections.defaultdict(set)
    for r in rows:
        if since and ts(r.get('updated') or '') < since:
            continue
        why = r.get('reason') or ''
        st, cl = r['status'], r.get('class') or ''
        if st == 'FAIL':
            txt = cl + ' ' + why
        elif cl == 'STRUCT-STOP':
            txt = 'STRUCT ' + why
        elif 'FAIL' in why and ('SUPERSEDED: FAIL' in why or 'was FAIL' in why):
            txt = why.split('was', 1)[-1]
        else:
            continue
        if CBC_NOT.search(txt.split('@')[0][:120]) or not CBC_DESIGN.search(txt):
            continue
        m = CBC_EVENT.search(why)
        ev[(r['die'], cbc_family(r['item']))].add(m.group(1) if m else r.get('event') or '?')
    return {k: sorted(v) for k, v in ev.items() if len(v) >= 2}


def registry():
    reg = {}
    try:
        for r in csv.DictReader((l for l in open(os.path.join(COORD, 'autopilot/OWNERS.tsv')) if not l.startswith('# ')), delimiter='\t'):
            reg[(r['die'], r['item'])] = r.get('owner', '')
    except (OSError, KeyError):
        pass
    return reg


LAUNCH = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d):\d\d \w+ AUTOPILOT: KIT-WAVE (?:LAUNCH|RELAUNCH-ON-FIX) (\w+)/(\S+?)(?:[:@ ]|$)')


def load_launches(tail=48 << 20):
    """(die, item) -> newest LAUNCH / RELAUNCH-ON-FIX time in autopilot/log.txt (LAUNCH-KEEP is not matched)"""
    out = {}
    try:
        with open(os.path.join(COORD, 'autopilot/log.txt'), 'rb') as f:
            f.seek(0, 2); f.seek(max(0, f.tell() - tail))
            for l in f.read().decode('utf-8', 'replace').split('\n'):
                m = LAUNCH.match(l)
                if m:
                    t = ts(m.group(1)); k = (m.group(2), m.group(3).split('#')[0])
                    if t > out.get(k, 0): out[k] = t
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent-ids'); ap.add_argument('--out', default=os.path.join(COORD, 'lanes/OWNERS-SWEEP.tsv'))
    ap.add_argument('--hours', type=float, default=6); ap.add_argument('--alive-hours', type=float, default=2)
    ap.add_argument('--cbc-days', type=float, default=0.0, help='count only kit_wave_stages rows updated in the last N days (0 = all; a superseded FAIL row is re-stamped when superseded)')
    ap.add_argument('--cbc-post', action='store_true', help='print the CBC-FALLBACK post line (families, events, unsigned types)')
    a = ap.parse_args()
    now = time.time(); win = a.hours * 3600
    ids = {}
    if a.agent_ids:
        src = sys.stdin if a.agent_ids == '-' else open(a.agent_ids)
        for l in src:
            f = l.rstrip('\n').split('\t')
            if len(f) >= 2: ids[f[0]] = f[1]       # later rows win
    idx, lastpost = load_lanes(now, win)
    lanes_known = set(lastpost) | set(ids)
    cache = json.load(open(fb.CACHE))
    rows = list(csv.DictReader(open(fb.STAGES), delimiter='\t'))
    last = {}
    for r in sorted(rows, key=lambda r: r['updated']):
        if r.get('plan_current') == 'no':
            continue
        if r['status'] == 'LINT-ADVISORY' and last.get((r['die'], r['item']), r)['status'] != 'LINT-ADVISORY':
            continue
        last[(r['die'], r['item'])] = r
    fb.LAST.clear(); fb.LAST.update(last)
    holds = fb.die_holds(); reg = registry(); launches = load_launches()
    cbc = cbc_failed_rounds(rows, now - a.cbc_days * 86400 if a.cbc_days else 0.0); cbc_hit = collections.defaultdict(list)
    out = []; notes = []
    for die, tag in DIES:
        plan = next(p for k, p in cache['plans'].items() if fb.PLAN_DIE.get(k.split('/')[0]) == die)
        designs = plan['designs']; signed = set(plan.get('signed_designs') or {})
        core_mods = set(m.split('#')[0] for m in designs); stset = set(plan.get('signed_types') or {})
        items = []
        for m in designs:
            if m in signed: continue
            r = fb.design_row(last, die, m, designs[m])
            items.append(('core', fb.short(m.split('#')[0]), m.split('#')[0], r, fb.label(r) if r else 'no kit-wave row'))
        for (d, item), r in last.items():
            if d != die or fb.is_core_row(item, r, core_mods) or fb.signed_type(item, stset): continue
            lab = fb.label(r)
            if lab not in ('running', 'signed (count pending)', 'cancelled (superseded)', 'needs parent receipt (re-sign)', 'duplicate (twin running)') \
                    and fb.held(holds, die, item, r):
                lab = 'held by die owner (plan event pending)'
            if lab in ('signed (count pending)', 'needs parent receipt (re-sign)') and (item.split('#')[0] in stset or fb.short(item) in stset):
                continue
            items.append(('type', fb.short(item), item, r, lab))
        ntypes = plan['types'] if isinstance(plan['types'], int) else len(plan['types'])
        nt = sum(1 for i in items if i[0] == 'type')
        if ntypes - len(stset) != nt:
            notes.append('%s: plan types %d, signed %d, rows %d (%d unsigned types without a kit-wave row)' % (tag, ntypes, len(stset), nt, ntypes - len(stset) - nt))
        for kind, short, item, r, lab in items:
            upd = ts(r['updated']) if r else 0.0
            age = (now - upd) / 3600 if upd else None
            cand = {}
            for lvl, k in keys(item):
                for lane, (t, snip) in idx.get(k, {}).items():
                    if lane in EXCLUDE_LANES: continue
                    c = cand.get(lane)
                    if c is None or (lvl, t) > (c[0], c[1]): cand[lane] = (lvl, t, snip)
            ro = reg.get((die, item.split('#')[0])) or reg.get((die, item)) or ''
            if ro and ro not in EXCLUDE_LANES and ro in lanes_known and ro not in cand:
                cand[ro] = (0, lastpost.get(ro, 0), 'registry owner')
            def alive(l): return lastpost.get(l, 0) >= now - a.alive_hours * 3600
            order = sorted(cand.items(), key=lambda kv: (-kv[1][0], not alive(kv[0]), -kv[1][1]))
            flags = []
            running = lab in RUNNING
            if order:
                lane, (lvl, t, snip) = order[0]
                match = {3: 'type', 2: 'cluster', 1: 'family', 0: 'registry'}[lvl]
                al = any(alive(l) for l, _ in order[:3])
                extra = [l for l, _ in order[1:3]]
                owner = lane + (' (+%s)' % ','.join(extra) if extra else '')
                if not al and not running: flags.append('DEAD-OWNER')
                lp = lastpost.get(lane, 0)
            else:
                lane = ''; match = ''; al = False; snip = ''; t = 0; lp = 0; owner = ''
                if running:
                    owner = 'KIT-WAVE(auto)'; match = 'autopilot'; al = True
                else:
                    flags.append('UNOWNED')
            failed = lab not in NOT_FAILED
            lt = launches.get((die, item.split('#')[0]), 0)
            if failed and lt > upd:
                age = (now - lt) / 3600; failed = False; lab = 'relaunched (LAUNCH %s)' % fmt_t(lt)
            if failed and age is not None and age > 1: flags.append('FAILED-NO-RELAUNCH')
            if r and failed and (r.get('class') or '') == 'UNCLASSIFIED': flags.append('UNCLASSIFIED')      # WAVE-PILOT-FIX 11-18 (COORD FLOW-1950 N): no rule names this failure; COORD starts a lane the same hour
            if not running and age is not None and age > 3: flags.append('STALE')
            if (die, cbc_family(item)) in cbc:
                flags.append('CBC-FALLBACK'); cbc_hit[(tag, die, cbc_family(item))].append(short)
            state = lab if not failed else 'FAILED ' + lab
            if age is not None and age > 3 and not running: state += ' (stale %.1fh)' % age
            kit = '%s %s %s' % (r['status'], r['stage'], r.get('class') or '') if r else 'no row'
            out.append([tag, short, kind, state, '%.1f' % age if age is not None else '', owner, match, 'yes' if al else 'no', fmt_t(lastpost.get(lane, 0)) if lane else '',
                        ids.get(lane, ''), kit.strip(), r['updated'] if r else '', fmt_t(t) + ' ' + snip if t else '', ','.join(flags)])
    hdr = ['die', 'type', 'kind', 'state', 'age_h', 'owning_lane', 'match', 'owner_alive', 'lane_last_post', 'agent_id', 'kit_last_action', 'kit_last_time', 'lane_last_mention', 'flags']
    with open(a.out, 'w') as f:
        f.write('# OWNERS-SWEEP %s PST (tools: ~/coord/bin/owners_sweep.py); one row per unsigned type/core on S81, HEAD, QC, KV; HBM skipped\n' % time.strftime('%Y-%m-%d %H:%M'))
        w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(hdr)
        for r in sorted(out, key=lambda r: (r[0], r[13] == '', r[1])): w.writerow([c.replace('\t', ' ').replace('\n', ' ') for c in r])
    cnt = collections.Counter(); ex = collections.defaultdict(list)
    for r in out:
        for fl in r[13].split(','):
            if fl: cnt[(r[0], fl)] += 1; ex[(r[0], fl)].append(r[1])
    print('rows %d' % len(out)); [print(n) for n in notes]
    for (d, fl), n in sorted(cnt.items()): print('%s %s %d e.g. %s' % (d, fl, n, ', '.join(ex[(d, fl)][:3])))
    print('rows with no flag: %d' % sum(1 for r in out if not r[13]))
    if a.cbc_post:
        fams = sorted(cbc_hit.items(), key=lambda kv: (kv[0][0], -len(kv[1])))
        if fams:
            print('CBC-POST CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds '
                  'tools/die_plan/cbc_pass.py rows into the next event): ' + '; '.join(
                      '%s %s: %d unsigned (%s), events %s' % (tag, fam, len(v), ','.join(sorted(v)[:3]), ','.join(cbc[(die, fam)][-4:]))
                      for (tag, die, fam), v in fams[:30]))
        else:
            print('CBC-POST none')


if __name__ == '__main__':
    main()
