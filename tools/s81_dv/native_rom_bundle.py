#!/usr/bin/env python3
"""Materialize emitted native XS/frame images for a bound-die simulation.

Each XS source uses seven shared literal image keys. Per-slice VIAMAP values
select its emitted calendars without a global OT_ROM_DIR. With --bound-top,
QX weights use absolute INSTANCE argument values in generated bound-RTL copies
and a copied behavioral ROM model supporting that opt-in filename prefix.
The manifest names the exact original SHA and replacement file for each copy.
Original RTL, shape parameters, wiring and cycle behavior stay unchanged.

Include direct_viamap.svh inside the die testbench (--dut names its instance),
and replace the listed bound-RTL and ROM-model sources with their bundle copies.
This does not fill uncompiled ROMs with zeros or qualify a PARTIAL programme.
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


QX_ROM = 'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'


def absolute_instance_overlay(text):
    """Only add opt-in initialization by absolute INSTANCE prefix to a sim copy."""
    old='        else if (VIAMAP != "")\n            $readmemh(VIAMAP, arr);'
    new=old+'\n        else if (INSTANCE.len() > 0 && INSTANCE.getc(0) == 8\'h2f)\n            $readmemh({INSTANCE, ".viamap.hex"}, arr);'
    if text.count(old)!=1:raise ValueError('unsupported QX behavioral ROM initialization source')
    return text.replace(old,new)


class BoundQX:
    """Resolve real generated partition calls; never infer a bank from its name."""
    def __init__(self, top):
        from qxpq_go_boundary import _group, _named
        self.top=Path(top);self.cells={};self.partitions={};self.offsets={};self.edits={}
        text=self.top.read_text()
        for match in re.finditer(r'(?m)^\s*([A-Za-z_]\w*)\s+',text):
            pos=match.end();params={};offset=0
            if text[pos:pos+1]=='#':
                p0=text.index('(',pos);p1=_group(text,p0)
                params=_named(text[p0+1:p1-1]);pos=p1;offset=p0+1
            name=re.match(r'\s*([A-Za-z_]\w*)\s*\(',text[pos:])
            if name:
                self.cells[name[1]]=(match[1],params);self.offsets[name[1]]=offset

    def banks(self,bound,selector):
        from gb_image_identity import calls
        if len(bound.split('.'))!=2:raise ValueError('QX binding must name an actual partition leaf')
        part,leaf=bound.split('.')
        if part not in self.cells:raise ValueError('QX partition absent from bound top')
        master,parent_params=self.cells[part]
        if master not in self.partitions:
            path=self.top.parent/(master+'.sv')
            self.partitions[master]={c['name']:c for c in calls(path.read_text())}
        call=self.partitions[master].get(leaf)
        if not call or call['module']!='ot_v41_rom_elem_q_qxpq_w10':
            raise ValueError('QX leaf differs from actual generated partition')
        params={k:v[2] for k,v in call['params'].items()}
        if params.get('NB')!='2' or params.get('PP')!='1':
            raise ValueError('QX direct bank loading requires actual NB2/PP1 source shape')
        key=params.get('INSTANCE')
        expression=parent_params[key][2] if key in parent_params else key
        if expression is None or quoted(expression)!=selector:
            raise ValueError('QX image identity differs from actual bound top parameter')
        return [(f'{bound}.u_e.g_mac[{m}].g_pp.u_rom{b}',
                 ('b' if m else '')+'_'+str(b)) for m in range(2) for b in range(2)]

    def patch_instance(self,bound,selector,absolute):
        self.banks(bound,selector)
        part,leaf=bound.split('.');master,parent_params=self.cells[part]
        call=self.partitions[master][leaf];key=call['params']['INSTANCE'][2]
        if key in parent_params:
            path=self.top;offset=self.offsets[part];begin,end,_=parent_params[key];name=key
        else:
            if sum(m==master for m,_ in self.cells.values())!=1:
                raise ValueError('literal QX INSTANCE in a shared partition needs per-instance specialization')
            path=self.top.parent/(master+'.sv');offset=call['p0']+1
            begin,end,_=call['params']['INSTANCE'];name='INSTANCE'
        replacement='.'+name+'('+json.dumps(absolute)+')'
        edits=self.edits.setdefault(path,{})
        span=(offset+begin,offset+end)
        if span in edits and edits[span]['replacement']!=replacement:
            raise ValueError('conflicting simulation image parameter patches')
        edits[span]=dict(replacement=replacement,bound_element=bound,parameter=name,old_expression=key)

    def overlays(self):
        result={};contents={}
        for path,edits in self.edits.items():
            original=path.read_text();text=original
            for (begin,end),patch in sorted(edits.items(),reverse=True):
                text=text[:begin]+patch['replacement']+text[end:]
            name='bind_rtl/'+path.name
            result[str(path.resolve())]=dict(original_sha256=digest(path),overlay_file=name,
                overlay_sha256=hashlib.sha256(text.encode()).hexdigest(),
                patch_scope='simulation INSTANCE argument values only; all shape parameters, ports and logic preserved',
                edits=[dict(begin=a,end=b,**v) for (a,b),v in sorted(edits.items())])
            contents[name]=text
        return result,contents


def bundle(programmes, names, report, out, *, dut='dut', bound_top=None, hardlink=False):
    if not PATH.fullmatch(dut):raise ValueError('unsafe DUT hierarchy')
    out=Path(out)
    if out.exists():raise ValueError('preserve prior bundle: select a new output directory')
    if report.get('n_errors') or report.get('errors') or report.get('type_splits'):
        raise ValueError('native ROM bundle requires a clean strict bind')
    images={}; direct=[]; slices=[]; programs=[]
    qx=BoundQX(bound_top) if bound_top is not None else None
    qx_loaded=0; qx_bindings=[]; source_roots=[]
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
        if selected['streamer'] not in ('ot_s81sl_xs4','ot_s81sl_xs'):
            raise ValueError('unsupported selected streamer; determine actual source ROM locations')
        # The source resolver pins the actual selected wrapper and child files.
        root=Path(selected['source_root']); sources=selected['source_sha256']
        source_roots.append(root)
        for source,sha in sources.items():
            if digest(root/source)!=sha:raise ValueError('selected native source changed: '+source)
        source=selected['resolved_module_sources'][selected['xg']]
        body=(root/source).read_text()
        child=re.findall(r'\b'+re.escape(selected['streamer'])+r'\s+(\w+)\s*\(',body)
        if len(child)!=1:raise ValueError('selected xg must contain one explicit native XS instance')
        original=sl+' (selected native u_xg)'
        locations=[bound for bound,asbuilt in names.items()
                   if asbuilt.split('.')[0]==sl and asbuilt.endswith('.u_xg')]
        if len(locations)!=1 or not PATH.fullmatch(locations[0]):
            raise ValueError('native xg does not have one exact bound hierarchy: '+original)
        streamer=(root/selected['resolved_module_sources'][selected['streamer']]).read_text()
        for key,macro in XS.items():
            if not re.search(r'\(\s*"'+re.escape(key)+r'"\s*\)\s*'+re.escape(macro)+r'\s*\(',streamer):
                raise ValueError('selected streamer ROM identity differs: '+macro)
            alias=sl+'_'+key
            add(path.parent/(key+'.viamap.hex'),alias+'.viamap.hex')
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
            available=[value+suffix+'.viamap.hex' in images for suffix in ('_0','_1','b_0','b_1')]
            if qx is not None and any(available):
                if not all(available):raise ValueError('partial QX bank set; retain the missing banks explicitly')
                locations=[bound for bound,asbuilt in names.items() if asbuilt==row['inst']]
                if len(locations)!=1 or not PATH.fullmatch(locations[0]):
                    raise ValueError('QX element does not have one exact bound hierarchy: '+row['inst'])
                banks=qx.banks(locations[0],value)
                absolute=str((out/value).resolve())
                qx.patch_instance(locations[0],value,absolute)
                qx_bindings.append(dict(bound_element=locations[0],selector=value,absolute_prefix=absolute,dut=dut,
                                       banks=[dict(hierarchy=macro,image=value+suffix+'.viamap.hex') for macro,suffix in banks]))
                qx_loaded+=len(banks)
    bind_overlays,bind_contents=qx.overlays() if qx_loaded else ({},{})
    overlays={}
    if qx_loaded:
        models=[(root/QX_ROM).read_text() for root in source_roots]
        if len(set(models))!=1:raise ValueError('selected source roots disagree on the QX behavioral ROM model')
        original=models[0];overlay=absolute_instance_overlay(original)
        import hashlib
        overlays[QX_ROM]=dict(module='ot_rom_4096x274_m8',original_sha256=hashlib.sha256(original.encode()).hexdigest(),
            overlay_file='ot_rom_4096x274_m8_bundle.v',overlay_sha256=hashlib.sha256(overlay.encode()).hexdigest(),
            patch_scope='simulation initial filename selection only: absolute INSTANCE loads its .viamap.hex when OT_ROM_DIR is unset',
            hardware_changed=False,added_cycles=0)
    missing=sorted(expected-images.keys())
    manifest=dict(schema='opentallas.s81.native_rom_bundle.v1',status='PARTIAL',
        programmes=programs,compiled_slices=sorted(slices),images=images,
        missing_bound_images=missing,missing_slice_programmes=sorted(
            {f'u_s_{col}{tier}' for col in range(8) for tier in 'NS'}-set(slices)),
        simulation_only=True,production_enabled=False,lifetime_qualified=False,
        image_materialization='hardlinks to immutable emitted images' if hardlink else 'copies',
        direct_viamap_macros=len(direct)+qx_loaded,direct_override_statements=len(direct),
        direct_viamap_qx_banks=qx_loaded,qx_bindings=qx_bindings,rom_model_overlays=overlays,bound_rtl_overlays=bind_overlays,
        direct_viamap_scope='exact covered XS/CFG ROMs and bound NB2/PP1 QX weight banks; other ROMs remain uncompiled',
        bound_top=str(Path(bound_top).resolve()) if bound_top is not None else None,
        qualification='emitted image assembly only; original programme and uncompiled ROM obligations remain')
    out.mkdir(parents=True)
    try:
        for name,record in images.items():
            if hardlink:
                import os
                os.link(record['source'],out/name)
            else:shutil.copyfile(record['source'],out/name)
        (out/'instances.svh').write_text('// Simulation-only direct ROM loading; do not set OT_ROM_DIR.\n'+'\n'.join(direct)+'\n')
        (out/'direct_viamap.svh').write_text('// Direct XS/CFG loading without OT_ROM_DIR; QX additionally requires the manifest source overlays.\n'+'\n'.join(direct)+'\n')
        if overlays:(out/overlays[QX_ROM]['overlay_file']).write_text(overlay)
        for name,text in bind_contents.items():
            target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
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
    parser.add_argument('--hardlink',action='store_true',help='link immutable emitted masks on the same filesystem')
    parser.add_argument('--bound-top',type=Path,help='actual bound top RTL; enables exact QX/MAT bank VIAMAP loading')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    m=bundle(args.programme,json.loads(args.bind_names.read_text()),
             json.loads(args.bind_report.read_text()),args.out,dut=args.dut,bound_top=args.bound_top,hardlink=args.hardlink)
    print(f"PARTIAL: {len(m['images'])} real images, {len(m['compiled_slices'])}/16 slice programmes, "
          f"{len(m['missing_bound_images'])} bound ROM images uncompiled")


if __name__=='__main__':main()
