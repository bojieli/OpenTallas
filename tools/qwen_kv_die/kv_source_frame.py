"""Validate an explicit diagnostic D2D frame against its selected source kit."""
import hashlib
import json
import re
from pathlib import Path


def load(root, manifest, kit, top):
    root = Path(root).resolve()

    def path(name):
        p = (root / name).resolve()
        if not p.is_relative_to(root):
            raise ValueError(f'source-frame path escapes source tree: {name}')
        return p

    def verify(name, digest):
        p = path(name)
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError(f'source-frame identity changed: {name}')
        return p

    rec = json.loads(path(manifest).read_text())
    if rec.get('schema') != 'opentallas.kv_d2d_source_frame.v1' or rec.get('qualification') != 'SOURCE_FRAME_DIAGNOSTIC_ONLY':
        raise ValueError('source-frame requires an explicit diagnostic identity receipt')
    if rec.get('kit') != f'physical/ref_tile/{kit}' or rec.get('top') != top:
        raise ValueError('source-frame does not identify the selected kit and top')
    sp = verify(f'physical/ref_tile/{kit}/spec.json', rec['spec_sha256'])
    spec = json.loads(sp.read_text())
    if spec['top'] != top or rec.get('params') != spec.get('params'):
        raise ValueError('source-frame parameters differ from selected source kit')
    sources = rec.get('source_sha256', {})
    if set(sources) != set(spec['sources']):
        raise ValueError('source-frame must identify every selected RTL source')
    recipes = rec.get('pin_recipe_sha256', {})
    required = {spec['io_tcl'], f'physical/ref_tile/{kit}/floorplan.json',
                f'physical/ref_tile/{kit}/pin_geometry_plan.json'}
    if not required.issubset(recipes):
        raise ValueError('source-frame lacks selected pin and floorplan recipe identities')
    for name, digest in list(sources.items()) + list(recipes.items()):
        verify(name, digest)
    if 'views' in Path(rec['lef']).parts:
        raise ValueError('diagnostic source-frame must remain outside views/')
    lef = verify(rec['lef'], rec['lef_sha256'])
    match = re.search(r'MACRO\s+' + re.escape(top) + r'\b.*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef.read_text(), re.S)
    if not match:
        raise ValueError('source-frame LEF lacks the selected top and outline')
    outline = list(map(float, match.groups()))
    expected = [float(spec['outline'][k]) for k in ('w', 'h')]
    if outline != list(map(float, rec['outline'])) or outline != expected:
        raise ValueError('source-frame LEF outline differs from selected source kit')
    return lef, rec
