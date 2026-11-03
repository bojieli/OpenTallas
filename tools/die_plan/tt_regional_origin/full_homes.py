#!/usr/bin/env python3
"""Prepare a complete TT FF-position intent and fail-closed native-name join.

A fresh RTL stage cannot preserve an all-pair point model with only moved-cell
hints. This includes every retained reference FF, replaces three origin states
with the16 regional/raw states, and requires exact new mapped FF coverage.
It emits metadata only; no native placement hook is silently installed.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
try:
    from .native_clock_join import source_expectation
except ImportError:
    from native_clock_join import source_expectation


def read(path):
    with (gzip.open(path,'rt') if str(path).endswith('.gz') else open(path)) as f:return json.load(f)


def prepare(reference,homes,source,raw):
    root=Path(__file__).resolve().parents[3]
    spec=importlib.util.spec_from_file_location('tt_geom',root/'tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    d=g.Design(reference);moves={r['name']:r['xy'] for r in homes};out=[];removed=[]
    for c in d.cells.values():
        if c[0]!='S' or c[1]=='REAL_MACRO_PORT':continue
        name=c[6]
        if any(name.startswith('u_bound.u_cland_origin/'+s+'$') for s in ('s1','s2','pd')):
            removed.append(name);continue
        xy=moves.pop(name,list(g.ctr(c)));w,h=c[4]-c[2],c[5]-c[3]
        out.append(dict(model_name=name,master=c[1],width_um=w,height_um=h,xy=xy,
                        source_identity=source_expectation(name),role='retained_reference_ff'))
    if moves:raise ValueError('Homes include unknown reference FFs: '+str(len(moves)))
    if len(removed)!=3:raise ValueError('Exact selected three origin states were not found')
    for row in source+raw:
        r,stage=row['region'],row['stage']
        name=(f'u_bound.g_tt_raw_regions.g_region[{r}].u_raw_copy/q' if stage=='raw' else f'u_bound.u_cland_origin/g_on.g_region[{r}].{stage}')
        b=row['box'];out.append(dict(model_name=name,master=row['master'],width_um=b[2]-b[0],height_um=b[3]-b[1],xy=row['xy'],source_identity=source_expectation(name),role='regional_replacement_or_raw_copy'))
    if len(source)!=12 or len(raw)!=4:raise ValueError('All16 regional states are mandatory')
    bad=[]
    for row in out:
        x,y=row['xy'];llx=x-row['width_um']/2;lly=y-row['height_um']/2
        if abs(llx/.054-round(llx/.054))>1e-5 or abs(lly/.27-round(lly/.27))>1e-5:bad.append(row['model_name'])
    return dict(schema='opentallas.tt_full_ff_homes.v1',enabled=False,status='PASS_ROW_SITE_INTENT_ONLY' if not bad else 'HELD_NONROW',
                reference_dump_sha256=hashlib.sha256(Path(reference).read_bytes()).hexdigest(),reference_ff_count=len(out)-13,
                orientation_policy='Exact fresh native row orientation at the target lower-left; reference orientation is not reused',
                removed_reference_states=removed,net_ff_added=13,cycles_added=0,target_count=len(out),
                nonrow_count=len(bad),nonrow=bad,targets=out,tree_or_placement_applied=False,
                policy='All retained FF anchors must join on the fresh mapped source. No old ODB/netlist/timing credit. Macro/FF collisions and every actual data/reset/clock constraint require the paired complete audit.')


def native_join(intent,inventory):
    if intent['status']!='PASS_ROW_SITE_INTENT_ONLY':raise ValueError('Full target intent is not on native rows/sites')
    if inventory.get('stage')!='mapped_preCTS' or inventory.get('source_event')!='tt_regional_origin_13ff':raise ValueError('New mapped regional-source inventory is required')
    if not inventory.get('source_sha256') or not inventory.get('netlist_sha256'):raise ValueError('Missing exact new source/netlist identity')
    if intent.get('target_count')!=len(intent['targets']) or intent.get('net_ff_added')!=13 or intent.get('cycles_added')!=0:
        raise ValueError('Incomplete or repriced full FF intent')
    if inventory.get('complete_ff_census') is not True:raise ValueError('An unfiltered complete native FF census is required')
    records=inventory['ff_cells'];by={r['model_name']:r for r in records}
    if len(by)!=len(records) or len({r['native_name'] for r in records})!=len(records):raise ValueError('Duplicate model/native FF identity')
    if set(by)!={r['model_name'] for r in intent['targets']}:raise ValueError('Missing or extra native FFs in the complete target map')
    joined=[]
    for t in intent['targets']:
        r=by[t['model_name']]
        if r['master']!=t['master'] or abs(r['width_um']-t['width_um'])>1e-6 or abs(r['height_um']-t['height_um'])>1e-6:
            raise ValueError('Native FF master/footprint changed: '+t['model_name'])
        if t['source_identity']:
            signal,edge,kind=t['source_identity']
            if r.get('rtl_signal')!=signal or r.get('rtl_edge')!=edge:raise ValueError('Native regional source alias/edge does not join: '+t['model_name'])
        elif r['native_name']!=t['model_name']:
            raise ValueError('An unchanged FF was silently renamed/aliased: '+t['model_name'])
        joined.append(dict(**t,native_name=r['native_name']))
    return dict(schema='opentallas.tt_full_native_ff_homes_join.v1',status='JOINED_METADATA_ONLY',
                enabled=False,placement_applied=False,physical_release='HELD',source_sha256=inventory['source_sha256'],
                netlist_sha256=inventory['netlist_sha256'],targets=joined,
                required='Actual native row orientation/occupancy, complete data/reset/macro reach and exact63clock phase/path join before any placement hook. Preserve every existing parent/corner/source gate.')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    for name in ('reference','homes','source','raw','out'):p.add_argument('--'+name,type=Path,required=True)
    p=sub.add_parser('join')
    for name in ('intent','inventory','out'):p.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    result=prepare(a.reference,read(a.homes),read(a.source),read(a.raw)) if a.command=='prepare' else native_join(read(a.intent),read(a.inventory))
    data=(json.dumps(result,separators=(',',':'))+'\n').encode()
    if str(a.out).endswith('.gz'):
        with gzip.GzipFile(filename=str(a.out),mode='wb',mtime=0) as f:f.write(data)
    else:a.out.write_bytes(data)
    print('TT_FULL_FF_HOMES',result['status'],len(result['targets']))
