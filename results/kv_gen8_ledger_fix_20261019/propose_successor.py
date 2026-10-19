"""Build an OFFLINE diagnostic ledger proposal; never modify a live run.

All original rows and expanded die bytes are preserved. This is deliberately
not a continuation driver or native-qualified profile issuer.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/qwen_kv_die'))
import kv_expand_parameters as P


def read(path):
    data = Path(path).read_bytes()
    return gzip.decompress(data) if str(path).endswith('.gz') else data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot-root', type=Path, required=True)
    ap.add_argument('--die', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    old = ROOT / 'results/kv_gen8_ledger_terminal_20261019'
    pins = json.loads((old / 'identity_snapshot.json').read_text())
    assert P.sha(args.die) == pins['run_files']['case_kv/die.v']['sha256']
    raw_expand = read(old / 'expand.json.gz')
    raw_sidecar = read(old / 'die.v.params.json.gz')
    assert hashlib.sha256(raw_expand).hexdigest() == pins['run_files']['expand.json']['sha256']
    assert hashlib.sha256(raw_sidecar).hexdigest() == pins['run_files']['case_kv/die.v.params.json']['sha256']
    report, sidecar = json.loads(raw_expand), json.loads(raw_sidecar)
    assert json.dumps(report, indent=1).encode() + b'\n' == raw_expand
    assert json.dumps(sidecar, indent=1).encode() + b'\n' == raw_sidecar
    previous_report, previous_sidecar = copy.deepcopy(report), copy.deepcopy(sidecar)
    module = 'qkd_astk_rly_296_fl'
    rtl = 'rtl/lib/face_land/qkd_astk_rly_296_fl.sv'
    view = 'physical/ref_tile/qkd_astk_rly_296/views/' + module
    identity = P.artifact_identity(args.snapshot_root, view, rtl)
    expected_identity = json.loads((Path(__file__).parent / 'selected_wrapper_identity.json').read_text())
    assert identity == expected_identity
    # Independent emitted-source census, not the defective ledger's own list.
    actual = re.findall(r'^\s+' + module + r'\s+(\S+)\s*\(', args.die.read_text(), re.M)
    missing = json.loads((old / 'inventory.json').read_text())['missing_instances']
    assert len(actual) == len(set(actual)) == 912
    assert set(actual) == set(missing)
    candidate_profile = {module: dict(parameters={'MUT': 0}, identity=identity)}
    literals, profile = P.preserve(args.snapshot_root, module, {}, rtl, view,
                                   candidate_profile, diagnostic=True)
    assert literals == {'MUT': "32'sb" + '0' * 32}
    assert profile['native_qualified'] is False and profile['frozen_receipt'] is None
    try:
        P.preserve(args.snapshot_root, module, {}, rtl, view, candidate_profile, diagnostic=False)
    except ValueError as error:
        assert 'native parameter qualification missing' in str(error)
    else:
        raise AssertionError('strict operation must refuse this diagnostic proposal')
    for inst in sorted(actual):
        assert inst not in report['parameter_instances'] and inst not in sidecar
        report['parameter_instances'][inst] = dict(module=module, literals=literals, profile=profile)
        sidecar[inst] = literals
    restored_report = copy.deepcopy(report)
    restored_sidecar = copy.deepcopy(sidecar)
    for inst in actual:
        del restored_report['parameter_instances'][inst]
        del restored_sidecar[inst]
    assert restored_report == previous_report and restored_sidecar == previous_sidecar
    # Exclusive directory creation prevents an old proposal being refreshed.
    args.out.mkdir(parents=True, exist_ok=False)
    outputs = {'expand.json': json.dumps(report, indent=1).encode() + b'\n',
               'case_kv/die.v.params.json': json.dumps(sidecar, indent=1).encode() + b'\n'}
    diffs = {}
    for name, data in outputs.items():
        destination = args.out / (name.replace('/', '__') + '.gz')
        destination.write_bytes(gzip.compress(data, mtime=0))
        diffs[name] = dict(before=pins['run_files'][name]['sha256'],
                           proposed=hashlib.sha256(data).hexdigest(), bytes=len(data),
                           added_rows=912, removed_rows=0, changed_existing_rows=0)
    helpers = {p: P.sha(ROOT / p) for p in ('tools/qwen_kv_die/kv_expand.py',
                                           'tools/qwen_kv_die/kv_expand_parameters.py')}
    manifest = dict(schema='opentallas.offline_ledger_proposal.v1',
                    status='PROPOSAL_ONLY_DIAGNOSTIC_NOT_CONTINUATION',
                    frozen_generated_source='5f2ce19bc', frozen_driver='cda9d9f9d',
                    helper_commit='d19b6b77f', exact_helpers=helpers,
                    changed_helper_sources={p: dict(before=pins['source_files'][p]['sha256'], after=h)
                                            for p, h in helpers.items()},
                    unchanged_die=pins['run_files']['case_kv/die.v'],
                    unchanged_output_identity={p: row for p, row in pins['run_files'].items()
                                               if p not in diffs},
                    changed_outputs=diffs, all_other_source_and_outputs='UNCHANGED_REQUIRED',
                    preserved_parameter_rows=7601, proposed_parameter_rows=8513,
                    preserved_sidecar_rows=7649, proposed_sidecar_rows=8561,
                    explicit_profile=candidate_profile, native_qualified=False,
                    strict_result='REFUSE: native parameter qualification missing',
                    continuation_authorized=False,
                    preconditions=['actual producer/binder fixture PASS',
                                   'ROOT review of complete source/output diff',
                                   'independent native parameter proof before strict use',
                                   'current reset/fanout/contact/PG qualification remains separate'])
    (args.out / 'source_output_diff.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(status=manifest['status'], changed_outputs=diffs), indent=2))


if __name__ == '__main__':
    main()
