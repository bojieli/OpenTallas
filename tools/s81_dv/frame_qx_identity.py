#!/usr/bin/env python3
"""Exact split-frame QX image prefixes, using canonical instance suffixes and unchanged electrical pins."""
import hashlib
import json
from pathlib import Path
import re
from gb_image_identity import calls

OLD='ot_v41_rom_elem_q_qxpq_w10'
NEW=OLD+'_gb'
SUFFIXES=('_0','_1','b_0','b_1')


def prove(parent_text, band_text):
    ref={(c['module'],c['name']):c for c in calls(parent_text) if c['module']==OLD}
    mapped={}
    for c in calls(band_text):
        if c['module']!=OLD:continue
        r=ref.get((c['module'],c['name']))
        if not r or 'INSTANCE' not in r['params']:
            raise ValueError('canonical QX identity missing: '+c['name'])
        if re.sub(r'\s+','',r['ports'])!=re.sub(r'\s+','',c['ports']):
            raise ValueError('split QX electrical pins changed: '+c['name'])
        expr=r['params']['INSTANCE'][2]
        suffix=re.fullmatch(r'\{\s*INSTANCE\s*,\s*"([A-Za-z0-9_]+)"\s*\}',expr)
        if not suffix:raise ValueError('unknown canonical QX image expression: '+expr)
        if c['name'] in mapped or suffix[1] in mapped.values():raise ValueError('duplicate QX image identity')
        mapped[c['name']]=suffix[1]
    if not mapped:raise ValueError('split band has no QX image-backed cells')
    return mapped


def emit_bound_aliases(parent_text,band_text,frame,band_instance,report,images):
    if not re.fullmatch(r'[A-Za-z_]\w*',frame) or not re.fullmatch(r'u_r\d+',band_instance):
        raise ValueError('unsafe frame/band identity')
    mapping=prove(parent_text,band_text)
    audit={}
    for row in report.get('instance_path_params',[]):
        if row['inst'] in audit:raise ValueError('duplicate bound image selector')
        audit[row['inst']]=row
    pending=[];rows=[]
    for name,suffix in mapping.items():
        inst=frame+'.'+band_instance+'.'+name;row=audit.get(inst)
        if not row or row.get('module') not in (OLD,NEW) or row.get('param')!='INSTANCE':
            raise ValueError('missing actual bound QX selector: '+inst)
        selector=json.loads(row.get('value','null'))
        if not selector or selector!=inst:raise ValueError('empty or wrong bound QX selector: '+inst)
        for bank in SUFFIXES:
            source=frame+suffix+bank+'.viamap.hex';dest=selector+bank+'.viamap.hex'
            data=(Path(images)/source).read_bytes();words=data.decode().splitlines()
            if len(words)!=512 or any(not re.fullmatch('[0-9a-fA-F]{548}',w) for w in words):
                raise ValueError('invalid4096x274 via-map: '+source)
            target=Path(images)/dest
            if target.exists() and target.read_bytes()!=data:raise ValueError('preserve conflicting QX alias: '+dest)
            pending.append((target,data));rows.append(dict(original_cell=inst,image=source,alias=dest,image_sha256=hashlib.sha256(data).hexdigest()))
    for target,data in pending:
        if not target.exists():target.write_bytes(data)
    return rows
