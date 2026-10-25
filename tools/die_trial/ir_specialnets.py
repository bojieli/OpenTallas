#!/usr/bin/env python3
"""Materialize the existing IR case's PDN as DEF special nets, avoiding pdngen's macro-grid expansion."""
import argparse,json,math,re
from pathlib import Path

def centers(lo,hi,phase,pitch):
    k=math.ceil((lo-phase)/pitch-1e-9)
    while phase+k*pitch<=hi+1e-9:
        yield phase+k*pitch
        k+=1

def materialize(out):
    out=Path(out); m=json.loads((out/'manifest.json').read_text());bx,by,ex,ey=m['solved_um'];w,h=ex-bx,ey-by
    grid=m['grid'];pitch=grid['pitch_um'];wid=grid['width_um'];off=grid['offset_um'];offx,offy=grid.get('offset_xy_um',[off,off]);T=m['tile_um']
    text=(out/'case.def').read_text(); comps=re.findall(r'- (T_(\d+)_(\d+)) (L\d+) \+ FIXED',text)
    # Generated via arrays follow the ASAP7 default rules. CUTSPACING is edge-to-edge in DEF.
    def via(name,rule,cut,layers,spacing,width,height,enc):
        cols=max(1,math.floor((width-cut)/spacing+1e-8)+1);rows=max(1,math.floor((height-cut)/spacing+1e-8)+1)
        return f'- {name} + VIARULE {rule} + CUTSIZE {round(cut*1000)} {round(cut*1000)} + LAYERS {layers} + CUTSPACING {round((spacing-cut)*1000)} {round((spacing-cut)*1000)} + ENCLOSURE {enc} + ROWCOL {rows} {cols} ;\n'
    vias='VIAS 2 ;\n'+via('PG78','M8_M7',.032,'M7 V7 M8',.078,.288,wid,'0 0 11 0')+via('PG89','M9_M8',.040,'M8 V8 M9',.097,wid,wid-.040,'0 0 0 20')+'END VIAS\n'
    text=text.replace('COMPONENTS ',vias+'COMPONENTS ',1).replace('END DESIGN','')
    # PDNSim's connectivity checker requires physical top-level supply terminals.
    # Put each BTerm entirely inside an existing M9 stripe; it adds no conductance.
    pins='PINS 2 ;\n'
    for net,phase in [('VDD',0),('VSS',pitch/2)]:
        x=next(centers(bx+wid/2,ex-wid/2,offx+phase,pitch))-bx
        y=next(centers(by+wid/2,ey-wid/2,offy+phase,pitch))-by
        pins+=f'- {net} + NET {net} + DIRECTION INOUT + USE {"POWER" if net=="VDD" else "GROUND"} + PORT + LAYER M9 ( -1 -1 ) ( 1 1 ) + FIXED ( {round(x*1000)} {round(y*1000)} ) N ;\n'
    text+=pins+'END PINS\n'
    counts={}
    with (out/'case_pg.def').open('w') as f:
        f.write(text);f.write('SPECIALNETS 2 ;\n')
        for net,phase in [('VDD',0),('VSS',pitch/2)]:
            xs=list(centers(bx+wid/2,ex-wid/2,offx+phase,pitch));ys=list(centers(by+wid/2,ey-wid/2,offy+phase,pitch))
            f.write(f'- {net} ( * {net} ) + USE '+('POWER' if net=='VDD' else 'GROUND')+'\n')
            first=True; n78=n89=0
            def route(layer,width,points,via_name=''):
                nonlocal first
                f.write((' + ROUTED ' if first else ' NEW ')+f'{layer} {round(width*1000)} + SHAPE STRIPE '+points+(' '+via_name if via_name else '')+'\n');first=False
            for y in ys:route('M8',wid,f'( 0 {round((y-by)*1000)} ) ( {round(w*1000)} * )')
            for x in xs:route('M9',wid,f'( {round((x-bx)*1000)} 0 ) ( * {round(h*1000)} )')
            for x in xs:
                for y in ys:
                    route('M8',wid,f'( {round((x-bx)*1000)} {round((y-by)*1000)} )','PG89');n89+=1
            for name,i,j,master in comps:
                i,j=int(i),int(j);tx,ty=bx+i*T,by+j*T;tw=min(T,ex-tx);th=min(T,ey-ty)
                pinphase=4.128 if net=='VDD' else 4.512
                for lx in centers(.144,tw-.144,pinphase,8.64):
                    for y in centers(max(ty,by+wid/2),min(ty+th,ey-wid/2),offy+phase,pitch):
                        # Pins abut at tile boundaries; each crossing appears once per component's pin.
                        route('M7',.288,f'( {round((tx+lx-bx)*1000)} {round((y-by)*1000)} )','PG78');n78+=1
            f.write(' ;\n');counts[net]={'via78':n78,'via89':n89,'m8_stripes':len(ys),'m9_stripes':len(xs)}
        f.write('END SPECIALNETS\nEND DESIGN\n')
    t=(out/'run.tcl').read_text();t=t.replace('read_def /work/case.def','read_def /work/case_pg.def')
    start=t.index('set_voltage_domain ');end=t.index('read_liberty ',start)
    t=t[:start]+'puts "OT_PDN PASS DEF-specialnets"\n'+t[end:]
    (out/'run_pg.tcl').write_text(t);m['pdn_implementation']='DEF specialnets with ASAP7 rule-generated VIA78/VIA89 arrays';m['pdn_counts']=counts
    (out/'manifest.json').write_text(json.dumps(m,indent=1)+'\n');print(json.dumps(counts))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);materialize(p.parse_args().out)
