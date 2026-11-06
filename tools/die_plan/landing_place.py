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


def band_rects(tn,name,band,t=None):
    """DIE-S81-47 11-01: the rect(s) of a landing band, nearest the bus pin first.  A band with rects_um (2..N disjoint
    rects; plan fix where no single legal rect exists, clock_landing_plan.fill_failed_bands) emits one cland_groups entry
    per rect with the same prefix and ring tag, and landing_placement.tcl packs the ring over them in that order.  Bands
    without rects_um return [rect_um] (unchanged output)."""
    if band.get('placement')=='FAIL' or not band.get('rect_um'):raise ValueError(f'{tn}.{name}: landing band absent')
    # Optional measured FF-only fill window. The outer reserved band remains
    # unchanged; a wide logic-sized band need not spread its FFs far past the
    # actual bus pins after its combinational logic is released to GPL.
    if 'ff_rect_um' in band:
        if band.get('ring_place') != 'ff' or 'rects_um' in band:
            raise ValueError(f'{tn}.{name}: ff_rect_um requires one FF-only band')
        outer, r = band['rect_um'], band['ff_rect_um']
        for rect in (outer, r):
            if not isinstance(rect, (list, tuple)) or len(rect) != 4 or any(
                    type(v) not in (int, float) or not isfinite(v) for v in rect):
                raise ValueError(f'{tn}.{name}: ff_rect_um needs four finite numeric coordinates')
        W,H=(t or {}).get('outline_um',[float('inf')]*2)
        if not (0 <= outer[0] <= r[0] < r[2] <= outer[2] <= W and
                0 <= outer[1] <= r[1] < r[3] <= outer[3] <= H):
            raise ValueError(f'{tn}.{name}: ff_rect_um must be inside the reserved band and type outline')
        return [list(r)]
    if 'rects_um' not in band:return [band['rect_um']]
    rs=band['rects_um']
    if not isinstance(rs,list) or len(rs)<2:raise ValueError(f'{tn}.{name}: rects_um needs 2 or more rects')
    if band.get('fill_axis') is not None:raise ValueError(f'{tn}.{name}: rects_um does not support fill_axis')
    W,H=(t or {}).get('outline_um',[float('inf')]*2)
    for r in rs:
        if not isinstance(r,(list,tuple)) or len(r)!=4 or any(type(v) not in (int,float) or not isfinite(v) for v in r):
            raise ValueError(f'{tn}.{name}: rects_um entry needs four finite numeric coordinates')
        if not (0<=r[0]<r[2]<=W and 0<=r[1]<r[3]<=H):raise ValueError(f'{tn}.{name}: rects_um entry {r} outside the type outline')
    for i,a in enumerate(rs):
        for b in rs[i+1:]:
            if min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6:
                raise ValueError(f'{tn}.{name}: rects_um entries overlap')
    if list(rs[0])!=list(band['rect_um']):raise ValueError(f'{tn}.{name}: rect_um must be the first rects_um entry')
    return [list(r) for r in rs]


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


def _native_role_banks(tn, name, band, typ):
    """Explicit opt-in native FF banks; no inferred clock roots or member counts."""
    cfg = band.get('native_role_banks')
    if cfg is None:
        return None
    if not isinstance(cfg, dict) or cfg.get('schema') != 'opentallas.landing_native_role_banks.v1':
        raise ValueError(f'{tn}.{name}: native_role_banks schema')
    if band.get('ring_place') != 'ff' or any(k in band for k in ('rects_um', 'ff_rect_um')):
        raise ValueError(f'{tn}.{name}: native role banks require one FF band without rectangle overrides')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
        raise ValueError('native role banks require an exact input bus name')
    required = {'schema', 'ff_pin_roles', 'banks', 'held_members', 'expected_total_members', 'expected_captures_per_port'}
    if set(cfg) != required or type(cfg['expected_captures_per_port']) is not int or cfg['expected_captures_per_port'] <= 0:
        raise ValueError('native role bank fields or first-capture slot count')
    roles = cfg.get('ff_pin_roles')
    if not isinstance(roles, dict) or not roles:
        raise ValueError('native role banks require qualified FF master pin roles')
    ident = lambda x: isinstance(x, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x)
    port = lambda x: isinstance(x, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\[[0-9]+\])?', x)
    for master, role in roles.items():
        if not ident(master) or not isinstance(role, dict) or set(role) != {'clock', 'data', 'reset'}:
            raise ValueError('native role banks need exact master clock/data/reset pin roles')
        if not ident(role['clock']) or not isinstance(role['data'], list) or not role['data'] or not isinstance(role['reset'], list):
            raise ValueError('native role banks require one clock pin and explicit data/reset pin lists')
        pins = [role['clock']] + role['data'] + role['reset']
        if not all(ident(x) for x in pins) or len(pins) != len(set(pins)):
            raise ValueError('duplicate or invalid native FF pin role')
    banks = cfg.get('banks')
    held = cfg.get('held_members')
    if not isinstance(banks, list) or not banks or not isinstance(held, list):
        raise ValueError('native role banks need banks and explicit held_members')
    width, height = typ['outline_um']
    names, filters = set(), []
    for bank in banks:
        required = {'name', 'clock_port', 'first_capture', 'expected_members', 'expected_first_capture', 'rect_um', 'members'}
        if not isinstance(bank, dict) or set(bank) != required:
            raise ValueError('native role bank fields')
        if not ident(bank['name']) or bank['name'] in names or not port(bank['clock_port']):
            raise ValueError('duplicate bank name or invalid exact native clock port')
        names.add(bank['name'])
        filt = bank['first_capture']
        if filt not in ('any', 'present', 'absent'):
            raise ValueError('native first_capture filter must be any, present or absent')
        for clock, old in filters:
            if clock == bank['clock_port'] and (old == filt or 'any' in (old, filt)):
                raise ValueError('overlapping native role bank filters')
        filters.append((bank['clock_port'], filt))
        count, first = bank['expected_members'], bank['expected_first_capture']
        if type(count) is not int or count <= 0 or type(first) is not int or not 0 <= first <= count:
            raise ValueError('native role bank expected member/first-capture counts')
        if filt == 'present' and first != count or filt == 'absent' and first != 0:
            raise ValueError('native role bank first-capture count contradicts its filter')
        members = bank['members']
        if not isinstance(members, list) or len(members) != count:
            raise ValueError('native role bank pinned member count mismatch')
        for member in members:
            if not isinstance(member, dict) or set(member) != {'name', 'master'}:
                raise ValueError('native role bank pinned member fields')
            native_name = member['name']
            if not isinstance(native_name, str) or not native_name or any(c in native_name for c in '{}\n\r\t\0') or member['master'] not in roles:
                raise ValueError('invalid pinned native role member name/master')
        rect = bank['rect_um']
        if not isinstance(rect, (list, tuple)) or len(rect) != 4 or any(type(v) not in (int, float) or not isfinite(v) for v in rect):
            raise ValueError('native role bank rectangle requires four finite coordinates')
        if not (0 <= rect[0] < rect[2] <= width and 0 <= rect[1] < rect[3] <= height):
            raise ValueError('native role bank rectangle outside type outline')
    for i, bank in enumerate(banks):
        a = bank['rect_um']
        for other in banks[i + 1:]:
            b = other['rect_um']
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                raise ValueError('native role bank rectangles overlap')
    seen = set()
    for bank in banks:
        for member in bank['members']:
            if member['name'] in seen:
                raise ValueError('duplicate pinned native role member')
            seen.add(member['name'])
    for member in held:
        if not isinstance(member, dict) or set(member) != {'name', 'master', 'clock_port'}:
            raise ValueError('held native role member fields')
        native_name = member['name']
        if not isinstance(native_name, str) or not native_name or any(c in native_name for c in '{}\n\r\t\0') or native_name in seen:
            raise ValueError('duplicate or invalid exact held native member')
        seen.add(native_name)
        if member['master'] not in roles or not port(member['clock_port']):
            raise ValueError('held native role member has unknown master/clock port')
    total = cfg.get('expected_total_members')
    if type(total) is not int or total != sum(b['expected_members'] for b in banks) + len(held):
        raise ValueError('native role bank total member count mismatch')
    return cfg


def _native_role_config(tn, typ):
    """Emit nothing unless a band explicitly opts in. Tcl braces preserve native names literally."""
    rows = []
    seen = set()
    atom = lambda v: '{' + str(v) + '}'
    for name, band in typ.get('clock', {}).get('landing_contract', {}).get('bands', {}).items():
        cfg = _native_role_banks(tn, name, band, typ)
        if cfg is None:
            continue
        prefix = band.get('instance', 'u_cland_' + name)
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', prefix) or prefix in seen:
            raise ValueError('native role banks require a unique exact group prefix')
        seen.add(prefix)
        roles = []
        for master, r in cfg['ff_pin_roles'].items():
            roles += [atom(master), atom('clock ' + atom(r['clock']) + ' data ' + atom(' '.join(r['data'])) + ' reset ' + atom(' '.join(r['reset'])))]
        banks = []
        for b in cfg['banks']:
            members = ' '.join(atom(m['name']) + ' ' + atom(m['master']) for m in b['members'])
            banks.append(atom(' '.join([atom(b['name']), atom(b['clock_port']), atom(b['first_capture']), str(b['expected_members']), str(b['expected_first_capture']), atom(' '.join(f'{v:.5f}' for v in b['rect_um'])), atom(members)])))
        held = [atom(' '.join(atom(m[k]) for k in ('name', 'master', 'clock_port'))) for m in cfg['held_members']]
        body = 'bus ' + atom(name) + ' total ' + str(cfg['expected_total_members']) + ' captures_per_port ' + str(cfg['expected_captures_per_port']) + ' roles ' + atom(' '.join(roles)) + ' banks ' + atom(' '.join(banks)) + ' held ' + atom(' '.join(held))
        rows.append('dict set ::cland_native_role_banks ' + atom(prefix) + ' ' + atom(body))
    return ('set ::cland_native_role_banks {}\n' + '\n'.join(rows) + '\n') if rows else ''


def _placement_source(active):
    source = Path(__file__).with_name('landing_placement.tcl').read_text()
    if not active:
        source = re.sub(r'^# BEGIN NATIVE_ROLE_BANKS\n.*?^# END NATIVE_ROLE_BANKS\n', '', source, flags=re.M | re.S)
    return source


def _band_groups(tn, name, band, typ):
    cfg = _native_role_banks(tn, name, band, typ or {})
    rects = [b['rect_um'] for b in cfg['banks']] if cfg else band_rects(tn, name, band, typ)
    tag = 'ring:' + name + _spread(band, _bus_order(typ or {}, name))
    prefix = band.get('instance', 'u_cland_' + name)
    groups = []
    face = band.get('freg_rect_um')
    if face is not None:
        # Optional first capture at the physical pin face. FREG otherwise shares
        # the storage band; adding the register alone does not shorten pin reach.
        wreg = (typ or {}).get('clock', {}).get('landing_ring_wreg') or {}
        if not wreg.get('freg') or name not in wreg.get('buses', []):
            raise ValueError(f'{tn}.{name}: freg_rect_um requires this bus FREG')
        if cfg or len(rects) != 1:
            raise ValueError(f'{tn}.{name}: separate FREG bank requires one ordinary storage band')
        w, h = typ['outline_um']
        if (not isinstance(face, (list, tuple)) or len(face) != 4
                or any(type(v) not in (int, float) or not isfinite(v) for v in face)
                or not (0 <= face[0] < face[2] <= w and 0 <= face[1] < face[3] <= h)):
            raise ValueError(f'{tn}.{name}: invalid freg_rect_um')
        main = rects[0]
        if min(face[2], main[2]) > max(face[0], main[0]) and min(face[3], main[3]) > max(face[1], main[1]):
            raise ValueError(f'{tn}.{name}: FREG and storage banks overlap')
        groups.append((prefix + '.g_freg.u_face', list(face),
                       'ring:' + name + '@freg' + _spread(band, _bus_order(typ, name))))
    groups.extend((prefix, rect, tag) for rect in rects)
    return groups

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
        # The last face relay contains a synchronous-reset AND as well as Q.
        # Keeping only Q at the pin let GPL drag its AND to the distant origin
        # reset: HEAD spn_end bu_o travelled 1.6 mm down and back (-181.51 ps).
        # Treat the complete final relay exactly like each transport relay.
        pins = [p for p in (t or {}).get('clock', {}).get('landing_contract', {}).get('pins', [])
                if p.get('name') == 'cland_fstart_out_' + bus and p.get('dir') == 'out']
        if len(pins) != 1:
            continue  # parameter-form/older plans without a final face site stay unchanged
        width, height = t['outline_um']
        x, y = pins[0]['xy_um']
        x = min(max(x, 4.32), width - 4.32)
        y = min(max(y, 4.32), height - 4.32)
        groups.append((f'u_cland_fstart_{safe(bus)}',
                       [x-4.32, y-4.32, x+4.32, y+4.32], 'writer-face:'+bus))
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
        groups += _band_groups(tn, name, band, P.types[tn])
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
    role_config = _native_role_config(tn, P.types[tn])
    return '\n'.join(out)+'\n'+override_check+role_config+_placement_source(bool(role_config))


def _dataflow_tcl(tn,c,t=None):
    """monitor="dataflow" (opt-in, FALLBACK-HEAD-2): ring storage bands plus the dedicated registered status
    output at each sender pin. No reset-tree collector exists, so nothing else is placed by this hook."""
    groups=_reader_start_groups(t)+_writer_start_groups(t)+_status_reset_groups(t);status=[]
    for name,band in sorted(c.get('bands',{}).items()):
        groups += _band_groups(tn, name, band, t)
    for pin in sorted(c.get('pins',[]),key=lambda q:q['name']):
        if pin['dir']=='out' and pin['name'].startswith(('cland_up_ready_','cland_up_fault_')):
            x,y=pin['xy_um'];status.append((pin['name'],x,y))
    groups, override_check = _group_rect_overrides(t or {}, groups)
    out=['set cland_groups {']
    out+=['  {'+p+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}' for p,r,tag in groups]
    out+=['}','set cland_optional_groups {','}','set cland_status {']
    out+=['  {'+n+f' {x:.5f} {y:.5f}'+'}' for n,x,y in status]
    out+=['}']
    role_config = _native_role_config(tn, t or {})
    return '\n'.join(out)+'\n'+override_check+role_config+_placement_source(bool(role_config))
