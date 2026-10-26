"""Opt-in native realization of the same FIRM stations used by physical kits."""
import contextlib,io,json,shutil,copy
from pathlib import Path


def source_entries(typ):
    """Coalesce only identical OUT geometry; IN/core entries remain owned by their existing flow."""
    buses={x['name']:x for x in typ.get('buses',[])}
    selected={}
    for e in typ.get('internal_stations',[]):
        if not e.get('conn','').startswith('bus:'):continue
        name=e['conn'][4:]
        if name not in buses:raise ValueError(f'internal station references unknown bus {name}')
        if buses[name]['dir']!='out':continue
        geometry={k:v for k,v in e.items() if k!='note'}
        if name in selected:
            old={k:v for k,v in selected[name].items() if k!='note'}
            if geometry!=old:raise ValueError(f'conflicting OUT station geometry {name}')
        else:selected[name]=copy.deepcopy(e)
    return list(selected.values())


def annotate(b):
    selected=set(b.ab.get('internal_stations_types', []))
    if not selected:return
    unknown=selected-set(b.types)
    if unknown:raise ValueError(f'internal stations unknown types: {sorted(unknown)}')
    lanes={x['id']:x for x in b.plan.get('lanes',[])}
    for part,p in b.parts.items():
        if p['type'] not in selected:continue
        t=b.types[p['type']]
        for e in source_entries(t):
            name=e['conn'][4:];bus=next(x for x in t['buses'] if x['name']==name)
            count=len(e['regs_um']);matches=[L for L in b.out_bus[part] if L['oname']==name]
            if len(matches)!=1:raise ValueError(f'native stations {part}.{name}: expected one outgoing lane')
            L=matches[0];raw=lanes.get(L.get('lane'),{})
            if int(raw.get('fixed_cycles',0))!=count:raise ValueError(f'native stations {L.get("lane")}: fixed_cycles must equal {count}')
            base=2+sum(h['stations'] for h in L.get('ft',[]))
            if L['cycles']<base+count:raise ValueError('native stations exceed priced lane depth')
            L['internal_source_cycles']=count


def materialize(b,tn,file):
    typ=b.types[tn];original=typ.get('split_of',tn)
    if original not in set(b.ab.get('internal_stations_types',[])):return
    typ=copy.deepcopy(typ)
    typ['internal_stations']=source_entries(typ)
    if not typ['internal_stations']:return
    # Binding removes proven constant/unused payload bits from the functional
    # lane. The native station carries that exact bound payload plus its epoch,
    # rather than the wider planning pin capacity. Keep the public plan intact.
    widths={}
    for part in b.by_type.get(tn,[]):
        for lane in b.out_bus.get(part,[]):
            widths.setdefault(lane['oname'],set()).add(int(lane['width']))
    for entry in typ['internal_stations']:
        name=entry['conn'][4:]
        actual=widths.get(name,set())
        if len(actual)!=1:raise ValueError(f'native stations {tn}.{name}: no unique bound payload width')
        width=next(iter(actual));bus=next(v for v in typ['buses'] if v['name']==name)
        if not 0<width<=int(bus['width']):raise ValueError(f'native stations {tn}.{name}: bound width exceeds plan capacity')
        bus['width']=width
    import kit_istations
    file=Path(file).resolve();kd=file.parent.parent/'native_internal_stations'/tn;kd.mkdir(parents=True,exist_ok=True)
    local=kd/file.name;shutil.copyfile(file,local)
    plan=kd/'plan.json';plan.write_text(json.dumps({'partition_types':{tn:typ}}))
    man=kd/'kit_rtl.json';man.write_text(json.dumps({'bound_module':file.stem,'files':[str(local)]}))
    with contextlib.redirect_stdout(io.StringIO()):kit_istations.main([str(plan),tn,str(kd),'--apply'])
    report=json.loads(man.read_text())['kit_istations']
    expected={e['conn']:len(e['regs_um']) for e in typ.get('internal_stations',[])}
    for row in report:
        if 'conn' not in row:continue
        if row['planned']!=expected[row['conn']] or len(row['stations'])!=row['planned']:raise ValueError('native station materialization count mismatch')
    shutil.copyfile(local,file)
    (kd/'receipt.json').write_text(json.dumps(dict(type=tn,entries=report,pricing='source stations replace equal receiver padding; total lane cycles unchanged'),indent=1)+'\n')
