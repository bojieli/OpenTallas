#!/usr/bin/env python3
"""Pure legacy-STG3 refetch checks using committed raw evidence; no simulation."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    repo = Path(__file__).resolve().parents[2]
    fixture = repo / 'results/rtl/tokfunc2_qw_1021/stg3'
    script = Path(__file__).with_name('normalize_collected_stg.py')
    raw = (fixture / 'original_result.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    results = []
    for variant in ('complete', 'missing_cal', 'corrupt_fixture'):
        with tempfile.TemporaryDirectory() as name:
            source = Path(name) / 'fleet/stg3'
            shutil.copytree(fixture, source)
            (source / 'result.json').write_bytes(raw)
            shared = source.parent / 'shared_fx'
            (source / 'fx').rename(shared)
            (source / 'fx').symlink_to(shared, target_is_directory=True)
            listing = subprocess.run([sys.executable, str(script.with_name('collect_files.py')),
                                      str(source)], capture_output=True, check=True)
            paths = [p.decode() for p in listing.stdout.split(b'\0') if p]
            assert sum(p.endswith('/bench.out') for p in paths) == 527
            assert sum(p.startswith('fx/') and p.endswith('_fixture.json') for p in paths) == 36
            assert 'pos/cal_mat/calibrate.out' in paths
            assert not any('/obj' in p or '/tree/' in p or p.endswith('/Vtb') for p in paths)
            stage = Path(name) / 'results/stg'
            for path in paths:
                target = stage / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / path, target)
            if variant == 'missing_cal':
                (stage / 'pos/cal_mat/calibrate.out').unlink()
            if variant == 'corrupt_fixture':
                (stage / 'fx/L0_fixture.json').write_text('{broken JSON')
            run = subprocess.run([sys.executable, str(script), str(stage)],
                                 capture_output=True, text=True)
            assert run.returncode == 0, run
            row = json.loads((stage / 'result.json').read_text())
            assert (stage / f'original_result.{digest}.json').read_bytes() == raw
            assert row['verdict'] == ('FAIL' if variant == 'complete' else 'INCOMPLETE')
            if variant == 'corrupt_fixture':
                assert any('local collector could not fold fetched evidence:' in s for s in row['failures'])
                assert row['delivery_timing_qualified'] is False
                results.append(dict(case=variant, verdict=row['verdict'], original_raw_unchanged=True))
                continue
            assert row['numeric_case_summary'] == dict(
                cases=527, expected_outcomes_met=527, unmet_cases=[])
            assert len(row['unknown_delivery_cases']) == 144
            assert row['delivery_timing_qualified'] is False
            for cfg in ('rel', 'pos'):
                for family in ('qkv', 'gu'):
                    assert row['cycles'][cfg][family]['all_layers'] is None
            if variant == 'missing_cal':
                assert 'pos/cal_mat/calibrate.out' in row['collection_normalization']['missing_evidence']
                assert 'pos/mat required calibration NOT_RECORDED rc=None' in row['failures']
            else:
                assert row['failures'] == ['pos/mat required calibration FAIL rc=1']
                assert row['collection_normalization']['missing_evidence'] == []
            results.append(dict(case=variant,
                                verdict=row['verdict'], numeric_outcomes='527/527',
                                unknown_delivery_cases=144, original_raw_unchanged=True))
    print(json.dumps(dict(verdict='PASS', scope='pure re-fold of preserved raw logs; no hardware',
                         cases=results), indent=1))


if __name__ == '__main__':
    main()
