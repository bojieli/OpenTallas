#!/usr/bin/env python3
"""405um lower bounds from explicit actual-native bit edges and physical pin bindings.

Does not choose roles, insert RTL, relocate cores, or authorize routing. Transport
sequences must follow actual manifest bit identities and the supplied source rules.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_bit(manifest,endpoint,direction):
    inst=manifest[endpoint['instance']]
    if inst['master']!=endpoint['expected_master']:raise ValueError('native master differs from explicit endpoint binding')
    port=inst['ports'][endpoint['port']]
    if port['direction']!=direction:raise ValueError('native endpoint direction differs from actual source')
    bit=endpoint['bit']
    if not isinstance(bit,int) or bit<0:raise ValueError('native bit must be a nonnegative index')
    for seg in port['segments']:
        width=seg[3]-seg[2]+1 if seg[0]=='n' else seg[1]
        if bit<width:
            if seg[0]!='n':raise ValueError('endpoint is a literal, not a driven variable source bit')
            return (seg[1],seg[2]+bit)
        bit-=width
    raise ValueError('native bit outside actual port width')


def history_stages(manifest,contract,edge):
    current=native_bit(manifest,edge['source_native'],'output');stages=0
    for step in edge['history']:
        name=step['instance'];actual=contract['transport_instances'][name]
        if manifest[name]['master']!=actual['master']:raise ValueError('transport master differs from actual source contract')
        if actual['rule']['map'].get(step['output_port'])!=step['input_port']:raise ValueError('transport ports are not an actual source map')
        if step['input_bit']!=step['output_bit']:raise ValueError('transport rule does not authorize bit reordering')
        base=dict(instance=name,expected_master=actual['master'])
        a=native_bit(manifest,dict(base,port=step['input_port'],bit=step['input_bit']),'input')
        z=native_bit(manifest,dict(base,port=step['output_port'],bit=step['output_bit']),'output')
        if a!=current:raise ValueError('transport history is not a continuous actual native bit path')
        count=actual['stages']
        if not isinstance(count,int) or count<0:raise ValueError('actual transport stage count invalid')
        stages+=count;current=z
    if current!=native_bit(manifest,edge['sink_native'],'input'):raise ValueError('actual source/history does not reach the declared native sink bit')
    return stages


class Pins:
    def __init__(self,plan,pin_root):self.plan=plan;self.root=Path(pin_root);self.tables={}
    def point(self,endpoint):
        t=self.plan['partition_types'][endpoint['type']]
        found=[h for h in t['hard_cores'] if h['inst']==endpoint['core']]
        if len(found)!=1:raise ValueError('physical core identity is not unique')
        h=found[0]
        if h['module']!=endpoint['expected_module']:raise ValueError('physical core master differs from explicit binding')
        file=self.root/h['pins_file'];key=str(file)
        if key not in self.tables:self.tables[key]=(digest(file),{p['name']:p for p in json.loads(file.read_text())})
        sha,table=self.tables[key]
        if sha!=endpoint['pins_sha256']:raise ValueError('bound physical pin table changed')
        p=table[endpoint['pin']];x,y=p['x'],p['y'];w,hh=h['outline_um']
        orient=h.get('orient','R0')
        if orient not in ['R0','MX','MY','R180']:raise ValueError('unsupported physical orientation')
        if orient in ['MY','R180']:x=w-x
        if orient in ['MX','R180']:y=hh-y
        ox,oy=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0])
        x,y=ox+dx+x,oy+dy+y
        parts=[p for p in self.plan['partitions'] if p['name']==endpoint['partition']]
        if len(parts)!=1 or parts[0]['type']!=endpoint['type']:raise ValueError('physical partition/type binding differs from actual plan')
        part=parts[0];w,hh=t['outline_um'];orient=part.get('orient','R0')
        if orient not in ['R0','MX','MY','R180']:raise ValueError('unsupported partition orientation')
        if orient in ['MY','R180']:x=w-x
        if orient in ['MX','R180']:y=hh-y
        return [part['origin_um'][0]+x,part['origin_um'][1]+y]


def analyze(plan,pin_root,manifest,history,ledger):
    if ledger.get('authority')!='ACTUAL_NATIVE_BIT_BINDING':raise ValueError('requires explicit actual native bit binding authority')
    if not ledger['edges']:raise ValueError('no explicitly bound native edges supplied')
    pins=Pins(plan,pin_root);rows=[];groups=collections.defaultdict(list);seen=set()
    for edge in ledger['edges']:
        row={'id':edge['id'],'bundle':edge['bundle'],'kind':edge['kind'],'bundle_bit':edge['bundle_bit']}
        try:
            if edge['id'] in seen:raise ValueError('duplicate edge id')
            seen.add(edge['id'])
            if edge['kind'] not in ['signal','clock']:raise ValueError('explicit signal or clock kind required')
            if not edge.get('epoch_binding'):raise ValueError('current source/calendar epoch binding is missing')
            stages=history_stages(manifest,history,edge)
            a=pins.point(edge['source_pin']);z=pins.point(edge['sink_pin'])
            distance=sum(abs(x-y) for x,y in zip(a,z));minimum=max(0,math.ceil((distance-1e-9)/405)-1)
            row.update(verdict='BOUND_LOWER_BOUND',source_um=a,sink_um=z,l1_um=distance,minimum_intermediate_sites=minimum,actual_transport_stages=stages)
            if edge['kind']=='signal':row['extra_signal_stage_lower_bound']=max(0,minimum-stages)
            else:row['clock_qualification']='Buffer/topology obligation only; signal FF stages and clock latency cannot be interchanged.'
        except (ValueError,KeyError,TypeError,IndexError) as e:row.update(verdict='FAIL',reason=str(e))
        rows.append(row);groups[(edge['bundle'],edge['kind'])].append(row)
    bundles=[]
    for name,spec in ledger['bundles'].items():
        kind=spec['kind'];items=groups.pop((name,kind),[]);good=[r for r in items if r['verdict']=='BOUND_LOWER_BOUND']
        indices=[r['bundle_bit'] for r in items]
        complete=sorted(indices)==list(range(spec['width'])) and len(good)==spec['width']
        row=dict(bundle=name,kind=kind,expected_bits=spec['width'],bound_bits=len(good),verdict='LOWER_BOUND_ONLY' if complete else 'FAIL_INCOMPLETE_BUNDLE')
        if good:
            row.update(max_l1_um=max(r['l1_um'] for r in good),transport_stage_histogram=dict(collections.Counter(r['actual_transport_stages'] for r in good)))
            if complete and kind=='signal':row['minimum_extra_uniform_stages']=max(r['extra_signal_stage_lower_bound'] for r in good)
        bundles.append(row)
    for (name,kind),items in groups.items():bundles.append(dict(bundle=name,kind=kind,verdict='FAIL_UNDECLARED_BUNDLE',bound_bits=len(items)))
    failed_bundles=sum(r['verdict'].startswith('FAIL') for r in bundles)
    failures=sum(r['verdict']=='FAIL' for r in rows)
    return dict(schema='opentallas.hbm.native_edge_bounds.v1',verdict='FAIL' if failures or failed_bundles else 'LOWER_BOUNDS_ONLY',failed_edges=failures,failed_bundles=failed_bundles,rows=rows,bundles=bundles,qualification='Per-bit endpoint L1 lower bounds only; no whole-source completeness is inferred from a bound subset. No obstacle path, shared FF/clock capacity, PG/hold, current calendar compilation or physical acceptance is established. Failed edges retained; no RTL/plan mutation.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['plan','pin_root','manifest','history','bindings','out']:p.add_argument('--'+name.replace('_','-'),required=True)
    a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('refusing existing output')
    ledger=json.load(open(a.bindings))
    for key,file in [('plan_sha256',a.plan),('manifest_sha256',a.manifest),('history_sha256',a.history)]:
        if ledger.get(key)!=digest(file):raise ValueError('explicit binding '+key+' differs from actual input')
    report=analyze(json.load(open(a.plan)),a.pin_root,json.load(open(a.manifest)),json.load(open(a.history)),ledger)
    out.write_text(json.dumps(report,indent=1)+'\n');print(report['verdict'],'failed_edges',report['failed_edges']);return report['verdict']=='FAIL'
if __name__=='__main__':raise SystemExit(main())
