#!/usr/bin/env python3
"""Extract actual mapped virtual START/RAW QN gates and all source loads.

No physical coordinates are fabricated. Missing aliases are resolved through the
actual named terminal source FF and its real mapped inverter, not net-name guesses.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path


def extract(assembly,mapped):
    p=mapped['modules']['ot_die_start_stages'];cells={n:c for n,c in p['cells'].items() if c['type']!='$scopeinfo'}
    outputpins={'Y','QN','SN','CON'};loads=collections.defaultdict(list)
    for n,c in cells.items():
        for pin,bits in c['connections'].items():
            if pin not in outputpins:
                for b in bits:loads[b].append(dict(kind='iterm',instance=n,pin=pin,master=c['type']))
    for n,v in p['ports'].items():
        if v['direction']=='output':
            for b in v['bits']:loads[b].append(dict(kind='bterm',name=n))
    records=[];stages=assembly['stages'];expected_ff=int(assembly['root_settle']).bit_length()+1
    for s in stages:
        i=s['id'];pref='u_st_'+i+'.';root=s['root']
        if s['pad']!=0:raise ValueError('PAD terminal FF extraction not implemented; fail closed')
        if not root:expected_ff+=5+2*int(s['edge_fall'])
        for signal in ('start','raw'):
            if root and signal=='raw':
                records.append(dict(region=s['region'],signal=signal,source='GLOBAL_RAW_INPUT',physical_home=None,
                                    holds=['actual external raw driver and local load inventory required']))
                continue
            prefix=pref+('start$_' if root else 's2$_') if signal=='start' else 'u_rst_'+i+'.r1$_'
            found=[(n,c)for n,c in cells.items() if n.startswith(prefix) and c['type'].startswith('DFF')]
            if len(found)!=1:raise ValueError(('source FF absent/ambiguous',s['region'],signal,found))
            ff,c=found[0];qn=c['connections']['QN'];assert len(qn)==1
            gates=[(n,x)for n,x in cells.items() if x['type'].startswith('INVx') and x['connections']['A']==qn]
            if len(gates)!=1:raise ValueError(('source QN inverter absent/ambiguous',ff,gates))
            inv,g=gates[0];ys=g['connections']['Y'];assert len(ys)==1
            sinks=loads[ys[0]]; buf2=[z for z in sinks if z.get('master')=='BUFx2_ASAP7_75t_R']
            records.append(dict(region=s['region'],stage_id=i,signal=signal,ff_instance=ff,ff_master=c['type'],
                ff_clock_bit=c['connections']['CLK'][0],qn_bit=qn[0],instance=inv,master=g['type'],output_bit=ys[0],
                all_output_sinks=sinks,kept_buf2_instances=[z['instance']for z in buf2],
                ff_xy_um=None,xy_um=None,qn_pin_um=None,input_pin_um=None,output_pin_um=None,
                holds=['actual legal source/gate/site allocation','whole-prefix clock load repricing','all actual local reset loads must be modeled']))
    ffcount=sum(c['type'].startswith('DFF') for c in cells.values())
    if ffcount!=expected_ff:raise ValueError(('mapped FF/CA source count mismatch',ffcount,expected_ff))
    return dict(schema='ot_start_source_inventory/1',physical_qualified=False,virtual_stages=len(stages),mapped_flops=ffcount,
                expected_source_flops=expected_ff,master_census=dict(collections.Counter(c['type']for c in cells.values())),
                source_records=records,all_cells=cells,
                holds=['native output BTerms are interfaces, not complete native-reader loads',
                       'actual global prefix+new clock tree source/load ownership','source homes/routes/PG not assigned'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('assembly');p.add_argument('mapped');p.add_argument('--out',required=True)
    a=p.parse_args();ab=Path(a.assembly).read_bytes();mb=Path(a.mapped).read_bytes();d=extract(json.loads(ab),json.loads(mb))
    d['assembly_sha256']=hashlib.sha256(ab).hexdigest();d['mapped_json_sha256']=hashlib.sha256(mb).hexdigest()
    Path(a.out).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:d[k]for k in ('virtual_stages','mapped_flops','expected_source_flops','physical_qualified')}))

if __name__=='__main__':main()
