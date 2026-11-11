"""Opt-in native realization of the same FIRM stations used by physical kits."""
import contextlib,io,json,shutil,copy
from pathlib import Path


def selected_buses(ab,*names):
    """Optional per-type OUT bus scope (asbuilt.internal_stations_buses {type: [bus]}).

    None = every OUT bus of the type (the original per-type opt-in).  A listed
    type realises only the named OUT buses natively; its other OUT stations stay
    KIT stations exactly as before the type was selected.
    """
    scope=(ab or {}).get('internal_stations_buses') or {}
    for n in names:
        if n in scope:return set(scope[n])
    return None


def face_first(e,typ,tol=2.0):
    """True unless the entry is provably written core -> face: to_um on the type outline and from_um inside it.
    Without an outline or both ends (older plans, unit fixtures) it keeps the face-first reading."""
    o=typ.get('outline_um');a,z=e.get('from_um'),e.get('to_um')
    if not o or not a or not z:return True
    edge=lambda p:min(p[0],p[1],o[0]-p[0],o[1]-p[1])<=tol
    return not (edge(z) and not edge(a))


def source_entries(typ,only=None):
    """Coalesce only identical OUT geometry; IN/core entries remain owned by their existing flow."""
    buses={x['name']:x for x in typ.get('buses',[])}
    if only is not None:
        missing=set(only)-{n for n,x in buses.items() if x.get('dir')=='out'}
        if missing:raise ValueError(f'internal_stations_buses names unknown OUT buses {sorted(missing)}')
    selected={}
    for e in typ.get('internal_stations',[]):
        if not e.get('conn','').startswith('bus:'):continue
        name=e['conn'][4:]
        if name not in buses:raise ValueError(f'internal station references unknown bus {name}')
        if buses[name]['dir']!='out':continue
        if only is not None and name not in only:continue
        geometry={k:v for k,v in e.items() if k!='note'}
        if name in selected:
            old={k:v for k,v in next(row for row in typ['internal_stations'] if row.get('conn')=='bus:'+name).items() if k!='note'}
            if geometry!=old:raise ValueError(f'conflicting OUT station geometry {name}')
        else:
            item=copy.deepcopy(e)
            # Plan bus geometry is written face->core even for OUT signals;
            # actual source stage zero must sit nearest the launching core.
            # STATION-FIX-HBM 11-11: reverse only an entry still written face first (from_um on the outline, to_um
            # inside it).  An entry already written core -> face (station_lint S7 fix, plan stationfix_1111) is
            # source ordered and kept, so both forms give the same native stations (idempotent).
            if item.get('capture')=='face flop' and item.get('launch')!='face flop' and face_first(item,typ):
                item['regs_um']=list(reversed(item['regs_um']))
                item['from_um'],item['to_um']=item.get('to_um'),item.get('from_um')
            selected[name]=item
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
        for e in source_entries(t,selected_buses(b.ab,p['type'],t.get('split_of',p['type']))):
            name=e['conn'][4:];bus=next(x for x in t['buses'] if x['name']==name)
            count=len(e['regs_um']);matches=[L for L in b.out_bus[part] if L['oname']==name]
            if len(matches)!=1:raise ValueError(f'native stations {part}.{name}: expected one outgoing lane')
            L=matches[0];raw=lanes.get(L.get('lane'),{})
            destination=b.parts.get(L.get('dst'),{})
            target=b.types.get(destination.get('type'),{})
            rows=[row for row in target.get('internal_stations',[]) if row.get('conn')=='bus:'+L.get('iname','')]
            incoming={len(row['regs_um']) for row in rows}
            # per-core rows of one bus merge to the deepest chain (kit_istations.bus_entries, KW-FIX-27); exact-site rows do not
            if len(incoming)>1 and any(row.get('bit_route') or 'bit_sites_um' in row or 'face_bit_sites_um' in row for row in rows):raise ValueError(f'native stations {L.get("lane")}: conflicting destination station counts')
            receiver=max(incoming,default=0)
            if int(raw.get('fixed_cycles',0))!=count+receiver:raise ValueError(f'native stations {L.get("lane")}: fixed_cycles must equal source {count} + destination {receiver}')
            base=2+sum(h['stations'] for h in L.get('ft',[]))+int(L.get('clock_landing_cycles',0))
            if L['cycles']<base+count:raise ValueError('native stations exceed priced lane depth')
            L['internal_source_cycles']=count


def materialize(b,tn,file):
    typ=b.types[tn];original=typ.get('split_of',tn)
    selected=set(b.ab.get('internal_stations_types',[]))
    if tn not in selected and original not in selected:return
    typ=copy.deepcopy(typ)
    typ['internal_stations']=source_entries(typ,selected_buses(b.ab,tn,original))
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
