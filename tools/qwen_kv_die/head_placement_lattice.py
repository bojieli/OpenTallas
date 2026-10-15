"""Integer site/track congruence matching ot_mts::rule/snap_origin.

The die source uses initialize_floorplan core origin0/site asap7sc7p5t.
This derives rules from every signal rectangle, including orientation. A later
OpenROAD actual-placement replay remains required; no collision-driven move is
silently inherited from the Tcl placer.
"""
import functools
import hashlib
import math
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import check_macro_track_alignment as C


@functools.lru_cache(maxsize=None)
def lef(path):
    text=Path(path).read_text();macros=C.parse_lef(text)
    if len(macros)!=1:raise ValueError('expected one hard macro: '+str(path))
    return macros[0]


def declared(outline,pins):
    macro=dict(name='DECLARED_PIN_PLAN',W=round(outline[0]*1000),H=round(outline[1]*1000),pins=[])
    for name,p in pins.items():
        x,y=p['xy'];w,h=(.144,.024)if p['layer']=='M4'else(.024,.144)
        macro['pins'].append(dict(name=name,use='SIGNAL',rects=[(p['layer'],
            tuple(round(v*1000)for v in(x-w/2,y-h/2,x+w/2,y+h/2)))]))
    return macro


def from_pin_tcl(path,outline):
    pins={}
    for name,layer,x,y in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{([\d.-]+) ([\d.-]+)\}',Path(path).read_text()):
        pins[name]=dict(layer=layer,xy=[float(x),float(y)])
    if not pins:raise ValueError('no declared pins: '+str(path))
    return declared(outline,pins)


_RULE_CACHE={}
_KEEP_MACROS={}
def rule(macro,orient):
    key=(id(macro),orient)
    if key in _RULE_CACHE:return _RULE_CACHE[key]
    _KEEP_MACROS[id(macro)]=macro
    axes={'x':(1,{0}),'y':(1,{0})}
    grouped={}
    for pin in macro['pins']:
        if pin['use']in('POWER','GROUND'):continue
        for layer,rect in pin['rects']:
            if layer not in C.ASAP7_TRACKS_NM:continue
            axis='y'if C.ASAP7_LAYERS[layer][0]=='H'else'x'
            r=C.transform_rect(rect,orient,macro['W'],macro['H'])
            grouped.setdefault((layer,axis),[]).append((r[1],r[3])if axis=='y'else(r[0],r[2]))
    for (layer,axis),pins in grouped.items():
        period,tracks=C.track_residues(C.ASAP7_TRACKS_NM[layer],axis)
        legal=C.legal_origins(pins,period,tracks,'center')
        old,previous=axes[axis];joint=math.lcm(old,period)
        axes[axis]=(joint,{r for r in range(joint)if r%old in previous and r%period in legal})
    result={}
    for axis,(period,legal)in axes.items():
        site=C.SITE_X_NM if axis=='x'else C.ROW_Y_NM
        grid=C.joint_grid(legal,period,site)
        if not grid['legal_origins_mod_joint_nm']:
            raise ValueError(f"no site/track origin for{macro['name']} {orient} {axis}")
        result[axis]=grid
    _RULE_CACHE[key]=result
    return result


def snap(macro,orient,xy):
    rules=rule(macro,orient);out=[]
    for axis,value in zip(('x','y'),xy):
        g=rules[axis];period=g['joint_period_nm'];target=round(value*1000)
        candidates=[]
        for residue in g['legal_origins_mod_joint_nm']:
            lower=math.floor((target-residue)/period)
            candidates.extend(residue+k*period for k in(lower,lower+1))
        point=min(candidates,key=lambda x:(abs(x-target),x));out.append(point/1000)
    return out,rules


def provenance():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in
        ('physical/common/ot_macro_track_snap.tcl','tools/check_macro_track_alignment.py',
         'tools/qwen_kv_die/head_placement_lattice.py')}
