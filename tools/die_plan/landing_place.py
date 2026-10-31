"""Fail-closed FIRM placement of actual mapped landing/collector cells."""
from pathlib import Path
from collections import defaultdict
from math import isfinite
import re


def safe(s):return re.sub(r'\W','_',s)


def _group_rect_overrides(t, groups):
    """Explicit physical collector/raw-copy sites; absent plans keep identical output."""
    c = t.get('clock', {}).get('landing_contract', {})
    if 'group_rects_um' not in c:
        return groups, ''
    overrides = c['group_rects_um']
    if not isinstance(overrides, dict):
        raise ValueError('landing group_rects_um must be an object')
    known = defaultdict(list)
    for prefix, rect, tag in groups:
        known[prefix].append(tag)
    width, height = t['outline_um']
    for prefix, rect in overrides.items():
        if not isinstance(prefix, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', prefix):
            raise ValueError(f'invalid landing group prefix {prefix!r}')
        tags = known.get(prefix, [])
        if len(tags) != 1 or not (tags[0].startswith('collector:') or tags[0] == 'raw-copy-optional'):
            raise ValueError(f'unknown, ambiguous or unsupported landing group override {prefix!r}')
        if not isinstance(rect, (list, tuple)) or len(rect) != 4 or any(
                type(v) not in (int, float) or not isfinite(v) for v in rect):
            raise ValueError(f'{prefix}: rectangle needs four finite numeric coordinates')
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError(f'{prefix}: rectangle must be ordered and inside the type outline')
    if not overrides:
        return groups, ''
    groups = [(p, overrides.get(p, r), tag) for p, r, tag in groups]
    # Optional copies can disappear during synthesis. An explicitly moved group
    # must exist in the actual mapped design, rather than silently consuming no site.
    names = ' '.join(sorted(overrides))
    check = '''foreach cland_override_prefix {%s} {
 set cland_override_found 0
 foreach cland_override_i [$ff_blk getInsts] {
  if {[regexp [format {(^|[/.])%%s[/.]} $cland_override_prefix] [$cland_override_i getName]]} {set cland_override_found 1; break}
 }
 if {!$cland_override_found} {error "OT_CLAND unused group rectangle override $cland_override_prefix"}
}
unset cland_override_prefix cland_override_found
''' % names
    return groups, check


def _bus_order(t,bus):
    """bit order of the band's bus on the type (buses[].order, or ft_slots in_order/out_order for <slot>_i/_o).
    FLOW-8 10-30 (DIE-HEAD-38 02:24 item 1): a slot with only 'order' (no in_order/out_order) uses it for both sides,
    the same fallback the schema pin layout uses (s_.get(stem + '_order', s_.get('order'))); before, the band read
    lsb_low and filled an lsb_high slot's ring reversed (+ff instead of +ffr: HEAD wshim_rx r2r 629 x343)."""
    for b in t.get('buses',[]):
        if b.get('name')==bus:return b.get('order','lsb_low')
    for s in t.get('ft_slots',[]):
        for suffix,key in (('_i','in_order'),('_o','out_order')):
            if s.get('name','')+suffix==bus:return s.get(key,s.get('order','lsb_low'))
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
    axis=band.get('fill_axis')
    if axis not in (None,'x'):
        raise ValueError(f"landing fill_axis {axis!r}: want 'x' or absent")
    if axis=='x' and not ff:
        raise ValueError("landing fill_axis='x' requires ring_place='ff'")
    return ('' if not sp or sp<=1.0 else f'@{sp:.4f}')+('+x' if axis=='x' else '')+ff


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


def _writer_start_groups(t):
    """W1 writer START relays at declared sites (DIE-HEAD-38), same FIRM packing; [] when absent."""
    cfg = (t or {}).get('clock', {}).get('landing_writer_start')
    if cfg is None:
        return []
    groups = []
    for bus, branch in sorted(cfg['branches'].items()):
        for i, stage in enumerate(branch['stages']):
            x, y = stage['xy_um']
            groups.append((f'u_cland_writer_start_{safe(bus)}_{i}',
                           [x-2.16, y-2.16, x+2.16, y+2.16], 'writer-start:'+bus))
    return groups


def _status_reset_groups(t):
    """DIE-HEAD-38 R1/R2 opt-in sites (absent = no group): status input relays, status stage anchors and
    same-cycle local reset copies, through the existing FIRM packing at +-2.16 um."""
    ck=(t or {}).get('clock',{});groups=[]
    near=lambda xy:[xy[0]-2.16,xy[1]-2.16,xy[0]+2.16,xy[1]+2.16]
    for tgt,rings in sorted((ck.get('landing_status_input_stages') or {}).items()):
        for ring,stages in sorted(rings.items()):
            for k,s in enumerate(stages):
                groups.append((f'u_cland_sin_{safe(tgt)}_{safe(ring)}_{k}',near(s['xy_um']),'status-stage:'+tgt))
    for inst,xy in sorted((ck.get('landing_status_anchors') or {}).items()):
        groups.append((inst,near(xy),'status-anchor'))
    for r in ck.get('landing_local_resets') or []:
        groups.append((f"u_cland_lrst_{safe(r['name'])}",near(r['xy_um']),'local-reset'))
    for branch in ck.get("landing_raw_branches") or []:
        for i, stage in enumerate(branch["stages"]):
            groups.append((f"u_cland_raw_{safe(branch['name'])}_{i}",near(stage["xy_um"]),"literal-local-reset"))
    return groups


def _source_node(s):
    """collector tree node of a local source: rst_n_t<tap> for a tapped source; a hard-tree source (tap None, e.g. the KV
    modeled-PHY wrappers whose collector tree is only cland_h* relays) names its relay in 'node'"""
    if s.get('tap') is None and s.get('node'):
        return s['node']
    return f"rst_n_t{s['tap']}"


def tcl(P,tn):
    c=P.types[tn].get('clock',{}).get('landing_contract',{})
    groups=_reader_start_groups(P.types[tn])+_writer_start_groups(P.types[tn])+_status_reset_groups(P.types[tn]);status=[];tree=c.get('collector_tree');root=c.get('collector_root_node')
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
        groups.append(('u_cland_rst_'+s['name'],near(tree['relays'][next(i for i,r in enumerate(tree['relays']) if r['q']==_source_node(s))]['xy']),'raw-copy-optional'))
    if root:
        adj=defaultdict(list);xy={'rst_root_n':tree['root']}
        for r in tree['relays']:adj[r['q']].append(r['d']);adj[r['d']].append(r['q']);xy[r['q']]=r['xy']
        parent={root:None};todo=[root]
        while todo:
            n=todo.pop()
            for q in adj[n]:
                if q not in parent:parent[q]=n;todo.append(q)
        sources=[_source_node(s) for s in c.get('collector_local_sources',[])]+[s['node'] for s in c.get('collector_children',[])]
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
    groups, override_check = _group_rect_overrides(P.types[tn], groups)
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
    return '\n'.join(out)+'\n'+override_check+Path(__file__).with_name('landing_placement.tcl').read_text()


def _dataflow_tcl(tn,c,t=None):
    """monitor="dataflow" (opt-in, FALLBACK-HEAD-2): ring storage bands plus the dedicated registered status
    output at each sender pin. No reset-tree collector exists, so nothing else is placed by this hook."""
    groups=_reader_start_groups(t)+_writer_start_groups(t)+_status_reset_groups(t);status=[]
    for name,band in sorted(c.get('bands',{}).items()):
        if band.get('placement')=='FAIL' or not band.get('rect_um'):raise ValueError(f'{tn}.{name}: landing band absent')
        groups.append((band.get('instance','u_cland_'+name),band['rect_um'],'ring:'+name+_spread(band,_bus_order(t or {},name))))
    for pin in sorted(c.get('pins',[]),key=lambda q:q['name']):
        if pin['dir']=='out' and pin['name'].startswith(('cland_up_ready_','cland_up_fault_')):
            x,y=pin['xy_um'];status.append((pin['name'],x,y))
    groups, override_check = _group_rect_overrides(t or {}, groups)
    out=['set cland_groups {']
    out+=['  {'+p+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}' for p,r,tag in groups]
    out+=['}','set cland_optional_groups {','}','set cland_status {']
    out+=['  {'+n+f' {x:.5f} {y:.5f}'+'}' for n,x,y in status]
    out+=['}']
    return '\n'.join(out)+'\n'+override_check+Path(__file__).with_name('landing_placement.tcl').read_text()
