"""Fail-closed checks for replacing a PQ reservation with a real hardened view."""
import hashlib
import re
from pathlib import Path


def load_lef(path):
    path=Path(path);text=path.read_text()
    m=re.search(r'^MACRO (\S+)',text,re.M);size=re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)',text)
    if not m or not size:raise ValueError('one complete macro LEF required')
    pins={}
    for p in re.finditer(r'\n  PIN (\S+)\n(.*?)\n  END \1',text,re.S):
        name,body=p.groups()
        if 'USE POWER' in body or 'USE GROUND' in body:continue
        direction=re.search(r'DIRECTION (\w+)',body)
        rectangles=[]
        for layer,section in re.findall(r'LAYER (\w+) ;(.*?)(?=LAYER|\Z)',body,re.S):
            for coords in re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',section):
                rectangles.append(dict(layer=layer,rect=list(map(float,coords))))
        if not direction or not rectangles:raise ValueError('missing pin direction or geometry: '+name)
        pins[name]=dict(direction=direction[1],rectangles=rectangles)
    if not pins:raise ValueError('LEF has no physical signal pins')
    return dict(master=m[1],width_um=float(size[1]),height_um=float(size[2]),pins=pins,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def validate(slot,view,expected_pins,stations,maximum_segment_um=100):
    """Check necessary physical conditions, never treat wire distance as closure.

    expected_pins maps every scalar bit to INPUT/OUTPUT. A new parity/valid field
    must enter this actual RTL contract; aggregate historical pin counts cannot
    qualify missing fields. Only R0 is currently produced by the PQ plan.
    """
    if slot.get('orient','R0')!='R0':raise ValueError('unsupported candidate orientation')
    fit=view['width_um']<=slot['w']+1e-6 and view['height_um']<=slot['h']+1e-6
    missing=sorted(set(expected_pins)-set(view['pins']))
    extra=sorted(set(view['pins'])-set(expected_pins))
    direction=[n for n in set(expected_pins)&set(view['pins'])if expected_pins[n]!=view['pins'][n]['direction']]
    distances={};outside=[]
    for name,p in view['pins'].items():
        choices=[]
        for r in p['rectangles']:
            x0,y0,x1,y1=r['rect']
            if min(x0,y0)<-1e-6 or x1>view['width_um']+1e-6 or y1>view['height_um']+1e-6:
                outside.append(name)
            x=slot['x']+(x0+x1)/2;y=slot['y']+(y0+y1)/2
            for s in stations:
                choices.append(max(s['x']-x,0,x-s['x']-s['w'])+max(s['y']-y,0,y-s['y']-s['h']))
        distances[name]=min(choices)if choices else None
    too_far=[n for n,d in distances.items()if d is None or d>maximum_segment_um+1e-6]
    return dict(geometry_PASS=fit and not(missing or extra or direction or outside or too_far),
        outline_fits=fit,missing_pins=missing,extra_pins=extra,wrong_directions=sorted(direction),
        pins_outside_macro=sorted(set(outside)),pins_beyond_station_reach=too_far,
        maximum_lower_bound_segment_um=max((d for d in distances.values()if d is not None),default=None),
        source_LEF_sha256=view['sha256'],all_distances_are_Manhattan_lower_bounds=True,
        obstacle_aware_routes_qualified=False,SS_FF_qualified=False,physical_adopted=False)
