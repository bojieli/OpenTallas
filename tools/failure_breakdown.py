#!/usr/bin/env python3
"""Write a concise per-die failure breakdown (cores + types) into RELEASE_TREE.md.

Cores: unsigned designs from the release-tree plan cache, classed by
lanes/CORE-CLASS.tsv (COORD override, prefix match) or else by the latest
kit-wave row. Types: latest current-plan kit-wave row per type item.
The block sits between the BREAKDOWN markers; run after release_tree_plan.py.
STALE section (WAVE-OPS-1 11-10): stale_list.py, full list in lanes/STALE.tsv; OT_FB_NO_STALE=1 skips it.
"""
import csv, json, collections, os, re, time

COORD = os.path.expanduser('~/coord')
CACHE = os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json')
STAGES = os.path.join(COORD, 'autopilot/kit_wave_stages.tsv')
OVR = os.path.join(COORD, 'lanes/CORE-CLASS.tsv')
TREE = os.path.join(COORD, 'RELEASE_TREE.md')
BEGIN, END = '<!-- BREAKDOWN BEGIN -->', '<!-- BREAKDOWN END -->'
DIES = [('s81', 'S81'), ('s81_head', 'HEAD'), ('qwen_compute', 'QC'), ('qwen_kvsys', 'KV'), ('hbm', 'HBM')]
PLAN_DIE = {'s81': 's81', 's81_head': 's81_head', 'results': 's81_head', 'qwen_compute': 'qwen_compute',
            'qwen_kvsys': 'qwen_kvsys', 'hbm': 'hbm'}

# (pattern on class+reason, short label); first match wins
FAIL_MAP = [
    (r'signed off but no flow release tag', 're-sign (flow tag)'),
    # KW-FIX-32 11-07 (COORD 17:42 (4), KV-TYPES-3 ASK 2): rows stopped from outside (ruling, operator, infra exit 137)
    # are not design results; they were other flow error
    (r'infra-stopped|exit 137|exit-137|[Ss]topped by ruling|Operator stopped|controller stopped|stopped from outside|stopped_by', 'stopped (ruling/infra)'),
    (r'insertion gate|band FAIL; fix the clock', 'clock window (resume)'),
    # KW-FIX-24 11-06 (COORD 19:2x (10)): the GRT-stage G2 setup gate rides the FAIL_POSTCTS marker (kit-wave class
    # post-cts-hold) but is a setup failure at global route, not a hold after CTS
    (r'legacy grt gate: G2 setup_tt|SETUP-AT-GRT', 'SETUP-AT-GRT'),
    (r'post-cts-hold|OT_HOLD', 'hold after CTS'),
    (r'routed-not-signed|routed: TT|late-ECO', 'timing after route'),
    (r'LEC not equivalent|LEC NOT EQ', 'LEC'),
    (r'FACE_GUARD|face guard', 'FACE_GUARD'),
    (r'ring band capacity|CLAND', 'CLAND ring band'),
    (r'400k|OT_NATIVE_CELL_CAP|native standard-cell count', 'over 400k cells'),
    (r'PDN-0006', 'PDN-0006'),
    (r'no recipe|CORE_VIEW|NO_RECIPE', 'no recipe'),
    (r'CORE_PREFLIGHT|faces not registered', 'unregistered pins'),
    (r'grt-overflow|congestion|GRT-0183', 'congestion'),
    (r'global_place', 'global_place error'),
    (r'detail_place|DPL-', 'detail_place'),
    (r'macro_place|MPL-|PLAN_CORE_MACROS', 'macro placement'),
    (r'relay-bay', 'relay-bay hop'),
    (r'pending plan delta', 'plan-delta hold'),
    (r'no host qualif|NOT RUN on', 'no host'),
    # KIT-FIX-F 11-13: the 173 "tooling" rows read by their error lines.  'port' matched "Connection closed ... port 22" and
    # "tie clock export form"; 'kit_rtl' matched any stage name; stopped / held / post-place rows fell to 'other flow error'.
    (r'@unit[^\n]*: KW_STAGE|restaged: unstarted', 'stopped by the wave (not a kit failure)'),
    (r'grt-timecap|OT_GRT_TIMECAP', 'GRT time cap (placed)'),
    (r'DRT-0255|DRT-0073|No access point|Maze Route', 'detail route error (placed)'),
    (r'ssh transport|Connection closed by', 'infra (ssh)'),
    (r'memory_bits|SYNTH_MEMORY_MAX_BITS', 'memory over synth cap (needs macro)'),
    (r"Can't resolve task name|GEN_LINT FAIL rtl_check", 'RTL lint at gen'),
    (r'differs from captured bound reset identity|KIT_TOPOLOGY_BIND_STALE|KIT_TOPOLOGY_', 'bind stale vs plan (re-bind)'),
    (r'KIT_NOT_SELF_CONTAINED|KIT_INPUT_MISSING|preferred HDL source missing|names missing files|tool input file missing',
     'kit input missing'),
    (r'gpl-noconverge|KW_PLACE_RC', 'place error'),
    (r'PORT_MISMATCH|PORT_BIND|port mismatch', 'port mismatch'),
    (r'@kit_rtl\b|KIT_RTL', 'kit_rtl'),
    # S81-OTHERFAIL-2 11-07: the remaining S81 'other flow error' signatures
    (r'FAIL_PREFLOOR reg_fanout', 'reg_fanout preflight'),
    (r'queue row rejected: kit carries FAIL_PREFLOOR', 'stale FAIL_PREFLOOR kit (LEC reject)'),
    (r'1_2_yosys\.v\] Error', 'synth stopped (OOM/kill)'),
]


def label(r):
    st = r['status']
    if st in ('RUNNING', 'QUEUED'):
        return 'running'
    if st == 'SIGNED':
        return 'signed (count pending)'
    if st == 'CANCELLED':
        return 'cancelled (superseded)'
    # S81-OTHERFAIL-2 11-07 23:2x: these statuses are not flow errors; they were 26 of S81's 32 'other flow error'.
    # WAIT-PARENT = local pass, io_hold_parent NEEDS_PARENT (counts, OWNER 11-03; counted ones are skipped in main()).
    if st == 'WAIT-PARENT':
        return 'needs parent receipt (re-sign)'
    if st == 'WITHDRAWN':
        return 'withdrawn (lane form)'
    if st == 'ROUTE-HELD':
        return 'placed, route held'
    text = (r.get('class') or '') + ' ' + (r.get('reason') or '')
    if st == 'LINT-ADVISORY':
        if 'without a signed view' in text:
            return 'waits on child core'
        if 'std cells > 150000' in text:
            return 'running (>150k advisory)'
        return 'running (lint advisory)'
    for pat, lab in FAIL_MAP:
        if re.search(pat, text):
            return lab
    if st == 'RETRY-INFRA':
        return 'infra (relaunch queued)'
    return 'other flow error'


def die_holds():
    """{die: [hold_items patterns]} from the wave config; a held type waits for its die owner, whatever its last row says"""
    try:
        cfg = json.load(open(os.path.join(COORD, 'autopilot/kit_wave.json')))
        return {d: list((v.get('hold_items') or {}).keys()) for d, v in cfg.get('dies', {}).items()}
    except (OSError, ValueError):
        return {}


def held(holds, die, item, r):
    import fnmatch
    names = [item, r.get('parent_item') or '']
    return any(fnmatch.fnmatchcase(n, pat) for n in names if n for pat in holds.get(die, []))


def is_core_row(item, r, core_mods):
    base = item.split('#')[0]
    return (base in core_mods or (r.get('parent_item') or '') in core_mods
            or re.sub(r'__v[0-9a-f]{12}$', '', base) in core_mods)


def short(name):
    return name.split('#')[0].replace('ot_', '').replace('hbm_', '')


def fmt(counter, names=None, limit=4):
    parts = []
    for lab, n in counter.most_common():
        s = '%s %d' % (lab, n)
        if names and lab in names and lab not in ('running', 'waits on child core'):
            ns = sorted(set(names[lab]))
            s += ' (%s%s)' % (', '.join(ns[:limit]), ', +%d' % (len(ns) - limit) if len(ns) > limit else '')
        parts.append(s)
    return ' · '.join(parts) if parts else 'none'


def design_row(last, die, did, design):
    """latest kit-wave row of one counter design: its own id, else its wave keys, else its module.
    COUNT-ARCHIVE-2 11-09 (DIE-HBM-97 12:00): the wave names a multi-design module's item module__v<sha256[:12] of the
    pins file> (the counter's designs[did]['wave_keys']), not the counter's id module#outline/<pins16>; without this the
    HBM __v rows read as 'no kit-wave row'."""
    r = last.get((die, did))
    if r: return r
    hits = [last[(die, w)] for w in (design or {}).get('wave_keys') or [] if (die, w) in last]
    if hits: return max(hits, key=lambda x: x.get('updated', ''))
    return last.get((die, did.split('#')[0]))


def main():
    cache = json.load(open(CACHE))
    rows = list(csv.DictReader(open(STAGES), delimiter='\t'))
    last = {}
    for r in sorted(rows, key=lambda r: r['updated']):
        if r.get('plan_current') == 'no':
            continue
        # QC-TYPES-11 11-08: prelint LINT-ADVISORY rows refresh every tick; they masked the real row (a route RUNNING or FAIL
        # read as 'waits on child core').  An advisory row labels the item only when it has no real row.
        if r['status'] == 'LINT-ADVISORY' and last.get((r['die'], r['item']), r)['status'] != 'LINT-ADVISORY':
            continue
        last[(r['die'], r['item'])] = r
    ovr = []
    for l in open(OVR):
        if l.startswith('#') or not l.strip():
            continue
        f = l.rstrip('\n').split('\t')
        ovr.append((f[0], f[1], f[2]))

    holds = die_holds()
    out = [BEGIN, '## FAILURES · unsigned cores and types by class (auto, %s)' % time.strftime('%Y-%m-%d %H:%M %Z')]
    for die, tag in DIES:
        plan = next(p for k, p in cache['plans'].items() if PLAN_DIE.get(k.split('/')[0]) == die)
        designs = plan['designs']
        # Count per design, as the official count does: a signed module does not cover its other outlines.
        signed = set(plan.get('signed_designs') or {})
        core_mods = set(m.split('#')[0] for m in designs)
        unsigned = [m for m in designs if m not in signed]
        cc, cn = collections.Counter(), collections.defaultdict(list)
        for m in unsigned:
            base = m.split('#')[0]
            lab = next((c for d, p, c in ovr if d == die and base.startswith(p)), None)
            if lab is None:
                r = design_row(last, die, m, designs[m])
                lab = label(r) if r else 'no kit-wave row'  # COORD 11-07: says only that the wave has no row; kits may exist outside it
            cc[lab] += 1
            cn[lab].append(short(base))
        ntypes = plan['types'] if isinstance(plan['types'], int) else len(plan['types'])
        stypes = len(plan.get('signed_types') or {})
        stset = set(plan.get('signed_types') or {})
        tc, tn = collections.Counter(), collections.defaultdict(list)
        for (d, item), r in last.items():
            # COUNT-AUDIT-3 11-07: kit-wave rows for a core outline variant carry '__v<hash>' (item
            # ot_hbm_hc_bank128_pair_core__v7d149b37532c, parent_item ot_hbm_hc_bank128_pair_core); they are
            # cores (counted in CORES via signed_designs), never types.
            if d != die or is_core_row(item, r, core_mods):
                continue
            lab = label(r)
            if lab not in ('running', 'signed (count pending)', 'cancelled (superseded)', 'needs parent receipt (re-sign)') \
                    and held(holds, die, item, r):
                lab = 'held by die owner (plan event pending)'
            # COORD 11-06: a SIGNED row already in the official count is not "count pending".
            if lab in ('signed (count pending)', 'needs parent receipt (re-sign)') and (
                    item.split('#')[0] in stset or short(item) in stset):
                continue
            tc[lab] += 1
            tn[lab].append(short(item))
        out.append('- [ ] FAIL.%s.CORES %d/%d signed · open: %s' % (tag, len(designs) - len(unsigned), len(designs), fmt(cc, cn, limit=3)))
        out.append('- [ ] FAIL.%s.TYPES %d/%d signed · kit rows: %s' % (tag, stypes, ntypes, fmt(tc, tn, limit=1)))
    # WAVE-OPS-1 11-10 (OWNER 11-10, item A): STALE = unsigned plan core/type, no live job, no kit-wave row change >= 6 h
    if not os.environ.get('OT_FB_NO_STALE'):
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import stale_list
            out += stale_list.section(cache, rows, DIES, plan_die=PLAN_DIE)
        except Exception as e:                       # the breakdown is still written; the failure is named in it
            out.append('### STALE · not computed: %s: %s' % (type(e).__name__, str(e)[:200]))
    out.append(END)
    block = '\n'.join(out)

    text = open(TREE).read()
    if BEGIN in text:
        text = re.sub(re.escape(BEGIN) + '.*?' + re.escape(END), block, text, flags=re.S)
    else:
        lines = text.split('\n')
        i = next(n for n, l in enumerate(lines) if l.startswith('## EDIT'))
        lines[i:i] = [block, '']
        text = '\n'.join(lines)
    open(TREE, 'w').write(text)
    print(block)


if __name__ == '__main__':
    main()
