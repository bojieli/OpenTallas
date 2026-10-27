"""Disjoint supply regions for CORE VDD and declared PHY supplies.

Uses one die-phase pattern for all pieces. Same-net overlapping domain halos are
united before PDN generation; the CORE grid occupies their exact complement.
OpenROAD voltage regions: https://openroad.readthedocs.io/en/latest/main/src/pdn/README.html
"""
import json


def regions(die):
    w,h=die['outline_um']; ds=die.get('pg',{}).get('domains',[])
    xs=sorted({0.,w,*[max(0,min(w,d['rect_um'][i])) for d in ds for i in (0,2)]})
    ys=sorted({0.,h,*[max(0,min(h,d['rect_um'][i])) for d in ds for i in (1,3)]})
    strips=[]
    for y0,y1 in zip(ys,ys[1:]):
        row=[]
        for x0,x1 in zip(xs,xs[1:]):
            x,y=(x0+x1)/2,(y0+y1)/2
            hit=[d for d in ds if d['rect_um'][0]<=x<d['rect_um'][2] and d['rect_um'][1]<=y<d['rect_um'][3]]
            keys={(tuple(d['nets']),json.dumps(d['grid'],sort_keys=True)) for d in hit}
            if len(keys)>1:raise ValueError('Overlapping PHY domains have different supplies or mesh contracts')
            if hit:power,ground=hit[0]['nets'];grid=hit[0]['grid']
            else:power,ground='VDD','VSS';grid=die['pg']['grid']
            key=(power,ground,json.dumps(grid,sort_keys=True))
            if row and row[-1][0]==key and row[-1][1][2]==x0:row[-1][1][2]=x1
            else:row.append((key,[x0,y0,x1,y1]))
        strips+=row
    out=[]
    for key,r in strips:
        prior=next((q for q in out if q['key']==key and q['rect_um'][0]==r[0] and q['rect_um'][2]==r[2] and q['rect_um'][3]==r[1]),None)
        if prior:prior['rect_um'][3]=r[3]
        else:out.append(dict(key=key,nets=list(key[:2]),grid=json.loads(key[2]),rect_um=r))
    return [{k:v for k,v in q.items() if k!='key'} for q in out]


# ------------------------------------------------------------------ ONE PDN RULE (COORD 10-26 13:13, lane PDN-ONE)
# The plan's PG rows (die.pg.grid / domain grids: layer, width, pitch, offset from the DIE origin, nets order) are the
# single source of every real PDN script (pdn_tcl, die_trial.psm_pdn_tcl, gen_phys.die_pdn_tcl) and of the die_infra
# PG model.  Stripe centres sit on the die lattice  offset + n * pitch/2, net = nets[n % 2], in every region; each
# region's add_pdn_stripe gets the first lattice stripe that fits inside the region as its -offset (from the region's
# lower edge, exact dbu) and that stripe's net as -starts_with, so no region drifts off phase or swaps parity.
# model_rects() reproduces pdngen (OpenROAD 26Q3) on those scripts, measured with pdn_model_match.py:
#   - a stripe is made only when it lies fully inside its region box;
#   - a stripe end on the core (= die) boundary stays at the boundary; an end on an inner region edge is trimmed to
#     the outer edge of the last same-net orthogonal stripe of the same grid it crosses (pdngen trims dangling
#     metal back to its last via); a stripe with an inner end and no same-net crossing is removed.
DBU = 1000
DIRS = {'M1': 'V', 'M2': 'H', 'M3': 'V', 'M4': 'H', 'M5': 'V', 'M6': 'H', 'M7': 'V', 'M8': 'H', 'M9': 'V'}


def _d(x):
    return int(round(float(x) * DBU))


def _u(v):
    """exact um text of an integer dbu value (never %g: 6 significant digits moved 13328.36 to 13328.4)."""
    t = f"{v / DBU:.3f}".rstrip('0').rstrip('.')
    return t if t not in ('', '-0') else '0'


def row_spec(s, rect, nets):
    """one plan PG row in one region rect (dbu) -> dict(layer, V, w, pitch, half, lo, hi, offset (from lo), start, other)
    or None when no lattice stripe fits.  nets = the row's own order (s['nets'], else the region's (power, ground))."""
    nets = list(s.get('nets') or nets)
    if len(nets) != 2:
        raise ValueError(f"PG row {s['layer']}: pdngen stripes alternate exactly one power and one ground net, got {nets}")
    V = DIRS[s['layer']] == 'V'
    lo, hi = (rect[0], rect[2]) if V else (rect[1], rect[3])
    w, pitch, off = _d(s['width_um']), _d(s['pitch_um']), _d(s['offset_um'])
    if pitch % 2:
        raise ValueError(f"PG row {s['layer']}: pitch {s['pitch_um']} is not an even number of dbu")
    half = pitch // 2
    n0 = -(-(2 * lo + w - 2 * off) // pitch)          # first lattice index with centre - w/2 >= lo
    c0 = off + n0 * half
    if 2 * c0 + w > 2 * hi:
        return None
    return dict(layer=s['layer'], V=V, w=w, pitch=pitch, half=half, lo=lo, hi=hi, offset=c0 - lo,
                start=nets[n0 % 2], other=nets[(n0 + 1) % 2])


def plan_regions(die, grid=None):
    """[(name, rect_dbu, (power, ground), [row_spec ...], layers)] -- the regions pdn_tcl emits, in order.  A plan
    without domains is one region = the die.  grid overrides die.pg.grid (infra_pg sized grid)."""
    if grid is not None:
        die = dict(die, pg=dict(die.get('pg', {}), grid=grid))
    out = []
    for k, r in enumerate(regions(die)):
        rect = [_d(x) for x in r['rect_um']]
        specs = [row_spec(s, rect, r['nets']) for s in r['grid']]
        out.append((f'ot_pg_{k}', rect, tuple(r['nets']), specs, [s['layer'] for s in r['grid']]))
    return out


def macro_region_grids_tcl(die, part_rects, part_pins=None, pin_layer="M7", core_net="VDD"):
    """OPT-IN (PDN-0233 fix, KV-PDN-M78 10-27): partition PG binding for a plan with die.pg.domains.

    pdn_tcl(die) puts EVERY die stripe in a region grid (ot_pg_k); the CORE domain then owns no die area and no
    stripes, so a '-voltage_domains {Core} -default' macro grid finds no M8 to connect the partition M7 PG pins to
    and pdngen fails with PDN-0232 on every instance + PDN-0233.  Here each partition joins the instance grid of the
    CORE-net region (power net == core_net) that holds the largest share of its outline (add_pdn_connect pin_layer ->
    that region's first grid layer).  A native instance grid has ONE domain, so a partition that straddles regions
    would leave the other regions' grids floating (PSM-0069); for those, part_pins {inst: [(net, layer, die_rect)]}
    (the abstract's real PG pin shapes) are clipped to every other region that carries the same net, and connected
    by the explicit same-net VIA78 contacts of PIN_VIAS_TCL (proc ot_pg_connect_pins, call it after pdngen).
    part_rects: {inst: (x0, y0, x1, y1) um}.  -> (tcl lines, {region: [inst]}, {inst: n clipped pin rects})."""
    allr = plan_regions(die)
    regs = [r for r in allr if r[2][0] == core_net and r[4]]
    if not regs:
        raise ValueError(f"no {core_net} PG region with a grid")

    def um(r):
        return [x / DBU for x in r]

    def area(a, b):
        return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    owner, own_of = {}, {}
    for inst in sorted(part_rects):
        best = max(regs, key=lambda r: area(part_rects[inst], um(r[1])))
        if area(part_rects[inst], um(best[1])) <= 0:
            raise ValueError(f"{inst}: outline overlaps no {core_net} PG region")
        owner.setdefault(best[0], []).append(inst)
        own_of[inst] = best[0]
    lines = []
    for name, _rect, _nets, _specs, layers in regs:
        if name not in owner:
            continue
        g = "{parts_" + name + "}"
        lines += [f"define_pdn_grid -name {g} -voltage_domains {{{name}}} -macro -instances {{{' '.join(owner[name])}}} "
                  "-halo {0 0 0 0}", f"add_pdn_connect -grid {g} -layers {{{pin_layer} {layers[0]}}}"]
    clipped, straddle = [], {}
    for inst in sorted(part_rects):
        others = [r for r in allr if r[0] != own_of[inst] and r[4] and area(part_rects[inst], um(r[1])) > 0]
        if not others:
            continue
        if part_pins is None or inst not in part_pins:
            raise ValueError(f"{inst}: straddles PG regions {[r[0] for r in others]} and needs its real PG pin shapes")
        n = 0
        for net, layer, q in part_pins[inst]:
            if layer != pin_layer:
                continue
            for r in others:
                if net not in r[2]:
                    continue
                b = um(r[1])
                c = [max(q[0], b[0]), max(q[1], b[1]), min(q[2], b[2]), min(q[3], b[3])]
                if c[0] < c[2] and c[1] < c[3]:
                    clipped.append((net, c)); n += 1
        if not n:
            raise ValueError(f"{inst}: straddles PG regions but exposes no {pin_layer} PG pin inside them")
        straddle[inst] = n
    if clipped:
        lines += ['set ot_pg_pin_rects {'] + ['  {' + net + ' ' + ' '.join(f'{x:.4f}' for x in c) + '}'
                                              for net, c in clipped] + ['}', PIN_VIAS_TCL.strip("\n")]
    return lines, owner, straddle


def stripe_tcl(grid_name, spec):
    """add_pdn_stripe for one row_spec (offset from the region / core lower edge, exact dbu, explicit parity)."""
    typ = 'GROUND' if spec['start'] == 'VSS' else 'POWER'
    return (f"add_pdn_stripe -grid {grid_name} -layer {spec['layer']} -width {_u(spec['w'])} -pitch {_u(spec['pitch'])} "
            f"-offset {_u(spec['offset'])} -spacing {_u(spec['half'] - spec['w'])} -starts_with {typ}")


def core_stripes_tcl(die, grid_name, grid=None):
    """the add_pdn_stripe lines of a plain CORE grid over the whole die (plans without domains): same lattice rule."""
    W, H = die['outline_um']
    g = grid if grid is not None else die.get('pg', {}).get('grid', [])
    rect = [0, 0, _d(W), _d(H)]
    return [stripe_tcl(grid_name, sp) for sp in (row_spec(s, rect, ('VDD', 'VSS')) for s in g) if sp]


def _lattice(sp):
    """[(net, centre)] of the stripes pdngen makes for one row_spec (fully inside lo..hi)."""
    out, c, j = [], sp['lo'] + sp['offset'], 0
    while 2 * c + sp['w'] <= 2 * sp['hi']:
        out.append((sp['start'] if j % 2 == 0 else sp['other'], c))
        c += sp['half']
        j += 1
    return out


def model_rects(die, grid=None, core=None):
    """[(net, layer, x0, y0, x1, y1)] in dbu: the exact pdngen result of pdn_tcl(die) (see the ONE PDN RULE note)."""
    W, H = die['outline_um']
    return region_model(plan_regions(die, grid), core or (0, 0, _d(W), _d(H)))


def rows_regions(rows):
    """plan_regions tuples back from die_infra.pg_grid region rows (row['region'], row['rect_um'], row['nets'])."""
    out, by = [], {}
    for g in rows:
        k = g['region']
        if k not in by:
            by[k] = (k, [_d(x) for x in g['rect_um']], tuple(g['region_nets']), [], [])
            out.append(by[k])
        _k, rect, nets, specs, layers = by[k]
        specs.append(row_spec(g, rect, nets))
        layers.append(g['layer'])
    return out


def halo(w):
    """pdngen's spacing halo (dbu) for a long M8/M9 stripe of width w (dbu): asap7_tech_1x_201209.lef SPACINGTABLE,
    last parallel-run column (same table as die_infra.pg_spacing)."""
    return 1000 if w >= 999.75 else 500 if w >= 499.75 else 40


def _pieces(sp, rect, others, core):
    """pieces of every lattice stripe of row_spec sp in region rect after pdngen's cut against the other regions'
    grid obstructions (each region box, bloated by this stripe's own spacing halo; a cut that leaves less than the
    full width drops that run).  -> [dict(net, c, lo, hi, blo, bhi)] (blo/bhi: end lies on the core boundary)."""
    V, w = sp['V'], sp['w']
    h = halo(w)
    A0, A1 = (rect[1], rect[3]) if V else (rect[0], rect[2])
    C0, C1 = (core[1], core[3]) if V else (core[0], core[2])
    out = []
    for net, c in _lattice(sp):
        a, b = c - w / 2, c + w / 2
        cuts = []
        for q in others:
            q0, q1, p0, p1 = (q[0], q[2], q[1], q[3]) if V else (q[1], q[3], q[0], q[2])
            if q0 - h < b and a < q1 + h and p0 - h < A1 and A0 < p1 + h:
                cuts.append((p0 - h, p1 + h))
        lo = A0
        for c0, c1 in sorted(cuts):
            if c1 <= lo:
                continue
            if c0 > lo:
                out.append(dict(net=net, c=c, lo=lo, hi=min(c0, A1)))
            lo = max(lo, c1)
            if lo >= A1:
                break
        if lo < A1:
            out.append(dict(net=net, c=c, lo=lo, hi=A1))
    for q in out:
        q['blo'], q['bhi'] = q['lo'] == C0, q['hi'] == C1
    return [q for q in out if q['hi'] > q['lo']]


def region_model(regs, core):
    """pdngen model of plan_regions tuples on core box core (dbu) -> [(net, layer, x0, y0, x1, y1)] in dbu.
    (1) lattice stripes fully inside the region; (2) cut by the other regions' boxes + spacing halo; (3) vias where
    same-net pieces of consecutive layers of the same grid overlap; (4) trim: a piece with < 2 vias is removed, the
    others are cut back to their outermost via on every end that is not on the core boundary; (5) a piece left
    without a via to a surviving piece is not written (pdngen writes only shapes with DB connectivity)."""
    import bisect
    out = []
    boxes = [r[1] for r in regs]
    for ri, (_name, rect, _nets, specs, layers) in enumerate(regs):
        others = [b for k, b in enumerate(boxes) if k != ri]
        rows = [(sp, _pieces(sp, rect, others, core)) for sp in specs if sp]
        for sp, ps in rows:
            for q in ps:
                q['w'] = sp['w']
        # orthogonal neighbours per row (add_pdn_connect between consecutive rows of the grid)
        nb = [[j for j in (i - 1, i + 1) if 0 <= j < len(rows) and rows[j][0]['V'] != rows[i][0]['V']
               and abs(layers.index(rows[j][0]['layer']) - layers.index(rows[i][0]['layer'])) == 1]
              for i in range(len(rows))]
        index = {}
        for i, (sp, ps) in enumerate(rows):
            for net in {q['net'] for q in ps}:
                lst = sorted((q for q in ps if q['net'] == net), key=lambda q: q['c'])
                index[(i, net)] = ([q['c'] for q in lst], lst)

        def crossings(i, p, alive=None):
            """[(along_lo, along_hi)] via spans of piece p of row i (with surviving pieces only when alive)."""
            res = []
            for j in nb[i]:
                cs, lst = index.get((j, p['net']), ([], []))
                wq = rows[j][0]['w']
                k0 = bisect.bisect_left(cs, p['lo'] - wq / 2)
                k1 = bisect.bisect_right(cs, p['hi'] + wq / 2)
                pa, pb = p['c'] - p['w'] / 2, p['c'] + p['w'] / 2
                for q in lst[k0:k1]:
                    if alive is not None and id(q) not in alive:
                        continue
                    s0, s1 = max(p['lo'], q['c'] - wq / 2), min(p['hi'], q['c'] + wq / 2)
                    if s0 < s1 and q['lo'] < pb and pa < q['hi']:
                        res.append((s0, s1))
            return res
        new = {}
        for i, (sp, ps) in enumerate(rows):
            for p in ps:
                v = crossings(i, p)
                if len(set(v)) < 2:
                    continue
                new[id(p)] = (p['lo'] if p['blo'] else min(x for x, _ in v), p['hi'] if p['bhi'] else max(x for _, x in v))
        alive = set(new)
        for i, (sp, ps) in enumerate(rows):
            for p in ps:
                if id(p) not in alive or not crossings(i, p, alive):
                    continue
                lo, hi = new[id(p)]
                a, b = p['c'] - sp['w'] / 2, p['c'] + sp['w'] / 2
                out.append((p['net'], sp['layer']) + ((a, lo, b, hi) if sp['V'] else (lo, a, hi, b)))
    return out


def pdn_tcl(die,loads=()):
    """Emit top meshes and optional (instance, power_net) abstract M7 connections."""
    rs=regions(die)
    loads=[q if isinstance(q,dict) else dict(inst=q[0],net=q[1],pin='VDD',rects=[[q[2][0],q[2][1],q[2][0]+1e-6,q[2][1]+1e-6]]) for q in loads]
    t=['set b [ord::get_db_block]', 'set dbu [[ord::get_db_tech] getDbUnitsPerMicron]']
    for net in sorted({n for r in rs for n in r['nets']}):
        typ='GROUND' if net=='VSS' else 'POWER'
        t += [f'set n [$b findNet {net}]',f'if {{$n eq "NULL"}} {{ set n [odb::dbNet_create $b {net}] }}',f'$n setSigType {typ}; $n setSpecial']
    for q in loads:
        inst,net,pin=q['inst'],q['net'],q['pin']
        flag='ground' if net=='VSS' else 'power'
        t += [f'add_global_connection -net {{{net}}} -inst_pattern {{^{inst}$}} -pin_pattern {{^{pin}$}} -{flag}',f'add_global_connection -net {{VSS}} -inst_pattern {{^{inst}$}} -pin_pattern {{^VSS$}} -ground']
    secondary=sorted({r['nets'][0]for r in rs}-{'VDD'})
    t += ['global_connect', 'set_voltage_domain -name Core -power VDD -ground VSS'+(' -secondary_power {'+' '.join(secondary)+'}' if secondary else '')]
    # ONE PDN RULE: exact dbu region boxes, per-row offset + parity from the die lattice (plan_regions / row_spec)
    for name,rect,(p,g),specs,layers in plan_regions(die):
        t += [f'set region [odb::dbRegion_create $b {name}]',f'odb::dbBox_create $region '+' '.join(f'[expr {{round({_u(x)}*$dbu)}}]' for x in rect),f'set_voltage_domain -name {name} -region {name} -power {p} -ground {g}',f'define_pdn_grid -name {name} -voltage_domains {{{name}}}']
        t += [stripe_tcl(name,sp) for sp in specs if sp]
        for a,b in zip(layers,layers[1:]):t.append(f"add_pdn_connect -grid {name} -layers {{{a} {b}}}")
    if loads:
        t += ['set ot_pg_pin_rects {']
        for q in loads:
            for r in q['rects']:
                t.append('  {'+q['net']+' '+' '.join(f'{x:.4f}'for x in r)+'}')
        t += ['}']
        t += [PIN_VIAS_TCL]
    return '\n'.join(t)+'\n'


def overlap(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]


def lef_pg_pins(text):
    import re
    pins={}
    for match in re.finditer(r'(?ms)^[ \t]*PIN[ \t]+(\S+)[ \t]*\n(.*?)^[ \t]*END[ \t]+\1[ \t]*$',text):
        name=match[1];body=match[2]
        use=re.search(r'\bUSE\s+(POWER|GROUND)\s*;',body)
        if not use:continue
        layer=None;rects=[]
        for line in body.splitlines():
            lm=re.search(r'\bLAYER\s+(\S+)\s*;',line)
            if lm:layer=lm[1]
            rm=re.search(r'\bRECT\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*;',line)
            if rm and layer:rects.append((layer,[float(rm[i])for i in range(1,5)]))
        pins[name]=dict(use=use[1],rects=rects)
    return pins


def resolve_loads(P,views,mapping):
    """Map real exposed PG pins. Never turn a mixed partition's entire VDD into PHY."""
    from pathlib import Path
    overrides=mapping.get('instances',{})
    unknown=set(overrides)-set(P.parts)
    if unknown:raise ValueError('PG map has unknown instances: '+', '.join(sorted(unknown)))
    loads=[];pgcache={}
    allowed={'VDD','VSS'}|{n for d in P.die.get('pg',{}).get('domains',[])for n in d['nets']}
    for inst in sorted(P.parts):
        tn=P.parts[inst]['type'];module=P.types[tn]['module']
        f=Path(views)/tn/(module+'.lef')
        if not f.is_file():raise ValueError(f'PG map requires actual abstract: {f}')
        if f not in pgcache:pgcache[f]=lef_pg_pins(f.read_text())
        pins=pgcache[f]
        nets={n:n for n in ['VDD','VSS','VDDPHY'] if n in pins}
        nets.update(overrides.get(inst,{}))
        for pin,net in nets.items():
            if net not in allowed:raise ValueError(f'{inst}/{pin}: undeclared supply net {net}')
            if pin not in pins:raise ValueError(f'{inst}: mapped supply pin {pin} absent from {f}; regenerate a truthful power interface before regional assembly')
            if pins[pin]['use']!=('GROUND' if net=='VSS' else 'POWER'):
                raise ValueError(f'{inst}/{pin}: PG USE incompatible with net {net}')
            rects=[]
            for layer,r in pins[pin]['rects']:
                if layer!='M7':continue
                a=P.to_die(inst,r[:2]);b=P.to_die(inst,r[2:]);rects.append([min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])])
            if not rects:raise ValueError(f'{inst}/{pin}: no exposed M7 PG geometry for the M8/M9 assembly mesh')
            loads.append(dict(inst=inst,pin=pin,net=net,rects=rects))
    for d in P.die.get('pg',{}).get('domains',[]):
        if not any(q['net']==d['nets'][0] and any(overlap(r,d['rect_um'])for r in q['rects'])for q in loads):
            raise ValueError(f"{d['name']}: no exposed {d['nets'][0]} power pin intersects its declared PHY region; existing CORE VDD pins cannot stand in for it")
    for q in loads:
        if q['net']!='VDD':continue
        for d in P.die.get('pg',{}).get('domains',[]):
            if d['nets'][0]!='VDD' and any(overlap(r,d['rect_um'])for r in q['rects']):
                raise ValueError(f"{q['inst']}/{q['pin']}: CORE VDD pin metal enters {d['name']} PHY region; use a truthful split PG abstract")
    return loads


def prototype_lef(P,tn,text,io):
    """Add PLANNED PHY PG interface only to a new mock abstract, never a signed view."""
    import re
    domains=P.die.get('pg',{}).get('domains',[])
    io_by_name={q['name']:q for q in io}
    per=[]
    for inst,p in P.parts.items():
        if p['type']!=tn:continue
        boxes=[]
        for d in domains:
            for name in d.get('io',[]):
                win=io_by_name.get(name)
                if not win or win.get('part')!=inst:continue
                # The containing partition's PG pin is split at the declared
                # domain boundary; the physical PHY body remains explicit in IO.
                a=P.rect(inst);b=d['rect_um'];r=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
                if r[0]>=r[2]or r[1]>=r[3]:continue
                u=P.to_type(inst,r[:2]);v=P.to_type(inst,r[2:]);boxes.append([min(u[0],v[0]),min(u[1],v[1]),max(u[0],v[0]),max(u[1],v[1])])
        per.append((inst,sorted([[round(x,4)for x in b]for b in boxes])))
    if not per or not any(boxes for _,boxes in per):return text
    sigs={json.dumps(boxes)for _,boxes in per}
    if len(sigs)!=1:raise ValueError(f'{tn}: per-instance PHY PG regions differ; cannot invent variants of a hardened type')
    boxes=per[0][1];pins=lef_pg_pins(text);vdd=pins.get('VDD')
    if not vdd:raise ValueError(f'{tn}: prototype needs existing CORE VDD interface')
    def subtract(r,b):
        if not overlap(r,b):return[r]
        x0,y0,x1,y1=r;u0,v0,u1,v1=b;out=[]
        if x0<u0:out.append([x0,y0,min(u0,x1),y1])
        if x1>u1:out.append([max(u1,x0),y0,x1,y1])
        a,c=max(x0,u0),min(x1,u1)
        if a<c and y0<v0:out.append([a,y0,c,min(v0,y1)])
        if a<c and y1>v1:out.append([a,max(v1,y0),c,y1])
        return[q for q in out if q[0]<q[2]and q[1]<q[3]]
    core=[];phy=[]
    for layer,r in vdd['rects']:
        cuts=[r]
        for b in boxes:
            # Keep a physical PG isolation gap between unrelated power pins.
            cuts=[a for q in cuts for a in subtract(q,[b[0]-.096,b[1]-.096,b[2]+.096,b[3]+.096])]
            if layer=='M7' and overlap(r,b):phy.append([layer,[max(r[0],b[0]),max(r[1],b[1]),min(r[2],b[2]),min(r[3],b[3])]])
        core +=[(layer,q)for q in cuts]
    if not core:
        raise ValueError(f'{tn}: declared PHY domain covers the entire containing partition and would erase its CORE VDD interface; specify a truthful smaller PHY footprint or a separately typed PHY-only macro')
    def pin(name,rects,use="POWER"):
        return '\n'.join([f'  PIN {name}','    DIRECTION INOUT ;',f'    USE {use} ;','    PORT']+[f'      LAYER {layer} ;\n        RECT '+ ' '.join(f'{x:.4f}'for x in r)+' ;'for layer,r in rects]+['    END',f'  END {name}'])
    text=re.sub(r'(?ms)^\s*PIN VDD\s*$.*?^\s*END VDD\s*$',lambda _:pin('VDD',[(layer,r)for layer,r in core if layer=='M7'])+'\n'+pin('VDDPHY',phy),text,count=1)
    # Only the external M7 PG interface is exported. The internal M5/M6
    # grid belongs inside the hardened block, not a collection of independent
    # die-level power terminals for PDNSim. No released view is changed.
    text=re.sub(r'(?ms)^\s*PIN VSS\s*$.*?^\s*END VSS\s*$',lambda _:pin('VSS',[(layer,r)for layer,r in pins['VSS']['rects']if layer=='M7'],'GROUND'),text,count=1)
    # The legacy mock has full M7 OBS, including over its PG pins. A planned
    # pin must have a real via landing window; retain the rest of the obstruction.
    allpins=lef_pg_pins(text)
    opening=[r for q in allpins.values()for layer,r in q['rects']if layer=='M7']
    width,height=P.types[tn]['outline_um'];obs=[[0,0,width,height]]
    for r in opening:obs=[a for q in obs for a in subtract(q,r)]
    def fixobs(match):
        body=match[0]
        replacement='    LAYER M7 ;\n'+'\n'.join('      RECT '+' '.join(f'{x:.4f}'for x in r)+' ;'for r in obs)
        return re.sub(r'(?ms)    LAYER M7 ;\s*RECT[^;]+;',lambda _:replacement,body,count=1)
    text=re.sub(r'(?ms)^  OBS\s*$.*?^  END\s*$',fixobs,text,count=1)
    return '# PLANNED PHY PG PROTOTYPE ONLY: no signoff or released-view claim\n'+text


PIN_VIAS_TCL = r'''
# Explicit same-net PG contacts for a containing macro spanning supply regions.
# Native macro grids select one voltage domain per instance and cannot represent
# this mixed macro. Use the technology's fixed VIA78 in a 2x2 array: 80nm pitch
# exceeds V7 cut32nm+spacing46nm and satisfies the wide-strap multi-cut rule.
proc ot_pg_connect_pins {} {
  global ot_pg_pin_rects
  set block [ord::get_db_block]
  set tech [ord::get_db_tech]
  set dbu [$tech getDbUnitsPerMicron]
  set via [$tech findVia VIA78]
  if {$via eq "NULL"} { error "regional PG needs actual technology VIA78" }
  set metal {}; set wires {}; set done {}; set count 0
  foreach q $ot_pg_pin_rects {
    lassign $q netname ux0 uy0 ux1 uy1
    if {![dict exists $metal $netname]} {
      set boxes {};set net [$block findNet $netname]
      foreach w [$net getSWires] {
        foreach s [$w getWires] {
          if {[$s isVia] || [[$s getTechLayer] getName] ne "M8"} continue
          lappend boxes [list [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
        }
      }
      dict set metal $netname $boxes
      dict set wires $netname [odb::dbSWire_create $net ROUTED]
    }
    set x0 [expr {round($ux0*$dbu)}];set y0 [expr {round($uy0*$dbu)}]
    set x1 [expr {round($ux1*$dbu)}];set y1 [expr {round($uy1*$dbu)}]
    foreach r [dict get $metal $netname] {
      lassign $r a b c d
      set x [expr {round(($x0+$x1)/2.0)}];set y [expr {round(($b+$d)/2.0)}]
      # Entire four-via enclosure must fit real M7 pin and actual same-net M8.
      set vx [expr {round(.056*$dbu)}];set vy [expr {round(.067*$dbu)}]
      set tx [expr {round(.067*$dbu)}];set ty [expr {round(.060*$dbu)}]
      if {$x-$vx<$x0 || $x+$vx>$x1 || $y-$vy<$y0 || $y+$vy>$y1 || $x-$tx<$a || $x+$tx>$c || $y-$ty<$b || $y+$ty>$d} continue
      set key [list $netname $x $y]
      if {[dict exists $done $key]} continue
      dict set done $key 1
      foreach dx {-0.040 0.040} {
        foreach dy {-0.040 0.040} {
          odb::dbSBox_create [dict get $wires $netname] $via [expr {round($x+$dx*$dbu)}] [expr {round($y+$dy*$dbu)}] STRIPE
          incr count
        }
      }
    }
  }
  puts "OT_PG_PIN_VIAS $count"
  if {!$count} {error "regional PG made no actual pin-to-mesh contacts"}
}
'''
