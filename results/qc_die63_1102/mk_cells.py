import json, sys, re, os
sys.path.insert(0, os.path.join(sys.argv[1], 'tools/die_plan'))
import cells as CE
wt = sys.argv[1]; best = json.load(open(sys.argv[2])); out = sys.argv[3]
qd = os.path.join(wt, 'physical/die_plan/qwen_compute')
P = json.load(open(qd + '/plan_of_record/plan_qc52.json')); T = P['partition_types']
notes = json.load(open(qd + '/plan_notes.json'))['cells_per_type']
def root(t):
    return re.split(r'__cl', t)[0]
rows = {}
NATIVE = {'native59': (254739, 'codex/qc-neighbor-counts-1101@c2b571529 (254739 std + 8 SRAM)'),
          'coll_ftm': (83317, 'codex/qc-neighbor-counts-1101@c2b571529'),
          'coll_ftc': (158904, 'codex/qc-neighbor-counts-1101@c2b571529'),
          'coll_core': (671634, 'epyc2 codex-qc62-collect-1101/native_pair_retry1/items/coll_core/receipt.json (671613 std + 21 SRAM)')}
for tn, t in T.items():
    if t.get('hard') or 'cells' in t or any('cells' in c for c in t.get('contents', [])):
        continue
    if tn in best:
        b = best[tn]; rows[tn] = dict(cells=b['cells'], basis='measured yosys synth_stat (kit of this type)', src='%s:%s' % (b['host'], b['path']))
        continue
    sib = [k for k in best if root(k) == root(tn)]
    pref = [k for k in sib if k.startswith(tn.rsplit('__cl', 1)[0] + '__cl')] if '__cl' in tn else []
    pick = (pref or sib)
    if pick:
        k = max(pick, key=lambda k: best[k]['mtime']); b = best[k]
        rows[tn] = dict(cells=b['cells'], basis='measured yosys synth_stat of landing-cohort sibling %s (same base RTL)' % k, src='%s:%s' % (b['host'], b['path']))
        continue
    if tn in NATIVE:
        rows[tn] = dict(cells=NATIVE[tn][0], basis='measured native d90 COUNT/ABI/FACE (Codex qc-neighbor-counts/native_pair)', src=NATIVE[tn][1])
        continue
    fam = re.sub(r'_v\d+$', '', root(tn))
    fs = [k for k in best if re.sub(r'_v\d+$', '', root(k)) == fam]
    if fs:
        k = max(fs, key=lambda k: best[k]['mtime']); b = best[k]
        rows[tn] = dict(cells=b['cells'], basis='measured yosys synth_stat of family variant %s (no kit of this variant yet)' % k, src='%s:%s' % (b['host'], b['path']))
        continue
    r = root(tn)
    if r in notes:
        rows[tn] = dict(cells=notes[r]['cells'], basis='plan estimate physical/die_plan/qwen_compute/plan_notes.json cells_per_type[%s] (no measured kit synth yet)' % r)
for tn, v in rows.items():
    if not v['basis'].startswith('measured'):
        continue
    m = re.search(r'(?:sibling|variant) (\S+)', v['basis'])
    srct = m.group(1) if m else tn
    rg = CE.landing_rings(T[srct]) if srct in T else None
    if rg is None:
        # source type left the plan: use this type's rings (same base RTL)
        rg = CE.landing_rings(T[tn])
    v['measured_total'] = v['cells']; v['landing_rings_in_measured'] = rg; v['cells'] = v['cells'] - rg
    v['basis'] += '; minus its landing rings %d (cells.py rule 6 adds this type\'s rings back)' % rg
json.dump(dict(schema='qc_cells_evidence.v1', note='DIE-QC-63 11-02: per-type std-cell estimates for G0C completeness [cells] (tools/die_plan/cells.py by_type source). Measured kit synth where one exists, else landing-cohort sibling, else plan_notes estimate; type.cells in the plan always wins.', cells_per_type=rows), open(out, 'w'), indent=1, sort_keys=True)
from collections import Counter
print(len(rows), Counter(v['basis'].split(' (')[0].split(' of ')[0][:40] for v in rows.values()))
print('missing', [tn for tn in T if tn not in rows and not T[tn].get('hard') and 'cells' not in T[tn] and not any('cells' in c for c in T[tn].get('contents', []))])
print('over400k', sorted((k, v['cells']) for k, v in rows.items() if v['cells'] + CE.landing_rings(T[k]) > 400000 and not T[k].get('hard_cores')))
