"""Native topology freshness and direct factory-instance census before generation.

This is preparation using existing generator names/receipts, not a new frontend
or physical release gate. Original bind directories are never rewritten.
"""
import hashlib
import json
import os
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
                               clock=clock,reset=typ.get('reset'),count_straps=typ.get('count_straps'),id_straps=typ.get('id_straps'),relay_sites=typ.get('relay_sites'),buses=[{k:b.get(k) for k in ['name','dir','width','kind']} for b in typ.get('buses',[])]))
    return dict(schema='opentallas.native_topology.v1',reset=digest(raw.get('reset')),types=types)


def native_contract(raw,asbuilt=None,plan_path=None):
    """Fingerprint only fields the native binder consumes, using its actual opt-ins.

    The complete posthook contract remains separate. In particular, IN/core
    stations and OUT stations not selected by internal_stations_types belong to
    KIT preparation, not native materialization.
    """
    ab=json.loads(Path(asbuilt).read_text()) if asbuilt else raw.get('asbuilt',{})
    table={};table_sha=None
    if ab.get('clock_landing_table'):
        base=Path(ab.get('base',Path(__file__).resolve().parents[2]))
        if not base.is_absolute():
            # Match bind.plan_base: an explicit manifest owns its relative base.
            # Inline asbuilt metadata remains relative to the containing plan.
            context = asbuilt or plan_path
            if context is None:raise ValueError('native clock table requires explicit full plan context')
            base=Path(context).parent/base
        path=Path(ab['clock_landing_table'])
        if not path.is_absolute():path=base/path
        base,path=base.resolve(),path.resolve()
        try:path.relative_to(base)
        except ValueError as error:raise ValueError('native clock table must resolve inside its declared native base') from error
        payload=path.read_bytes();table=json.loads(payload);table_sha=hashlib.sha256(payload).hexdigest()
    selected=set(ab.get('internal_stations_types',[]))
    lineage=table.get('collector',{}).get('types',{})
    types={};reset_context={};ownership={}
    for name,typ in raw['partition_types'].items():
        base=lineage.get(name,{}).get('base_type',name)
        owns_out=any(name==s or base==s or base.startswith(s+'_') for s in selected)
        entries=[]
        if owns_out:
            from native_istations import source_entries,selected_buses
            entries=source_entries(typ,selected_buses(ab,name,base))
        native_conns={e['conn'] for e in entries}
        ownership[name]=[dict(conn=e.get('conn'),stages=len(e.get('regs_um',[])),phase='NATIVE' if e.get('conn') in native_conns else 'KIT') for e in typ.get('internal_stations',[])]
        clock={k:v for k,v in typ.get('clock',{}).items() if k.startswith('landing_')} if table_sha else {}
        type_contract=dict(native_out_stations=entries,clock=clock,clock_table_sha256=table_sha,
            buses=[{k:b.get(k) for k in ['name','dir','width','kind']} for b in typ.get('buses',[])],
            count_straps=typ.get('count_straps'),id_straps=typ.get('id_straps'))
        import bind_leaf_reset
        leaf_rules=bind_leaf_reset.selected(ab.get('reset_gate_bindings'),name,typ.get('hard_cores',[]))
        if leaf_rules:type_contract['reset_gate_bindings']=leaf_rules
        types[name]=digest(type_contract)
        reset_context[name]=dict(reset=typ.get('reset'),hard=typ.get('hard'),
            clock={k:v for k,v in typ.get('clock',{}).items() if not k.startswith('landing_')})
    transport=dict(lanes=[{k:l.get(k) for k in ['id','ports','fixed_cycles','stations','cycles']} for l in raw.get('lanes',[])],
                   ports=[{k:p.get(k) for k in ['id','src','dst','width','kind']} for p in raw.get('ports',[])])
    return dict(schema='opentallas.native_topology.v2',types=types,ownership=ownership,clock_table_sha256=table_sha,
                reset=digest(dict(global_reset=raw.get('reset'),types=reset_context)),transport=digest(transport))


def write_bind_receipt(raw,out,asbuilt=None,topology=None,plan_path=None):
    receipt=dict(topology or native_contract(raw,asbuilt,plan_path))
    receipt['asbuilt_sha256']=hashlib.sha256(Path(asbuilt).read_bytes()).hexdigest() if asbuilt else digest(raw.get('asbuilt'))
    Path(out,'native_topology.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def bind_matches(raw,tn,out,asbuilt=None,plan_path=None):
    path=Path(out)/'native_topology.json'
    if not path.is_file():return False
    old=json.loads(path.read_text());new=native_contract(raw,asbuilt,plan_path)
    if asbuilt and old.get('asbuilt_sha256')!=hashlib.sha256(Path(asbuilt).read_bytes()).hexdigest():return False
    if old.get('transport') != new['transport'] or old.get('types',{}).get(tn) != new['types'][tn]:
        return False
    if old.get('reset') == new['reset']:
        return True
    if os.environ.get('OT_NATIVE_RESET_SCOPE') != 'selected':
        return False
    # The canonical producer context must still reproduce its complete receipt.
    # Never stamp an old bind or ignore changed selected/global native inputs.
    provenance = Path(out)/'provenance_bind.json'
    if not provenance.is_file():
        return False
    producer_path = Path(os.environ.get('OT_NATIVE_PRODUCER_CONTEXT') or
                         json.loads(provenance.read_text()).get('provenance',{}).get('plan',''))
    if not producer_path.is_absolute() or not producer_path.is_file():
        return False
    producer = json.loads(producer_path.read_text())
    reference = native_contract(producer, asbuilt, producer_path)
    if any(old.get(key) != reference.get(key) for key in ('reset','transport','clock_table_sha256')):
        return False
    if old.get('types') != reference['types'] or old.get('ownership') != reference['ownership']:
        return False
    return selected_reset_context(producer, tn) == selected_reset_context(raw, tn)


def selected_reset_context(raw, tn):
    """All global reset inputs and this type's native reset/clock inputs."""
    typ = raw['partition_types'][tn]
    return dict(global_reset=raw.get('reset'), reset=typ.get('reset'), hard=typ.get('hard'),
                clock={k:v for k,v in typ.get('clock',{}).items() if not k.startswith('landing_')})


def has_topology(raw,tn,asbuilt=None):
    ab=json.loads(Path(asbuilt).read_text()) if asbuilt else raw.get('asbuilt',{})
    typ=raw['partition_types'][tn]
    return bool(ab.get('clock_landing_table') or raw.get('reset') or typ.get('reset') or typ.get('internal_stations') or
                typ.get('clock',{}).get('landing_raw_branches') or typ.get('count_straps') or typ.get('id_straps'))


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
    stations={};core_chains={}
    for entry in typ.get('internal_stations',[]):
        conn=entry.get('conn','')
        if not conn.startswith('bus:'):continue
        if entry.get('core'):
            # SUL0-PINFACE-1 per-hard-core pin-face chains u_ist_<bus>__<cores>_<g>_<j> (QC su_l): one chain per entry,
            # every chain of a bus has len(regs_um) stations; checked below by name, not by the u_ist_<bus>_<j> bus form
            core_chains.setdefault(conn,[]).append(len(entry['regs_um']));continue
        # one chain per bus at the deepest entry (kit_istations.bus_entries)
        stations[conn]=max(stations.get(conn,0),len(entry['regs_um']))
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
        # HBM-KITIST-1 11-12: opt-in station forms (kit_istation_forms.py).  station_trees: the receipt lists the tree nodes
        # u_ist_<bus>_t<id>, every reader sits `planned` stations from the face.  pad_landing: the chain has `stages`
        # (>= planned) stations, per-bit depths differ (receipt carries bit_depth).
        frows=[r for r in report if r.get('conn')==conn]
        tree=next((r for r in frows if r.get('station_tree')),None)
        padl=next((r for r in frows if r.get('pad_landing')),None)
        if tree:
            names=tree.get('stations',[])
            pads=sorted(set(re.findall(r'\bu_b(?:in|out)_'+re.escape(bus)+r'_pad\d+\b',text)))
            if tree.get('planned')!=count:problems.append(f'{conn}: tree receipt planned {tree.get("planned")}, expected {count}')
            bad=[d for d in tree['station_tree'].get('reader_stations',[]) if d!=count]
            if bad or not tree['station_tree'].get('reader_stations'):
                problems.append(f'{conn}: tree readers at {sorted(set(bad))} stations, bus latency is {count}')
            if re.search(r'\bu_ist_'+re.escape(bus)+r'_\d+\s*\(',text):
                problems.append(f'{conn}: plain chain stations beside a station tree')
            if len(names)!=len(set(names)) or len(names)!=tree['station_tree'].get('nodes'):
                problems.append(f'{conn}: tree receipt lists {len(names)} stations for {tree["station_tree"].get("nodes")} nodes')
            ks={n:[k for k in ['ot_dp_st','ot_dp_ste'] if len(_instance_type_spans(text,k,n))==1] for n in names}
            for n in names:
                if len(ks[n])!=1:problems.append(f'{n}: expected one canonical station instance, found {len(ks[n])}')
                required.append(dict(inst=n,master=ks[n][0] if len(ks[n])==1 else 'ot_dp_st',kind=conn))
            emitted_bus_stages[conn]=pads+[n for n in names if len(ks[n])==1]
            continue
        expect=padl['pad_landing']['stages'] if padl else count
        candidates=set(re.findall(r'\b(u_ist_'+re.escape(bus)+r'_\d+|u_b(?:in|out)_'+re.escape(bus)+r'_pad\d+)\b',text))
        kinds={name:[kind for kind in ['ot_dp_st','ot_dp_ste'] if len(_instance_type_spans(text,kind,name))==1] for name in sorted(candidates)}
        emitted=[name for name,ks in kinds.items() if len(ks)==1]
        emitted_bus_stages[conn]=emitted
        if len(emitted)!=expect:
            problems.append(f'{conn}: actual source emitted {len(emitted)} stages, expected {expect}')
        if require_receipt and not rows:
            problems.append(f'{conn}: missing kit_istations factory receipt for {count} stages')
            continue
        for row in rows:
            names=row.get('stations',[])
            if row.get('planned')!=count or len(names)!=expect:
                problems.append(f'{conn}: factory emitted {len(names)} stages, expected {expect}')
            for name in names:
                choices=kinds.get(name,[])
                if len(choices)!=1:problems.append(f'{name}: expected one canonical station instance, found {len(choices)}')
                required.append(dict(inst=name,master=choices[0] if len(choices)==1 else 'ot_dp_st',kind=conn))
    for conn,depths in core_chains.items():
        from gen_rtl import sv_id
        bus=sv_id(conn[4:]);count=max(depths)
        if len(set(depths))!=1:problems.append(f'{conn}: core chains carry unequal depths {sorted(set(depths))}')
        names=sorted(set(re.findall(r'\bu_ist_'+re.escape(bus)+r'__\w+?_\d+_\d+\b',text)))
        kinds={n:[k for k in ['ot_dp_st','ot_dp_ste'] if len(_instance_type_spans(text,k,n))==1] for n in names}
        emitted=[n for n,ks in kinds.items() if len(ks)==1]
        emitted_bus_stages[conn]=emitted
        stations[conn]=count
        rows=[r for r in report if r.get('conn')==conn]
        if len(emitted)!=count*len(depths):
            problems.append(f'{conn}: actual source emitted {len(emitted)} core-chain stages, expected {count*len(depths)}')
        if require_receipt and len(rows)!=len(depths):
            problems.append(f'{conn}: kit_istations factory receipt has {len(rows)} core chains, expected {len(depths)}')
        for row in rows:
            rn=row.get('stations',[])
            if row.get('planned')!=count or len(rn)!=count:
                problems.append(f'{conn}: factory emitted {len(rn)} core-chain stages, expected {count}')
            for name in rn:
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


def verify_component_source(receipt_path, *, context_plan,prepared_plan,bind_out,type_name,instance=None,asbuilt=None):
    """Use the approved read-only verifier; never turn LOCAL evidence into a bind stamp."""
    import bind_component
    report=bind_component.verify(receipt_path,context_plan=context_plan,prepared_plan=prepared_plan,
        bind_out=bind_out,type_name=type_name,instance=instance,asbuilt=asbuilt)
    if report.get('scope')!='LOCAL_COMPONENT' or report.get('source_preparation_only') is not True:
        raise ValueError('component verifier did not return explicit LOCAL source-preparation evidence')
    return report


def localize_bound(kd):
    """Give the kit a local copy of a bound module that bind kit-rtl left at the bind output (a variant bound type whose
    text it did not rewrite, e.g. QC sle_fe_v2).  kit_istations edits only kit-local copies, and the bind output is never
    touched.  Same bytes; only the kit's paths change.  Refuses a different file already at the local path."""
    kd=Path(kd);mfile=kd/'kit_rtl.json';man=json.loads(mfile.read_text())
    bound=next((Path(f) for f in man['files'] if Path(f).stem==man.get('bound_module')),None)
    if bound is None or bound.resolve().parent==kd.resolve():return None
    local=kd/bound.name
    if local.exists() and local.read_bytes()!=bound.read_bytes():
        raise ValueError(f'KIT_TOPOLOGY_REGENERATE: {local} differs from bound source {bound}')
    shutil.copyfile(bound,local)
    for fl in kd.glob('kit_rtl*.f'):
        lines=fl.read_text().splitlines(keepends=True)
        fl.write_text(''.join(str(local)+'\n' if ln.strip()==str(bound) else ln for ln in lines))
    man['files']=[str(local) if f==str(bound) else f for f in man['files']]
    mfile.write_text(json.dumps(man,indent=1))
    return local


def prepare_stations(plan,tn,rtl_dir,native_plan=None,asbuilt=None):
    """Canonical IN/core application and OUT reuse, once on a fresh kit copy."""
    import kit_istations
    raw=json.loads(Path(plan).read_text());kd=Path(rtl_dir).resolve()
    localize_bound(kd)
    man=json.loads((kd/'kit_rtl.json').read_text())
    context=json.loads(Path(native_plan).read_text()) if native_plan else raw
    manifest=asbuilt or man.get('asbuilt_manifest')
    component_report=None
    if man.get('component_proof'):
        component_report=verify_component_source(man['component_proof'],context_plan=native_plan or plan,
            prepared_plan=plan,bind_out=man['bind_out'],type_name=tn,asbuilt=manifest)
    if component_report is None and (tn not in context['partition_types'] or native_contract(context,asbuilt or man.get('asbuilt_manifest'),native_plan or plan)['types'][tn]!=native_contract(dict(raw,asbuilt=context.get('asbuilt',{})) if not (asbuilt or man.get('asbuilt_manifest')) else raw,asbuilt or man.get('asbuilt_manifest'),native_plan or plan)['types'][tn]):
        raise ValueError('KIT_TOPOLOGY_CONTEXT: selected topology differs from full native plan')
    if native_plan and component_report is None and digest(raw.get('reset'))!=digest(context.get('reset')):
        raise ValueError('KIT_TOPOLOGY_CONTEXT: selected reset topology differs from full native plan')
    if native_plan and component_report is None and has_topology(context,tn,manifest):
        if not man.get('bind_out') or not bind_matches(context,tn,man['bind_out'],manifest,native_plan):
            raise ValueError('KIT_TOPOLOGY_BIND_STALE: regenerate the canonical native bind for this full plan/asbuilt context')
    fingerprint=digest(dict(type=contract(raw)['types'][tn],reset=contract(context)['reset'],
                            asbuilt=hashlib.sha256(Path(manifest).read_bytes()).hexdigest() if manifest else None,
                            component=hashlib.sha256(Path(man['component_proof']).read_bytes()).hexdigest() if component_report else None))
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
    if component_report is not None:
        result.update(source_scope='LOCAL_COMPONENT',source_preparation_only=True,
                      component_report=component_report,global_bind=component_report['global_bind'])
    (kd/'kit_topology.json').write_text(json.dumps(result,indent=2)+'\n')
    if result['problems']:
        raise ValueError('KIT_TOPOLOGY_SOURCE: '+'; '.join(result['problems']))
    if not stamp.exists():
        stamp.write_text(json.dumps(dict(fingerprint=fingerprint,source_sha256=result['source_sha256'],
                         native_plan=str(native_plan or plan),asbuilt=manifest),indent=2)+'\n')
    return result


def stage_inventory(rtl_dir,kit,*,top=None):
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
    if top is None:
        top=json.loads((kit/'freeze.json').read_text()).get('module')
    if not isinstance(top,str) or not top:
        raise ValueError('KIT_TOPOLOGY_SOURCE: explicit selected parent module required')
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
        write_bind_receipt(raw,a.bind_out,a.asbuilt,plan_path=a.plan)
        return 0
    result=source_census(raw,a.type,a.rtl_dir)
    Path(a.receipt).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['raw_expected','raw_emitted','planned_bus_stages','emitted_bus_stages','problems']}))
    return 2 if result['problems'] else 0


if __name__=='__main__':
    raise SystemExit(main())
