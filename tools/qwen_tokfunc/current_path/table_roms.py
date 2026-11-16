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



def selected_identity(bound, *, require_native_slice_ids=False):
    """Resolve each actual selected STM instance; never infer from old recipe knobs."""
    names = json.loads((bound / 'bind_names.json').read_text())
    sources = json.loads((bound / 'asbuilt_sources.json').read_text())
    top = bound / 'rtl/qwen_compute_bound_top.sv'
    text = top.read_text()
    rows = []
    pins = {str(top): hashlib.sha256(top.read_bytes()).hexdigest()}
    for actual, logical in sorted(names.items()):
        m = re.fullmatch(r'dvs_([WE])(\d)\.u_core\.u_sub\.u_stm', logical)
        if not m:
            continue
        sid = 5-int(m[2]) if m[1]=='W' else 6+int(m[2])
        root, child = actual.split('.')
        decl = re.findall(r'^\s*(\w+)\s+'+re.escape(root)+r'\s*\(', text, re.M)
        if len(decl)!=1:
            raise ValueError(f'cannot resolve selected STM partition {actual}')
        wrapper = bound/'rtl'/f'{decl[0]}.sv'
        wtext = wrapper.read_text()
        pins[str(wrapper)] = hashlib.sha256(wrapper.read_bytes()).hexdigest()
        matches = re.findall(r'^\s*(qfd_dv_s6_stm\w*)\s*(?:#\((.*?)\)\s*)?'+re.escape(child)+r'\s*\(', wtext, re.M|re.S)
        if len(matches)!=1:
            raise ValueError(f'cannot resolve selected STM core {actual}')
        master, parameters = matches[0]
        override = re.findall(r'\.TSLICE\(\s*(\d+)\s*\)', parameters)
        if len(override)>1:
            raise ValueError('ambiguous selected TSLICE')
        default_source = None
        if override:
            numeric = int(override[0])
        else:
            defaults = []
            for source in sources['lib']+sources['full']:
                if not source.endswith('qfd_dv_s6_leaves.sv'):
                    continue
                sp = Path(source); st = sp.read_text()
                block = re.search(r'module\s+'+re.escape(master)+r'\s*#\((.*?)\)\s*\(', st, re.S)
                if block:
                    d = re.findall(r'parameter\s+integer\s+TSLICE\s*=\s*(\d+)', block[1])
                    if len(d)==1:
                        defaults.append(int(d[0])); default_source=str(sp)
                        pins[str(sp)] = hashlib.sha256(sp.read_bytes()).hexdigest()
            if len(defaults)!=1:
                raise ValueError(f'unresolved source-selected TSLICE default {master}')
            numeric=defaults[0]
        if numeric not in range(12):
            raise ValueError('source-selected TSLICE outside production shape')
        rows.append(dict(slice=sid, actual=actual, logical=logical, partition_master=decl[0],
                         core_master=master, numeric_TSLICE=numeric, native_identity_matches=numeric==sid,
                         required_mask_prefix=f'table_s{sid}_m', default_source=default_source))
    if sorted(r['slice'] for r in rows)!=list(range(12)):
        raise ValueError('selected source must contain all12 distinct slice loaders')
    native_ok=all(r['native_identity_matches'] for r in rows)
    if require_native_slice_ids and not native_ok:
        raise ValueError('release mask identity rejected: source-selected TSLICE does not match physical slice')
    return dict(schema='opentallas.qc-selected-table-identity.v1',
                status='NATIVE_IDENTITIES_MATCH' if native_ok else 'NATIVE_IDENTITY_BLOCKED_REQUIRES_SCOPE_OVERLAY',
                native_release_identity_valid=native_ok, source_sha256=pins, loaders=rows,
                simulation_scope_overlay_required=not native_ok,
                scope='Selected source identity only; per-scope overlay can qualify simulation filename selection, never a physical mask assignment.')



def physical_assignment(identity, images):
    """Personalize mask content per actual macro instance; numeric TSLICE stays fixed."""
    expected={f'table_s{s}_m{k}.viamap.hex' for s in range(12) for k in range(4)}
    if set(images)!=expected:
        raise ValueError('physical mask assignment requires exactly48 pinned images')
    assignment={}
    for row in identity['loaders']:
        for k in range(4):
            name=f'table_s{row["slice"]}_m{k}.viamap.hex'
            assignment[f'{row["actual"]}.u_tload.u_ld.m{k}']=dict(slice=row['slice'],lane=k,file=name,sha256=images[name])
    validate_assignment(identity, assignment, images)
    return dict(schema='opentallas.qc-physical-table-mask-assignment.v1',
                status='SOURCE_MAPPING_ONLY_NOT_INSTALLED', assignments=assignment,
                numeric_TSLICE_changed=False, added_cycles=0,
                source_identity_sha256=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
                scope='Physical macro-instance personalization proposal; independent of simulation filename selection and not an installed mask set.')


def validate_assignment(identity, assignment, images):
    expected={f'{row["actual"]}.u_tload.u_ld.m{k}':(row['slice'],k)
              for row in identity['loaders'] for k in range(4)}
    if set(assignment)!=set(expected) or len(expected)!=48:
        raise ValueError('actual physical macro instance coverage differs')
    for actual,(sid,lane) in expected.items():
        r=assignment[actual];name=f'table_s{sid}_m{lane}.viamap.hex'
        if (r['slice'],r['lane'],r['file'],r['sha256'])!=(sid,lane,name,images[name]):
            raise ValueError(f'source-selected physical mask identity mismatch {actual}')
    if len({r['file']for r in assignment.values()})!=48:
        raise ValueError('physical mask assignment aliases slices')


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
    p.add_argument('--mask-receipt', type=Path, help='pin actual per-slice image hashes; rejects swapped or stale masks')
    p.add_argument('--require-native-slice-ids', action='store_true', help='reject repeated/default TSLICE for physical release identity')
    a = p.parse_args()
    identity = selected_identity(a.bound, require_native_slice_ids=a.require_native_slice_ids)
    mapping = bindings(a.bound, a.rom_top or ['tb_qcdie.u_qc', 'tb_kvslice.u_qc'])
    expected = {f'table_s{s}_m{k}.viamap.hex' for s in range(12) for k in range(4)}
    if set(mapping.values()) != expected:
        raise ValueError('physical file set is not exactly twelve four-macro slices')
    expected_hashes = None
    if a.mask_receipt:
        expected_hashes=json.loads(a.mask_receipt.read_text())['images']
        if set(expected_hashes)!=expected:
            raise ValueError('mask receipt must pin exactly48 production slice files')
    images = {}
    for name in sorted(expected):
        path = a.masks / name
        data = path.read_bytes()
        if len(data.splitlines()) != 512 or any(len(row)!=532 or re.fullmatch(rb'[0-9a-fA-F]+',row) is None for row in data.splitlines()):
            raise ValueError(f'{name}: expected512physical rows')
        images[name] = hashlib.sha256(data).hexdigest()
        if expected_hashes is not None and images[name]!=expected_hashes[name]:
            raise ValueError(f'{name}: source-selected mask identity mismatch')
    a.out.mkdir(parents=True, exist_ok=False)
    output = a.out / 'sim_ot_rom_4096x266_table.v'
    output.write_text(namespace(a.model, mapping))
    report = dict(schema='opentallas.qc-table-simulation-binding.v1',
                  source=str(a.model), source_sha256=hashlib.sha256(a.model.read_bytes()).hexdigest(),
                  overlay=str(output), overlay_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  bound=str(a.bound), scopes=mapping, images=images,
                  mask_receipt_sha256=hashlib.sha256(a.mask_receipt.read_bytes()).hexdigest() if a.mask_receipt else None,
                  runtime_plusarg=f'OT_QC_TABLE_ROM_DIR={a.masks}',
                  numeric_SLICE_unchanged=True, added_cycles=0, selected_source_identity=identity,
                  native_release_identity_valid=identity['native_release_identity_valid'],
                  loader_btab_bases=[0,272,344,416],
                  qualified_loader_profiles=[dict(CAPTURE_STAGE=0,LOCAL_CTRL=0,WE_COPIES=34,hierarchical=True),dict(CAPTURE_STAGE=1,LOCAL_CTRL=1,WE_COPIES=67,hierarchical=False)],
                  physical_capture_join_match='Current no-S6_SIM inlined reference0/0; archived ns4 is1/1 but not attached by current plan. Check any new selected physical profile separately.',
                  scope='Simulation file identity only; source programme/native execution/physical closure remain separate.')
    (a.out/'binding.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(scopes=len(mapping), physical_files=len(images), runtime_plusarg=report['runtime_plusarg'])))


if __name__ == '__main__':
    main()
