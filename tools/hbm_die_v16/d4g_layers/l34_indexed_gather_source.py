#!/usr/bin/env python3
"""Compose the real gather endpoint after LOAD, with actual observation and exact IJS views.

The direct-bank fixture ages are input parameters, never a die route-age claim.
Placement, clock/reset, host guard and current-source token qualification remain open.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/hbm_static'))
from bind_indexed_gather import bind


def apply(graph, read_sample, write_commit, records):
    c,report=bind(graph,read_sample,write_commit)
    observed=[]
    obs=c['instances']['obs_SW'];lo=obs['params']['N']
    for item in list(c['open_outputs']):
        n,p,b=item
        if n!='su_indexed_gather':continue
        assert p in ('active','done','edge_index','engine_busy','engine_done','engine_start','descriptor'),p
        c['edges'].append(dict(name='l34_observe_'+p,bits=b,source=[n,p,0,b],sink=['obs_SW','obs',lo,lo+b],
            clock='stream',ready_or_credit=False,allowed_exception=None,
            basis='Actual F20 gather debug export read by the existing host-query observer',region='su_indexed_gather'))
        observed.append(dict(port=p,lo=lo,bits=b));lo+=b;c['open_outputs'].remove(item)
    assert lo<=512,lo
    obs['params']['N']=lo;obs['ports']['obs']['bits']=lo;obs['force_synth']=True
    obs.pop('physical_view',None);obs.pop('closed_record',None)
    for name in ('host_status','host_cp_ingress'):
        i=c['instances'][name];i['force_synth']=True
        i.pop('physical_view',None);i.pop('closed_record',None)
    for n,i in c['instances'].items():
        if n=='su_indexed_gather' or n.startswith('indexed_gather_select_'):
            i['slot']=n;i['force_synth']=True
    # SAFE_STREAM remains explicit even before the corresponding exact view is collected.
    for q in ('SW','SE','NW','NE'):
        i=c['instances']['cxij_'+q+'_s'];i['params']['SAFE_STREAM']=1;i['force_synth']=True
        i.pop('physical_view',None);i.pop('closed_record',None)
    chosen=[]
    for record in records:
        record=record.resolve()
        r=json.loads(record.read_text());assert r['status']=='CLOSED' and r['block']=='ot_hbm_su_static_cxport_ij_s'
        assert r['job_spec']['ref_tile'] is True
        kit=ROOT/'physical/ref_tile'/r['job'].split('-')[0];spec=json.loads((kit/'spec.json').read_text());params=spec['params']
        qid=params['QID'];q=('SW','SE','NW','NE')[qid];n='cxij_'+q+'_s';i=c['instances'][n]
        assert params['SAFE_STREAM']==1 and all(i['params'].get(k)==v for k,v in params.items()),(n,params,i['params'])
        source=ROOT/i['source'];qualified=subprocess.check_output(['git','-C',str(ROOT),'show',r['source_commit']+':'+i['source']])
        assert source.read_bytes()==qualified,(n,'qualified source mismatch')
        view=kit/'views'/i['master'];assert (view/(i['master']+'.lef')).is_file(),view
        i.pop('force_synth',None);i['physical_view']=str(view.relative_to(ROOT));i['closed_record']=str(record.relative_to(ROOT))
        chosen.append(dict(instance=n,QID=qid,params=params,record=i['closed_record'],view=i['physical_view'],source_sha256=hashlib.sha256(qualified).hexdigest()))
    c['masters']=dict(sorted(collections.Counter(i['master'] for i in c['instances'].values()).items()))
    c['summary']['clock_reset_ports']=len(c['clock_resets'])
    report.update(observed_exports=observed,observer_SW_width=lo,exact_closed_ijs=chosen,
        physical_view_alias=False,source_only_placement_open=True)
    return c,report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('input','output','report'):p.add_argument(n,type=Path)
    p.add_argument('--read-sample',type=int,required=True);p.add_argument('--write-commit',type=int,required=True)
    p.add_argument('--closed-record',type=Path,action='append',default=[])
    a=p.parse_args();c,r=apply(json.loads(a.input.read_text()),a.read_sample,a.write_commit,a.closed_record)
    for path,value in ((a.output,c),(a.report,r)):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=1)+'\n')
    print('GATHER_SOURCE_ATTACHED',len(r['banks']),'banks; observed bits',sum(x['bits'] for x in r['observed_exports']),'; exact CLOSED IJS',len(r['exact_closed_ijs']),'; die ages and placement OPEN')
