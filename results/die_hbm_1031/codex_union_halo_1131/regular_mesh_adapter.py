"""Diagnostic adapter: actual union-sited mesh buffer contacts, regular FIXED metal.
Native macro K ports are an explicit unresolved ledger, never boundary aliases.
"""
from collections import defaultdict
import copy
import math
import clock_routed as C


def adapt(pilot, params, *, allow_missing_native=False, gap_offset=0):
    g=pilot['geom'];cells=copy.deepcopy(pilot['cells'])
    missing=list(g.get('core_loads',[]))
    if missing and not allow_missing_native:
        raise ValueError(f'{len(missing)} native child clock hooks unimplemented')
    pitch=float(params['pg_pitch'])
    def gap(v):return round((math.floor(v/pitch)+.5)*pitch,4)
    hl,vl=params['strap_layers']['h'],params['strap_layers']['v']
    if (hl,vl)!=('M8','M9'):raise ValueError('contact adapter requires actual M8/M9 layer policy')
    vcuts=defaultdict(set);hcuts=defaultdict(set);paths=[];drivers=[];loads=[]
    for n,c in cells.items():
        c['lib']=c['master'];c['orient']='MX' if round(c['y']/float(params['row_h']))%2 else 'R0'
    for role,names,pin in [('driver',g['drivers'],'Y'),('load',[n for n in g['mesh_loads'] if n not in missing],'A')]:
        for n in names:
            px,py=C.pin_point(cells,n,pin,cells[n]['lib'])
            if role=='driver':
                ax,ay=g['drv_anchor'][n];layer=vl;row=gap(ay)
            else:
                ax,ay=g['tap_node'][n];layer=vl if n in g.get('taps_on_v',[]) else hl;row=gap(ay) if layer==vl else ay
            sx=round(gap(px)+gap_offset*pitch,4)
            points=[(layer,ax,ay)]
            if layer==vl:
                vcuts[ax].add(ay);vcuts[ax].add(row);points += [(vl,ax,row),(hl,ax,row)]
            else:
                hcuts[ay].add(ax)
            points += [(hl,sx,row),(vl,sx,row),(vl,sx,py)]
            points=[p for i,p in enumerate(points) if not i or p!=points[i-1]]
            if row in g['hy']:
                hcuts[row].update([ax,sx])
            if sx in g['vx']:
                vcuts[sx].update([row,py])
            paths.append(dict(role=role,cell=n,pin=pin,vertices=points))
            (drivers if role=='driver' else loads).append(dict(anchor=list(points[-1]),units=[n]))
    edges=[]
    def add(a,b):
        if a!=b:edges.append([list(a),list(b)])
    for x in g['vx']:
        ys=sorted({*g['y_span'],*g['hy'],*vcuts[x]})
        for a,b in zip(ys,ys[1:]):add((vl,x,a),(vl,x,b))
    for y in g['hy']:
        xs=sorted({*g['x_span'],*g['vx'],*hcuts[y]})
        for a,b in zip(xs,xs[1:]):add((hl,a,y),(hl,b,y))
        for x in g['vx']:add((hl,x,y),(vl,x,y))
    for path in paths:
        for a,b in zip(path['vertices'],path['vertices'][1:]):add(a,b)
    # Exact duplicate edges carry one physical conductor, not parallel RC.
    edges=list({tuple(sorted((tuple(a),tuple(b)))):(a,b) for a,b in edges}.values())
    graph=dict(edges=edges,vias=sum(a[0]!=b[0]for a,b in edges),drivers=drivers,cell_loads=loads,taps=[])
    record=dict(scope='Partial physical current-union clock contact diagnostic; original hub census. Native child hooks/current station event held.',missing_native_hooks=missing,actual_driver_contacts=len(drivers),buffer_input_contacts=len(loads),release_qualified=False,paths=paths)
    return dict(name='ck_mesh',explicit_mesh=True,ndr='4w',mesh_graph=graph),cells,record


def fixed_tcl(pilot, params, *, ndr_name, allow_missing_native=False, gap_offset=0):
    wire,cells,record=adapt(pilot,params,allow_missing_native=allow_missing_native,gap_offset=gap_offset)
    lines,emitted=C.routed_tcl([wire],cells,{},C.BUF_DEFAULT,ndr_name)
    prefix=['set blk [ord::get_db_block]','set tech [ord::get_db_tech]',
            'set mesh [$blk findNet ck_mesh]',
            'if {$mesh == "NULL"} {error {missing actual ck_mesh net}}',
            'foreach sw [$mesh getSWires] {odb::dbSWire_destroy $sw}']
    record['emitted']=emitted
    return prefix+lines,record
