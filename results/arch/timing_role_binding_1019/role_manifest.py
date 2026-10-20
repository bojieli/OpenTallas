#!/usr/bin/env python3
"""Unconnected, fail-closed timing-role manifest prototype. No production imports."""
import hashlib,json,pathlib,re
MASTER='ot_sram_1r1w_512x128_m4_r2c2_p192_sc2'
ROLES={'tt_max','tt_min','ss_max','ss_min','ff_min','ff_max'}
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
    if not set(required_roles)<=ROLES:refuse('foreign role requested')
    # ROOT correction: nominal CQ is not a minimum at ANY corner. The
    # conditional zero model has unresolved transition/reference dependencies.
    # No reviewed complete MIN policy exists, so this prototype admits none.
    refuse('TT/SS/FF MIN unqualified; nominal CQ forbidden; reviewed complete bound policy absent')
