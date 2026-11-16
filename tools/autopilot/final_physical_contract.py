"""Recover the routed physical interface from a signed final DEF and its paired LEF.

Requested kit pins and freeze records remain historical inputs. This derives a
new physical contract; it never edits or re-signs the routed implementation.
"""
import hashlib
import re
from pathlib import Path


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _nm(v):
    return round(float(v) * 1000)


def derive(def_path, lef_path, module):
    dp, lp = Path(def_path), Path(lef_path)
    text, lef = dp.read_text(), lp.read_text()
    design = re.search(r'^DESIGN\s+(\S+)\s*;', text, re.M)
    units = re.search(r'UNITS DISTANCE MICRONS\s+(\d+)\s*;', text)
    area = re.search(r'DIEAREA\s+\(\s*0\s+0\s*\)\s+\(\s*(\d+)\s+(\d+)\s*\)', text)
    size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', lef)
    master = re.search(r'^MACRO\s+(\S+)', lef, re.M)
    if not all((design, units, area, size, master)) or design[1] != module or master[1] != module:
        raise ValueError('final DEF/LEF module, units or outline absent/mismatched')
    u = int(units[1]); outline = [int(area[i]) / u for i in (1, 2)]
    if tuple(map(_nm, outline)) != tuple(_nm(size[i]) for i in (1, 2)):
        raise ValueError('final DEF/LEF outlines differ')
    section = re.search(r'^PINS\s+(\d+)\s*;(.*?)^END PINS', text, re.M | re.S)
    if not section:
        raise ValueError('final DEF PINS absent')
    raw = re.findall(r'^\s*-\s+(\S+)\s+(.*?);', section[2], re.M | re.S)
    if len(raw) != int(section[1]):
        raise ValueError('incomplete final DEF pin section')
    actual, geometry = {}, {}
    for name, body in raw:
        use = re.search(r'\+ USE\s+(\w+)', body)
        if use and use[1] in ('POWER', 'GROUND'):
            continue
        shapes = re.findall(r'\+ LAYER\s+(\S+)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)', body)
        fixed = re.search(r'\+ (?:FIXED|PLACED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)', body)
        direction = re.search(r'\+ DIRECTION\s+(\w+)', body)
        if len(shapes) != 1 or not fixed or fixed[3] != 'N' or not direction or name in actual:
            raise ValueError('unsupported or duplicate final BTerm geometry: ' + name)
        layer, *rr = shapes[0]; x0,y0,x1,y1 = map(int, rr); x,y = int(fixed[1]),int(fixed[2])
        box = [(x+x0)/u,(y+y0)/u,(x+x1)/u,(y+y1)/u]
        actual[name] = dict(name=name,layer=layer,x=round((box[0]+box[2])/2,6),y=round((box[1]+box[3])/2,6))
        geometry[name] = dict(direction=direction[1],layer=layer,rect_um=box)
    seen = set()
    for name, body in re.findall(r'^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$', lef, re.M | re.S):
        use = re.search(r'\bUSE\s+(\w+)\s*;', body)
        if use and use[1] in ('POWER','GROUND'):
            continue
        layer = re.search(r'\bLAYER\s+(\S+)\s*;',body)
        rects = re.findall(r'\bRECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;',body)
        direction = re.search(r'\bDIRECTION\s+(\w+)\s*;',body)
        if name not in actual or name in seen or not layer or len(rects)!=1 or not direction:
            raise ValueError('final LEF/DEF pin set or geometry differs: '+name)
        seen.add(name); r=list(map(float,rects[0])); q=actual[name]
        if (layer[1]!=q['layer'] or direction[1]!=geometry[name]['direction'] or
            tuple(map(_nm,r))!=tuple(map(_nm,geometry[name]['rect_um']))):
            raise ValueError('final LEF/DEF pin rectangle differs: '+name)
    if seen != set(actual):
        raise ValueError('final LEF is missing signal BTerms')
    return dict(schema='opentallas.final_physical_contract.v1',module=module,outline_um=outline,
                pins=[actual[n] for n in sorted(actual)],actual_geometry=geometry,
                sources=dict(def_path=str(dp),def_sha256=_sha(dp),lef_path=str(lp),lef_sha256=_sha(lp)),
                basis='signed final DEF BTerms cross-checked against paired LEF; no requested coordinates substituted')
