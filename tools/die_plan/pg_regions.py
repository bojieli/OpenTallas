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
    for k,r in enumerate(rs):
        name=f'ot_pg_{k}';p,g=r['nets'];rect=r['rect_um']
        t += [f'set region [odb::dbRegion_create $b {name}]',f'odb::dbBox_create $region '+ ' '.join(f'[expr {{round({x:g}*$dbu)}}]' for x in rect),f'set_voltage_domain -name {name} -region {name} -power {p} -ground {g}',f'define_pdn_grid -name {name} -voltage_domains {{{name}}} -starts_with GROUND']
        for s in r['grid']:
            # All region pieces use the die's global phase, including net parity.
            axis=1 if s['layer']=='M8' else 0
            offset=(s['offset_um']-rect[axis])%s['pitch_um']
            t.append(f"add_pdn_stripe -grid {name} -layer {s['layer']} -width {s['width_um']:g} -pitch {s['pitch_um']:g} -offset {offset:g} -spacing {s['pitch_um']/2-s['width_um']:g}")
        for a,b in zip(r['grid'],r['grid'][1:]):t.append(f"add_pdn_connect -grid {name} -layers {{{a['layer']} {b['layer']}}}")
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
