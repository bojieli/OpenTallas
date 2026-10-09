#!/usr/bin/env python3
"""Planning-only actual SM3/wide pins on the pinned R25 logical network.

Literal strip pins replace box-projection SM endpoints. Registered endpoint TSV
is consumed when the wide physical run emits it. Historical tree association,
other generated macro anchors and corridor legality remain unqualified.
"""
import argparse
import hashlib
import inspect
import json
import math
from pathlib import Path
import re
import hbm_accel_die_fp as H
import hbm_accel_smh_physical as F

BUNDLE = {
    'd': r'^rsp_',
    'q': r'^req_',
    'x': r'^xw_',
    'r': r'^(rv$|rrow|rdata|fault$)',
    'c': r'^(start|op_|busy$|arrive$|release|d_valid$|d_ready$|d_base|d_lines)',
}

def pin_manifest(width):
    g=dict(F.GEOM,front_w=width,front_channel_um=240 if width>432 else 120)
    pos,die,hcore=F.floorplan(g)
    fx,fy=pos['front'];ports={};strips={}
    for st in F.STRIPS:
        pins,height=F.strip_pins(g,hcore,st)
        lo,hi=F.strip_span(g,hcore,st)
        records={n:dict(layer=l,x=x,y=y) for n,l,_,x,y in pins}
        strips[st]=dict(origin_um=[fx,fy+lo],die_um=[width,height],
            pin_tcl_sha256=hashlib.sha256(F.pin_tcl(pins).encode()).hexdigest(),pins=records)
    for n,l,_,x,y in F.front_pins(g,hcore):
        if l=='M5':
            st='front_n' if y>0 else 'front_s'
            ports[n]=dict(strip=st,strip_xy_um=[x,strips[st]['die_um'][1] if y>0 else 0],
                element_xy_um=[fx+x,die[1] if y>0 else 0],layer=l)
    south=[v['element_xy_um'][0] for v in ports.values() if v['strip']=='front_s']
    return dict(element_die_um=die,ports=ports,strips=strips,south_span_um=[min(south),max(south)])

def build_actual(manifest):
    # Scope patch to this probe's function; default generator source is unchanged.
    src=inspect.getsource(H.build)
    old='lo, hi = 1467.804, 1608.444'
    if src.count(old)!=1: raise RuntimeError('pinned result reservation anchor changed')
    src=src.replace(old,"lo, hi = variant['actual_sm_south_span_um']")
    scope=dict(H.__dict__);exec(compile(src,H.__file__,'exec'),scope)
    return scope['build'](dict(H.R25,sm_wh=tuple(manifest['element_die_um']),
        sm_physical_grid=(3,3),side_padding_um=207.36,
        actual_sm_south_span_um=manifest['south_span_um']),network_probe=True)

def transformed(it,points):
    # Literal generator frame; model bodies have a 24nm abstract shave.
    w,h=it.w+H.SHAVE,it.h+H.SHAVE
    for x,y in points:
        if it.orient in ('MY','R180'): x=w-x
        if it.orient in ('MX','R180'): y=h-y
        yield it.x+x,it.y+y

def paths(m,manifest):
    by={i.name:i for i in m['insts']};bus={b[0]:b for b in m['buses']}
    points={p:[v['element_xy_um'] for n,v in manifest['ports'].items() if re.search(r,n)] for p,r in BUNDLE.items()}
    if any(not v for v in points.values()): raise RuntimeError('empty actual pin bundle')
    def center(i):return i.x+i.w/2,i.y+i.h/2
    def near(i,q):return min(max(q[0],i.x),i.x+i.w),min(max(q[1],i.y),i.y+i.h)
    out={};bindings={}
    for path,ids in m['paths'].items():
        segs=[]
        for bid in ids:
            eps=bus[bid][3];an,ap=eps[0];bn,bp=eps[-1];a,b=by[an],by[bn]
            aa=list(transformed(a,points[ap])) if a.kind=='sm' else [near(a,center(b))]
            bb=list(transformed(b,points[bp])) if b.kind=='sm' else [near(b,center(a))]
            if a.kind!='sm' and b.kind!='sm':
                aa=[near(a,bb[0])];bb=[near(b,aa[0])]
            if a.kind=='sm' and b.kind!='sm': bb=[near(b,x) for x in aa]
            if b.kind=='sm' and a.kind!='sm': aa=[near(a,x) for x in bb]
            # Worst actual pin in the bundle; multi-face control is intentional.
            if a.kind=='sm' and b.kind=='sm': pairs=((x,y) for x in aa for y in bb)
            else:pairs=zip(aa,bb)
            length=max(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in pairs)
            segs.append(dict(bus=bid,um=round(length,3),stages=H.seg_stages(m,bid,length)))
            for name,port,it in ((an,ap,a),(bn,bp,b)):
                if it.kind=='sm':bindings[f'{name}/{port}']=dict(orient=it.orient,
                    bundle=port,pin_count=sum(bool(re.search(BUNDLE[port],n)) for n in manifest['ports']))
        out[path]=dict(um=round(sum(s['um'] for s in segs),3),stages=sum(s['stages'] for s in segs),segments=segs)
    return out,bindings

def main():
    if hashlib.sha256(Path(H.__file__).read_bytes()).hexdigest()!='88537944b65232dc376a96274834e3b967f7ce9bcb3fc11b0f39d8d3e56b7084':
        raise RuntimeError('use pinned0cb3d9624 die generator inventory')
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--endpoint-tsv',type=Path);p.add_argument('--endpoint-strip',choices=F.STRIPS,default='front_c')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    result=dict(scope='actual literal SM pin planning; no routed timing or corridor qualification',
        geometry_evidence='3467f362e',generator_source='0cb3d962452b9a627de3a386cd4e0baf5be0c7bf',
        probe_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        die_generator_sha256=hashlib.sha256(Path(H.__file__).read_bytes()).hexdigest(),
        strip_generator_sha256=hashlib.sha256(Path(F.__file__).read_bytes()).hexdigest(),
        timing_qualified=False,network_qualified=False,logical_to_literal_pin_bundle_regex=BUNDLE,cases={},limitations=[
            'historical logical tree association retained',
            'non-SM endpoints remain macro-box projections',
            'relay source cells and all transformed corridors require physical checks',
            'logical bundle widths are legacy network contracts, not an RTL integration proof'])
    for name,width in (('sm3_reference',432),('wide',570.24)):
        manifest=pin_manifest(width);m=build_actual(manifest);pp,bindings=paths(m,manifest)
        result['cases'][name]=dict(legality=H.legality(m),paths=pp,bindings=bindings,
            die_area_mm2=m['geo']['W']*m['geo']['H']/1e6)
        (a.out/(name+'_pins.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    ref=result['cases']['sm3_reference']['paths'];wide=result['cases']['wide']['paths']
    result['wide_delta_per_path']={n:dict(um=round(w['um']-ref[n]['um'],3),stages=w['stages']-ref[n]['stages']) for n,w in wide.items()}
    result['wide_delta_by_class']={c:dict(max_ref_stages=max(v['stages'] for n,v in ref.items() if H.path_class(n)==c),
        max_wide_stages=max(v['stages'] for n,v in wide.items() if H.path_class(n)==c),
        max_path_delta_stages=max(v['stages'] for n,v in result['wide_delta_per_path'].items() if H.path_class(n)==c))
        for c in {H.path_class(n) for n in wide} if c}
    result['die_cost']=dict(source_evidence='3467f362e',wide_area_mm2=result['cases']['wide']['die_area_mm2'],
        area_delta_vs_actual_sm3_mm2=result['cases']['wide']['die_area_mm2']-result['cases']['sm3_reference']['die_area_mm2'],
        area_delta_vs_adopted_r25_mm2=10.069649)
    result['registered_endpoint_binding']='pending actual wide placement TSV'
    if a.endpoint_tsv:
        import csv
        rows=list(csv.DictReader(a.endpoint_tsv.open(),delimiter='\t'))
        manifest=pin_manifest(570.24);literal=manifest['strips'][a.endpoint_strip]['pins']
        for row in rows:
            if row['port'] not in literal: raise ValueError(f"unbound actual register port {row['port']}")
            row['pin_to_cell_origin_um']=abs(float(row['pin_x_um'])-float(row['cell_x_um']))+abs(float(row['pin_y_um'])-float(row['cell_y_um']))
            row['element_xy_um']=[float(row['pin_x_um'])+manifest['strips'][a.endpoint_strip]['origin_um'][0],
                float(row['pin_y_um'])+manifest['strips'][a.endpoint_strip]['origin_um'][1]]
        result['registered_endpoint_binding']=dict(source_sha256=hashlib.sha256(a.endpoint_tsv.read_bytes()).hexdigest(),
            strip=a.endpoint_strip,rows=rows,max_pin_to_cell_origin_um=max(r['pin_to_cell_origin_um'] for r in rows),
            status='actual placed DFF cells, not routed wire length or added latency credit')
    (a.out/'probe.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['wide_delta_by_class'],indent=2))
if __name__=='__main__':main()
