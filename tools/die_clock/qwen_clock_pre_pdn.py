#!/usr/bin/env python3
"""Source-bound prototype: fixed PG-safe clocks/rows BEFORE original full PDN.

Prepare records the actual immutable supply blueprint, installs fixed rows,
then removes supply special wires in a separate ODB. Run the original pinned
PDN source on that output. Verify requires the generated mesh to match the
blueprint, unchanged cell geometry, literal contacts, shorts and native PG
continuity. No shared GEN hook, timing or production adoption is enabled.
"""
import argparse,hashlib,json
from pathlib import Path
import odb
from openroad import Tech,Design


def digest(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),sort_keys=True).encode()).hexdigest()


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def rect(q):return [q.xMin(),q.yMin(),q.xMax(),q.yMax()]


def geometry(block):
    return digest(sorted((i.getName(),i.getMaster().getName(),str(i.getOrient()),rect(i.getBBox())) for i in block.getInsts()))


def mesh(block):
    die=block.getDieArea();shapes=[]
    for name in ('VDD','VSS'):
        net=block.findNet(name)
        if net is None:raise ValueError('actual supply absent '+name)
        for sw in net.getSWires():
            for r in sw.getWires():
                if r.isVia():continue
                layer=r.getTechLayer().getName()
                if ((layer=='M8' and r.xMax()-r.xMin()>(die.xMax()-die.xMin())/2) or
                    (layer=='M9' and r.yMax()-r.yMin()>(die.yMax()-die.yMin())/2)):
                    shapes.append([name,layer,*rect(r)])
    if {r[0]+'/'+r[1] for r in shapes}!={'VDD/M8','VDD/M9','VSS/M8','VSS/M9'}:
        raise ValueError('actual complete core mesh blueprint absent')
    return sorted(shapes)


def main(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    t=Tech();d=Design(t);d.readDb(a.odb);b=d.getBlock()
    manifest=json.loads(Path(a.manifest).read_text());names=[v[0] for v in manifest['cells']]
    if any(any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in n) for n in names):
        raise ValueError('unsupported explicit clock identifier')
    record=dict(schema='opentallas.qwen.clock_before_original_pdn.v1',operation=a.command,
                tool_source=a.tool_source,gen_source=a.gen_source,input_odb_sha256=sha(a.odb),
                manifest_sha256=sha(a.manifest),row_policy_sha256=sha(a.policy),driver_sha256=sha(__file__),
                power_qualified=False,timing_qualified=False,production_admitted=False,steps=[])
    def command(code):
        display=code if not code.startswith('set stage_clocks ') else 'set stage_clocks {explicit manifest '+str(len(names))+' cells}'
        step=dict(command=display,command_sha256=hashlib.sha256(code.encode()).hexdigest(),status=None)
        record['steps'].append(step)
        (out/'record.json').write_text(json.dumps(record,indent=1)+'\n')
        print('CLOCK_PDN_BEGIN '+display,flush=True)
        status=int(d.evalTclString('set stage_code [catch {'+code+'} stage_message]; set stage_code'))
        message=d.evalTclString('set stage_message')
        step.update(status=status,message=message if not code.startswith('set stage_clocks ') else str(len(names))+' explicit clock cells')
        (out/'record.json').write_text(json.dumps(record,indent=1)+'\n')
        print(json.dumps(record['steps'][-1]),flush=True)
        if status:raise ValueError('native stage rejected: '+message)
    command('source {'+a.policy+'}')
    command('set stage_clocks {'+' '.join(names)+'}')
    if a.command=='prepare':
        if not manifest.get('clock_power_site_model'):raise ValueError('source-bound PG-safe topology required')
        before=geometry(b);core=rect(b.getCoreArea());blueprint=mesh(b)
        command('ot_clock_rows_candidate $stage_clocks')
        if geometry(b)!=before:raise ValueError('fixed rows moved actual cells')
        if rect(b.getCoreArea())!=core:raise ValueError('new rows change actual core origin/extent; explicit PDN phase fix required')
        record.update(planned_core_mesh_from_actual_shapes=blueprint,planned_core_mesh_sha256=digest(blueprint),
                      actual_core_dbu=core,cell_geometry_sha256=before,clock_cells=len(names),
                      clock_power_site_model=manifest['clock_power_site_model'],
                      source_pg_reference_only=True,future_generated_pg_verified=False)
        removed=0
        for netname in ('VDD','VSS'):
            for sw in list(b.findNet(netname).getSWires()):odb.dbSWire.destroy(sw);removed+=1
        if any(len(b.findNet(n).getSWires()) for n in ('VDD','VSS')):raise ValueError('supply shapes remain before PDN')
        if geometry(b)!=before:raise ValueError('PG removal changed actual cells')
        d.writeDb(str(out/'before_original_pdn.odb'))
        record.update(removed_supply_swires=removed,output_odb_sha256=sha(out/'before_original_pdn.odb'),
                      required_next=['Run exact original source-pinned full PDN, without movable clock relocation',
                                     'Verify generated mesh against this blueprint, then actual contacts/shorts/native continuity',
                                     'Repeat independent placed 405um/endpoints/overlap/row checks and ROOT review before timing'])
    else:
        if not a.reference:raise ValueError('source-bound prepare receipt required')
        reference=json.loads(Path(a.reference).read_text())
        if (reference['manifest_sha256']!=record['manifest_sha256'] or reference['gen_source']!=a.gen_source
                or reference['row_policy_sha256']!=record['row_policy_sha256'] or reference.get('operation')!='prepare'):
            raise ValueError('programme/GEN/clock manifest differs from planned PG blueprint')
        if geometry(b)!=reference['cell_geometry_sha256'] or rect(b.getCoreArea())!=reference['actual_core_dbu']:
            raise ValueError('generated PDN changed pinned cell geometry/core/clock coordinates')
        if a.command=='generate':
            if not a.pdn_source or record['input_odb_sha256']!=reference['output_odb_sha256']:
                raise ValueError('exact prepared ODB and original pinned PDN source required')
            if any(len(b.findNet(n).getSWires()) for n in ('VDD','VSS')):
                raise ValueError('original PDN generation requires supply-wire-free prepared ODB')
            record['original_pdn_sources']={path:sha(path) for path in [a.pdn_source,*a.pdn_companion]}
            command('source {'+a.pdn_source+'}')
            command('pdngen -failed_via_report {'+str(out/'failed_vias.rpt')+'}')
            d.writeDb(str(out/'generated_pdn.odb'))
            record['generated_odb_sha256']=sha(out/'generated_pdn.odb')
            (out/'record.json').write_text(json.dumps(record,indent=1)+'\n')
        if geometry(b)!=reference['cell_geometry_sha256'] or rect(b.getCoreArea())!=reference['actual_core_dbu']:
            raise ValueError('actual generated PG altered pinned clock/cell geometry or core')
        actual=mesh(b)
        if actual!=reference['planned_core_mesh_from_actual_shapes']:raise ValueError('actual generated mesh differs from planned source-bound blueprint')
        record.update(reference_sha256=sha(a.reference),actual_generated_mesh_sha256=digest(actual),
                      generated_mesh_matches_blueprint=True,all_cell_coordinates_unchanged=True)
        for code in ('ot_clock_pg_contact_check $stage_clocks','ot_tie_rows_verify 8.64 .48',
                     'check_power_grid -net VDD','check_power_grid -net VSS'):command(code)
        record['actual_contacts_stack_shorts_native_continuity_pass']=True
    (out/'record.json').write_text(json.dumps(record,indent=1)+'\n')
    print('CLOCK_BEFORE_ORIGINAL_PDN_DONE timing_qualified=0 production_admitted=0',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('prepare','generate','verify'))
    for n in ('odb','manifest','policy','out','tool-source','gen-source'):p.add_argument('--'+n,required=True)
    p.add_argument('--reference')
    p.add_argument('--pdn-source')
    p.add_argument('--pdn-companion',action='append',default=[])
    main(p.parse_args())
