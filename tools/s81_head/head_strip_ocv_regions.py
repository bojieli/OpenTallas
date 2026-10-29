#!/usr/bin/env python3
"""Bind fresh physical-pin OCV rows to HK4 logical clock regions.

No clock timing is changed: retain every measured tap pair bound, discard only
same-region links which belong to intra-region STA, and rename the endpoints
to the explicit region IDs used by CA origins.
"""
import argparse,json
from pathlib import Path

def convert(ocv,table,mapping):
    ports={r['port']:r for r in table['ports']}
    out=dict(ocv);out['corners']={}
    for key,c in ocv['corners'].items():
        if c.get('all') is None:continue
        rows=[]
        for r in c['all']:
            if r['port'] not in ports:
                assert mapping[r['src']]==mapping[r['dst']],('undeclared crossing',r['port'])
                continue
            pr=ports[r['port']]
            assert (r['src'],r['dst'])==(pr['src'],pr['dst']),('stale endpoints',r['port'])
            nr=dict(r,physical_src=r['src'],physical_dst=r['dst'],src=mapping[r['src']],dst=mapping[r['dst']])
            assert nr['src']!=nr['dst']
            rows.append(nr)
        assert {r['port'] for r in rows}==set(ports),('missing fresh crossing rows',key)
        out['corners'][key]=dict(c,all=rows,crossings=len(rows),worst_margin_ps=min(r['margin_ps'] for r in rows),under_100=sum(r['margin_ps']<100 for r in rows),under_0=sum(r['margin_ps']<0 for r in rows))
    out['region_scope']={'parts':len(mapping),'regions':len(set(mapping.values())),'crossings':len(ports),'source':'explicit HK4 part_region map; physical OCV bounds unchanged'}
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ocv');p.add_argument('--table',required=True);p.add_argument('--regions',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    out=convert(json.load(open(a.ocv)),json.load(open(a.table)),json.load(open(a.regions))['part_region']);Path(a.out).write_text(json.dumps(out,indent=1));print(json.dumps(out['region_scope']))
if __name__=='__main__':main()
