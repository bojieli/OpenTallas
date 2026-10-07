#!/usr/bin/env python3
"""Price conditional QS3 on a pinned main ledger without adopting any lever."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import dsrom_1m_allmeasured as D
import dsrom_1m_allmeasured_adapters as AD
import three_machine_compose as TM

ROOT = Path(__file__).resolve().parents[1]
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def review(main_commit, out):
    main_commit = subprocess.check_output(['git', 'rev-parse', main_commit], cwd=ROOT, text=True).strip()
    ledger_path = 'results/rtl/dsrom_recovery_20261004/levers/s81_die_tiles.json'
    ledger_bytes = subprocess.check_output(['git', 'show', main_commit + ':' + ledger_path], cwd=ROOT)
    assert (ROOT / ledger_path).read_bytes() == ledger_bytes, 'ledger differs from pinned main'
    published = json.loads(subprocess.check_output(['git', 'show', main_commit + ':results/arch/three_machine_compose/compose.json'], cwd=ROOT))['ds_rom']
    rp_path = ROOT / 'results/rtl/dsrom_field_reprice_r8_20261006/reprice.json'
    rp = json.loads(rp_path.read_text())
    for p, h in {**rp['inputs'], **rp['tool_sha256']}.items():
        assert digest(ROOT / p) == h, p
    for name in ['field_spine', 'field_spine_pq', 'qelem_pq']:
        assert json.loads((TM.RECOVERY / 'levers' / (name + '.json')).read_text())['verdict'] == 'PENDING_SSFF'
    geom0, rel0 = AD.FIELD_GEOM, D.rel
    try:
        AD.FIELD_GEOM = 'f183.60'
        baseline = TM._row(D.compose(TM._args(TM.RECOVERY), write_output=False))
        for k in ['AR_tok_s', 'MTP_tok_s', 'AR_us', 'MTP_step_us']:
            assert baseline[k] == published[k], (k, baseline[k], published[k])
        with tempfile.TemporaryDirectory() as td:
            literal = TM._row(TM._with_flipped(TM.RECOVERY, Path(td), ['qelem_pq']))
            # Full-field QS3 cycles already include the decode stage. Price the explicit
            # candidate without the ledger's older 0.17% decode approximation as well.
            scratch = Path(td) / 'dedup'
            shutil.copytree(TM.RECOVERY / 'levers', scratch / 'levers')
            q = scratch / 'levers/qelem_pq.json'
            qd = json.loads(q.read_text()); qd['verdict'] = 'ADOPT'; q.write_text(json.dumps(qd))
            l = scratch / 'levers/s81_die_tiles.json'
            ld = json.loads(l.read_text())
            removed = [x for x in ld['adds'] if x.get('item') == 'pq_qelem']
            assert removed and all(x['cycles'] == 0 and x['frac'] == 0.0017 for x in removed)
            ld['adds'] = [x for x in ld['adds'] if x.get('item') != 'pq_qelem']
            l.write_text(json.dumps(ld)); D.rel = TM.rel
            dedup = TM._row(D.compose(TM._args(scratch), write_output=False))
            AD.FIELD_GEOM = 'f198.72'
            fitted = TM._row(D.compose(TM._args(scratch), write_output=False))
    finally:
        AD.FIELD_GEOM, D.rel = geom0, rel0
    rec = dict(schema='opentallas.dsrom-qs3-current-ledger-review.v1', main_commit=main_commit,
               status='PENDING_SSFF', adopted=False, geometry='f183.60',
               baseline=baseline, baseline_matches_published_main=True,
               conditional_qs3_literal_ledger=literal, conditional_qs3_deduplicated=dedup,
               conditional_qs3_route_frame=dict(geometry='f198.72', frame_height_um=192.24, composed=fitted,
                   delta_vs_current_main=TM._delta(fitted, baseline),
                   caveat='QS3 route uses 192.24 um height. f183.60 scenarios isolate cycle changes but do not prove QS3 fits that smaller frame. Taller-frame placement is analytically composed, not remeasured; selected v6 geometry input is absent.'),
               deduplicated_delta=TM._delta(dedup, baseline),
               overlap=dict(item='pq_qelem', fractional_charge=0.0017, removed_rows_in_scratch=len(removed),
                            rule='Candidate full-field QS3 measurement includes decode stages. Remove only this older approximation when adopting QS3; current headline ledger remains unchanged.'),
               unpriced_geometries=rp.get('unpriced_geometries', {}),
               pending=['Actual QS3 and v13b R16/R128 SS>=15 FF>=15 DRC0 closure',
                        'Required exact/negative and die-context integration gates',
                        'Coordinator adoption and fresh composition; no field_spine_pq stacking'],
               supersedes='adoption_review_20261007.json used obsolete 1649.9/4834.9 baseline; retained as history',
               inputs={ledger_path: digest(ROOT / ledger_path), str(rp_path.relative_to(ROOT)): digest(rp_path),
                       'results/rtl/dsrom_recovery_20261004/levers/qelem_pq.json': digest(TM.RECOVERY / 'levers/qelem_pq.json'),
                       'tools/dsrom_qs3_reprice_review.py': digest(Path(__file__))})
    out.write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps({k:rec[k] for k in ['baseline','conditional_qs3_literal_ledger','conditional_qs3_deduplicated','overlap']}, indent=2))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-commit', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); review(a.main_commit, a.out)
