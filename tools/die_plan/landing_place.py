"""Fail-closed FIRM placement of actual mapped landing/collector cells."""
from pathlib import Path
from collections import defaultdict
import re


def safe(s):return re.sub(r'\W','_',s)


def _bus_order(t,bus):
    """bit order of the band's bus on the type (buses[].order, or ft_slots in_order/out_order for <slot>_i/_o)."""
    for b in t.get('buses',[]):
        if b.get('name')==bus:return b.get('order','lsb_low')
    for s in t.get('ft_slots',[]):
        for suffix,key in (('_i','in_order'),('_o','out_order')):
            if s.get('name','')+suffix==bus:return s.get(key,'lsb_low')
    return 'lsb_low'


def _spread(band,order='lsb_low'):
    """DIE-HEAD-12 opt-in band_spread: ring tag suffix '@<spread>' (landing_placement.tcl widens each ring cell's reserved
    footprint by it, so the ring fills the whole band); no suffix when the band has no spread (default plans)."""
    sp=band.get('spread')
    # DIE-HEAD-13 opt-in band_ring="ff": '+ff' = place only the ring flops FIRM (bit-major), ring logic to GPL
    # DIE-HEAD-32 10-29: '+ffr' = the same, bit-major in DESCENDING bit order, for an lsb_high bus (bit 0 at the window's
    # high end): the band fills from its low corner, so the slot fill follows the pin order (hd_tile hk5m V1: ascending
    # fill put i[565]'s ring flops at the band top, 301.6 um from its pin at the bottom). lsb_low stays '+ff'.
    ff='' if band.get('ring_place')!='ff' else ('+ffr' if order=='lsb_high' else '+ff')
    return ('' if not sp or sp<=1.0 else f'@{sp:.4f}')+ff


def _reader_start_groups(t):
    """Actual kept relay instances at declared sites, through existing FIRM packing."""
    cfg = (t or {}).get('clock', {}).get('landing_reader_start')
    if cfg is None:
        return []
    groups = []
    if 'origin_rect_um' in cfg:
        groups.append(('u_cland_origin', cfg['origin_rect_um'], 'reader-start-origin'))
    for bus, branch in sorted(cfg['branches'].items()):
        for i, stage in enumerate(branch['stages']):
            x, y = stage['xy_um']
            groups.append((f'u_cland_reader_start_{safe(bus)}_{i}',
                           [x-2.16, y-2.16, x+2.16, y+2.16], 'reader-start:'+bus))
    return groups


def tcl(P,tn):
    c=P.types[tn].get('clock',{}).get('landing_contract',{})
    groups=_reader_start_groups(P.types[tn]);status=[];tree=c.get('collector_tree');root=c.get('collector_root_node')
    def near(xy):
        x,y=xy;return [x-2.16,y-2.16,x+2.16,y+2.16]
    if c.get('monitor')=='dataflow' or (root and tree is None):
        return _dataflow_tcl(tn,c,P.types[tn])
    for name,band in c.get('bands',{}).items():
        if band.get('placement')=='FAIL' or not band.get('rect_um'):raise ValueError(f'{tn}.{name}: landing band absent')
        groups.append((band.get('instance','u_cland_'+name),band['rect_um'],'ring:'+name+_spread(band,_bus_order(P.types[tn],name))))
    for s in c.get('collector_local_sources',[]):
        x,y=s['xy_um']
        for kind in ('ready','fault'):status.append((f'landing_{kind}_'+s['name'],x,y))
        groups.append(('u_cland_rst_'+s['name'],near(tree['relays'][next(i for i,r in enumerate(tree['relays']) if r['q']==f"rst_n_t{s['tap']}")]['xy']),'raw-copy-optional'))
    if root:
        adj=defaultdict(list);xy={'rst_root_n':tree['root']}
        for r in tree['relays']:adj[r['q']].append(r['d']);adj[r['d']].append(r['q']);xy[r['q']]=r['xy']
        parent={root:None};todo=[root]
        while todo:
            n=todo.pop()
            for q in adj[n]:
                if q not in parent:parent[q]=n;todo.append(q)
        sources=[f"rst_n_t{s['tap']}" for s in c.get('collector_local_sources',[])]+[s['node'] for s in c.get('collector_children',[])]
        active=set()
        for n in sources:
            while n is not None:active.add(n);n=parent[n]
        for n in sorted(active):
            groups.append(('u_cland_collect_'+safe(n),near(xy[n]),'collector:'+n))
            if n!='rst_root_n':groups.append(('u_cland_reset_'+safe(n),near(xy[n]),'raw-copy-optional'))
        for s in c.get('collector_children',[]):
            if s['seam']:
                x,y=s['xy_um'];i=s['index']
                status.extend([(f'cland_dn_trained_{i}',x,y),(f'cland_dn_guard_{i}',x,y)])
    out=['set cland_groups {']
    for p,r,tag in groups:
        # Optional raw copies only exist when the original START tap is gated.
        if tag=='raw-copy-optional':continue
        out.append('  {'+p+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}')
    out+=['}','set cland_optional_groups {']
    for p,r,tag in groups:
        if tag=='raw-copy-optional':out.append('  {'+p+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}')
    out+=['}','set cland_status {']
    out+=['  {'+n+f' {x:.5f} {y:.5f}'+'}' for n,x,y in status]
    out+=['}']
    return '\n'.join(out)+'\n'+Path(__file__).with_name('landing_placement.tcl').read_text()


def _dataflow_tcl(tn,c,t=None):
    """monitor="dataflow" (opt-in, FALLBACK-HEAD-2): ring storage bands plus the dedicated registered status
    output at each sender pin. No reset-tree collector exists, so nothing else is placed by this hook."""
    groups=_reader_start_groups(t);status=[]
    for name,band in sorted(c.get('bands',{}).items()):
        if band.get('placement')=='FAIL' or not band.get('rect_um'):raise ValueError(f'{tn}.{name}: landing band absent')
        groups.append((band.get('instance','u_cland_'+name),band['rect_um'],'ring:'+name+_spread(band,_bus_order(t or {},name))))
    for pin in sorted(c.get('pins',[]),key=lambda q:q['name']):
        if pin['dir']=='out' and pin['name'].startswith(('cland_up_ready_','cland_up_fault_')):
            x,y=pin['xy_um'];status.append((pin['name'],x,y))
    out=['set cland_groups {']
    out+=['  {'+p+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}' for p,r,tag in groups]
    out+=['}','set cland_optional_groups {','}','set cland_status {']
    out+=['  {'+n+f' {x:.5f} {y:.5f}'+'}' for n,x,y in status]
    out+=['}']
    return '\n'.join(out)+'\n'+Path(__file__).with_name('landing_placement.tcl').read_text()
