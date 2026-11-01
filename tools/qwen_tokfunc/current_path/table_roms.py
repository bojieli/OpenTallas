#!/usr/bin/env python3
"""Bind each actual QC loader to its physical mask files in simulation.

The current bound loaders share numeric SLICE=0. Nested defparams through
shared parent specializations collapse in Verilator5.050. A simulation-only
ROM initializer instead uses each actual instance scope. The cell read path,
loader state, numeric selectors and physical RTL stay unchanged.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def bindings(bound, rom_tops):
    names = json.loads((bound / 'bind_names.json').read_text())
    found = {}
    for actual, logical in names.items():
        m = re.fullmatch(r'dvs_([WE])(\d)\.u_core\.u_sub\.u_stm', logical)
        if not m:
            continue
        side, number = m[1], int(m[2])
        if number not in range(6):
            raise ValueError(f'unknown physical slice identity: {logical}')
        sid = 5 - number if side == 'W' else 6 + number
        if sid in found:
            raise ValueError(f'duplicate table loader for slice {sid}')
        found[sid] = actual
    if set(found) != set(range(12)):
        raise ValueError(f'actual table loader map incomplete: {sorted(found)}')
    result = {}
    for sid, actual in sorted(found.items()):
        for top in rom_tops:
            for lane in range(4):
                result[f'{top}.{actual}.u_tload.u_ld.m{lane}'] = f'table_s{sid}_m{lane}.viamap.hex'
    return result


def namespace(source, scope_to_file):
    """Change only the existing macro initialization filename selection."""
    text = source.read_text()
    if 'OT_QC_TABLE_ROM_DIR' in text:
        raise ValueError('source already has a table namespace')
    declaration = '    integer init_i;'
    hook = '        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir) && INSTANCE != "")'
    code_hook = '        if ($value$plusargs("OT_QC_CODE_ROM_DIR=%s", rom_dir)'
    if text.count(declaration) != 1:
        raise ValueError('macro initialization declaration changed')
    cases = []
    for scope, name in sorted(scope_to_file.items()):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.$]*', scope):
            raise ValueError(f'unsupported simulation scope {scope!r}')
        if not re.fullmatch(r'table_s(?:[0-9]|1[01])_m[0-3]\.viamap\.hex', name):
            raise ValueError(f'invalid physical table basename {name!r}')
        cases.append(f'                "{scope}": table_file="{name}";')
    new = '''        if ($value$plusargs("OT_QC_TABLE_ROM_DIR=%s", table_dir) && INSTANCE.len() >= 7 && INSTANCE.substr(0,6) == "table_s") begin
            table_scope=$sformatf("%m");
            case(table_scope)
CASES
                default: $fatal(1,"Unmapped QC table mask path %s",table_scope);
            endcase
            $readmemh({table_dir,"/",table_file},arr);
        end else if'''.replace('CASES', '\n'.join(cases))
    if code_hook in text:
        if text.count(code_hook) != 1:
            raise ValueError('ambiguous existing QC code namespace')
        text = text.replace(code_hook, new + code_hook[len('        if'):], 1)
    else:
        if text.count(hook) != 1:
            raise ValueError('macro initializer hook changed')
        following = ''' ($value$plusargs("OT_QC_CODE_ROM_DIR=%s", rom_dir) && INSTANCE.len() >= 6 && INSTANCE.substr(0,5) == "qtile_")
            $readmemh({rom_dir, "/", INSTANCE, ".viamap.hex"}, arr);
        else if ($value$plusargs("OT_ROM_DIR=%s", rom_dir) && INSTANCE != "")'''
        text = text.replace(hook, new + following, 1)
    return text.replace(declaration, '    string table_dir, table_file, table_scope;\n' + declaration, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bound', type=Path, required=True)
    p.add_argument('--masks', type=Path, required=True)
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rom-top', action='append', default=[])
    a = p.parse_args()
    mapping = bindings(a.bound, a.rom_top or ['tb_qcdie.u_qc', 'tb_kvslice.u_qc'])
    expected = {f'table_s{s}_m{k}.viamap.hex' for s in range(12) for k in range(4)}
    if set(mapping.values()) != expected:
        raise ValueError('physical file set is not exactly twelve four-macro slices')
    images = {}
    for name in sorted(expected):
        path = a.masks / name
        data = path.read_bytes()
        if len(data.splitlines()) != 512:
            raise ValueError(f'{name}: expected512physical rows')
        images[name] = hashlib.sha256(data).hexdigest()
    a.out.mkdir(parents=True, exist_ok=False)
    output = a.out / 'sim_ot_rom_4096x266_table.v'
    output.write_text(namespace(a.model, mapping))
    report = dict(schema='opentallas.qc-table-simulation-binding.v1',
                  source=str(a.model), source_sha256=hashlib.sha256(a.model.read_bytes()).hexdigest(),
                  overlay=str(output), overlay_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  bound=str(a.bound), scopes=mapping, images=images,
                  runtime_plusarg=f'OT_QC_TABLE_ROM_DIR={a.masks}',
                  numeric_SLICE_unchanged=True, added_cycles=0,
                  loader_btab_bases=[0,272,344,416],
                  physical_capture_join_match='OPEN: physical ELAB blackboxes STM; reference sim requires OT_S6_SIM',
                  scope='Simulation file identity only; source programme/native execution/physical closure remain separate.')
    (a.out/'binding.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(scopes=len(mapping), physical_files=len(images), runtime_plusarg=report['runtime_plusarg'])))


if __name__ == '__main__':
    main()
