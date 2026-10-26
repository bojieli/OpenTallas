#!/usr/bin/env python3
"""Emit physical face RTL from qualified literal ports and exact plan pins.

No synthesis, def-use analysis, dropped pins, P&R, or qualification is implied.
The existing coregen mapping and face-shell emitter remain authoritative.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--api-root', type=Path, required=True)
    ap.add_argument('--profile-dir', type=Path, required=True)
    ap.add_argument('--views', type=Path, required=True)
    ap.add_argument('--core', action='append', required=True,
                    choices=['body', 'edge', 'vm', 'reduce', 'ring_ag'])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        ap.error('output already exists; preserve previous attempts')
    root = a.api_root.resolve()
    api = root / 'physical/die_plan/hbm_arch_cores'
    sys.path[:0] = [str(api), str(root / 'tools/die_plan')]
    kit = load('q3_face_kit', root / 'physical/die_plan/hbm/q3sync_kits/build_kit.py')
    gen = load('q3_face_gen', api / 'gen_core_kit_hbm.py')
    fs = load('q3_face_fs', api / 'face_shell.py')
    census = json.loads((a.profile_dir / 'census.json').read_text())
    if (census['status'] != 'PASS_GENERATED' or census['unclassified_total'] or
            census['unresolved_instantiations'] or census['modules_in_closure'] != 32):
        ap.error('profile must be the qualified complete 32-module closure')
    views = json.loads(a.views.read_text())['view_list']
    receipts = {}
    a.out.mkdir(parents=True)
    (a.out / 'ot_hbm_face_reg.sv').write_text(fs.CELL_SV)
    for core in a.core:
        recipe, staged, profile = kit.recipe_from_census(core, census, a.profile_dir, root)
        canonical = kit.TOPS[core]
        names = {canonical, 'ot_hfd_coll_q2_hard_v8g__' + core}
        candidates = [v for v in views if v['module'] in names]
        if len(candidates) != 1:
            raise SystemExit(f'{core}: need exactly one selected physical view, found {len(candidates)}')
        v = candidates[0]
        module = v['module']
        pins_path = a.views.parent / v['pins_file']
        if sha(pins_path) != v['pins_sha256']:
            raise SystemExit(f'{core}: plan pin hash changed')
        pb = gen.buses_of([p['name'] for p in json.loads(pins_path.read_text())])
        ports = [tuple(p) for p in profile['port_inventory']['ports']]
        widths = {n: pb[n][0] for n in sorted(pb)}
        scalars = {n for n, (w, scalar) in pb.items() if scalar}
        cmap, straps, ties = None, {}, {}
        if v.get('canonical_type'):
            ct = json.loads((gen.HARDEN / 'canonical_ports_split.json').read_text())['types'][v['canonical_type']]
            tids = [t for t in ct['type_ids'] if re.sub(r'__[\d.]+x[\d.]+$', '', t) == module]
            if len(tids) != 1:
                raise SystemExit(f'{core}: ambiguous canonical mapping')
            ti = ct['type_ids'][tids[0]]
            cmap, straps = ti['cut_pins'], ti.get('straps') or {}
            ties = dict(k.split('=', 1) for k in (ti.get('tied_at_parent') or {}))
        wrapper, mapping = gen.build_wrapper(module + '__fcore', pb, recipe['profile_top'], {},
                                             ports, cmap=cmap, straps=straps, ties=ties)
        if mapping['open_outputs']:
            raise SystemExit(f'{core}: unmatched outputs {mapping["open_outputs"]}')
        top_dirs = {n: d for n, d, w in ports}
        dirs, passthru = {}, set()
        native_bypass = set(profile['clock_ports'] + profile['reset_ports'])
        clocks = []
        for n in widths:
            native = next(iter(cmap[n])) if cmap else n
            dirs[n] = top_dirs[native]
            if native in native_bypass:
                passthru.add(n)
            if native in profile['clock_ports']:
                clocks.append(n)
        if not clocks:
            raise SystemExit(f'{core}: no qualified physical clock port')
        clock = sorted(clocks)[0]
        shell = fs.emit_shell(module, module + '__fcore', {}, widths, dirs, widths,
                              passthru, clock, scalars=scalars)
        (a.out / (module + '__wrap.sv')).write_text(wrapper)
        (a.out / (module + '__fshell.sv')).write_text(shell)
        receipts[core] = dict(module=module, profile=profile, view=v, mapping=mapping,
                              widths=widths, dirs=dirs, scalars=sorted(scalars),
                              passthrough=sorted(passthru), clock=clock,
                              latency=dict(in_cycles=1, out_cycles=1),
                              source_status='EMITTED_UNQUALIFIED_NO_TIMING_CREDIT')
    receipt = dict(status='EMITTED_UNQUALIFIED', cores=receipts,
                   api_hashes={n: sha(api / n) for n in ['gen_core_kit_hbm.py', 'face_shell.py']},
                   files={p.name: sha(p) for p in a.out.glob('*.sv')})
    (a.out / 'face_sources.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('EMITTED_UNQUALIFIED', ','.join(receipts))


if __name__ == '__main__':
    main()
