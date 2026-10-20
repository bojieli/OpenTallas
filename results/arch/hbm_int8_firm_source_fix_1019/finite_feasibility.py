"""Small source geometry audit; never imports OpenDB or invokes an EDA engine."""
import collections, gzip, hashlib, json, pathlib, sys

KIT = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
load = lambda n: json.load(gzip.open(KIT / 'inputs' / (n + '.json.gz'), 'rt'))
pos = load('positions')
a = json.loads((KIT / 'allowlist.json').read_text())
old = pos['insts']
assert pos['units'] == 1000
assert set(x['orient'] for x in old.values()) <= {'R0', 'MX'}

def overlap_pairs(boxes):
    rows = collections.defaultdict(list)
    for n, b in boxes.items():
        rows[b[1]].append((b[0], b[2], b[3], n))
    pairs = []
    for y, row in rows.items():
        active = []
        for left, right, top, n in sorted(row):
            active = [v for v in active if v[1] > left]
            for lo, hi, yt, other in active:
                pairs.append(dict(a=other, b=n, overlap_dbu=[left, y, min(hi, right), min(yt, top)]))
            active.append((left, right, top, n))
    return pairs

baseline = {n: v['bbox'][:] for n, v in old.items()}
assert not overlap_pairs(baseline), 'baseline overlap must be independently resolved'
frozen = {n: b[:] for n, b in baseline.items()}
row_orients = collections.defaultdict(set)
for v in old.values():
    row_orients[v['bbox'][1]].add(v['orient'])
assert all(len(v) == 1 for v in row_orients.values())
counts = collections.Counter()
changed_locations, changed_orients = [], []
for n, r in a['replacement_cells'].items():
    before = old[n]
    planned = a['placement'][n]['bbox']
    assert before['master'] == r['old_master']
    width, height = planned[2] - planned[0], planned[3] - planned[1]
    assert height == before['bbox'][3] - before['bbox'][1] == 270
    # Exact pinned dbInst.cpp: swapMaster keeps origin/orientation/status and
    # recomputes bbox. R0/MX and equal height preserve bbox lower-left; width
    # grows toward +X. Other orientations intentionally refuse above.
    x, y = before['bbox'][:2]
    frozen[n] = [x, y, x + width, y + height]
    if before['location'] != planned[:2]: changed_locations.append(n)
    if before['bbox'][1] != planned[1]: counts['row_changes'] += 1
    if before['orient'] not in row_orients[planned[1]]: changed_orients.append(n)

growth_pairs = overlap_pairs(frozen)
full = dict(frozen)
full.update({n: a['placement'][n]['bbox'][:] for n in a['added_cells']})
full_pairs = overlap_pairs(full)
report = dict(
    schema='hbm.int8.firm_source_feasibility.v1', verdict='STRUCTURAL_REPLACEMENT_REFUSED',
    source_only=True, native_engine_run=False, baseline_cells=len(old), replacements=1078,
    baseline_overlap_pairs=0, planned_existing_location_changes=len(changed_locations),
    planned_existing_row_changes=counts['row_changes'],
    planned_orientation_changes_inferred_from_unanimous_existing_row_peers=len(changed_orients),
    row_orientation_caveat='Peer-derived parity, not a new native getRows result; all 171 occupied rows unanimous; original row inventory has 464 rows.',
    placement_status_caveat='Frozen export lacks status/origin; actual first failing instance FIRM. No all-FIRM claim.',
    preserved_origin_orientation_growth_overlap_pairs=len(growth_pairs),
    preserved_origin_orientation_growth_affected_instances=len({p[k] for p in growth_pairs for k in ['a','b']}),
    unchanged_1866_new_positions_full_overlap_pairs=len(full_pairs),
    growth_overlap_pairs=growth_pairs, full_overlap_pairs=full_pairs,
    changed_location_instances=changed_locations, inferred_changed_orientation_instances=changed_orients,
    inputs={str(p.relative_to(KIT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [KIT/'allowlist.json', KIT/'inputs/positions.json.gz']},
    next='New structural same-origin replacement model required; packing or redundant setter changes cannot repair these protected overlaps.',
    native_master_origin_site_phase_status_checks='OPEN before any root regrant',
    recomputed_cap_reach_rc_timing='OPEN; blocked by finite geometry refusal')
OUT.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k: v for k, v in report.items() if not isinstance(v, (list, dict))}, indent=2))
