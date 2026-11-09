#!/usr/bin/env python3
"""HEAD-PLAN-1 (COORD RULING 11-09 02:33 "ONE FINAL SWITCH PER DIE"): compose every pending HEAD plan event into ONE plan.

  head_final_switch.py SPEC.json OUT_DIR [--repo R]

SPEC = {"base": {"plan": PATH, "sidecar": PATH, "also_equal": [PATH ...]},
        "events": [ {"id", "owner_rows": [...], "why", "kind": "diff", "from": PATH, "to": PATH, "sidecar_to": PATH?}
                  | {"id", ..., "kind": "ops", "ops": [{"op": "set"|"merge"|"append_unique", "path": [...], "value": ...}]} ],
        "assets": {"<plan path string to rewrite>": "<new repo-relative path>"}}
A diff event is the change between its OWN base ("from") and its plan ("to"), cut at these units:
  top-level key (clock, reset, die, budgets, census, note, latency excluded), partition_types.<type>.<key>,
  partition_types.<type> (add / remove), partitions[name], ports[id], lanes[id].
Each unit is applied onto the composed plan only when the composed value equals the event base value (or any value in
base.also_equal plans, i.e. untouched since that ancestor) or already equals the event value; anything else is a
CONFLICT and the tool stops. Two events touching one unit with different values is a CONFLICT. `note` is appended.
Afterwards the latency table is recomputed (schema.Plan.lane_latency, gen.py latency --inplace semantics) and the
receipt lists, per lane, old -> new cycles (the switch's pin-cycle table) and every unit touched (the miter's scope).
Preservation: every unit not named by an event is asserted byte-identical (sort_keys JSON) to the base.
"""
import argparse
import copy
import gzip
import hashlib
import json
import sys
from pathlib import Path

LISTS = {'partitions': 'name', 'ports': 'id', 'lanes': 'id'}
DEEP_TOP = {'clock', 'reset'}
SKIP_TOP = {'latency', 'note', 'partition_types', 'partitions', 'ports', 'lanes'}


def J(x):
    return json.dumps(x, sort_keys=True)


def load(p):
    p = Path(p)
    raw = gzip.open(p).read() if p.suffix == '.gz' else p.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


MISSING = object()


def units(plan):
    """unit key -> value (MISSING for absent)."""
    u = {}
    def flat(path, v, depth):
        # top-level clock/reset are die-wide dicts edited by many events: cut them 3 keys deep (lists stay whole)
        if isinstance(v, dict) and depth < 4 and path[0] in DEEP_TOP:
            for kk, vv in v.items():
                flat(path + (kk,), vv, depth + 1)
            if not v:
                u[('top',) + path] = v
        else:
            u[('top',) + path] = v
    for k, v in plan.items():
        if k in SKIP_TOP:
            continue
        flat((k,), v, 1)
    for tn, t in plan['partition_types'].items():
        u[('type', tn)] = True
        for k, v in t.items():
            u[('tkey', tn, k)] = v
    for lk, idk in LISTS.items():
        for row in plan[lk]:
            u[(lk, row[idk])] = row
    return u


def delta(a, b):
    ua, ub = units(a), units(b)
    out = {}
    for k in set(ua) | set(ub):
        va, vb = ua.get(k, MISSING), ub.get(k, MISSING)
        if (va is MISSING) != (vb is MISSING) or (va is not MISSING and J(va) != J(vb)):
            out[k] = (va, vb)
    return out


def get_unit(plan, k):
    if k[0] == 'top':
        o = plan
        for kk in k[1:]:
            if not isinstance(o, dict) or kk not in o:
                return MISSING
            o = o[kk]
        return o
    if k[0] == 'type':
        return True if k[1] in plan['partition_types'] else MISSING
    if k[0] == 'tkey':
        t = plan['partition_types'].get(k[1])
        return MISSING if t is None else t.get(k[2], MISSING)
    idk = LISTS[k[0]]
    for row in plan[k[0]]:
        if row[idk] == k[1]:
            return row
    return MISSING


def set_unit(plan, k, v):
    if k[0] == 'top':
        o = plan
        for kk in k[1:-1]:
            o = o.setdefault(kk, {})
        if v is MISSING:
            o.pop(k[-1], None)
        else:
            o[k[-1]] = copy.deepcopy(v)
    elif k[0] == 'type':
        if v is MISSING:
            plan['partition_types'].pop(k[1], None)
        else:
            plan['partition_types'].setdefault(k[1], {})
    elif k[0] == 'tkey':
        t = plan['partition_types'].setdefault(k[1], {})
        if v is MISSING:
            t.pop(k[2], None)
        else:
            t[k[2]] = copy.deepcopy(v)
    else:
        idk = LISTS[k[0]]
        rows = plan[k[0]]
        for i, row in enumerate(rows):
            if row[idk] == k[1]:
                if v is MISSING:
                    del rows[i]
                else:
                    rows[i] = copy.deepcopy(v)
                return
        if v is not MISSING:
            rows.append(copy.deepcopy(v))


def same(a, b):
    if a is MISSING or b is MISSING:
        return a is b
    return J(a) == J(b)


def path_get(obj, path):
    for p in path:
        if isinstance(obj, list):
            if isinstance(p, dict):
                (kk, vv), = p.items()
                obj = next(x for x in obj if x.get(kk) == vv)
            else:
                obj = obj[p]
        else:
            obj = obj[p]
    return obj


def apply_op(plan, op):
    path = op['path']
    parent = path_get(plan, path[:-1])
    last = path[-1]
    if op['op'] == 'set':
        old = parent.get(last, None) if isinstance(parent, dict) else parent[last]
        if 'expect' in op and J(old) != J(op['expect']):
            raise SystemExit('op expect mismatch at %s: %s' % (path, J(old)[:200]))
        parent[last] = copy.deepcopy(op['value'])
    elif op['op'] == 'merge':
        tgt = parent.setdefault(last, {})
        for kk, vv in op['value'].items():
            if kk in tgt and J(tgt[kk]) != J(vv) and not op.get('override'):
                raise SystemExit('op merge conflict at %s.%s' % (path, kk))
            tgt[kk] = copy.deepcopy(vv)
    elif op['op'] == 'append_unique':
        tgt = parent.setdefault(last, [])
        for vv in op['value']:
            if vv not in tgt:
                tgt.append(vv)
    else:
        raise SystemExit('unknown op ' + op['op'])


def ukey(k):
    return '/'.join(str(x) for x in k)


def ops_units(plan_before, plan_after):
    return sorted(ukey(k) for k in delta(plan_before, plan_after))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--repo', default='.')
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    base, base_sha = load(spec['base']['plan'])
    ancestors = [load(p)[0] for p in spec['base'].get('also_equal', [])]
    plan = copy.deepcopy(base)
    sidecar_src = spec['base']['sidecar']
    owner = {}
    receipt = dict(schema='opentallas.head_final_switch.v1', base=spec['base']['plan'], base_sha256=base_sha,
                   events=[], conflicts=[])
    notes = []
    for ev in spec['events']:
        before = copy.deepcopy(plan)
        rec = dict(id=ev['id'], why=ev.get('why'), owner_rows=ev.get('owner_rows', []), kind=ev['kind'])
        if ev['kind'] == 'diff':
            fa, sa = load(ev['from']); fb, sb = load(ev['to'])
            rec.update(event_base=ev['from'], event_base_sha256=sa, event_plan=ev['to'], event_plan_sha256=sb)
            d = delta(fa, fb)
            skip = set(ev.get('skip_units', []))
            applied, already = [], []
            for k, (va, vb) in sorted(d.items(), key=lambda kv: ukey(kv[0])):
                if ukey(k) in skip:
                    continue
                cur = get_unit(plan, k)
                if same(cur, vb):
                    already.append(ukey(k)); owner.setdefault(ukey(k), ev['id']); continue
                ok = same(cur, va) or any(same(get_unit(anc, k), va) and same(get_unit(base, k), get_unit(anc, k))
                                          for anc in ancestors) or ukey(k) in ev.get('take_units', [])
                if not ok:
                    receipt['conflicts'].append(dict(event=ev['id'], unit=ukey(k), composed=J(cur)[:300] if cur is not MISSING else None,
                                                     event_base=J(va)[:300] if va is not MISSING else None,
                                                     event_plan=J(vb)[:300] if vb is not MISSING else None))
                    continue
                if ukey(k) in owner and owner[ukey(k)] != ev['id']:
                    receipt['conflicts'].append(dict(event=ev['id'], unit=ukey(k), other=owner[ukey(k)]))
                    continue
                set_unit(plan, k, vb); owner[ukey(k)] = ev['id']; applied.append(ukey(k))
            if J(fa.get('note', '')) != J(fb.get('note', '')):
                nb = fb.get('note', '')
                notes.append(nb[len(fa.get('note', '')):] if nb.startswith(fa.get('note', '')) else ' | ' + ev['id'])
            rec.update(units_applied=applied, units_already=already)
            if ev.get('sidecar_to'):
                sidecar_src = ev['sidecar_to']
                rec['sidecar'] = dict(path=ev['sidecar_to'], sha256=load(ev['sidecar_to'])[1])
        else:
            for op in ev['ops']:
                apply_op(plan, op)
            rec['ops'] = ev['ops']
            rec['units_applied'] = ops_units(before, plan)
            for u in rec['units_applied']:
                if u in owner and owner[u] != ev['id'] and not ev.get('stacks_on'):
                    receipt['conflicts'].append(dict(event=ev['id'], unit=u, other=owner[u]))
                owner.setdefault(u, ev['id'])
            notes.append(' | %s (HEAD-PLAN-1 final switch): %s' % (ev['id'], ev.get('why', '')))
        receipt['events'].append(rec)
    if receipt['conflicts']:
        (out / 'switch_receipt.json').write_text(json.dumps(receipt, indent=1))
        print('CONFLICTS', len(receipt['conflicts']))
        for c in receipt['conflicts'][:30]:
            print(' ', c)
        sys.exit(3)
    # asset path rewrites (absolute host paths -> repo-relative copies in the plan dir)
    txt = json.dumps(plan)
    for old, new in spec.get('assets', {}).items():
        txt = txt.replace(json.dumps(old)[1:-1], json.dumps(new)[1:-1])
    plan = json.loads(txt)
    plan['note'] = base.get('note', '') + ''.join(notes)
    # preservation: every unit nobody named is byte-identical to the base
    named = set(owner)
    for k, (va, vb) in delta(base, plan).items():
        if ukey(k) not in named and ukey(k) not in set(spec.get('assets_units', [])):
            if not (k[0] == 'tkey' and any(new in J(vb) for new in spec.get('assets', {}).values())):
                raise SystemExit('PRESERVATION FAIL: unit changed by nobody: ' + ukey(k))
    # latency table, same rule as gen.py latency --inplace (schema.Plan.lane_latency)
    sys.path.insert(0, str(Path(a.repo) / 'tools/die_plan'))
    from schema import Plan
    P = Plan(plan)
    old_lat = base['latency']['lanes']
    new_lat = {}
    for l in plan['lanes']:
        r = P.lane_latency(l['id'])
        new_lat[l['id']] = {k: v for k, v in r.items()} if isinstance(r, dict) else r
    plan['latency'] = dict(base['latency'], lanes=new_lat)
    changed = []
    for lid in sorted(set(old_lat) | set(new_lat)):
        o = old_lat.get(lid, {}).get('cycles'); n = new_lat.get(lid, {}).get('cycles')
        if o != n:
            changed.append(dict(lane=lid, old=o, new=n, by=sorted({owner[u] for u in owner if u.endswith('/' + lid)}) or None))
    receipt['lane_cycles_changed'] = changed
    data = (json.dumps(plan, indent=1) + '\n').encode()
    (out / 'source_plan.json').write_bytes(data)
    sc = Path(sidecar_src)
    side = gzip.open(sc).read() if sc.suffix == '.gz' else sc.read_bytes()
    (out / 'source_sidecar.json').write_bytes(side)
    receipt.update(plan_sha256=hashlib.sha256(data).hexdigest(), sidecar=str(sidecar_src),
                   sidecar_sha256=hashlib.sha256(side).hexdigest(), units_by_event={})
    for u, e in sorted(owner.items()):
        receipt['units_by_event'].setdefault(e, []).append(u)
    receipt['preservation'] = 'every unit not named in units_by_event byte-identical to the base (sort_keys JSON)'
    (out / 'switch_receipt.json').write_text(json.dumps(receipt, indent=1))
    print('SWITCH', receipt['plan_sha256'][:12], 'events', len(receipt['events']), 'units', len(owner),
          'lanes changed', len(changed))
    for c in changed:
        print('  LANE', c)


if __name__ == '__main__':
    main()
