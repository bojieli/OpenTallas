"""Reset-scope packet builder for KIT_TOPOLOGY_BIND_STALE rows (S81-TYPES-7, 11-08).

Read-only. For each wave item it evaluates the canonical kit_topology freshness
predicate twice against the bind of record: default (full reset digest) and
OT_NATIVE_RESET_SCOPE=selected (complete producer receipt + selected reset
context). It names every type whose reset context moved between the producer
plan and the current plan, and writes the item_env a wave batch needs. Nothing
is stamped and no bind, plan or receipt is written.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_topology as kt  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def producer_path(bind_out, override=None):
    if override:
        return Path(override)
    prov = json.loads((Path(bind_out) / 'provenance_bind.json').read_text())
    return Path(prov.get('provenance', {}).get('plan', ''))


def moved_reset_types(producer, current):
    """Types whose native reset context differs (the reason a full digest moved)."""
    names = set(producer['partition_types']) | set(current['partition_types'])
    out = []
    for tn in sorted(names):
        a = producer['partition_types'].get(tn)
        b = current['partition_types'].get(tn)
        if a is None or b is None:
            out.append(dict(type=tn, why='missing in ' + ('producer' if a is None else 'current')))
            continue
        ca, cb = kt.selected_reset_context(producer, tn), kt.selected_reset_context(current, tn)
        if ca != cb:
            keys = [k for k in ('reset', 'hard') if ca[k] != cb[k]]
            keys += ['clock.' + k for k in sorted(set(ca['clock']) | set(cb['clock']))
                     if ca['clock'].get(k) != cb['clock'].get(k)]
            out.append(dict(type=tn, why=keys))
    return out


def evaluate(plan_path, bind_out, asbuilt, items, override=None):
    current = json.loads(Path(plan_path).read_text())
    prod = producer_path(bind_out, override)
    if not prod.is_absolute() or not prod.is_file():
        raise SystemExit(f'producer context missing: {prod}')
    producer = json.loads(prod.read_text())
    receipt = json.loads((Path(bind_out) / 'native_topology.json').read_text())
    reference = kt.native_contract(producer, asbuilt, prod)
    receipt_ok = {k: receipt.get(k) == reference.get(k)
                  for k in ('reset', 'transport', 'clock_table_sha256', 'types', 'ownership')}
    receipt_ok['asbuilt_sha256'] = receipt.get('asbuilt_sha256') == sha(asbuilt)
    moved = moved_reset_types(producer, current)
    global_same = producer.get('reset') == current.get('reset')
    rows = []
    saved = {k: os.environ.get(k) for k in ('OT_NATIVE_RESET_SCOPE', 'OT_NATIVE_PRODUCER_CONTEXT')}
    try:
        for item in items:
            tn = item
            row = dict(item=item, type=tn)
            if tn not in current['partition_types']:
                row.update(verdict='NOT_A_TYPE')
                rows.append(row)
                continue
            for k in saved:
                os.environ.pop(k, None)
            row['default'] = kt.bind_matches(current, tn, bind_out, asbuilt, plan_path)
            os.environ['OT_NATIVE_RESET_SCOPE'] = 'selected'
            if override:
                os.environ['OT_NATIVE_PRODUCER_CONTEXT'] = str(prod)
            row['selected'] = kt.bind_matches(current, tn, bind_out, asbuilt, plan_path)
            row['own_reset_moved'] = any(m['type'] == tn for m in moved)
            row['verdict'] = ('ALREADY_FRESH' if row['default'] else
                              'SELECTED_PASS' if row['selected'] else 'REBIND_NEEDED')
            if row['verdict'] == 'SELECTED_PASS':
                env = {'OT_NATIVE_RESET_SCOPE': 'selected'}
                if override:
                    env['OT_NATIVE_PRODUCER_CONTEXT'] = str(prod)
                row['item_env'] = env
            rows.append(row)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return dict(schema='opentallas.reset_scope_packet.v1', plan=str(plan_path), plan_sha256=sha(plan_path),
                bind_out=str(bind_out), asbuilt=str(asbuilt), asbuilt_sha256=sha(asbuilt),
                producer=str(prod), producer_sha256=sha(prod), receipt_reproduced=receipt_ok,
                global_reset_same=global_same, moved_reset_types=moved, rows=rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('plan')
    ap.add_argument('bind_out')
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--items', nargs='+', required=True)
    ap.add_argument('--producer', help='absolute producer plan (default: bind provenance plan)')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    res = evaluate(a.plan, a.bind_out, a.asbuilt, a.items, a.producer)
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(txt + '\n')
    for r in res['rows']:
        print(r['verdict'], r['item'], 'default', r.get('default'), 'selected', r.get('selected'),
              'own_reset_moved', r.get('own_reset_moved'))
    print('receipt_reproduced', res['receipt_reproduced'], 'global_reset_same', res['global_reset_same'])
    print('moved_reset_types', [m['type'] for m in res['moved_reset_types']])
    return 0 if all(r['verdict'] != 'REBIND_NEEDED' for r in res['rows']) else 3


if __name__ == '__main__':
    sys.exit(main())
