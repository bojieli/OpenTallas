"""Prove actual VP HW/WL words to both actual VN input halves; no local latency."""
import argparse,json
from pathlib import Path
from layer_prog.bound_die import BoundDie,object_items
from layer_prog.bound_entry_transport import BufferSinks
from layer_prog.bound_return_transport import check_variant,desc_of
FIELDS=dict(hw_v=1,hw_j=3,hw_hf=1,hw_d=256,wl_v=1,wl_i=3,wl_d=128)


def collect(die,entry):
    if entry.get('verdict')!='PASS_BOUND_TRANSPORT' or entry['die_sha256']!=die.die_sha or entry['source_asbuilt_sha256']!=die.inventory['source_asbuilt_sha256']:
        raise ValueError('VP/VN transport needs identical passing entry source')
    rows=[];seen=set()
    for leaf in entry['leaves']:
        vp=leaf['vp'];base=vp.removesuffix('.u_vp')
        if base==vp:raise ValueError('actual VP instance ABI differs')
        row=dict(slice=leaf['slice'],leaf=leaf['leaf'],vp=vp,halves={})
        try:
            for half in ('a','b'):
                target=base+'.u_vn.u_'+half;meta=die.inventory['leaf_interfaces'].get(target,{})
                if meta.get('module')!='ot_s81sl_vn_'+half or meta.get('kind')!='leaf' or target in seen:
                    raise ValueError('one distinct actual VN atomic half required: '+target)
                seen.add(target);fields={}
                for port,width in FIELDS.items():
                    if meta.get('ports',{}).get(port)!={'dir':'input','width':width}:
                        raise ValueError('actual VN half port ABI differs: '+target+'.'+port)
                    ages=set()
                    for bit in range(width):
                        pin=f'{target}.{port}[{bit}]';check_variant(die,pin);d=desc_of(die,pin)
                        offset=128 if port=='wl_d'and half=='b'else 0
                        net=die.units[vp]['ports'][port]['bits'][bit+offset]
                        pins=die.inventory['drivers'].get(str(net),[])
                        if len(pins)!=1:raise ValueError('VP output bit has ambiguous/missing actual source driver')
                        expected=pins[0]
                        check_variant(die,expected)
                        if d[1]!=expected:raise ValueError(f'{pin}: bound source {d[1]} differs from {expected}')
                        ages.add(d[2])
                    if len(ages)!=1:raise ValueError('VP/VN field ages differ within word')
                    fields[port]=dict(age_edges=ages.pop(),bits=width,source_output_bit_offset=(128 if port=='wl_d'and half=='b'else 0))
                for group in [('hw_v','hw_j','hw_hf','hw_d'),('wl_v','wl_i','wl_d')]:
                    if len({fields[p]['age_edges']for p in group})!=1:raise ValueError('VP/VN valid and payload ages disagree')
                row['halves'][half]=dict(vn=target,fields=fields,HW_transport_edges=fields['hw_v']['age_edges'],WL_transport_edges=fields['wl_v']['age_edges'])
            row['status']='PASS'
        except (KeyError,ValueError)as exc:row.update(status='BLOCKED',reason=str(exc))
        rows.append(row)
    ok=len(rows)==80 and all(r['status']=='PASS'for r in rows)
    return dict(schema='opentallas.s81.bound_vp_vn_transport.v1',verdict='PASS_BOUND_VP_VN_TRANSPORT'if ok else'BLOCKED',
        die_sha256=die.die_sha,source_asbuilt_sha256=die.inventory['source_asbuilt_sha256'],leaves=rows,
        scope='exact VP HW256/control and split WL128/control to actual VN_a/VN_b input pins only; VN local commit/capture separate',
        readiness_qualified=False,native_job_sealed=False,full_token=False,added_rtl_cycles=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bound','inventory','entry','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior output')
    die=BoundDie(a.bound,a.inventory);interfaces=die.inventory['leaf_interfaces'];wanted=set()
    for name,meta in interfaces.items():
        width=BufferSinks.width(meta)
        if width is not None:wanted.update(f'{name}.A[{i}]'for i in range(width))
        elif meta.get('module')in('ot_s81sl_vn_a','ot_s81sl_vn_b'):
            wanted.update(f'{name}.{p}[{i}]'for p,w in FIELDS.items()for i in range(w))
    raw={k:v for k,v in object_items(a.bound/'bind_sinks.json')if k in wanted}
    die.sinks=BufferSinks(raw,interfaces)
    result=collect(die,json.loads(a.entry.read_text()))
    # Two narrow controls use the just-traced source graph; no second bind scan.
    if result['verdict']=='PASS_BOUND_VP_VN_TRANSPORT':
        row=result['leaves'][0];target=row['halves']['a']['vn']+'.hw_d[0]'
        original=die.sinks.get(target);controls={}
        for label,desc in [('wrong_payload_bit',['pin',original[1].rsplit('[',1)[0]+'[1]',original[2],original[3]]),('wrong_payload_age',['pin',original[1],original[2]+1,original[3]])]:
            die.sinks.cache[target]=desc
            failed=collect(die,json.loads(a.entry.read_text()))
            controls[label]=failed['verdict']=='BLOCKED'
            die.sinks.cache[target]=original
        if not all(controls.values()):raise ValueError('VP/VN transport control escaped')
        result['controls_caught']=controls
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print(result['verdict'],len(result['leaves']),'leaves',sum(r['status']!='PASS'for r in result['leaves']),'blocked')
    return 0 if result['verdict']=='PASS_BOUND_VP_VN_TRANSPORT'else 2
if __name__=='__main__':raise SystemExit(main())
