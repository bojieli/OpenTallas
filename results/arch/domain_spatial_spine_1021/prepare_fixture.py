#!/usr/bin/env python3
"""Prepare saved real OpenROAD scenes; this program never launches an EDA tool."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(path, target):
    with tarfile.open(path) as tf:
        for item in tf.getmembers():
            p = Path(item.name)
            if p.is_absolute() or '..' in p.parts or not item.isfile():
                raise ValueError('fixture archive contains unsupported path/type')
        tf.extractall(target)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('case', choices=['shell3', 'ctlm2'])
    p.add_argument('output', type=Path)
    p.add_argument('--api-root', required=True, type=Path,
                   help='ROOT current99/FRAME projection with API, not an older whole ref_tile file')
    a = p.parse_args()
    out = a.output.resolve()
    if out.exists():
        raise ValueError('use a fresh output directory; never overwrite a prior witness')
    data = HERE/'fixtures'
    fixture = json.loads((data/'manifest.json').read_text())[a.case]
    std = json.loads((data/'standard_libs.json').read_text())
    assert digest(data/(a.case+'_scene.tgz')) == fixture['scene_archive_sha256']
    assert digest(data/(a.case+'.odb.gz')) == fixture['compressed_odb_sha256']
    assert digest(data/'stdlibs.tgz') == std['archive_sha256']
    out.mkdir(parents=True)
    scene = out/'src'
    scene.mkdir()
    unpack(data/(a.case+'_scene.tgz'), scene)
    for path, sha in fixture['scene_files'].items():
        assert digest(scene/path) == sha, path
    libs = out/'libs'
    libs.mkdir()
    unpack(data/'stdlibs.tgz', libs)
    for path, sha in std['files'].items():
        assert digest(libs/path) == sha, path
    with gzip.open(data/(a.case+'.odb.gz'), 'rb') as f:
        with (out/'placed.odb').open('wb') as target:
            shutil.copyfileobj(f, target)
    assert digest(out/'placed.odb') == fixture['odb_sha256']

    api = a.api_root.resolve()
    sys.path.insert(0, str(api/'tools/ref_tile'))
    import ref_tile as R
    import domain_spatial_spine as D
    # Runtime helper sources come from ROOT's selected framework. The saved
    # database/macro models stay frozen. Record every substituted helper.
    helpers = ['physical/common_flow/clock_spine.tcl',
               'physical/common_flow/domain_spatial_spine.tcl',
               'physical/common_flow/clock_entries.tcl',
               'physical/common_flow/clock_family.tcl',
               'physical/common_flow/native_pg_binding.tcl']
    helper_hashes = {}
    for rel in helpers:
        (scene/rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(api/rel, scene/rel)
        helper_hashes[rel] = digest(scene/rel)
    R.ROOT = scene
    tile = fixture['tile']
    kd = 'physical/ref_tile/'+tile
    spec = json.loads((scene/kd/'spec.json').read_text())
    if any(spec.get(key) for key in ('pre_cts_extra', 'sdc_extra', 'boundary_tcl', 'forwarded_clock')):
        raise ValueError('saved fixture contains a generic clock hook; no bypass is permitted')
    domains = R.clock_entry_constraints.domains(spec)
    config = dict(version=1, roots=[dict(domain=next(n for n, d in domains.items() if port in d['ports']), port=port)
                                   for port in spec['clock_ports']],
                  symmetric=True, bin_um=30, leaf_max=16, iterations=10, rc_cal=False,
                  macro_leaf=a.case == 'shell3', macro_pin_leaf=a.case == 'shell3')
    variant = copy.deepcopy(spec)
    variant['domain_spatial_spine'] = config
    D.validate(variant, domains, api)
    # Generate BOTH from the selected current framework, preserving its clock
    # timing basis. No old FRAME file is projected into the selected API tree.
    plain = R.gen_hooks(spec, kd)
    opt = R.gen_hooks(variant, kd)
    assert all(plain[k] == opt[k] for k in plain if k != 'pre_cts.tcl')
    sdc = R.gen_sdc(spec, float(spec.get('route', {}).get('period_ps', 770)))
    assert sdc == R.gen_sdc(variant, float(spec.get('route', {}).get('period_ps', 770)))
    (scene/kd/'clock.sdc').write_text(sdc)
    for name, text in opt.items():
        (scene/kd/name).write_text(text)
    macro_libs = [p for p in fixture['scene_files'] if p.endswith('_tt.lib')]
    lines = [f'read_liberty /w/libs/{name}' for name in sorted(std['files'])]
    lines += [f'read_liberty /src/{path}' for path in macro_libs]
    lines += ['read_db /w/placed.odb', f'read_sdc /src/{kd}/clock.sdc',
              f'source /src/{kd}/pre_cts.tcl',
              'source /w/contact_trace.tcl',
              'set expected [dict create '+ ' '.join(f'{k} {v}' for k,v in fixture['expected_physical_liberty_contacts'].items())+']',
              'set actual [ot_dsp::admit]',
              'dict for {root count} $expected {if {[dict get $actual $root] != $count} {error "physical/source count mismatch $root"}}',
              'puts "ACTUAL_COLLECTOR_BASELINE PASS (physical Liberty contacts, not STA sinkcount)"']
    (out/'load.tcl').write_text('\n'.join(lines)+'\n')
    shutil.copy2(HERE/'fixture_modes.tcl', out/'fixture_modes.tcl')
    shutil.copy2(HERE/'contact_trace.tcl', out/'contact_trace.tcl')
    receipt = dict(case=a.case, fixture=fixture, api_root=str(api),
                   api_source_hashes={str(p.relative_to(api)):digest(p) for p in
                       [api/'tools/ref_tile/ref_tile.py', api/'tools/ref_tile/clock_entry_constraints.py',
                        api/'tools/ref_tile/domain_spatial_spine.py']}, helper_hashes=helper_hashes,
                   config=config, clock_sdc_sha256=digest(scene/kd/'clock.sdc'),
                   non_PRE_CTS_hooks_and_SDC_byte_identical_between_current_control_and_optin=True,
                   status='PREPARED_NOT_RUN; ROOT owns actual execution and interpretation')
    (out/'prepared.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('FIXTURE_PREPARED_NOT_RUN', a.case, out)


if __name__ == '__main__':
    main()
