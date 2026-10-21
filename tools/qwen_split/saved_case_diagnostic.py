"""Verify an explicitly frozen failed-GEN case for physical diagnosis only.

The manifest is a review artifact, never a GEN or calendar qualification.
Create it only after source/bind/reset prerequisites have been recorded.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate(root, manifest):
    root = root.resolve()
    if manifest.get('schema') != 'opentallas.saved_case_physical_diagnostic.v1':
        raise ValueError('unknown diagnostic manifest')
    if manifest.get('original_gen_exit') != 1 or manifest.get('compiler_verdict') != 'FAIL':
        raise ValueError('failed source/compilation evidence must remain explicit')
    if manifest.get('qualification_eligible') is not False:
        raise ValueError('saved failed GEN cannot be a qualification')
    for name, digest in manifest['sha256'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha(path) != digest:
            raise ValueError('saved case/source identity differs: ' + name)
    required = {'out.log', 'out/case/die.v', 'out/case/elements.lef',
                'out/case/place.tcl', 'out/case/manifest.json', 'out/pin_bit_reach.json',
                'pre_bind/port_bind.json', 'reset_sync_audit.txt', 'hier_check.line',
                'diagnostic_compiler_failure.json', 'diagnostic_open_classification.json'}
    if not required.issubset(manifest['sha256']):
        raise ValueError('manifest misses actual source/physical prerequisites')
    if not any(line == 'rc=1' for line in (root/'out.log').read_text().splitlines()):
        raise ValueError('original GEN rc1 evidence missing')
    compiler = json.loads((root/'diagnostic_compiler_failure.json').read_text())
    if not any(row.get('severity') == 'FAIL' for row in compiler.get('findings', [])):
        raise ValueError('retained compiler failure evidence is absent')
    reach = json.loads((root/'out/pin_bit_reach.json').read_text())
    if reach.get('over') != 0 or reach.get('limit_um') != 405.0 or reach.get('relay_skip') is not False:
        raise ValueError('actual per-bit reach gate failed or skipped')
    if 'PASS' not in (root/'reset_sync_audit.txt').read_text():
        raise ValueError('actual reset audit is not PASS')
    if 'HIER_CHECK PASS' not in (root/'hier_check.line').read_text():
        raise ValueError('actual hierarchical source binding is not PASS')
    report = json.loads((root/'pre_bind/port_bind.json').read_text())
    if set(report.get('failing', [])) != {'output_open_ports'}:
        raise ValueError('strict source report has additional or missing failure classes')
    for name in ('lane_latency_audit.txt','record_bundle_audit.txt','die_param_audit.txt','hr_contract.txt'):
        path = 'pre_bind/'+name
        if path not in manifest['sha256'] or 'PASS' not in (root/path).read_text():
            raise ValueError('actual source/record/parameter contract not PASS: '+name)
    if not any(name.startswith('src/rtl/') for name in manifest['sha256']):
        raise ValueError('manifest has no actual source identities')
    # Retain every original failure and allow only the reviewed open-output
    # diagnostic category. No input/source/width/driver/parameter waiver.
    for master, row in report['masters'].items():
        if any(reason != 'OUTPUT_OPEN' for reason in row.get('fails', [])):
            raise ValueError('non-output strict source failure: ' + master)
    classification = json.loads((root/'diagnostic_open_classification.json').read_text())
    actual = sorted((m,p) for m,row in report['masters'].items() for p in row['output_open'])
    declared = sorted((row['master'],row['port']) for row in classification['rows'])
    if actual != declared:
        raise ValueError('open outputs differ from exact reviewed diagnostic inventory')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path)
    ap.add_argument('manifest', type=Path)
    args = ap.parse_args()
    if os.environ.get('OT_SAVED_CASE_PHYSICAL_DIAGNOSTIC') != '1':
        raise SystemExit('saved failed-GEN physical entry is disabled by default')
    manifest = validate(args.root, json.loads(args.manifest.read_text()))
    chain = args.root/'chain'
    chain.mkdir(exist_ok=True)
    text = ('PHYSICAL_DIAGNOSTIC_ONLY\nORIGINAL_GEN_EXIT=1\nCOMPILER=FAIL\n'
            'NO_GEN_DONE; NO_QUALIFIED_SCHEDULE; NO_DIE_RELEASE\n')
    (chain/'DIAGNOSTIC_ONLY').write_text(text)
    (chain/'NOT_A_DIE_RESULT').write_text(text)
    print('SAVED_CASE_PHYSICAL_DIAGNOSTIC_IDENTITY_PASS originals remain FAIL')


if __name__ == '__main__':
    main()
