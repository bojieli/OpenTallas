#!/usr/bin/env python3
"""Prepare additive startup repair; copy the unchanged calendar, never compile."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/w17_window_qdq8_connected_preparation_20261002'
OLD = 'rtl/test/w17_window_qdq8_connected/tb.sv'
NEW = 'rtl/test/w17_window_qdq8_connected_startup_guard/tb.sv'
BEFORE = 'else if(desc_count<NOPS&&life_done_count==desc_count&&source_done_count==desc_count)'
AFTER = 'else if(desc_count>0&&desc_count<NOPS&&life_done_count==desc_count&&source_done_count==desc_count)'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(out):
    out = Path(out).resolve()
    manifest = json.loads((BASE / 'files_sha256.json').read_text())
    for path, digest in manifest.items():
        assert sha(BASE / path) == digest, path
    model = json.loads((BASE / 'model.json').read_text())
    assert sha(ROOT / 'tools/w17_window_qdq8_connected_model.py') == model['generator_sha256']
    for path, digest in model['source_sha256'].items():
        assert sha(ROOT / path) == digest
        assert hashlib.sha256(subprocess.check_output(
            ['git', 'show', model['source_commit'] + ':' + path], cwd=ROOT)).hexdigest() == digest
    for key in ('candidate_sha256', 'dependencies_sha256', 'fixture_sha256'):
        for path, digest in model[key].items():
            assert sha(ROOT / path) == digest
    original = (ROOT / OLD).read_text()
    repaired = (ROOT / NEW).read_text()
    assert original.count(BEFORE) == 1
    assert repaired == original.replace(BEFORE, AFTER)
    assert not out.exists()
    out.mkdir()
    for path in manifest:
        dst = out / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BASE / path, dst)
    (out / 'sources/tb.sv').write_bytes((ROOT / NEW).read_bytes())
    previous_root = model['preparation']['commands']['retain0']['cwd']
    for command in model['preparation']['commands'].values():
        command['compile'] = [arg.replace(previous_root, str(out)) for arg in command['compile']]
        command['runtime'] = [arg.replace(previous_root, str(out)) for arg in command['runtime']]
        command['cwd'] = str(out)
    model['fixture_sha256'].pop(OLD)
    model['fixture_sha256'][NEW] = sha(ROOT / NEW)
    model['preparation']['snapshot_sha256']['tb.sv'] = sha(ROOT / NEW)
    model['preparation']['source_bytes'] = sum(p.stat().st_size for p in (out / 'sources').iterdir())
    model['startup_repair'] = dict(
        failed_fixture=OLD, failed_fixture_sha256=sha(ROOT / OLD),
        original_model_sha256=sha(BASE / 'model.json'),
        preparation_tool_sha256=sha(Path(__file__)),
        change='Continuation requires a positive previously accepted descriptor count.',
        predictions='All cases, event journals, oracle and numerical fields copied unchanged.',
        runtime='NONE; no compile or simulation; fresh runner binding and parent GO required.',
        preserved_failure='results/rtl/w17_window_qdq8_connected_single_run_20261002/record.json')
    (out / 'model.json').write_text(json.dumps(model, indent=2) + '\n')
    fresh = {path: sha(out / path) for path in manifest}
    (out / 'files_sha256.json').write_text(json.dumps(fresh, indent=2) + '\n')
    changed = sorted(path for path in manifest if fresh[path] != manifest[path])
    assert changed == ['model.json', 'sources/tb.sv']
    receipt = dict(verdict='PREPARED_STATIC_ONLY_PENDING_FRESH_RUNNER_AND_GO',
                   changed_snapshot_files=changed, files_sha256=fresh,
                   no_compile=True, no_runtime=True, predictions_byteidentical=True,
                   model_sha256=sha(out / 'model.json'), manifest_sha256=sha(out / 'files_sha256.json'))
    (out / 'startup_repair_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.out), indent=2))
