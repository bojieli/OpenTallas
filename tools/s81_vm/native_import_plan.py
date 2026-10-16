#!/usr/bin/env python3
"""Prepare actual pin bindings for the 540-leaf A2F candidate, without adoption.

Every reused binding must match its full elaborated parameter dictionary. New
bindings are explicit below; the pending HF4 has gate geometry only. Missing
pins are fatal. Missing homes/native/clock/compiler proof remain blockers.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import child_lint as CL


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_binding(leaf, old):
    path = leaf['path']
    if path in ('dut.u_wfc.split_return.u_ret.lo', 'dut.u_wfc.split_return.u_ret.hi'):
        expected = ('dsfd_vm_wfc_return256', {'RESPONSE_PAD': 2})
        kit = 'dsfd_vm_wfc_return256_native_1016_r2'
    elif path == 'dut.u_wfc.split_return.u_ret.diag':
        expected = ('dsfd_vm_native_valid_diag', {})
        kit = 'dsfd_vm_native_valid_diag_native_0400_r2'
    elif path == 'dut.u_core.u_seq':
        expected = ('dsfd_vm_seq_tile', {'X_AL_WIDTH': 4})
        kit = 'dsfd_vm_seq_tile_hf4_native_1016_r1'
    else:
        prior = old[path]
        expected = (prior['master'], prior['parameters'])
        kit = prior['kit']
    if (leaf['master'], leaf['parameters']) != expected:
        raise ValueError('master/parameter identity mismatch: ' + path)
    return kit


def model(path, gate=False):
    if gate:
        raw = json.loads(path.read_text())
        if not isinstance(raw.get('pins'), list):
            raise ValueError('gate geometry requires actual BPin rows, not a kit face plan')
        _, _, w, h = raw['die']
        pins = collections.defaultdict(list)
        for name, *rect in raw['pins']:
            if name not in ('VDD', 'VSS'):
                pins[name.replace('\\', '')].append(rect)
        cell = raw['top']
    else:
        raw = CL.parse_lef(path.read_text())
        w, h, cell = raw['W'], raw['H'], raw['name']
        pins = {name.replace('\\', ''): pin['rects'] for name, pin in raw['pins'].items()
                if not CL.is_pg(name, pin)}
    result = {}
    for name, rects in pins.items():
        choices = [(CL.face_of(r, w, h), r) for r in rects]
        face, rect = next(((f, r) for f, r in choices if f), choices[0])
        result[name] = dict(rects=rects, anchor_layer=rect[0], anchor_face=face,
                            anchor_um=[(rect[1]+rect[3])/2, (rect[2]+rect[4])/2])
    return dict(physical_cell=cell, outline_um=[w, h], pins=result,
                source_sha256=sha(path), evidence='GATE_ONLY_ROUTE_NATIVE_PENDING' if gate
                else 'PUBLISHED_LEF_NATIVE_RECEIPT_NOT_INFERRED')


def require_pins(leaf, physical):
    mapping = {}
    for port, spec in leaf['ports'].items():
        for bit in range(spec['bits']):
            literal = f'{port}[{bit}]' if spec['bits'] > 1 else port
            actual = literal if literal in physical['pins'] else port+'[0]' if spec['bits'] == 1 else literal
            if actual not in physical['pins']:
                raise ValueError('missing actual pin: ' + leaf['path'] + '/' + literal)
            mapping[literal] = actual
    return mapping


def build(inputs, source):
    manifest = json.loads((inputs/'source_manifest.json').read_text())
    graph = json.loads((inputs/'graph_summary.json').read_text())
    if graph['hard_leaves'] != 540 or sha(inputs/'parent.xml') != graph['xml_sha256']:
        raise ValueError('graph XML/count provenance mismatch')
    for entry in manifest['files']:
        if sha(source/Path(entry['path']).name) != entry['sha256']:
            raise ValueError('source manifest drift: ' + entry['path'])
    inventory = json.loads((inputs/'inventory.json').read_text())['leaves']
    if len(inventory) != 540 or len({r['path'] for r in inventory}) != 540:
        raise ValueError('candidate requires exactly 540 distinct actual leaves')
    old = {r['path']: r for r in json.loads((inputs/'old_leaves.json').read_text())['leaves']}
    homes = json.loads((inputs/'homes.json').read_text())['placement']
    models, rows, missing_homes, changed_shapes, clocks = {}, [], [], [], []
    for leaf in inventory:
        kit = select_binding(leaf, old)
        if kit not in models:
            if kit == 'dsfd_vm_seq_tile_hf4_native_1016_r1':
                models[kit] = model(inputs/'hf4_floorplan.json', gate=True)
            else:
                files = list((inputs/'closed_lefs'/kit).glob('*.lef'))
                if len(files) != 1:
                    raise ValueError('requires one actual published LEF: ' + kit)
                models[kit] = model(files[0])
        physical = models[kit]
        mapping = require_pins(leaf, physical)
        for port, spec in leaf['ports'].items():
            if port in ('ck', 'ck_control', 'ck_req', 'ck_rsp', 's_ck', 't_ck'):
                for bit in range(spec['bits']):
                    pin = f'{port}[{bit}]' if spec['bits']>1 else port
                    actual = mapping[pin]
                    clocks.append(dict(child=leaf['path'], port=pin, physical_pin=actual,
                                       local_xy_um=physical['pins'][actual]['anchor_um'],
                                       layer=physical['pins'][actual]['anchor_layer']))
        home = homes.get(leaf['path'])
        if home is None:
            missing_homes.append(leaf['path'])
        elif any(abs(a-b)>0.001 for a,b in zip(physical['outline_um'],[home['w_um'],home['h_um']])):
            changed_shapes.append(dict(path=leaf['path'], actual_um=physical['outline_um'],
                                       preview_um=[home['w_um'],home['h_um']]))
        rows.append(dict(path=leaf['path'], master=leaf['master'], parameters=leaf['parameters'],
                         ports=leaf['ports'], kit=kit, physical_cell=physical['physical_cell'],
                         outline_um=physical['outline_um'], actual_pin_map=mapping,
                         preview_home=home, placement_adopted=False))
    report = dict(schema='opentallas.s81.vm-native-import-plan.v1',
                  status='BLOCKED_IMPORT_PLAN_ONLY', source_commit=manifest['commit'],
                  source_files_verified=len(manifest['files']), actual_leaves=len(rows),
                  exact_pin_models=len(models), source_parameters=manifest['parameters'],
                  input_sha256={p.name:sha(p) for p in inputs.iterdir() if p.is_file()},
                  missing_homes=missing_homes, changed_outline_homes=changed_shapes,
                  literal_clock_contacts=clocks,
                  blockers=['HF4 param4 route/native verdict pending; param3 cannot substitute',
                            'All published LEFs still require their source-exact native/clock receipts',
                            '540 actual child homes and incident joins need die allocation and reach/cut proof',
                            'External ABI, fixed compiler profile and epoch-reset contract remain unbound',
                            'Die clock phi-R delivery and literal pair timing remain unproved'],
                  leaves=rows)
    return report, models


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--inputs', type=Path, required=True)
    ap.add_argument('--flat-source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args=ap.parse_args()
    report, models=build(args.inputs,args.flat_source)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'plan.json').write_text(json.dumps(report,indent=1)+'\n')
    with gzip.open(args.out/'models.json.gz','wt') as f:
        json.dump(models,f,separators=(',',':'))
    summary={k:v for k,v in report.items() if k not in ('leaves','literal_clock_contacts')}
    summary['literal_clock_contacts']=len(report['literal_clock_contacts'])
    print(json.dumps(summary,indent=1))


if __name__=='__main__':
    main()
