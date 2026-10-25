"""Opt-in native realization of the same FIRM stations used by physical kits."""
import contextlib,io,json,shutil
from pathlib import Path


def annotate(b):
    selected=set(b.ab.get('internal_stations_types', []))
    if not selected:return
    unknown=selected-set(b.types)
    if unknown:raise ValueError(f'internal stations unknown types: {sorted(unknown)}')
    lanes={x['id']:x for x in b.plan.get('lanes',[])}
    for part,p in b.parts.items():
        if p['type'] not in selected:continue
        t=b.types[p['type']]
        for e in t.get('internal_stations',[]):
            if not e.get('conn','').startswith('bus:'):raise ValueError('native stations supports explicit bus entries only')
            name=e['conn'][4:];bus=next(x for x in t['buses'] if x['name']==name)
            if bus['dir']!='out':raise ValueError('native source station relocation requires an out bus')
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
    import kit_istations
    file=Path(file);kd=file.parent.parent/'native_internal_stations'/tn;kd.mkdir(parents=True,exist_ok=True)
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
