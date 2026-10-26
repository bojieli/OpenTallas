"""PROTO 2026-10-25: cheap per-bit FT geometry audit of every soft type of a plan (Codex corrected recipe 02:54/03:33:
actual pin-bit reach <= 405 um + station sites / explicit cell envelopes vs hard cores, other cells, outline).

    python3 geom_scan.py PLAN.json OUT.json      (run from the repo root; uses results/proto_codex_1025/corrected)
"""
import json, sys, time
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
sys.path.insert(0, str(ROOT / "results/proto_codex_1025/corrected"))
import scan as SC          # noqa: E402  (its sys.path insert is relative to its own dir; ours above covers tools)
import audit_one as AO     # noqa: E402

plan, out = sys.argv[1], sys.argv[2]
P = SC.S.Plan(SC.S.load(plan))
rows = {}
t0 = time.time()
for tn in sorted(P.types):
    if P.types[tn].get('hard'):
        continue
    try:
        r = SC.scan(P, tn)
        f = AO.footprints(P, tn)
        bad = bool(r['failures'] or f['core_intersections'] or f['overlaps'] or f['outside_outline'])
        r.update(footprints=f, verdict='FAIL' if bad else 'PASS')
    except Exception as e:  # a plan defect the scan cannot model is a FAIL with the reason
        r = dict(verdict='FAIL', error=f'{type(e).__name__}: {e}')
    rows[tn] = r
Path(out).write_text(json.dumps(dict(plan=plan, types=rows, elapsed_s=round(time.time() - t0, 1)), indent=1) + '\n')
print(plan, 'types', len(rows), 'FAIL', sum(r['verdict'] == 'FAIL' for r in rows.values()), 's', round(time.time() - t0, 1))
