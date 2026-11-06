#!/usr/bin/env python3
"""Write a concise per-die failure breakdown (cores + types) into RELEASE_TREE.md.

Cores: unsigned designs from the release-tree plan cache, classed by
lanes/CORE-CLASS.tsv (COORD override, prefix match) or else by the latest
kit-wave row. Types: latest current-plan kit-wave row per type item.
The block sits between the BREAKDOWN markers; run after release_tree_plan.py.
"""
import csv, json, collections, os, re, time

COORD = os.path.expanduser('~/coord')
CACHE = os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json')
STAGES = os.path.join(COORD, 'autopilot/kit_wave_stages.tsv')
OVR = os.path.join(COORD, 'lanes/CORE-CLASS.tsv')
TREE = os.path.join(COORD, 'RELEASE_TREE.md')
BEGIN, END = '<!-- BREAKDOWN BEGIN -->', '<!-- BREAKDOWN END -->'
DIES = [('s81', 'S81'), ('s81_head', 'HEAD'), ('qwen_compute', 'QC'), ('qwen_kvsys', 'KV'), ('hbm', 'HBM')]
PLAN_DIE = {'s81': 's81', 'results': 's81_head', 'qwen_compute': 'qwen_compute',
            'qwen_kvsys': 'qwen_kvsys', 'hbm': 'hbm'}

# (pattern on class+reason, short label); first match wins
FAIL_MAP = [
    (r'signed off but no flow release tag', 're-sign (flow tag)'),
    (r'insertion gate|band FAIL; fix the clock', 'clock window (resume)'),
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
    (r'PORT_MISMATCH|port', 'port mismatch'),
    (r'kit_rtl|KIT_RTL', 'kit_rtl'),
]


def label(r):
    st = r['status']
    if st in ('RUNNING', 'QUEUED'):
        return 'running'
    if st == 'SIGNED':
        return 'signed (count pending)'
    if st == 'CANCELLED':
        return 'cancelled (superseded)'
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
    return 'other flow error'


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


def main():
    cache = json.load(open(CACHE))
    rows = list(csv.DictReader(open(STAGES), delimiter='\t'))
    last = {}
    for r in sorted(rows, key=lambda r: r['updated']):
        if r.get('plan_current') == 'no':
            continue
        last[(r['die'], r['item'])] = r
    ovr = []
    for l in open(OVR):
        if l.startswith('#') or not l.strip():
            continue
        f = l.rstrip('\n').split('\t')
        ovr.append((f[0], f[1], f[2]))

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
                r = last.get((die, m)) or last.get((die, base))
                lab = label(r) if r else 'not tried'
            cc[lab] += 1
            cn[lab].append(short(base))
        ntypes = plan['types'] if isinstance(plan['types'], int) else len(plan['types'])
        stypes = len(plan.get('signed_types') or {})
        stset = set(plan.get('signed_types') or {})
        tc, tn = collections.Counter(), collections.defaultdict(list)
        for (d, item), r in last.items():
            if d != die or item.split('#')[0] in core_mods:
                continue
            lab = label(r)
            # COORD 11-06: a SIGNED row already in the official count is not "count pending".
            if lab == 'signed (count pending)' and (item.split('#')[0] in stset or short(item) in stset):
                continue
            tc[lab] += 1
            tn[lab].append(short(item))
        out.append('- [ ] FAIL.%s.CORES %d/%d signed · open: %s' % (tag, len(designs) - len(unsigned), len(designs), fmt(cc, cn, limit=3)))
        out.append('- [ ] FAIL.%s.TYPES %d/%d signed · kit rows: %s' % (tag, stypes, ntypes, fmt(tc, tn, limit=1)))
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
