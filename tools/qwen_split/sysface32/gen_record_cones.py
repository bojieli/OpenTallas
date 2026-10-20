"""Group private, single-consumer record cones without crossing shared nodes.

Each selected cone has one FF data sink, unique kept hierarchy, and exact
Boolean equations from the existing generic source. Shared-driver boundaries,
all registers, clock/reset pins and original default files remain unchanged.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


def generate(repo, minimum=20, parent=False, copy_control=False):
    repo = Path(repo)
    rtl = repo / 'rtl/qwen_split'
    original = rtl / ('qfd_sys_face_n32_bounded.sv' if parent else 'qfd_sys_face_record_port_n32.sv')
    prefix = 'qfd_bmath_' if parent else 'qfd_record32_'
    source = original.read_text()
    cells, drivers, fanout = {}, {}, collections.Counter()
    pattern = r'^(\(\* keep=1, keep_hierarchy="yes" \*\) ' + re.escape(prefix) + r'(\w+) #\(\.ID\(0\)\) (u_\d+)\((.*?)\);)$'
    for match in re.finditer(pattern, source, re.M):
        line, kind, name, body = match.groups()
        pins = dict(re.findall(r'\.(\w+)\(([^()]*)\)', body))
        out = 'Q' if 'dff' in kind else 'Y'
        cells[name] = kind, pins, line
        assert pins[out] not in drivers
        drivers[pins[out]] = name
        fanout.update(net for pin, net in pins.items() if pin != out)
    for line in source.splitlines():
        if line.startswith('assign '):
            fanout.update(re.findall(r'\bn_\d+\b', line))
        elif line.endswith(');') and re.fullmatch(pattern, line) is None:
            # Preserve every connection to a child/macro/non-numbered helper
            # as an opaque boundary. Counting outputs too is conservative.
            fanout.update(re.findall(r'\bn_\d+\b', line))

    def walk(net, selected):
        name = drivers.get(net)
        if name is None:
            return
        kind, pins, _ = cells[name]
        if 'dff' in kind or fanout[net] != 1:
            return
        assert kind in ('and', 'or', 'xor', 'not', 'mux')
        selected.add(name)
        for pin, value in pins.items():
            if pin != 'Y':
                walk(value, selected)

    groups, consumed = [], set()
    for sink, (kind, pins, _) in cells.items():
        if 'dff' not in kind:
            continue
        selected = set()
        walk(pins['D'], selected)
        if len(selected) < minimum:
            continue
        assert not (selected & consumed)
        consumed.update(selected)
        groups.append((sink, pins['D'], selected))
    modules = []
    receipt = []
    replacement = {}
    for sink, output, selected in groups:
        produced = {cells[name][1]['Y'] for name in selected}
        inputs = sorted({net for name in selected for pin, net in cells[name][1].items()
                         if pin != 'Y' and net not in produced and re.fullmatch(r'n_\d+', net)})
        name = ('qfd_parent_cone_' if parent else 'qfd_record_cone_') + sink
        lines = [f'(* keep_hierarchy="yes" *) module {name}(' + ','.join(inputs + ['Y']) + ');',
                 'input wire ' + ','.join(inputs) + ';', 'output wire Y;',
                 'wire ' + ','.join(sorted(produced)) + ';']
        for cell in sorted(selected):
            kind, pin, _ = cells[cell]
            a, b = pin.get('A'), pin.get('B')
            expr = {'and': lambda: f'{a} & {b}', 'or': lambda: f'{a} | {b}',
                    'xor': lambda: f'{a} ^ {b}', 'not': lambda: f'~{a}',
                    'mux': lambda: f"{pin['S']} ? {b} : {a}"}[kind]()
            lines.append(f"assign {pin['Y']} = {expr};")
        lines += [f'assign Y={output};', 'endmodule']
        modules.append('\n'.join(lines))
        instance = f'(* keep=1, keep_hierarchy="yes" *) {name} u_cone_{sink}(' + ','.join(
            f'.{net}({net})' for net in inputs) + f',.Y({output}));'
        root = drivers[output]
        for cell in selected:
            replacement[cells[cell][2]] = instance if cell == root else ''
        receipt.append({'sink_FF': sink, 'D': output, 'cells': len(selected),
                        'inputs': inputs, 'single_consumer_nodes': sorted(produced),
                        'hierarchy': name, 'extra_edges': 0})
    result = '\n'.join(replacement.get(line, line) for line in source.splitlines()) + '\n'
    if parent:
        result = result.replace('module qfd_sys_face_n32_bounded(', 'module qfd_sys_face_n32_opt(', 1)
        result = result.replace('qfd_sys_face_record_port_n32 ', 'qfd_sys_face_record_port_n32_opt ')
    else:
        result = result.replace('module qfd_sys_face_record_port_n32(',
                                '(* keep_hierarchy="yes" *) module qfd_sys_face_record_port_n32_opt(', 1)
        result = result.replace('qfd_record32_', 'qfd_recordgroup_')
    result += '\n'.join(modules) + '\n'
    control_copy = None
    if copy_control:
        assert parent, 'Control copy belongs only to the source-pinned parent experiment'
        expected = 'qfd_bmath_and #(.ID(0)) u_5677(.A(n_5624),.B(n_7635),.Y(n_6430));'
        assert result.count(expected) == 1
        connection = '.n_6430(n_6430)'
        assert result.count(connection) == 1
        assert 'qfd_parent_cone_u_1150 u_cone_u_1150(' in result
        result = result.replace(connection, '.n_6430(parent_control_copy)', 1)
        copy = '\nwire parent_control_copy;\n(* keep=1, keep_hierarchy="yes" *) qfd_bmath_and #(.ID(1)) u_parent_control_copy(.A(n_5624),.B(n_7635),.Y(parent_control_copy));\n'
        result = result.replace('endmodule', copy + 'endmodule', 1)
        control_copy = {'original': 'u_5677: n_5624 & n_7635 -> n_6430',
                        'private_consumer': 'u_cone_u_1150', 'extra_combinational_cells': 1,
                        'extra_FF': 0, 'extra_edges': 0,
                        'reason': 'Actual attempt10 has one 33-load output. Actual native inputs have 7/6 loads before this added same-function AND input pair; no threshold waiver.'}
    seq_pattern = r'\b' + prefix + r's?dff_'
    original_seq = [line for line in source.splitlines() if 'module ' not in line and re.search(seq_pattern, line)]
    new_seq = [line.replace('qfd_recordgroup_', 'qfd_record32_') for line in result.splitlines()
               if 'module ' not in line and re.search(seq_pattern, line.replace('qfd_recordgroup_', 'qfd_record32_'))]
    assert original_seq == new_seq
    destination = rtl / ('qfd_sys_face_n32_opt.sv' if parent else 'qfd_sys_face_record_port_n32_opt.sv')
    destination.write_text(result)
    if not parent:
        top = (rtl / 'qfd_sys_face_n32_bounded.sv').read_text()
        top = top.replace('module qfd_sys_face_n32_bounded(', 'module qfd_sys_face_n32_opt(', 1)
        top = top.replace('qfd_sys_face_record_port_n32 ', 'qfd_sys_face_record_port_n32_opt ')
        (rtl / 'qfd_sys_face_n32_opt.sv').write_text(top)
    out = repo / 'results/arch/qw_sysface5_0720'
    report = {'schema': 'opentallas.sysface_record_cones.v1', 'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
              'output_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'groups': receipt,
              'all_FF_instance_lines_preserved': len(new_seq), 'physical_qualification': False,
              'source_bound_control_copy': control_copy,
              'scope': 'Opt-in source experiment only. Every grouped internal node had one actual generic consumer; no shared-driver boundary or FF was absorbed. Actual native census/depth and protocol remain mandatory.'}
    (out / ('parent_cone_model.json' if parent else 'cone_model.json')).write_text(json.dumps(report, indent=2) + '\n')
    print('PRIVATE_CONES', len(groups), 'CELLS', len(consumed), 'FF_UNCHANGED', len(new_seq))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--minimum', type=int, default=20)
    parser.add_argument('--parent', action='store_true')
    parser.add_argument('--copy-control', action='store_true')
    args = parser.parse_args()
    generate(args.repo, args.minimum, args.parent, args.copy_control)
