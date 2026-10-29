#!/usr/bin/env python3
"""Extract exact logical source interfaces for the bound-die compiler adapter.

Run on the canonical bind's Yosys JSON, with its actual manifest and emitted
bound top. Only requested logical units' port nets and their real endpoints are
exported. This file does not infer legacy aliases, route ages, or unit latency.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import bind_elab as E


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def native_control_units(rtl_dir):
    """Read exact atomic source paths from the binder's emitted instances.

    Slice wrappers have changed hierarchy across plan revisions. Do not guess
    u_lp/u_sl (or any future wrapper): the binder records the original path
    immediately above each emitted instance, and extract() checks that path
    against the actual elaborated source before publishing an inventory.
    """
    paths = set()
    for path in sorted(Path(rtl_dir).glob('*.sv')):
        paths.update(re.findall(r'^\s*// as-built (\S+)\s*$', path.read_text(), re.M))
    slices = [f'u_s_{col}{tier}' for col in range(8) for tier in ('S', 'N')]
    units = ['u_seqhost', 'u_bk_sel']
    for sl in slices:
        units.append(sl)
        for atom in ('u_xg', 'u_xr'):
            matches = sorted(p for p in paths if p.startswith(sl + '.') and p.endswith('.' + atom))
            if len(matches) != 1:
                raise ValueError(f'{sl}: emitted source needs one exact {atom}, found {matches}')
            units.append(matches[0])
    return units


def native_vp_units(yjs, manifest):
    """Find dissolved VP parents in source, including reused partition copies.

    An emitted type shows only its representative's source comments. The
    original elaboration supplies every actual parent, so repeated copies must
    be discovered here rather than synthesizing names for missing comments.
    """
    ab = manifest.get('asbuilt', manifest)
    mods = yjs['modules']
    names = {m.get('attributes', {}).get('hdlname', name): name for name, m in mods.items()}
    rules = [(re.compile(r['inst']), r['module']) for r in ab.get('substitute_parent', [])]
    found = []

    def walk(module, path):
        meta = mods[module]
        if meta.get('attributes', {}).get('hdlname', module) == 'ot_s81sl_vp':
            found.append(path)
            return
        for name, cell in meta.get('cells', {}).items():
            child_path = f'{path}.{name}' if path else name
            if not path and not re.fullmatch(r'u_s_[0-7][NS]', name):
                continue
            child = cell['type']
            variant = next((v for rx, v in rules if rx.fullmatch(child_path)), None)
            if variant:
                if variant not in names:
                    raise ValueError('unelaborated selected parent '+variant)
                child = names[variant]
            if child in mods and 'blackbox' not in mods[child].get('attributes', {}):
                walk(child, child_path)

    walk(ab['top'], '')
    for col in range(8):
        for tier in ('S', 'N'):
            sl = f'u_s_{col}{tier}'
            vps = [p for p in found if p.startswith(sl+'.')]
            if len(vps) != 5:
                raise ValueError(f'{sl}: actual source needs five VP parents, found {vps}')
    return sorted(found)


def extract(yjs, manifest, units, *, asbuilt_sha256, top_sha256, native_entry=False):
    ab = manifest.get('asbuilt', manifest)
    if native_entry:
        units = units + native_vp_units(yjs, manifest)
    if not units or len(set(units)) != len(units):
        raise ValueError('request a nonempty, unique list of exact logical instance paths')
    top = ab['top']
    F = E.flatten(yjs, top, ab.get('substitute_parent', ()), retain_hierarchy_ports=units)
    selected = dict(F.instances)
    wanted = set(units)
    # A logical unit can itself be a leaf, rather than a dissolved parent.
    for c in F.cells:
        if c.path in wanted and c.path not in selected:
            defaults = yjs['modules'].get(c.ytype, {}).get('parameter_default_values', {})
            params = {k: E._pval(v)[0] for k, v in defaults.items()}
            params.update(c.params)
            selected[c.path] = dict(master=c.module, params=params,
                ports={pn: dict(dir=c.dirs.get(pn, 'unknown'), bits=bits)
                       for pn, bits in c.ports.items()})
    missing = wanted - selected.keys()
    if missing:
        raise ValueError('logical instances absent from actual source: ' + ','.join(sorted(missing)))
    nets = {b for r in selected.values() for p in r['ports'].values() for b in p['bits'] if isinstance(b, int)}
    drivers, inputs, interfaces = defaultdict(list), defaultdict(list), {}
    for c in F.cells:
        touched = False
        for pn, bits in c.ports.items():
            direction = c.dirs.get(pn)
            for i, b in enumerate(bits):
                if b not in nets:
                    continue
                touched = True
                endpoint = f'{c.path}.{pn}[{i}]'
                if direction in ('output', 'inout'):
                    drivers[str(b)].append(endpoint)
                if direction in ('input', 'inout'):
                    inputs[str(b)].append(endpoint)
                if direction not in ('input', 'output', 'inout'):
                    raise ValueError(f'actual endpoint {endpoint} lacks a direction')
        if touched:
            interfaces[c.path] = dict(module=c.module, kind=c.kind,
                ports={pn: dict(dir=c.dirs.get(pn, 'unknown'), width=len(bits)) for pn, bits in c.ports.items()})
    for pn, (direction, bits) in F.top_ports.items():
        for i, b in enumerate(bits):
            if b not in nets:
                continue
            endpoint = f'$top.{pn}[{i}]'
            if direction in ('input', 'inout'):
                drivers[str(b)].append(endpoint)
            if direction in ('output', 'inout'):
                inputs[str(b)].append(endpoint)
    return dict(schema='opentallas.s81.bound_inventory.v1', source_top=top,
        source_asbuilt_sha256=asbuilt_sha256, source_top_sha256=top_sha256,
        units={u: selected[u] for u in units},
        drivers={k: sorted(v) for k, v in drivers.items()},
        input_pins={k: sorted(v) for k, v in inputs.items()}, leaf_interfaces=interfaces,
        constant_drivers={str(k): dict(value=v[0], source=v[1]) for k, v in F.const_drivers.items() if k in nets},
        source_variants=dict(parent_applied=F.parent_variants,
            leaf_rules=ab.get('substitute_inst', []), leaf_rules_applied=False,
            note='Leaf source variants must be projected explicitly by the adapter; no alias or ABI narrowing is inferred'),
        qualification='Exact source inventory only; transport and internal latency require their own current views')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--asbuilt', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--bound-top', type=Path, required=True)
    ap.add_argument('--unit', action='append', default=[], help='exact logical source instance; repeat as needed')
    ap.add_argument('--units-json', type=Path, help='JSON list of additional exact source instances')
    ap.add_argument('--native-control-units', action='store_true',
                    help='derive seqhost, selector, slices and their exact atomic xg/xr paths from emitted RTL')
    ap.add_argument('--native-entry-units', action='store_true',
                    help='also retain the five exact VP source parents per slice for entry transport')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    units = a.unit + (json.loads(a.units_json.read_text()) if a.units_json else [])
    if a.native_control_units or a.native_entry_units:
        if units:
            ap.error('--native-control-units cannot be combined with explicit units')
        units = native_control_units(a.bound_top.parent)
    ab_hash, top_hash = digest(a.asbuilt), digest(a.bound_top)
    yjs = json.loads(a.asbuilt.read_text())
    manifest = json.loads(a.manifest.read_text())
    rec = extract(yjs, manifest, units, asbuilt_sha256=ab_hash, top_sha256=top_hash,
                  native_entry=a.native_entry_units)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    partial = a.out.with_name(a.out.name + f'.partial.{os.getpid()}')
    with partial.open('x') as f:
        json.dump(rec, f, separators=(',', ':'))
        f.write('\n')
    os.link(partial, a.out)  # publish a complete artifact atomically; never replace an older result
    partial.unlink()
    print(json.dumps(dict(out=str(a.out), units=len(rec['units']), source_nets=len(set(rec['drivers'])|set(rec['input_pins'])),
                          leaf_interfaces=len(rec['leaf_interfaces']), source_top_sha256=top_hash)))


if __name__ == '__main__':
    main()
