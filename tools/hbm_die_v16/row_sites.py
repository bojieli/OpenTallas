"""Source-bound per-stage placement transport, with exact graph invariance.

Geometry and clock phase remain separate hard gates. This transport never
changes a stage count, master, clock, reset, edge, splice, strap or ring setting.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import re

ROW = re.compile(r'lane row (\S+) (\d+)/(\d+) ([A-Z]+); site \(([-\d.]+), ([-\d.]+)\) um')


def graph_digest(spec):
    normalized = copy.deepcopy(spec)
    for inst in normalized['instances']:
        inst['note'] = ROW.sub(lambda m: m.group(0).split('; site ')[0] + '; site (POSITION) um', inst.get('note', ''))
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def transport(spec, inputs, export=None, plan=None):
    rows = {}
    for inst in spec['instances']:
        match = ROW.search(inst.get('note', ''))
        if match and ('_k' in match[1] or '_pa' in match[1]):
            row = rows.setdefault(match[1], dict(instances=[], master=inst['master'], tiles=int(match[3]),
                                                  direction=match[4], xy=[float(match[5]), float(match[6])], slot=inst['slot']))
            row['instances'].append(inst['name'])
    binding = {key: hashlib.sha256(Path(path).read_bytes()).hexdigest() for key, path in inputs.items() if path}
    digest = graph_digest(spec)
    packet = dict(schema='opentallas.hbm.pad_row_sites.v1', input_sha256=binding,
                  graph_sha256=digest, rows=rows, geometry_qualified=False,
                  scope='Actual ordered pad/landing stage identity; legal cell-row/endpoint/clock qualification required')
    if export:
        Path(export).write_text(json.dumps(packet, indent=1) + '\n')
    if not plan:
        return dict(exported_rows=len(rows), assigned_rows=0, graph_sha256=digest, geometry_qualified=False)
    assigned = json.loads(Path(plan).read_text())
    if assigned.get('input_sha256') != binding or assigned.get('graph_sha256') != digest:
        raise ValueError('ROW_SITES REFUSED: source/graph binding differs')
    if set(assigned.get('rows', {})) != set(rows):
        raise ValueError('ROW_SITES REFUSED: missing/extra landing or ordered pad stage')
    for key, row in rows.items():
        target = assigned['rows'][key]
        for field in ('instances', 'master', 'tiles', 'direction', 'slot'):
            if target.get(field) != row[field]:
                raise ValueError(f'ROW_SITES REFUSED: stage identity differs {key}.{field}')
        xy = target.get('xy')
        if not isinstance(xy, list) or len(xy) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in xy):
            raise ValueError(f'ROW_SITES REFUSED: non-finite/missing coordinate {key}')
    for inst in spec['instances']:
        match = ROW.search(inst.get('note', ''))
        if match and match[1] in rows:
            x,y = assigned['rows'][match[1]]['xy']
            inst['note'] = ROW.sub(lambda m: m.group(0).split('; site ')[0] + f'; site ({x:.1f}, {y:.1f}) um', inst['note'])
    if graph_digest(spec) != digest:
        raise ValueError('ROW_SITES REFUSED: functional/clock/reset/ordered stage graph changed')
    return dict(exported_rows=len(rows), assigned_rows=len(rows), graph_sha256=digest,
                plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(), geometry_qualified=False)
