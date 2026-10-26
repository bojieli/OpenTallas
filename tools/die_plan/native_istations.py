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
            old={k:v for k,v in next(row for row in typ['internal_stations'] if row.get('conn')=='bus:'+name).items() if k!='note'}
            if geometry!=old:raise ValueError(f'conflicting OUT station geometry {name}')
        else:
            item=copy.deepcopy(e)
            # Plan bus geometry is written face->core even for OUT signals;
            # actual source stage zero must sit nearest the launching core.
            if item.get('capture')=='face flop' and item.get('launch')!='face flop':
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
        for e in source_entries(t):
            name=e['conn'][4:];bus=next(x for x in t['buses'] if x['name']==name)
            count=len(e['regs_um']);matches=[L for L in b.out_bus[part] if L['oname']==name]
            if len(matches)!=1:raise ValueError(f'native stations {part}.{name}: expected one outgoing lane')
            L=matches[0];raw=lanes.get(L.get('lane'),{})
            destination=b.parts.get(L.get('dst'),{})
            target=b.types.get(destination.get('type'),{})
            incoming={len(row['regs_um']) for row in target.get('internal_stations',[]) if row.get('conn')=='bus:'+L.get('iname','')}
            if len(incoming)>1:raise ValueError(f'native stations {L.get("lane")}: conflicting destination station counts')
            receiver=next(iter(incoming),0)
            if int(raw.get('fixed_cycles',0))!=count+receiver:raise ValueError(f'native stations {L.get("lane")}: fixed_cycles must equal source {count} + destination {receiver}')
            base=2+sum(h['stations'] for h in L.get('ft',[]))
            if L['cycles']<base+count:raise ValueError('native stations exceed priced lane depth')
            L['internal_source_cycles']=count


def materialize(b,tn,file):
    typ=b.types[tn];original=typ.get('split_of',tn)
    selected=set(b.ab.get('internal_stations_types',[]))
    if tn not in selected and original not in selected:return
    typ=copy.deepcopy(typ)
    typ['internal_stations']=source_entries(typ)
    if not typ['internal_stations']:return
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
