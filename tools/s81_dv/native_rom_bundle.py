#!/usr/bin/env python3
"""Materialize emitted native XS/frame images for a bound-die simulation.

Each XS source uses the same seven literal image keys. Different slices may
have different calendars; flattening their image directories silently loads
one slice's programme into every streamer. This tool preserves frame aliases,
assigns distinct XS keys and emits simulation-only hierarchical INSTANCE
parameters against the binder's actual xg placement. Include instances.svh
inside the die testbench, whose DUT path is given by --dut.

This does not fill uncompiled ROMs with zeros or qualify a PARTIAL programme.
The manifest retains missing bound frame selectors and selected slice coverage.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

XS = dict(pq_calendar_action='u_cal_action', pq_calendar_time='u_cal_time',
          pq_phase0='u_phase0', **{f'pq_stream{i}':f'u_stream{i}' for i in range(4)})
PATH = re.compile(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\Z')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1 << 20), b''):h.update(block)
    return h.hexdigest()


def quoted(value):
    # Binder values are SV string literals, not executable expressions.
    if not isinstance(value,str) or not re.fullmatch(r'"[A-Za-z0-9_.]+"',value):
        raise ValueError('unsupported bound ROM INSTANCE value')
    return value[1:-1]


def bundle(programmes, names, report, out, *, dut='dut'):
    if not PATH.fullmatch(dut):raise ValueError('unsafe DUT hierarchy')
    out=Path(out)
    if out.exists():raise ValueError('preserve prior bundle: select a new output directory')
    if report.get('n_errors') or report.get('errors') or report.get('type_splits'):
        raise ValueError('native ROM bundle requires a clean strict bind')
    images={}; overrides=[]; direct=[]; slices=[]; programs=[]
    def add(source,name):
        if Path(name).name!=name or not re.fullmatch(r'[A-Za-z0-9_.]+\.viamap\.hex',name):
            raise ValueError('unsafe ROM image name')
        source=Path(source)
        sha=digest(source)
        if name in images and images[name]['sha256']!=sha:
            raise ValueError('different image payloads select the same runtime ROM: '+name)
        images[name]=dict(source=str(source.resolve()),sha256=sha)
    for path in programmes:
        path=Path(path);p=json.loads(path.read_text());sl=p['slice'];selected=p['selected_slice_source']
        if p.get('schema') not in ('opentallas.s81.aproj_native_programme.v1','opentallas.s81.native_slice_images.v1'):
            raise ValueError('unsupported native programme schema')
        if not re.fullmatch(r'u_s_[0-7][NS]',sl) or sl in slices:
            raise ValueError('one native programme per actual slice is required')
        if selected['streamer']!='ot_s81sl_xs4':
            raise ValueError('unsupported selected streamer; determine actual source ROM locations')
        # The source resolver pins the actual selected wrapper and child files.
        root=Path(selected['source_root']); sources=selected['source_sha256']
        for source,sha in sources.items():
            if digest(root/source)!=sha:raise ValueError('selected native source changed: '+source)
        source=selected['resolved_module_sources'][selected['xg']]
        body=(root/source).read_text()
        child=re.findall(r'\bot_s81sl_xs4\s+(\w+)\s*\(',body)
        if len(child)!=1:raise ValueError('selected xg must contain one explicit native XS instance')
        original=sl+'.u_sl.u_xg'
        locations=[bound for bound,asbuilt in names.items() if asbuilt==original]
        if len(locations)!=1 or not PATH.fullmatch(locations[0]):
            raise ValueError('native xg does not have one exact bound hierarchy: '+original)
        for key,macro in XS.items():
            alias=sl+'_'+key
            add(path.parent/(key+'.viamap.hex'),alias+'.viamap.hex')
            overrides.append(f'defparam {dut}.{locations[0]}.{child[0]}.{macro}.INSTANCE = "{alias}";')
            direct.append(f'defparam {dut}.{locations[0]}.{child[0]}.{macro}.VIAMAP = {json.dumps(str((out/(alias+".viamap.hex")).resolve()))};')
        frames=path.parent/'frame_images'
        if not frames.is_dir():raise ValueError('native frame image material is missing')
        for image in sorted(frames.glob('*.viamap.hex')):add(image,image.name)
        slices.append(sl)
        programs.append(dict(path=str(path.resolve()),sha256=digest(path),op=p['op'],slice=sl,
                             status=p['status'],lifetime_qualified=p['lifetime_qualified'],
                             sealed_programme_held=p['sealed_programme_held']))
    if not slices:raise ValueError('at least one emitted native programme is required')
    expected=set()
    for row in report.get('instance_path_params',[]):
        if row.get('param')!='INSTANCE':continue
        value=quoted(row['value']);module=row.get('module','')
        if module.startswith('ot_rom_'):
            name=value+'.viamap.hex';expected.add(name)
            if name in images:
                locations=[bound for bound,asbuilt in names.items() if asbuilt==row['inst']]
                if len(locations)!=1 or not PATH.fullmatch(locations[0]):
                    raise ValueError('frame ROM does not have one exact bound hierarchy: '+row['inst'])
                direct.append(f'defparam {dut}.{locations[0]}.VIAMAP = {json.dumps(str((out/name).resolve()))};')
        elif module in ('ot_v41_rom_elem_q_qxpq_w10','ot_v41_rom_elem_q_qxpq_w10_gb'):
            expected.update(value+suffix+'.viamap.hex' for suffix in ('_0','_1','b_0','b_1'))
    missing=sorted(expected-images.keys())
    manifest=dict(schema='opentallas.s81.native_rom_bundle.v1',status='PARTIAL',
        programmes=programs,compiled_slices=sorted(slices),images=images,
        missing_bound_images=missing,missing_slice_programmes=sorted(
            {f'u_s_{col}{tier}' for col in range(8) for tier in 'NS'}-set(slices)),
        simulation_only=True,production_enabled=False,lifetime_qualified=False,
        direct_viamap_macros=len(direct),direct_viamap_scope='XS and standalone CFG ROMs only; QX weight banks require the global bundle',
        qualification='emitted image assembly only; original programme and uncompiled ROM obligations remain')
    out.mkdir(parents=True)
    try:
        for name,record in images.items():shutil.copyfile(record['source'],out/name)
        (out/'instances.svh').write_text('// Simulation-only native ROM image selection.\n'+'\n'.join(overrides)+'\n')
        (out/'direct_viamap.svh').write_text('// Simulation-only partial XS/CFG loading without +OT_ROM_DIR.\n'+'\n'.join(direct)+'\n')
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    except BaseException:
        # Keep partial output as failure evidence; a subsequent attempt needs a new destination.
        raise
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--programme',type=Path,action='append',required=True)
    parser.add_argument('--bind-names',type=Path,required=True)
    parser.add_argument('--bind-report',type=Path,required=True)
    parser.add_argument('--dut',default='dut')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    m=bundle(args.programme,json.loads(args.bind_names.read_text()),
             json.loads(args.bind_report.read_text()),args.out,dut=args.dut)
    print(f"PARTIAL: {len(m['images'])} real images, {len(m['compiled_slices'])}/16 slice programmes, "
          f"{len(m['missing_bound_images'])} bound ROM images uncompiled")


if __name__=='__main__':main()
