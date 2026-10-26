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


def clock_slices(core, root, ports):
    """Verify the old q2 plan's packed clock layout against native assembly."""
    layouts = {
        'reduce': ('clk_reduce', {'reduce_clk_control': (0, 0),
                                 'reduce_clk_state': (16, 1), 'reduce_clk_add': (32, 17)}),
        'ring_ag': ('clk_ring', {'ring_clk': (0, 0),
                              'ring_clk_state': (8, 1), 'ring_clk_add': (16, 9)}),
    }
    if core not in layouts:
        raise SystemExit('unsupported packed clock map')
    bus, layout = layouts[core]
    source = root / 'rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hbm_q3_producer_native.sv'
    text = source.read_text()
    widths = {n: w for n, d, w in ports}
    for name, (hi, lo) in layout.items():
        exprs = re.findall(r'(?m)^\s*\.' + name + r'\(([^\n]+)\),?\s*$', text)
        expected = list(range(hi, lo - 1, -1))
        if (len(exprs) != 1 or widths.get(name) != len(expected) or
                re.findall(r'([A-Za-z_]\w*)\[\d+\]', exprs[0]) != [bus] * len(expected) or
                [int(i) for i in re.findall(r'\[(\d+)\]', exprs[0])] != expected):
            raise SystemExit(f'packed clock layout differs from native source: {name}')
    return bus, layout, dict(source=str(source), sha256=sha(source), slices=layout)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--api-root', type=Path, required=True)
    ap.add_argument('--profile-dir', type=Path, required=True)
    ap.add_argument('--views', type=Path, required=True)
    ap.add_argument('--common-clock-dir', type=Path,
                    help='qualified one-clock adapter cohort; requires matching plan pins')
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
        native_clocks = list(profile['clock_ports'])
        if a.common_clock_dir:
            adapt = load('q3_face_oneclk', root / 'tools/hbm_b2/q3sync/q3_common_clock.py')
            recipe, staged, profile = adapt.adapt_recipe(
                core, recipe, staged, profile, a.common_clock_dir)
            if core in ('reduce', 'ring_ag') and module != canonical:
                recipe, profile = kit.canonical_oneclk_map(
                    core, recipe, profile, native_clocks, root)
        pins_path = a.views.parent / v['pins_file']
        if sha(pins_path) != v['pins_sha256']:
            raise SystemExit(f'{core}: plan pin hash changed')
        pb = gen.buses_of([p['name'] for p in json.loads(pins_path.read_text())])
        ports = [tuple(p) for p in profile['port_inventory']['ports']]
        widths = {n: pb[n][0] for n in sorted(pb)}
        scalars = {n for n, (w, scalar) in pb.items() if scalar}
        cmap, straps, ties = None, {}, {}
        if recipe.get('canonical_pin_map'):
            cmap = recipe['canonical_pin_map']
        elif v.get('canonical_type'):
            ct = json.loads((gen.HARDEN / 'canonical_ports_split.json').read_text())['types'][v['canonical_type']]
            tids = [t for t in ct['type_ids'] if re.sub(r'__[\d.]+x[\d.]+$', '', t) == module]
            if len(tids) != 1:
                raise SystemExit(f'{core}: ambiguous canonical mapping')
            ti = ct['type_ids'][tids[0]]
            cmap, straps = ti['cut_pins'], ti.get('straps') or {}
            ties = dict(k.split('=', 1) for k in (ti.get('tied_at_parent') or {}))
        if a.common_clock_dir:
            if set(profile['clock_ports']) != {'clk'} or 'clk' not in pb:
                raise SystemExit(f'{core}: one-clock adapter requires the plan scalar clk pin')
            for old in native_clocks:
                if old != 'clk' and old in pb:
                    raise SystemExit(f'{core}: stale physical clock pin {old}')
            if pb['clk'] != (1, True):
                raise SystemExit(f'{core}: physical clk must be scalar')
        wrapper_pb, wrapper_cmap, packed = pb, cmap, None
        clock_proof = None
        if cmap and any(len(mp) != 1 for mp in cmap.values()):
            bus, layout, clock_proof = clock_slices(core, root, ports)
            if (pb[bus][0] != sum(hi-lo+1 for hi, lo in layout.values()) or
                    cmap[bus] != {n: hi-lo+1 for n, (hi, lo) in layout.items()} or
                    any(len(mp) != 1 for n, mp in cmap.items() if n != bus)):
                raise SystemExit(f'{core}: ambiguous mapping outside qualified packed clock')
            wrapper_pb, wrapper_cmap = dict(pb), dict(cmap)
            del wrapper_pb[bus]
            del wrapper_cmap[bus]
            for n, (hi, lo) in layout.items():
                wrapper_pb[n] = (hi - lo + 1, hi == lo)
                wrapper_cmap[n] = {n: hi - lo + 1}
            packed = (bus, layout)
        wrapper, mapping = gen.build_wrapper(module + '__fcore', wrapper_pb, recipe['profile_top'], {},
                                             ports, cmap=wrapper_cmap, straps=straps, ties=ties)
        if packed:
            bus, layout = packed
            declarations = []
            for line in wrapper.splitlines():
                if any(re.fullmatch(r'\s*input wire (?:\[\d+:0\] )?' + n + ',?', line) for n in layout):
                    continue
                declarations.append(line)
            wrapper = '\n'.join(declarations) + '\n'
            wrapper = wrapper.replace('module ' + module + '__fcore (\n',
                'module ' + module + '__fcore (\n    input wire [' + str(pb[bus][0]-1) + ':0] ' + bus + ',\n')
            for n, (hi, lo) in layout.items():
                expr = f'{bus}[{hi}]' if hi == lo else f'{bus}[{hi}:{lo}]'
                wrapper = wrapper.replace(f'.{n}({n})', f'.{n}({expr})')
        if mapping['open_outputs']:
            raise SystemExit(f'{core}: unmatched outputs {mapping["open_outputs"]}')
        top_dirs = {n: d for n, d, w in ports}
        dirs, passthru = {}, set()
        native_bypass = set(profile['clock_ports'] + profile['reset_ports'])
        clocks = []
        for n in widths:
            if packed and n == packed[0]:
                dirs[n] = 'input'
                passthru.add(n)
                clocks.append(n)
                continue
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
        if a.common_clock_dir:
            adapter = staged[next(p for p in staged if p.startswith('tools/hbm_b2/q3sync/oneclk/'))]
            (a.out / adapter.name).write_bytes(adapter.read_bytes())
        receipts[core] = dict(module=module, profile=profile, view=v, mapping=mapping,
                              widths=widths, dirs=dirs, scalars=sorted(scalars),
                              passthrough=sorted(passthru), clock=clock,
                              latency=dict(in_cycles=1, out_cycles=1),
                              packed_clock_proof=clock_proof,
                              source_status='EMITTED_UNQUALIFIED_NO_TIMING_CREDIT')
    receipt = dict(status='EMITTED_UNQUALIFIED', cores=receipts,
                   api_hashes={n: sha(api / n) for n in ['gen_core_kit_hbm.py', 'face_shell.py']},
                   files={p.name: sha(p) for p in a.out.glob('*.sv')})
    (a.out / 'face_sources.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('EMITTED_UNQUALIFIED', ','.join(receipts))


if __name__ == '__main__':
    main()
