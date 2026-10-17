#!/usr/bin/env python3
"""Inventory exact HBM view requests without copying or qualifying timing receipts."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(instance):
    return canonical({k: instance.get(k, {}) for k in ('master', 'ports', 'params')})


def plan(contract, views, root, receipt_root):
    groups = defaultdict(list)
    for name, inst in contract['instances'].items():
        groups[signature(inst)].append(name)
    rows = []
    counts = Counter()
    for sig, names in sorted(groups.items()):
        instance = contract['instances'][names[0]]
        digest = hashlib.sha256(sig.encode()).hexdigest()
        row = dict(json.loads(sig), request_id=instance['master']+'__sig_'+digest[:16],
                   signature_sha256=digest, instances=sorted(names), source=instance['source'],
                   source_sha256=sha(root/instance['source']) if (root/instance['source']).is_file() else None,
                   clock_inputs={p:v for p,v in instance['ports'].items() if v['direction']=='input' and ('clk' in p or 'clock' in p)},
                   clock_R_status='UNVERIFIED: exact source/parameter-bound insertion.json required',
                   candidate_cells=[], receipt_checks=[], native_qualified=False)
        for cell, view in sorted(views.items()):
            if view['master'] != instance['master'] or view.get('params', {}) != instance.get('params', {}):
                continue
            # Compare the complete port ABI from the actual representative, not pin counts.
            representative = contract['instances'].get(view.get('representative'))
            if representative is None or representative['ports'] != instance['ports']:
                continue
            row['candidate_cells'].append(cell)
            meta = receipt_root/'synth'/cell/'meta.json'
            check = dict(cell=cell, kind=view.get('kind'), metadata_present=meta.is_file(),
                         parameter_receipt_verified=False, native_qualified=False)
            if meta.is_file():
                metadata = json.loads(meta.read_text())
                consumed = metadata.get('source_file_sha256', {})
                check.update(metadata_sha256=sha(meta), declared_source_snapshot=metadata.get('declared_source_snapshot'),
                             source_files=len(consumed), source_drift=[], unresolved_files=[])
                for path, expected in consumed.items():
                    current = root/path
                    if not current.is_file():
                        check['unresolved_files'].append(path)
                    elif sha(current) != expected:
                        check['source_drift'].append(path)
                # A wrapper hash alone does not reveal the parameter literals. Require an
                # explicit complete exact ABI in the receipt; old metadata lacks this.
                check['parameter_receipt_verified'] = metadata.get('exact_signature') == json.loads(sig)
            row['receipt_checks'].append(check)
        row['inventory_status'] = 'EXACT_DECLARATION_CANDIDATE' if row['candidate_cells'] else 'NEEDS_EXACT_EXPORT_OR_GENERIC_STRAP'
        counts[row['inventory_status']] += len(names)
        rows.append(row)
    return dict(policy='Planning only. Candidate membership is not source/native proof. No timing receipt is cloned.',
                instances=len(contract['instances']), exact_requests=len(rows), instance_counts=dict(counts),
                request_counts=dict(Counter(r['inventory_status'] for r in rows)), rows=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', required=True, type=Path)
    parser.add_argument('--views', required=True, type=Path)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--receipt-root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args=parser.parse_args()
    result=plan(json.loads(args.contract.read_text()),json.loads(args.views.read_text()),args.root,args.receipt_root)
    result['inputs']={str(p):sha(p) for p in (args.contract,args.views)}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:result[k] for k in ('instances','exact_requests','instance_counts','request_counts')}))


if __name__ == '__main__':
    main()
