"""Forward the selected native ROM head hook through the real S81 hierarchy.

Compose after the existing native-result export. This emits successor sources;
it never modifies selected originals or builds a core/array.
"""
from pathlib import Path
import hashlib
import dsrom_s81_native_head_hook as hook

NAMES = ('head_up_valid', 'head_up_last', 'head_up_ready', 'head_up_data',
         'head_up_identity', 'head_dn_valid', 'head_dn_last', 'head_dn_ready',
         'head_dn_data', 'head_dn_identity', 'head_final_valid',
         'head_final_ready', 'head_final_data', 'head_final_identity')
PORTS = '''    input wire head_up_valid,head_up_last,
    output wire head_up_ready,
    input wire [511:0] head_up_data,
    input wire [46:0] head_up_identity,
    output wire head_dn_valid,head_dn_last,
    input wire head_dn_ready,
    output wire [511:0] head_dn_data,
    output wire [46:0] head_dn_identity,
    input wire head_final_valid,
    output wire head_final_ready,
    input wire [511:0] head_final_data,
    input wire [46:0] head_final_identity,
'''
FORWARD = '        ' + ','.join(f'.{n}({n})' for n in NAMES) + ',\n'
HIERARCHY = {
    'ot_chip_v41x_tile.sv': 'ot_hdc_core_v41x',
    'ot_chip_v41x_die_owner_safe_c8.sv': 'ot_chip_v41x_tile',
    'ot_v41_rt_die_l20_c8.sv': 'ot_chip_v41x_die_owner_safe_c8',
}


def one(text, old, new):
    if text.count(old) != 1:
        raise ValueError('selected native head hierarchy hook changed: ' + old)
    return text.replace(old, new, 1)


def forward(text, child):
    text = one(text, '    parameter integer S81_CAPTURE=0,',
               '    parameter integer OPT_NATIVE_HEAD=0,\n    parameter integer S81_CAPTURE=0,')
    text = one(text, '    input wire [ROM_R*19-1:0] capture_root_rows,',
               PORTS + '    input wire [ROM_R*19-1:0] capture_root_rows,')
    text = one(text, child + ' #(', child + ' #(.OPT_NATIVE_HEAD(OPT_NATIVE_HEAD),')
    return one(text, '        .capture_root_rows(capture_root_rows),',
               FORWARD + '        .capture_root_rows(capture_root_rows),')


def install(selected, output, *, enable=False):
    if type(enable) is not bool:
        raise ValueError('enable must be bool')
    if enable and (selected.get('parameters', {}).get('S81_CAPTURE') != 1 or
                   selected.get('parameters', {}).get('NATIVE_RESULT_READ') != 1):
        raise ValueError('select actual S81 capture and intaken native result export before head opt-in')
    output = Path(output).resolve()
    paths = [Path(p).resolve() for p in selected['sources']]
    originals = {p: p.read_bytes() for p in paths}
    if any(output == p.parent or output in p.parents for p in paths):
        raise ValueError('new disjoint successor directory required')
    for p, data in originals.items():
        if hashlib.sha256(data).hexdigest() != selected['source_sha256'].get(str(p)):
            raise ValueError('selected source pin changed: ' + str(p))
    by_name = {}
    for p in paths:
        if p.name in by_name:
            raise ValueError('duplicate selected source filename: ' + p.name)
        by_name[p.name] = p
    for p in (hook.CORE, hook.ADAPT):
        if originals.get(by_name.get(p.name)) != p.read_bytes():
            raise ValueError('head hook requires its actual selected parent: ' + p.name)
    top = originals[by_name['ot_v41_rt_die_l20_c8.sv']].decode()
    if 'native_result_producer_take' not in top or 'native_result_token' not in top:
        raise ValueError('compose after the actual intaken native result export')
    # Price is in the existing owner model plus model_before_wiring.json.
    # This only forwards those existing signals and adds no hardware state.
    hook.emit(output / 'native')
    replacements = {by_name[p.name]: output / 'native' / p.name
                    for p in (hook.CORE, hook.ADAPT)}
    for name, child in HIERARCHY.items():
        p = by_name[name]
        dest = output / 'native' / name
        text = forward(originals[p].decode(), child)
        if name == 'ot_v41_rt_die_l20_c8.sv':
            text = one(text, '    input wire head_up_valid,head_up_last,',
                       '    output wire native_head_selected,\n    input wire head_up_valid,head_up_last,')
            text = one(text, '\nendmodule',
                       '\n    assign native_head_selected = OPT_NATIVE_HEAD != 0;\nendmodule')
        dest.write_text(text)
        replacements[p] = dest
    if any(p.read_bytes() != data for p, data in originals.items()):
        raise ValueError('selected source changed during successor emission')
    sources = [replacements.get(p, p) for p in paths]
    root = hook.ROOT
    for rel in ('rtl/rom/collectives/ot_rom_coll_pkg.sv',
                'rtl/rom/collectives/ot_rom_coll_skid.sv',
                'rtl/dsrom_sys/s81_native_head/ot_rom_argmax_rows.sv',
                'rtl/dsrom_sys/s81_native_head/ot_dsrom_s81_head_amax.sv'):
        p = root / rel
        if p not in sources:
            sources.append(p)
    # The package must precede modules importing it in the compile list.
    pkg = root / 'rtl/rom/collectives/ot_rom_coll_pkg.sv'
    sources.remove(pkg)
    sources.insert(0, pkg)
    args = [a for a in selected.get('verilator_args', [])
            if not a.startswith('-GOPT_NATIVE_HEAD=')]
    result = dict(selected)
    result.update(sources=sources,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  parameters=dict(selected.get('parameters', {}), OPT_NATIVE_HEAD=int(enable)),
                  verilator_args=args + ['-GOPT_NATIVE_HEAD=' + str(int(enable))],
                  native_head_global_ports_bound=True,
                  trained_DOT_bound=False, physical_admission=False,
                  measured_system_result=False)
    return result
