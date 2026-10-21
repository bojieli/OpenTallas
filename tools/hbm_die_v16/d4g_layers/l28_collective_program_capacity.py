#!/usr/bin/env python3
"""Select the measured iterated-tag collective configuration before r15 synthesis.

ROWS=256 supports the measured DS RS144 programme (218 rows, 862/872 cycles).
Use the exact issuer_m256/v7 source manifest; a ROWS override of old v8g RTL
without its 8-bit programme-counter and issuer selection is insufficient.
"""
import argparse
import hashlib
import json
from pathlib import Path


def apply(contract):
    selected = []
    manifest = Path(__file__).resolve().parents[3] / 'results/arch/hbm_release_r15_1021/collective_rows256_source.json'
    sources = json.loads(manifest.read_text())['sources']
    expected = {'hb_coll_' + q for q in ('SW', 'SE', 'NW', 'NE')}
    for name in sorted(expected):
        item = contract['instances'][name]
        if item['master'] not in ('ot_hfd_coll_q2_hard_v8g', 'ot_hfd_coll_q3_hard_v8x'):
            raise ValueError(f'unreviewed collective master {name}: {item["master"]}')
        item.setdefault('params', {}).update(AR_ITER=1, ROWS=256)
        # A closed view of another parameterisation cannot qualify this parent.
        for key in ('physical_view', 'closed_record'):
            item.pop(key, None)
        item['rtl_deps'] = sorted(set(item.get('rtl_deps', [])) | {s['path'] for s in sources if s['kind'] == 'die' and s['path'] != item['source']})
        selected.append(name)
    return dict(selected=selected, params=dict(AR_ITER=1, ROWS=256),
                evidence='claude/tok-func-hbm-xdie-1021 results/rtl/tok_func_hbm_1021/xdie',
                outstanding=['r15 die synthesis and physical implementation at ROWS256; CLOSED128 issuer is not interchangeable'],
                qualification='FUNCTIONAL_PARAMETER_SELECTION_ONLY; parent synthesis/physical implementation outstanding')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    contract = json.loads(args.input.read_text())
    report = apply(contract)
    root = Path(__file__).resolve().parents[3]
    paths = sorted({p for i in contract['instances'].values() for p in [i.get('source')] + list(i.get('rtl_deps') or []) if p})
    report['source_sha256'] = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths if (root / p).is_file()}
    report['missing_sources'] = [p for p in paths if not (root / p).is_file()]
    report['source_complete'] = not report['missing_sources']
    args.output.write_text(json.dumps(contract, indent=1) + '\n')
    report['contract_sha256'] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    if args.report:
        args.report.write_text(json.dumps(report, indent=1) + '\n')
    print('L28_COLLECTIVE_PARAMS AR_ITER=1 ROWS=256 instances=4 DS_RS144=862/872cycles')
