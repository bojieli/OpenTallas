"""Project binder-declared, value-audited R8 pad-count inputs into physical metadata."""
import copy
import json
import re
from pathlib import Path


def declared(kit_rtl_json):
    kr = json.loads(Path(kit_rtl_json).read_text())
    ports = {r['port']: (r['dir'], r['width']) for r in kr.get('bound_only_pins', [])}
    if not kr.get('bind_out'):
        if any(name.startswith('strap_r8pad_') for name in ports):
            raise ValueError('R8 count ports lack their bind authority')
        # Native station/source manifests have no binder metadata to project.
        return []
    root = Path(kr['bind_out'])
    mf = root/'bind_parent_id_straps.json'
    if not mf.exists():
        if any(name.startswith('strap_r8pad_') for name in ports):
            raise ValueError('R8 count ports lack their bind manifest')
        return []
    manifest = json.loads(mf.read_text())
    rows = manifest.get('types', {}).get(kr.get('bound_type', kr.get('type')), {})
    result = []
    for name, row in rows.items():
        if row.get('kind') != 'r8pad_strap':
            continue
        if not re.fullmatch(r'strap_r8pad_[A-Za-z0-9_]+', name) or row.get('width') != 4 or ports.get(name) != ('input', 4):
            raise ValueError(f'invalid bound R8 count declaration: {name}')
        audit = json.loads((root/'bind_r8pad_strap_audit.json').read_text())
        if audit.get('verdict') != 'PASS' or audit.get('errors') or audit.get('checked_bits', 0) < 4:
            raise ValueError(f'R8 count value audit not PASS: {name}')
        owners = kr.get('instances', [])
        if (not isinstance(owners, list) or not owners or any(not isinstance(q, str) for q in owners)
                or len(set(owners)) != len(owners)):
            raise ValueError(f'R8 count lacks exact owning instances: {name}')
        values = [manifest.get('instances', {}).get(q, {}).get(name, {}) for q in owners]
        if any(v.get('kind') != 'r8pad_strap' or v.get('width') != 4 or type(v.get('value')) is not int or not 0 <= v['value'] < 16 for v in values):
            raise ValueError(f'R8 count owning-instance ties absent/invalid: {name}')
        result.append({'name': name, 'width': 4})
    actual_r8 = {name for name in ports if name.startswith('strap_r8pad_')}
    if actual_r8 != {row['name'] for row in result}:
        raise ValueError('R8 count ports disagree with the declared bind inventory')
    return result


def project(raw, kit_rtl):
    result = raw
    for tn, fl in (kit_rtl or {}).items():
        kit_json = Path(fl).with_name('kit_rtl.json')
        if not kit_json.is_file():
            # A plain native filelist carries no bound metadata to promote.
            continue
        additions = declared(kit_json)
        if not additions:
            continue
        kr = json.loads(kit_json.read_text())
        parts = {p['name']: p['type'] for p in raw.get('partitions', [])}
        if kr.get('plan_type') != tn or any(parts.get(q) != tn for q in kr['instances']):
            raise ValueError(f'type {tn}: R8 kit instances disagree with owning plan type')
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
