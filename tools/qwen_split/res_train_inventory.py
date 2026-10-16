"""Measure the adopted train24 serializer from a hierarchical mapped JSON.

This inventory proves mapped cell area and clock/reset fanout only.  It does not
qualify placement, CTS, native pin timing, routing, or the compiler producer.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re


def inventory(mapped, libraries, source, slot=(777.576, 518.376)):
    libs = {}
    for file in libraries:
        text = Path(file).read_text()
        for match in re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\).*?\barea\s*:\s*([\d.]+)', text, re.S):
            libs[match[1]] = float(match[2])
    design = json.loads(Path(mapped).read_text())
    modules = design['modules']
    top = 'qfd_res_train_static'
    params = {k: int(v, 2) for k, v in modules[top]['parameter_default_values'].items()}
    if params['BAND'] not in range(3) or params['NB'] != 3 or params['D'] != 2 or params['MAX_TRAIN'] != 8:
        raise ValueError(f'not the adopted train24 shape: {params}')
    cells, clocks, resets = collections.Counter(), collections.Counter(), collections.Counter()
    leaves = []
    ports = modules[top]['ports']
    root_names = {}
    for name, port in ports.items():
        if name in ('ck', 'ck_bank', 'rst_n'):
            for index, bit in enumerate(port['bits']):
                root_names[bit] = name if len(port['bits']) == 1 else f'{name}[{index}]'

    def capture_census(module):
        cells = module['cells']
        drivers = {}
        for name, cell in cells.items():
            output = 'QN' if cell['type'].startswith('DFF') else 'Y'
            for bit in cell['connections'][output]:
                drivers[bit] = name
        def cone(bits):
            seen, sequential, front = set(), set(), list(bits)
            while front:
                name = drivers.get(front.pop())
                if name is None or name in seen:
                    continue
                seen.add(name)
                cell = cells[name]
                if cell['type'].startswith('DFF'):
                    sequential.add(name)
                else:
                    for port, bits in cell['connections'].items():
                        if port != 'Y':
                            front.extend(bits)
            return seen-sequential, sequential
        _, output_ff = cone(module['ports']['q']['bits'])
        capture_ff = {n for n,c in cells.items() if c['type'].startswith('DFF')} - output_ff
        capture_logic, _ = cone([bit for n in capture_ff for bit in cells[n]['connections']['D']])
        if len(capture_ff) != 4392:
            raise ValueError(f'capture register census changed: {len(capture_ff)}')
        return dict(capture_ff=len(capture_ff), output_ff=len(output_ff),
                    capture_input_logic_cells=len(capture_logic),
                    capture_and_input_logic_area_um2=round(sum(libs[cells[n]['type']] for n in capture_ff|capture_logic),6))

    def walk(name, bindings, path):
        module = modules[name]
        def net(bit):
            if isinstance(bit, str):
                return bit
            return bindings.get(bit, (path, bit))
        own = collections.Counter()
        for cname, cell in module['cells'].items():
            typ = cell['type']
            if typ in modules:
                child = modules[typ]
                child_bindings = {}
                for pname, port in child['ports'].items():
                    for internal, external in zip(port['bits'], cell['connections'][pname]):
                        child_bindings[internal] = net(external)
                walk(typ, child_bindings, path + '/' + cname)
            else:
                if typ not in libs:
                    raise ValueError(f'unmapped or unknown cell {path}/{cname}: {typ}')
                cells[typ] += 1
                own[typ] += 1
                if typ.startswith('DFF'):
                    clock = net(cell['connections']['CLK'][0])
                    clocks[str(clock)] += 1
                    if 'RESETN' in cell['connections']:
                        resets[str(net(cell['connections']['RESETN'][0]))] += 1
        if 'qfd_res_train_bank' in name:
            leaves.append(dict(path=path, cell_count=sum(own.values()),
                               ff=sum(n for t, n in own.items() if t.startswith('DFF')),
                               area_um2=round(sum(libs[t]*n for t, n in own.items()), 6),
                               **capture_census(module)))

    walk(top, root_names, top)
    if len(leaves) != 24 or len(clocks) != 25:
        raise ValueError(f'expected 24 banks and 25 roots: {len(leaves)}, {clocks}')
    if set(clocks) != {'ck', *[f'ck_bank[{k}]' for k in range(24)]}:
        raise ValueError(f'non-port clock root: {clocks}')
    area = sum(libs[t]*n for t, n in cells.items())
    width, height = slot
    halo, gap, control_height, capture_height = 4.32, 4.32, 51.84, 207.36
    capture_area = sum(b['capture_and_input_logic_area_um2'] for b in leaves)
    bank_w = (width - 2*halo - 5*gap)/6
    bank_h = (height - capture_height - halo - control_height - gap - 3*gap)/4
    soft_banks = [dict(index=k, x=round(halo+(k%6)*(bank_w+gap),6),
                       y=round(control_height+gap+(k//6)*(bank_h+gap),6),
                       w=round(bank_w,6), h=round(bank_h,6)) for k in range(24)]
    if any(b['x']+b['w']>width or b['y']+b['h']>height for b in soft_banks):
        raise ValueError('bank region exceeds the parent slot')
    if max(b['area_um2']-b['capture_and_input_logic_area_um2'] for b in leaves)/.4 > bank_w*bank_h:
        raise ValueError('mapped bank does not fit the proposed 40pct soft region')
    bits = sum(len(port['bits']) for port in ports.values())
    # ck_bank is a vector in this measured core, but 24 scalar wrapper entries.
    groups = len(ports) + 23
    return dict(schema='opentallas.qwen.res-train-physical-inventory.v1', top=top,
                source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                mapped_sha256=hashlib.sha256(Path(mapped).read_bytes()).hexdigest(),
                libraries={Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in libraries},
                source_shape=dict(banks=24, band=params['BAND'], parameters=params, max_train=8, bank_declared_ff=4975,
                                  bank_unused_padding_removed=32),
                cell_count=sum(cells.values()), ff=sum(clocks.values()),
                mapped_cell_area_um2=round(area, 6), clock_sinks=dict(sorted(clocks.items())),
                reset_sinks=dict(resets), banks=leaves,
                slot_um=[width, height], slot_area_um2=round(width*height, 6),
                mapped_occupancy=area/(width*height),
                floorplan_area_at_40pct_um2=round(area/.4, 6),
                abi_bits=bits, wrapper_groups=groups,
                all_pins_one_face_at_96nm_um=round(bits*.096+groups, 6),
                available_wide_face_um=width-8,
                fits_cell_area_at_40pct=area/.4 <= width*height,
                fits_pin_capacity_on_wide_face=bits*.096+groups <= width-8,
                soft_home_proposal=dict(kind='unqualified_shallow_capture_strip_and_soft_emit_regions_in_flat_parent',
                    capture_region_um=[0,height-capture_height,width,capture_height],
                    capture_ff=sum(b['capture_ff'] for b in leaves),
                    capture_and_input_logic_area_um2=round(capture_area,6),
                    capture_region_occupancy=capture_area/(width*capture_height),
                    capture_placement='Place rq capture bits by source bit position across the wide incident face; '+
                                      'repeat 24 bank rows in the shallow strip. These are soft constraints, not measured paths.',
                    bank_grid=[6,4], halo_um=halo, gap_um=gap, banks=soft_banks,
                    controller_merge_region_um=[0,0,width,control_height],
                    worst_emit_region_mapped_occupancy=max(b['area_um2']-b['capture_and_input_logic_area_um2'] for b in leaves)/(bank_w*bank_h),
                    constraint='No hard bank obstructions: shared rq and merge routes must cross soft regions. '+
                               'A hard 24-macro grid would require a separate channel-capacity proof.',
                    required_receipts=['parent pin-registered native launch/capture',
                                       '4425-bit rq fanout and 24x551 merge GRT',
                                       '25-root CTS and 119260-load reset tree',
                                       'actual same-slot TT/FF DRC and bound join961t proof']),
                qualification='MAPPED_AREA_AND_CLOCK_CENSUS_ONLY',
                open=['Place rq capture flops by matching rq bit positions at the incident face.',
                      'Route 4425-bit rq distribution across 24 capture banks; measure native capture timing.',
                      'Place/route 24x551 merge inputs and rb face registers; measure native launch timing.',
                      'Build/reset-buffer the real reset fanout and all 25 clock trees.',
                      'Use the current die pin plan and preserve the compiler/static command contract.',
                      'TT/FF, DRC, native timing and production-shape throughput are not qualified here.'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mapped', required=True)
    p.add_argument('--libs', nargs='+', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    rec = inventory(a.mapped, a.libs, a.source)
    Path(a.out).write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps({k: v for k, v in rec.items() if k not in ('banks', 'libraries', 'open')}, indent=2))


if __name__ == '__main__':
    main()
