"""Native topology freshness and direct factory-instance census before generation.

This is preparation using existing generator names/receipts, not a new frontend
or physical release gate. Original bind directories are never rewritten.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def contract(raw):
    types={}
    for name,typ in raw['partition_types'].items():
        clock={k:v for k,v in typ.get('clock',{}).items() if k.startswith('landing_')}
        types[name]=digest(dict(internal_stations=typ.get('internal_stations',[]),
                               clock=clock,reset=typ.get('reset'),buses=[{k:b.get(k) for k in ['name','dir','width','kind']} for b in typ.get('buses',[])]))
    return dict(schema='opentallas.native_topology.v1',reset=digest(raw.get('reset')),types=types)


def write_bind_receipt(raw,out,asbuilt=None,topology=None):
    receipt=dict(topology or contract(raw))
    receipt['asbuilt_sha256']=hashlib.sha256(Path(asbuilt).read_bytes()).hexdigest() if asbuilt else digest(raw.get('asbuilt'))
    Path(out,'native_topology.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def bind_matches(raw,tn,out,asbuilt=None):
    path=Path(out)/'native_topology.json'
    if not path.is_file():return False
    old=json.loads(path.read_text());new=contract(raw)
    if asbuilt and old.get('asbuilt_sha256')!=hashlib.sha256(Path(asbuilt).read_bytes()).hexdigest():return False
    return old.get('reset')==new['reset'] and old.get('types',{}).get(tn)==new['types'][tn]


def has_topology(raw,tn):
    typ=raw['partition_types'][tn]
    return bool(raw.get('reset') or typ.get('reset') or typ.get('internal_stations') or
                typ.get('clock',{}).get('landing_raw_branches'))


def source_census(raw,tn,rtl_dir, *, require_receipt=True):
    """Use native generator names and its actual station receipt, then inspect RTL.

    Literal raw branches also check D/Q/clock, so a same-count stale reset base
    cannot pass. Bus stations use actual pad/ist names from kit_istations.
    """
    from kit_assembly import _masked_rtl,_instance_type_spans
    from landing_raw_branches import RawBranches
    kd=Path(rtl_dir);man=json.loads((kd/'kit_rtl.json').read_text())
    matches=[Path(p) for p in man['files'] if Path(p).stem==man['bound_module']]
    if len(matches)!=1:raise ValueError('topology census needs one explicit bound source')
    source=matches[0]
    if source.resolve().parent!=kd.resolve():
        raise ValueError('topology census requires the actual kit-local bound source, after canonical reset/station preparation')
    text=_masked_rtl(source.read_text())
    typ=raw['partition_types'][tn];required=[];problems=[]
    drivers=RawBranches.driver_index(text)
    actual_raw={inst:pins for hits in drivers.values() for inst,pins in hits
                if re.fullmatch(r'u_cland_raw_\w+_\d+',inst)}
    expected_raw=set()
    for branch in typ.get('clock',{}).get('landing_raw_branches',[]):
        previous=branch['base']
        for stage,_ in enumerate(branch['stages']):
            inst=f"u_cland_raw_{branch['name']}_{stage}";net=inst[2:]
            expected_raw.add(inst)
            expected={'clk':'clk','d':previous,'q':net}
            if len(_instance_type_spans(text,'ot_dp_rrelay',inst))!=1:
                problems.append(f'{inst}: expected one emitted ot_dp_rrelay')
            if actual_raw.get(inst)!=expected:
                problems.append(f'{inst}: emitted {actual_raw.get(inst)}, expected {expected}')
            required.append(dict(inst=inst,master='ot_dp_rrelay',kind='literal_raw_reset'))
            previous=net
    problems += [f'unplanned literal raw relay {n}' for n in sorted(set(actual_raw)-expected_raw)]
    stations={}
    for entry in typ.get('internal_stations',[]):
        conn=entry.get('conn','')
        if not conn.startswith('bus:'):continue
        count=len(entry['regs_um'])
        if conn in stations and stations[conn]!=count:
            problems.append(f'{conn}: conflicting planned stage counts')
        stations[conn]=count
    report=man.get('kit_istations',[])
    emitted_bus_stages={}
    for conn,count in stations.items():
        from gen_rtl import sv_id
        bus=sv_id(conn[4:])
        bus_row=next(b for b in typ['buses'] if b['name']==conn[4:])
        from kit_istations import packed_input_delay,bound_bus_width
        width=bound_bus_width(tn,bus_row,text,man)
        packed=packed_input_delay(tn,bus_row,text,width,count)
        rows=[r for r in report if r.get('conn')==conn]
        if packed:
            emitted_bus_stages[conn]=packed['stage_registers']
            if require_receipt and not rows:
                problems.append(f'{conn}: packed {count} stages need canonical placement receipt')
            if any(r.get('packed_delay')!=packed or r.get('stations')!=packed['stage_registers'] for r in rows):
                problems.append(f'{conn}: packed-delay source/placement receipt differs')
            required.append(dict(inst=packed['instance'],master='ot_dp_dly',
                                 parameters=dict(W=packed['width'],D=packed['depth']),
                                 register_bits=packed['width']*packed['depth'],kind=conn))
            continue
        candidates=set(re.findall(r'\b(u_ist_'+re.escape(bus)+r'_\d+|u_b(?:in|out)_'+re.escape(bus)+r'_pad\d+)\b',text))
        kinds={name:[kind for kind in ['ot_dp_st','ot_dp_ste'] if len(_instance_type_spans(text,kind,name))==1] for name in sorted(candidates)}
        emitted=[name for name,ks in kinds.items() if len(ks)==1]
        emitted_bus_stages[conn]=emitted
        if len(emitted)!=count:
            problems.append(f'{conn}: actual source emitted {len(emitted)} stages, expected {count}')
        if require_receipt and not rows:
            problems.append(f'{conn}: missing kit_istations factory receipt for {count} stages')
            continue
        for row in rows:
            names=row.get('stations',[])
            if row.get('planned')!=count or len(names)!=count:
                problems.append(f'{conn}: factory emitted {len(names)} stages, expected {count}')
            for name in names:
                choices=kinds.get(name,[])
                if len(choices)!=1:problems.append(f'{name}: expected one canonical station instance, found {len(choices)}')
                required.append(dict(inst=name,master=choices[0] if len(choices)==1 else 'ot_dp_st',kind=conn))
    required=list({(r['inst'],r['master']):r for r in required}.values())
    return dict(schema='opentallas.kit_topology.v1',type=tn,source=str(source),
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                topology=contract(raw)['types'][tn],raw_expected=len(expected_raw),raw_emitted=len(actual_raw),
                planned_bus_stages=stations,emitted_bus_stages=emitted_bus_stages,required_instances=required,problems=problems)


def install_inventory(census,receipt,top):
    """Augment the existing one-frontend inventory, including zero hard children."""
    from kit_assembly import __file__ as helper
    receipt=Path(receipt)
    data=json.loads(receipt.read_text()) if receipt.exists() else dict(
        schema='opentallas.kit_assembly.v1',bindings=[],parent_profile=dict(top=top,parameters={}))
    required={}
    for row in data.get('required_instances',[])+census['required_instances']:
        if row['inst'] in required and required[row['inst']]['master']!=row['master']:
            raise ValueError('conflicting explicit factory instance '+row['inst'])
        required.setdefault(row['inst'],row)
    data['required_instances']=list(required.values())
    receipt.write_text(json.dumps(data,indent=2)+'\n')
    shutil.copyfile(helper,receipt.parent/'kit_assembly.py')


def prepare_stations(plan,tn,rtl_dir,native_plan=None,asbuilt=None):
    """Canonical IN/core application and OUT reuse, once on a fresh kit copy."""
    import kit_istations
    raw=json.loads(Path(plan).read_text());kd=Path(rtl_dir).resolve()
    man=json.loads((kd/'kit_rtl.json').read_text())
    context=json.loads(Path(native_plan).read_text()) if native_plan else raw
    if tn not in context['partition_types'] or contract(context)['types'][tn]!=contract(raw)['types'][tn]:
        raise ValueError('KIT_TOPOLOGY_CONTEXT: selected topology differs from full native plan')
    manifest=asbuilt or man.get('asbuilt_manifest')
    if native_plan and digest(raw.get('reset'))!=digest(context.get('reset')):
        raise ValueError('KIT_TOPOLOGY_CONTEXT: selected reset topology differs from full native plan')
    if native_plan and has_topology(context,tn):
        if not man.get('bind_out') or not bind_matches(context,tn,man['bind_out'],manifest):
            raise ValueError('KIT_TOPOLOGY_BIND_STALE: regenerate the canonical native bind for this full plan/asbuilt context')
    fingerprint=digest(dict(type=contract(raw)['types'][tn],reset=contract(context)['reset'],
                            asbuilt=hashlib.sha256(Path(manifest).read_bytes()).hexdigest() if manifest else None))
    stamp=kd/'kit_topology_prepared.json'
    bound=next(Path(f) for f in man['files'] if Path(f).stem==man['bound_module'])
    if stamp.exists():
        old=json.loads(stamp.read_text())
        if old['fingerprint']!=fingerprint or old['source_sha256']!=hashlib.sha256(bound.read_bytes()).hexdigest():
            raise ValueError('KIT_TOPOLOGY_REGENERATE: prepared source/context changed; regenerate a fresh kit copy')
        result=source_census(raw,tn,kd)
    else:
        kit_istations.main([str(plan),tn,str(kd),'--apply'])
        result=source_census(raw,tn,kd)
    (kd/'kit_topology.json').write_text(json.dumps(result,indent=2)+'\n')
    if result['problems']:
        raise ValueError('KIT_TOPOLOGY_SOURCE: '+'; '.join(result['problems']))
    if not stamp.exists():
        stamp.write_text(json.dumps(dict(fingerprint=fingerprint,source_sha256=result['source_sha256'],
                         native_plan=str(native_plan or plan),asbuilt=manifest),indent=2)+'\n')
    return result


def stage_inventory(rtl_dir,kit):
    """Carry preparation expectations through the ordinary gen.py physical kit."""
    rtl_dir,kit=Path(rtl_dir),Path(kit)
    source=rtl_dir/'kit_topology.json'
    if not source.exists():return
    census=json.loads(source.read_text())
    if census.get('problems'):raise ValueError('KIT_TOPOLOGY_SOURCE: unsuccessful preparation cannot be staged')
    bound=Path(census['source'])
    if hashlib.sha256(bound.read_bytes()).hexdigest()!=census['source_sha256']:
        raise ValueError('KIT_TOPOLOGY_REGENERATE: source changed after canonical station preparation')
    assembly=rtl_dir/'kit_assembly.json'
    if assembly.exists() and not (kit/'kit_assembly.json').exists():
        shutil.copyfile(assembly,kit/'kit_assembly.json')
    top=json.loads((kit/'freeze.json').read_text())['module']
    install_inventory(census,kit/'kit_assembly.json',top)
    shutil.copyfile(source,kit/'kit_topology.json')


def main():
    import argparse,sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    census=sub.add_parser('census');census.add_argument('plan');census.add_argument('type');census.add_argument('rtl_dir');census.add_argument('--receipt',required=True)
    prepare=sub.add_parser('prepare-stations');prepare.add_argument('plan');prepare.add_argument('type');prepare.add_argument('rtl_dir');prepare.add_argument('--native-plan');prepare.add_argument('--asbuilt')
    stamp=sub.add_parser('stamp-bind');stamp.add_argument('plan');stamp.add_argument('bind_out');stamp.add_argument('--asbuilt')
    a=p.parse_args();raw=json.loads(Path(a.plan).read_text())
    if a.command=='prepare-stations':
        result=prepare_stations(a.plan,a.type,a.rtl_dir,a.native_plan,a.asbuilt)
        print(json.dumps(dict(type=a.type,required_instances=len(result['required_instances']),problems=result['problems'])))
        return 0
    if a.command=='stamp-bind':
        report=json.loads(Path(a.bind_out,'bind_report.json').read_text())
        if report.get('n_errors',1):raise ValueError('only a successful fresh native bind can record topology')
        write_bind_receipt(raw,a.bind_out,a.asbuilt)
        return 0
    result=source_census(raw,a.type,a.rtl_dir)
    Path(a.receipt).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['raw_expected','raw_emitted','planned_bus_stages','emitted_bus_stages','problems']}))
    return 2 if result['problems'] else 0


if __name__=='__main__':
    raise SystemExit(main())
