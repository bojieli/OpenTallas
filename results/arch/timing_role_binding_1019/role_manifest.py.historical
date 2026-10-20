#!/usr/bin/env python3
"""Unconnected, fail-closed timing-role manifest prototype. No production imports."""
import hashlib,json,pathlib,re
MASTER='ot_sram_1r1w_512x128_m4_r2c2_p192_sc2'
ROLES={'tt_max','ss_max','ff_min','ff_max'}
IDENTITY={'master','source_sha256','model_sha256','geometry_sha256','behavior_sha256'}
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def refuse(message):raise ValueError('ROLE_BINDING_REFUSED '+message)
def read(path,approved_manifest_sha256,expected_identity,required_roles):
    path=pathlib.Path(path)
    if digest(path)!=approved_manifest_sha256:refuse('unreviewed manifest digest')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:refuse('duplicate key '+k)
            d[k]=v
        return d
    m=json.loads(path.read_text(),object_pairs_hook=unique)
    if set(expected_identity)!=IDENTITY or expected_identity['master']!=MASTER:refuse('unsupported identity')
    if m.get('identity')!=expected_identity:refuse('master/source/model/geometry/behavior identity')
    for k in IDENTITY-{'master'}:
        if not re.fullmatch('[0-9a-f]{64}',expected_identity[k]):refuse('invalid '+k)
    if m.get('schema')!='opentallas.sc2-timing-roles.prototype.v1':refuse('schema')
    rows=m.get('roles',{})
    if set(rows)!=ROLES:refuse('missing or foreign explicit role')
    if not set(required_roles)<=ROLES:refuse('unreviewed role requested; TT/SS minimum has no bound')
    result={}
    for role,row in rows.items():
        if row.get('corner')!=role[:2] or row.get('analysis')!=role[3:]:refuse('swapped role metadata '+role)
        if row.get('domain')!={'slew_ps':[5,320],'load_ff':[0.72,46.08]}:refuse('domain '+role)
        if row.get('constraint_policy')!='upper_requirements':refuse('constraint policy '+role)
        if role=='ff_min' and row.get('added_access_minimum_delay_ps')!=0:refuse('manufactured minimum access delay')
        rel=pathlib.Path(row.get('file',''))
        if rel.is_absolute() or '..' in rel.parts or not rel.name:refuse('nonlocal role path')
        f=path.parent/rel
        if not f.is_file() or digest(f)!=row.get('sha256'):refuse('missing/wrong role bytes '+role)
        text=f.read_text()
        if not re.search(r'\bcell\s*\(\s*'+re.escape(MASTER)+r'\s*\)',text):refuse('wrong actual cell '+role)
        library=re.search(r'\blibrary\s*\(\s*([^\s)]+)\s*\)',text)
        if not library or library[1]!=row.get('library'):refuse('wrong actual library '+role)
        result[role]={'file':str(f.resolve()),'sha256':row['sha256'],'library':library[1]}
    # Distinct roles must not alias one file; exact approved hashes certify their
    # reviewed numerical meanings. A self-authored sidecar cannot certify a bound.
    if len({r['file'] for r in result.values()})!=4:refuse('role file alias')
    return {'identity':expected_identity,'approved_manifest_sha256':approved_manifest_sha256,'roles':result}
