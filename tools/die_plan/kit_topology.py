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
        candidates=set(re.findall(r'\b(u_ist_'+re.escape(bus)+r'_\d+|u_b(?:in|out)_'+re.escape(bus)+r'_pad\d+)\b',text))
        emitted=[name for name in sorted(candidates) if len(_instance_type_spans(text,'ot_dp_st',name))==1]
        emitted_bus_stages[conn]=emitted
        if len(emitted)!=count:
            problems.append(f'{conn}: actual source emitted {len(emitted)} stages, expected {count}')
        rows=[r for r in report if r.get('conn')==conn]
        if require_receipt and not rows:
            problems.append(f'{conn}: missing kit_istations factory receipt for {count} stages')
            continue
        for row in rows:
            names=row.get('stations',[])
            if row.get('planned')!=count or len(names)!=count:
                problems.append(f'{conn}: factory emitted {len(names)} stages, expected {count}')
            for name in names:
                hits=_instance_type_spans(text,'ot_dp_st',name)
                if len(hits)!=1:problems.append(f'{name}: expected one emitted ot_dp_st, found {len(hits)}')
                required.append(dict(inst=name,master='ot_dp_st',kind=conn))
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
    data['required_instances']=census['required_instances']
    receipt.write_text(json.dumps(data,indent=2)+'\n')
    shutil.copyfile(helper,receipt.parent/'kit_assembly.py')


def main():
    import argparse,sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    census=sub.add_parser('census');census.add_argument('plan');census.add_argument('type');census.add_argument('rtl_dir');census.add_argument('--receipt',required=True)
    stamp=sub.add_parser('stamp-bind');stamp.add_argument('plan');stamp.add_argument('bind_out');stamp.add_argument('--asbuilt')
    a=p.parse_args();raw=json.loads(Path(a.plan).read_text())
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
