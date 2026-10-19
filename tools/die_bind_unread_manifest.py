#!/usr/bin/env python3
"""Immutable, instance-and-bit-scoped unread review proposals. No approval refresh.

The proposal digest must be approved separately before passing it to die_port_bind.
This module never changes a source-intent review or broadens its ranges.
"""
import hashlib
import json
from pathlib import Path
import subprocess

SCHEMA = 'opentallas.die.unread-manifest.v1'


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return digest_bytes(Path(path).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def refuse(message):
    raise ValueError('unread review REFUSED: ' + message + '; renewed semantic review required')


def relative(path, root):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        refuse('RTL source outside source root: ' + str(path))


def ranges(entry):
    width = entry.get('width')
    if type(width) is not int or width <= 0:
        refuse('invalid width')
    out = set()
    rs = entry.get('unread_ranges')
    if not isinstance(rs, list) or not rs:
        refuse('empty/non-list unread ranges')
    for r in rs:
        if (not isinstance(r, list) or len(r) != 2 or any(type(i) is not int for i in r)
                or not 0 <= r[0] <= r[1] < width):
            refuse('out-of-range or malformed unread range')
        bits = set(range(r[0], r[1] + 1))
        if out & bits:
            refuse('overlapping unread ranges')
        out |= bits
    if entry.get('bit_count') != len(out):
        refuse('bit_count differs from exact ranges')
    for key in ('instance', 'master', 'port', 'net', 'source'):
        if not isinstance(entry.get(key), str) or not entry[key] or '*' in entry[key]:
            refuse('missing or wildcard ' + key)
    return out


def review_entries(review):
    entries = review.get('approved_entries')
    if not isinstance(entries, list):
        refuse('review has no approved_entries')
    seen = {}
    for e in entries:
        bits = ranges(e)
        key = (e['instance'], e['master'], e['port'])
        if seen.setdefault(key, set()) & bits:
            refuse('overlapping entries for instance port')
        seen[key] |= bits
    if sum(len(x) for x in seen.values()) != review.get('approved_bits'):
        refuse('approved_bits differs from exact entries')
    return entries


def selected_sources(idx, insts, root):
    todo = [mst for mst, _, _, _ in insts if mst != '__assign__']
    selected = {}
    while todo:
        name = todo.pop()
        if name in selected:
            continue
        mod = idx.get(name)
        if mod is None:
            refuse('unresolved selected module ' + name)
        selected[name] = {'path': relative(mod.path, root), 'sha256': digest(mod.path)}
        todo.extend(mod.children(idx))
    return selected


def snapshot(die, top, contract, idx, mparams, options, root, parse_die):
    _, _, _, insts = parse_die(die, top)
    instances = []
    for master, name, params, cm in insts:
        if master == '__assign__':
            continue
        effective = params or {k: v for k, v in mparams.get(master, {}).items() if not k.startswith('_')}
        instances.append({'instance': name, 'master': master, 'params': effective})
    return {'die_sha256': digest(die), 'contract_sha256': digest(contract), 'top': top,
            'instances': instances, 'selected_sources': selected_sources(idx, insts, root),
            'options': json.loads(canonical(options))}


def propose(review_path, die, top, contract, idx, mparams, options, root, parse_die):
    """Build a proposal only from the already reviewed historical source bytes.

    Re-running against drift refuses; it cannot bless new current hashes.
    ROOT must review the resulting immutable proposal digest before use.
    """
    review = json.loads(Path(review_path).read_text())
    review_entries(review)
    for key, path in [('die_v', die), ('contract', contract)]:
        if review['inputs'][key]['sha256'] != digest(path):
            refuse('reviewed ' + key + ' changed')
    snap = snapshot(die, top, contract, idx, mparams, options, root, parse_die)
    rev = review.get('source_commit')
    if not isinstance(rev, str) or not rev or not all(c in '0123456789abcdef' for c in rev):
        refuse('missing historical source revision')
    pins = dict(review.get('source_sha256', {}))
    historical_hashes = {}
    for ent in snap['selected_sources'].values():
        p, sha = ent['path'], ent['sha256']
        try:
            if p not in historical_hashes:
                historical = subprocess.run(['git', 'show', rev + ':' + p], cwd=root,
                                            check=True, capture_output=True).stdout
                historical_hashes[p] = digest_bytes(historical)
        except subprocess.CalledProcessError:
            refuse('historical source missing ' + p)
        if historical_hashes[p] != sha:
            refuse('selected source drift ' + p)
        if p in pins and pins[p] != sha:
            refuse('reviewed source differs ' + p)
        pins[p] = sha
    for p, sha in pins.items():
        if digest(Path(root) / p) != sha:
            refuse('reviewed source drift ' + p)
    return {'schema': SCHEMA, 'review_sha256': digest(review_path), 'source_commit': rev,
            'source_sha256': pins, 'snapshot': snap, 'entries': review['approved_entries']}


def validate(manifest_path, expected_sha, review_path, die, top, contract, idx,
             mparams, options, root, parse_die, expr_bits):
    if digest(manifest_path) != expected_sha:
        refuse('manifest digest differs from explicitly approved digest')
    obj = json.loads(Path(manifest_path).read_text())
    review = json.loads(Path(review_path).read_text())
    review_entries(review)
    if obj.get('schema') != SCHEMA or obj.get('review_sha256') != digest(review_path):
        refuse('review identity changed')
    if obj.get('entries') != review['approved_entries'] or obj.get('source_commit') != review.get('source_commit'):
        refuse('manifest permissions differ from exact reviewed entries')
    for p, sha in review.get('source_sha256', {}).items():
        if obj.get('source_sha256', {}).get(p) != sha:
            refuse('reviewed source pin removed ' + p)
    snap = snapshot(die, top, contract, idx, mparams, options, root, parse_die)
    if obj.get('snapshot') != snap:
        refuse('source/contract/die/parameters/options identity drift')
    for p, sha in obj.get('source_sha256', {}).items():
        if digest(Path(root) / p) != sha:
            refuse('source bytes changed ' + p)
    for ent in snap['selected_sources'].values():
        if obj.get('source_sha256', {}).get(ent['path']) != ent['sha256']:
            refuse('selected closure source pin missing')
    nets, _, _, insts = parse_die(die, top)
    by_name = {name: (mst, params, cm) for mst, name, params, cm in insts}
    if len(by_name) != len(insts):
        refuse('duplicate instance identity')
    approved = set()
    for e in obj['entries']:
        bits = ranges(e)
        if e['instance'] not in by_name:
            refuse('reviewed instance missing')
        mst, params, cm = by_name[e['instance']]
        if mst != e['master'] or e['port'] not in cm:
            refuse('reviewed master/port differs')
        mod = idx[mst]
        params = params or {k: v for k, v in mparams.get(mst, {}).items() if not k.startswith('_')}
        if (relative(mod.path, root) != e['source'] or mod.ports.get(e['port'], (None,))[0] != 'output'
                or mod.width(e['port'], mod.env(params)) != e['width']):
            refuse('reviewed source/direction/width differs')
        wirebits = expr_bits(cm[e['port']], nets)
        if wirebits is None or len(wirebits) != e['width']:
            refuse('reviewed output expression differs')
        for i in bits:
            b = wirebits[len(wirebits) - 1 - i]
            if b[0] != e['net'] or b[1] != i:
                refuse('reviewed net/bit mapping differs')
            if b in approved:
                refuse('overlapping net permissions')
            approved.add(b)
    return approved
