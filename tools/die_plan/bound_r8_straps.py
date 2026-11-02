"""Project binder-declared, value-audited R8 pad-count inputs into physical metadata."""
import copy
import json
import re
from pathlib import Path


def declared(kit_rtl_json):
    kr = json.loads(Path(kit_rtl_json).read_text())
    root = Path(kr['bind_out'])
    manifest = json.loads((root/'bind_parent_id_straps.json').read_text())
    rows = manifest.get('types', {}).get(kr['bound_type'], {})
    ports = {r['port']: (r['dir'], r['width']) for r in kr.get('bound_only_pins', [])}
    result = []
    for name, row in rows.items():
        if row.get('kind') != 'r8pad_strap':
            continue
        if not re.fullmatch(r'strap_r8pad_[A-Za-z0-9_]+', name) or row.get('width') != 4 or ports.get(name) != ('input', 4):
            raise ValueError(f'invalid bound R8 count declaration: {name}')
        audit = json.loads((root/'bind_r8pad_strap_audit.json').read_text())
        if audit.get('verdict') != 'PASS' or audit.get('errors') or audit.get('checked_bits', 0) < 4:
            raise ValueError(f'R8 count value audit not PASS: {name}')
        values = [v[name] for v in manifest.get('instances', {}).values() if name in v]
        if not values or any(v.get('kind') != 'r8pad_strap' or v.get('width') != 4 or type(v.get('value')) is not int or not 0 <= v['value'] < 16 for v in values):
            raise ValueError(f'R8 count instance ties absent/invalid: {name}')
        result.append({'name': name, 'width': 4})
    return result


def project(raw, kit_rtl):
    result = raw
    for tn, fl in (kit_rtl or {}).items():
        additions = declared(Path(fl).with_name('kit_rtl.json'))
        if not additions:
            continue
        if result is raw:
            result = copy.deepcopy(raw)
        t = result['partition_types'][tn]
        existing = {r['name']: r for r in t.get('id_straps', []) + t.get('count_straps', [])}
        for row in additions:
            old = existing.get(row['name'])
            if old and old['width'] != row['width']:
                raise ValueError(f'conflicting R8 count declaration: {row["name"]}')
            if not old:
                t.setdefault('count_straps', []).append(row)
                existing[row['name']] = row
    return result
