#!/usr/bin/env python3
"""Compose current native CB16 R8 support/phase classes from actual bind data.

For an unfrozen plan, use a fresh post-landing probe/R8 base with old optional phase overlays disabled.
When preserving an existing phase implementation, explicitly supply its overlays; --rebase-existing adds
only their recorded tree_align deltas onto a newly regenerated base. Final actual-source fixedpoint is separate.
"""
import argparse,copy,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def module(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def compose(args):
    if args.out.exists():raise ValueError(f'refuse existing output {args.out}')
    raw=json.loads(args.plan.read_text());table=json.loads(args.r8.read_text());report=json.loads((args.bound/'bind_report.json').read_text());ids=json.loads(args.parent_ids.read_text())
    for key in ('unbound','tied','undriven','multiply_bound'):
        if report['proof'].get(key,0):raise ValueError(f'base source has {key}: {report["proof"][key]}')
    args.out.mkdir(parents=True)
    current={m['id']:copy.deepcopy(m) for m in table['members']}
    for path in args.existing_overlay:
        for old in json.loads(path.read_text())['members']:
            if old['id'] not in current:raise ValueError(f'overlay member absent from current source: {old["id"]}')
            base=current[old['id']]
            if args.rebase_existing:
                extra=old.get('tree_align')
                if type(extra) is not int or extra<0:raise ValueError('rebasing requires a recorded nonnegative tree_align delta')
                current[old['id']]=dict(base,pad=base['pad']+extra,landed=base['landed']+extra)
            else:
                if old.get('bound')!=base.get('bound'):raise ValueError('base bound depth changed: use a fresh solve or explicit --rebase-existing')
                current[old['id']]=copy.deepcopy(old)
    table['members']=[current[m['id']] for m in table['members']]
    effective=args.out/'effective_r8.json';effective.write_text(json.dumps(table,indent=1)+'\n')
    support=module(HERE/'apply_r8_support_classes.py','support')
    cbtypes={next(p['type'] for p in raw['partitions'] if p['name']==m['sink_part']) for m in table['members'] if m['sink'].startswith('c16_')}
    sr=copy.deepcopy(report);sr['type_splits']=[s for s in report.get('type_splits',[]) if s['type'] not in cbtypes]
    raw,smanifest=support.apply(raw,sr,table)
    dag=module(HERE/'bind/cb16_dag.py','dag');overlay=dag.align(args.bound,effective,args.out/'dag_overlay.json')
    phase=module(HERE/'apply_cb16_phase_types.py','phase');manifest=phase.classify(raw,table,overlay);raw=phase.apply(raw,manifest)
    ancestry={}
    for path in args.family_manifest:
        old=json.loads(path.read_text());ancestry.update(old.get('family_ancestry',{}));ancestry.update({c['type']:c['family'] for c in old['classes'] if c['type']!=c['family']})
    if args.landing_table:
        landing=json.loads(args.landing_table.read_text());collector=landing.get('landing_table',landing)['collector']
        ancestry.update({name:v['base_type'] for name,v in collector['types'].items() if name!=v['base_type']})
    phase.refresh_parent_ids(raw,manifest,ids,ancestry)
    (args.out/'support_classes.json').write_text(json.dumps(smanifest,indent=1)+'\n')
    (args.out/'phase_classes.json').write_text(json.dumps(manifest,indent=1)+'\n')
    (args.out/'plan.json').write_text(json.dumps(raw,indent=1)+'\n')
    result=dict(schema='opentallas.qc.cb16.composition.v1',input_types=len(json.loads(args.plan.read_text())['partition_types']),output_types=len(raw['partition_types']),support_new_types=smanifest['new_type_count'],cb_new_types=manifest['new_type_count'],cb_classes=len(manifest['classes']),logical_added_ff=manifest['logical_added_ff'],root_added_cycles_max=manifest['root_added_cycles_max'],internal_stations_types=[c['type'] for c in manifest['classes']],scope='Logical candidate composition. Rebind at these explicit classes and require actual-source DAG fixedpoint zero; physical closure and full token gate remain separate.')
    (args.out/'composition.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('internal_stations_types','scope')}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','bound','r8','parent-ids','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--existing-overlay',type=Path,action='append',default=[]);p.add_argument('--rebase-existing',action='store_true');p.add_argument('--family-manifest',type=Path,action='append',default=[]);p.add_argument('--landing-table',type=Path)
    compose(p.parse_args())
