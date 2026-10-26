#!/usr/bin/env python3
"""Recover source RTL directions for an existing budget model without rebuilding its generator.

The generated die netlist is authoritative for instance/port/net connections. Geometry,
anchors and bus topology are preserved. This proves source directions only: it does
not promote real_masters or establish functional/native/physical qualification.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as DPB


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def invariants(model):
    """All existing model fields except direction annotations and their failure count."""
    obj = {k: v for k, v in model.items() if k not in
           ('buses', 'endpoint_dir_failures', 'endpoint_dir_failure_examples', 'direction_repair', 'endpoint_dir_segments')}
    obj['buses'] = [[bid, cls, bits, [ep[:2] for ep in eps]] for bid, cls, bits, eps in model['buses']]
    return canonical(obj)


def ranges(expr, nets):
    """Connection width and compact (net, low, high-exclusive) ranges; no bit expansion."""
    e = expr.strip()
    if not e:
        return 0, []
    if e.startswith('{') and e.endswith('}'):
        inner = e[1:-1].strip()
        rep = re.fullmatch(r'(\d+)\s*\{(.*)\}', inner, re.S)
        if rep:
            w, rr = ranges('{' + rep[2] + '}', nets)
            return w * int(rep[1]), rr * int(rep[1])
        w, rr = 0, []
        for part in DPB._split_commas(inner):
            n, rows = ranges(part, nets)
            w += n
            rr += rows
        return w, rr
    c = re.fullmatch(r"(\d+)'[sS]?[bBhHdDoO][0-9a-fA-F_xXzZ?]+", e)
    if c:
        return int(c[1]), []
    m = re.fullmatch(r'(\\\S+|\w+)\s*(?:\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?', e)
    if not m or m[1] not in nets:
        raise ValueError(f'unsupported or undeclared connection: {e[:160]}')
    name = m[1]
    w, lo = nets[name]
    a, b = (lo, lo + w - 1) if m[2] is None else (int(m[2]), int(m[3] or m[2]))
    low, high = min(a, b), max(a, b) + 1
    if low < lo or high > lo + w:
        raise ValueError(f'out-of-range connection: {e}')
    return high - low, [(name, low, high)]


def collapse(rows, width, offset=0):
    """Require exact once-only full-width coverage; never infer unknown directions."""
    rows = sorted(rows)
    out, pos = [], offset
    for lo, hi, d in rows:
        if (lo > pos or hi <= lo or hi > offset + width or d not in ('in', 'out', 'io')
                or (lo < pos and (not out or out[-1][2] != d))):
            raise ValueError(f'gap/overlap/invalid direction at {pos}: {(lo, hi, d)} width {width}')
        if out and out[-1][2] == d:
            out[-1][1] = max(pos, hi)
        else:
            out.append([lo, hi, d])
        pos = max(pos, hi)
    if pos != offset + width:
        raise ValueError(f'incomplete source coverage {pos}/{width}')
    return out


def repair(model, die_v, idx, amb, mparams):
    """Resolve each modeled endpoint against actual generated named-port connections."""
    # DPB handles non-ANSI top declarations, inline instance parameters and named connections.
    nets, tin, tout, instances = DPB.parse_die(die_v)
    by = {i[0]: i for i in model['insts']}
    requests = defaultdict(lambda: defaultdict(list))
    for bi, (bid, cls, width, eps) in enumerate(model['buses']):
        for ei, (inst, port, *_) in enumerate(eps):
            net = 'n_' + bid if 'n_' + bid in nets else bid
            requests[inst][net].append((bi, ei, width))
    counts = Counter(dict.fromkeys(('in', 'out', 'io', 'mixed', 'missing', 'partial', 'source_errors'), 0))
    errors = []
    error_counts = Counter()
    evidence = {}
    seen = set()
    source_files = set()

    def fail(inst, reason):
        counts['source_errors'] += 1
        error_counts[str(reason)] += 1
        if len(errors) < 40:
            errors.append(dict(instance=inst, error=str(reason)))

    def resolve(inst, conn, port_conn=None, port_widths=None):
        for net, endpoints in requests[inst].items():
            for bi, ei, width in endpoints:
                ep = model['buses'][bi][3][ei]
                try:
                    base_port = ep[1].split('@', 1)[0].split('[', 1)[0]
                    selected = (port_conn[base_port] if port_conn is not None and base_port in port_conn else conn)
                    span = re.fullmatch(r'(.+)\[(\d+):(\d+)\]@(\d+)', ep[1])
                    partial = False
                    if span:
                        lo, hi, offset = int(span[2]), int(span[3]), int(span[4])
                        extent = abs(hi - lo) + 1
                        if (port_widths is None or base_port not in port_widths or
                                max(lo, hi) >= port_widths[base_port] or offset + extent > width):
                            raise ValueError(f'invalid source endpoint slice {ep[1]}')
                        seg = collapse(selected.get(net, []), extent, offset)
                        partial = extent < width
                        if partial:
                            counts['partial'] += 1
                    else:
                        seg = collapse(selected.get(net, []), width)
                    ds = {s[2] for s in seg}
                    ep[2] = next(iter(ds)) if len(ds) == 1 else 'mixed'
                    counts[ep[2]] += 1
                    if len(ds) > 1 or partial:
                        evidence[f'{bi}:{ei}'] = seg
                except ValueError as e:
                    ep[2] = '?'
                    counts['missing'] += 1
                    if len(errors) < 40:
                        errors.append(dict(bus=model['buses'][bi][0], instance=inst, port=ep[1], error=str(e)))

    for master, inst, inline, conns in instances:
        if inst not in requests:
            continue
        if inst in seen:
            fail(inst, 'duplicate die instance')
            continue
        seen.add(inst)
        conn = defaultdict(list)
        port_conn = {}
        port_widths = {}
        try:
            if inst not in by or by[inst][1] != master:
                raise ValueError(f'netlist/model master mismatch {master}')
            if master not in idx or master in amb:
                raise ValueError(f'missing/ambiguous module {master}: {amb.get(master)}')
            mod = idx[master]
            source_files.add(mod.path)
            if conns.dups:
                raise ValueError(f'duplicate named ports {conns.dups}')
            if mod.port_parse_errors:
                raise ValueError(f'unparsed RTL ports {mod.port_parse_errors}')
            overrides = {k: v for k, v in mparams.get(master, {}).items() if not k.startswith('_')}
            overrides.update(inline)
            env = mod.env(overrides)
            for port, expr in conns.items():
                port_conn[port] = defaultdict(list)
                width, rr = ranges(expr, nets)
                if not any(net in requests[inst] for net, _, _ in rr):
                    continue
                if port not in mod.ports:
                    raise ValueError(f'connected port absent in RTL: {master}.{port}')
                direction = {'input': 'in', 'output': 'out', 'inout': 'io'}.get(mod.ports[port][0])
                if direction is None:
                    raise ValueError(f'unknown RTL direction {master}.{port}')
                actual = mod.width(port, env)
                port_widths[port] = actual
                if actual != width:
                    raise ValueError(f'port width mismatch {master}.{port}: source {actual}, netlist {width}')
                for net, lo, hi in rr:
                    if net in requests[inst]:
                        conn[net].append((lo, hi, direction))
                        port_conn[port][net].append((lo, hi, direction))
        except (ValueError, KeyError) as e:
            fail(inst, e)
            conn.clear()  # do not publish partially parsed instance evidence
            port_conn.clear()
            port_widths.clear()
        resolve(inst, conn, port_conn, port_widths)
    for inst in requests.keys() - seen:
        if inst == 'TOP':
            conn = {net: [(0, width, 'out' if net in tin else 'in' if net in tout else '?')]
                    for net, endpoints in requests[inst].items() for _, _, width in endpoints}
            resolve(inst, conn)
        else:
            fail(inst, 'model instance absent from generated netlist')
            resolve(inst, {})
    model['endpoint_dir_failures'] = counts['missing'] + counts['mixed']
    model['endpoint_dir_failure_examples'] = errors
    model['endpoint_dir_segments'] = evidence
    return counts, source_files, error_counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model-in', required=True, type=Path)
    ap.add_argument('--src', required=True, type=Path)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--source-hashes', required=True, type=Path,
                    help='JSON source_commit + files {relative_path: SHA256}, derived from immutable Git blobs')
    ap.add_argument('--die-v', required=True, type=Path)
    ap.add_argument('--glue', required=True, type=Path)
    ap.add_argument('--manifest', required=True, type=Path)
    ap.add_argument('--rtl-file', action='append', default=[], type=Path,
                    help='additional explicit immutable source (for masters not listed in the case manifest)')
    ap.add_argument('--params', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args(argv)
    if a.out.resolve() == a.model_in.resolve():
        ap.error('preserve original model: --out must differ from --model-in')
    DPB.ROOT = a.src.resolve()
    # Explicitly require all supplied evidence; DPB indexing otherwise skips absent files.
    artifacts = [a.model_in, a.die_v, a.glue, a.manifest, a.params, a.source_hashes]
    hashes = {str(p.resolve()): digest(p) for p in artifacts}
    files, defines, _ = DPB.load_manifest(a.manifest)
    paths = [a.glue.resolve()] + [Path(f) if Path(f).is_absolute() else DPB.ROOT / f for f in files] + [p.resolve() for p in a.rtl_file]
    expected = json.loads(a.source_hashes.read_text())
    if expected['source_commit'] != a.source_commit:
        raise ValueError('source commit disagrees with expected Git-blob manifest')
    for p in paths + [a.manifest.resolve()]:
        actual_hash = digest(p)
        if p.resolve() == a.glue.resolve():
            continue  # generated case artifact, separately bound by exact bytes
        rel = str(p.resolve().relative_to(DPB.ROOT))
        if expected['files'].get(rel) != actual_hash:
            raise ValueError(f'source file differs from immutable Git-blob manifest: {rel}')
    defs = {d.partition('=')[0]: d.partition('=')[2] for d in defines}
    # Only explicit source/manifest files: never silently search a live/default source tree.
    idx, amb = DPB.rtl_index([], paths, defs, paths)
    with gzip.open(a.model_in, 'rt') as f:
        model = json.load(f)
    before = invariants(model)
    counts, used, error_counts = repair(model, a.die_v, idx, amb, json.loads(a.params.read_text()).get('masters', {}))
    assert invariants(model) == before, 'geometry/topology/anchors changed'
    rec = dict(schema='opentallas.budgets.source_directions.v1', source_commit=a.source_commit,
               scope='Exact supplied old case; source RTL directions only. No real-view/native/physical qualification.',
               artifact_sha256=hashes, source_sha256={str(p): digest(p) for p in sorted(set(map(str, paths)))},
               used_source_files=sorted(used), defines=defs,
               parser_sha256=digest(DPB.__file__), repair_tool_sha256=digest(__file__),
               invariant_sha256=before, counts=dict(counts), source_error_counts=dict(error_counts),
               status='INCOMPLETE' if counts['missing'] or counts['mixed'] or counts['source_errors'] else 'SOURCE_DIRECTIONS_RESOLVED',
               mixed_policy='Mixed bundles retain mixed, with exact bit ranges in endpoint_dir_segments (bus-index:endpoint-index); never coerced to in/out; scalar-direction gate stays INCOMPLETE. Explicit p[lo:hi]@offset subsets retain only their source-connected ranges; unused bus bits are not invented.')
    model['direction_repair'] = rec
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.out, 'wt') as f:
        json.dump(model, f, separators=(',', ':'))
    receipt = a.out.with_suffix('.receipt.json')
    receipt.write_text(json.dumps(rec | {'output_sha256': digest(a.out)}, indent=2) + '\n')
    print(json.dumps(dict(status=rec['status'], counts=dict(counts), invariant_sha256=before)))
    return int(bool(counts['missing'] or counts['mixed'] or counts['source_errors']))


if __name__ == '__main__':
    raise SystemExit(main())
