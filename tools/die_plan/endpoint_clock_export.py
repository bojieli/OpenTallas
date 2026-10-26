"""Bind native TT/FF endpoint exports to immutable recovered route inputs.

This stores measurements, never substitutes a mean and never grants SIGNED.
Tcl export runs in the caller's already loaded, unchanged policy scene.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def make_manifest(view_id, files, source_sha=''):
    required={'netlist', 'spef', 'odb', 'sdc', 'config'}
    if set(files) != required:
        raise ValueError('manifest needs exact netlist/SPEF/ODB/SDC/config inputs')
    return dict(schema='opentallas.endpoint_clock.inputs.v1', view_id=view_id, source_sha=source_sha,
                qualification='NOT_EVALUATED', inputs={k:dict(path=str(Path(p).resolve()),
                sha256=sha256(p),bytes=Path(p).stat().st_size) for k,p in sorted(files.items())})


def read_export(path, corner, manifest, manifest_sha):
    records=[json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    headers=[r for r in records if r['kind']=='header']
    summaries=[r for r in records if r['kind']=='summary']
    if len(headers)!=1 or len(summaries)!=1:
        raise ValueError('export must contain one header and one complete summary')
    header=headers[0]
    if header.get('schema')!='opentallas.endpoint_clock.v1' or header.get('corner')!=corner:
        raise ValueError('wrong schema/native corner')
    if header.get('view_id')!=manifest['view_id'] or header.get('input_manifest_sha256')!=manifest_sha:
        raise ValueError('export does not match immutable view manifest')
    if header.get('constraints_unchanged') is not True:
        raise ValueError('measurement scene mutated constraints')
    out=dict(header=header,summary=summaries[0],registers={},ports={},clocks={})
    for row in records:
        kind=row['kind']
        if kind in ('header','summary'):
            continue
        if kind=='register': table,key='registers',row['clock_pin']
        elif kind=='port': table,key='ports',row['name']
        elif kind=='clock': table,key='clocks',row['name']
        else: raise ValueError(f'unknown export record {kind}')
        if key in out[table]:raise ValueError(f'duplicate {kind} identity {key}')
        out[table][key]=row
    if summaries[0]['ports']!=len(out['ports']):raise ValueError('incomplete port export')
    if summaries[0]['registers']!=len({r['instance'] for r in out['registers'].values()}):
        raise ValueError('incomplete register export')
    return out


def pack(manifest_path, tt, ff):
    manifest_path=Path(manifest_path);manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='opentallas.endpoint_clock.inputs.v1':raise ValueError('wrong input manifest schema')
    if set(manifest.get('inputs',{}))!={'netlist','spef','odb','sdc','config'}:
        raise ValueError('incomplete actual-view input manifest')
    for name,item in manifest['inputs'].items():
        if sha256(item['path'])!=item['sha256']:raise ValueError(f'changed immutable input {name}')
    digest=sha256(manifest_path)
    data={c:read_export(p,c,manifest,digest) for c,p in [('TT',tt),('FF',ff)]}
    issues=[];registers={};ports={}
    for key in sorted(data['TT']['registers'].keys()|data['FF']['registers'].keys()):
        rows={c:data[c]['registers'].get(key) for c in ('TT','FF')}
        flags=set()
        for c,row in rows.items():
            if row is None:flags.add('MISSING_'+c+'_RECORD')
            else:
                flags.update(row.get('flags',[]))
                if any(not isinstance(row.get(k),(int,float)) or not math.isfinite(row[k]) for k in ('early_ps','late_ps')):
                    flags.add('CLOCK_ARRIVAL_UNAVAILABLE')
        if flags:issues.append(dict(kind='register',identity=key,flags=sorted(flags)))
        registers[key]=dict(corners=rows,flags=sorted(flags))
    fields=('ff_members','terminals','async_terminals','clock_terminals','bypass_ports','unmapped_endpoints')
    for key in sorted(data['TT']['ports'].keys()|data['FF']['ports'].keys()):
        rows={c:data[c]['ports'].get(key) for c in ('TT','FF')};flags=set()
        for c,row in rows.items():
            if row is None:flags.add('MISSING_'+c+'_RECORD')
            else:flags.update(row.get('flags',[]))
        unions={field:sorted({v for row in rows.values() if row for v in row.get(field,[])}) for field in fields}
        if all(rows.values()) and any(rows['TT'].get(f,[])!=rows['FF'].get(f,[]) for f in fields):
            flags.add('CORNER_MEMBERSHIP_DIFFERS')
        if flags:issues.append(dict(kind='port',identity=key,flags=sorted(flags)))
        ports[key]=dict(corners=rows,union=unions,flags=sorted(flags))
    return dict(schema='opentallas.endpoint_clock.paired.v1', view_id=manifest['view_id'],
                input_manifest_sha256=digest, inputs=manifest['inputs'], source_sha=manifest.get('source_sha',''),
                qualification='NOT_EVALUATED', requires_fresh_policy_signoff=True,
                requires_actual_parent_sta=True, clocks={c:data[c]['clocks'] for c in data},
                registers=registers,ports=ports,issues=issues,
                complete_corner_coverage=not any(f.startswith('MISSING_') for x in issues for f in x['flags']))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    m=sub.add_parser('manifest');m.add_argument('--view-id',required=True);m.add_argument('--source-sha',default='')
    for field in ('netlist','spef','odb','sdc','config'):m.add_argument('--'+field,required=True)
    m.add_argument('--out',required=True)
    p=sub.add_parser('pack');p.add_argument('--manifest',required=True);p.add_argument('--tt',required=True);p.add_argument('--ff',required=True);p.add_argument('--out',required=True)
    a=ap.parse_args()
    if Path(a.out).exists():raise ValueError('output exists; preserve it and choose a new snapshot path')
    if a.command=='manifest':
        result=make_manifest(a.view_id,{k:getattr(a,k) for k in ('netlist','spef','odb','sdc','config')},a.source_sha)
    else:result=pack(a.manifest,a.tt,a.ff)
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(output=a.out,sha256=sha256(a.out),qualification='NOT_EVALUATED')))


if __name__=='__main__':main()
