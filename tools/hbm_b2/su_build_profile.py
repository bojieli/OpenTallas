#!/usr/bin/env python3
"""Explicit candidate SU build parameters for the actual eight-slice source.

No profile is selected by default. A fresh bind and compiler run must consume
this candidate and the same named profile before any physical-view adoption.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_static import su_lane_build as B

PROFILES={'m5a3w1':dict(mlat=5,alat=3,wcopy=1),'m5a4w1':dict(mlat=5,alat=4,wcopy=1)}
SLICE=re.compile(r'^(  ot_hbm_su_static_pgslice_lg(?:_s)? #\()([^\n]*)(\) (su_(NW|NE)([0-3])) \()',re.M)


def apply_profile(source, name):
    if name not in PROFILES:raise ValueError('explicit supported SU profile required')
    target=PROFILES[name]; rows=[]
    source_slices=re.findall(r'^  ot_hbm_su_static_pgslice_lg(?:_s)? #[^\n]* (su_(?:NW|NE|SW|SE)[0-3]) \(',source,re.M)
    if len(source_slices)!=8:raise ValueError('candidate requires exactly eight source slices; extra S-role copies are forbidden')
    def patch(m):
        parameters=m[2]; old={k:int(v) for k,v in re.findall(r'\.(\w+)\((\d+)\)',parameters)}
        required={'MLAT','ALAT','LEAF','QID','G'}
        if required-set(old):raise ValueError(m[4]+': missing literal source params '+str(sorted(required-set(old))))
        if old['QID']!={'NW':2,'NE':3}[m[5]] or old['G']!=int(m[6]):raise ValueError(m[4]+': source role/group differs')
        B.check(old['MLAT'],old['ALAT'],old['LEAF'],old.get('WCOPY',0))
        for field,value in [('MLAT',target['mlat']),('ALAT',target['alat']),('WCOPY',target['wcopy'])]:
            term=re.compile(r'\.'+field+r'\([^()]*\)')
            if term.search(parameters):
                if len(term.findall(parameters))!=1:raise ValueError('duplicate '+field)
                parameters=term.sub('.'+field+'('+str(value)+')',parameters)
            else:parameters+=', .'+field+'('+str(value)+')'
        old_ii={str(fn):B.side_ii(fn,old['MLAT'],old['ALAT']) for fn in B.SIDE_FN}
        new_ii={str(fn):B.side_ii(fn,target['mlat'],target['alat']) for fn in B.SIDE_FN}
        rows.append(dict(instance=m[4],old=old,target=dict(target,leaf=old['LEAF']),
                         linear_cycle_delta=B.lin(target['mlat'],target['alat'],old['LEAF'])-B.lin(old['MLAT'],old['ALAT'],old['LEAF']),
                         bank_commit_cycle_delta=target['wcopy']-old.get('WCOPY',0),
                         source_side_ii=old_ii,target_side_ii=new_ii))
        return m[1]+parameters+m[3]
    result=SLICE.sub(patch,source)
    expected={f'su_{role}{i}' for role in ('NW','NE') for i in range(4)}
    if len(rows)!=8 or {r['instance'] for r in rows}!=expected:raise ValueError('candidate requires exactly the eight current NW/NE slices')
    receipt=dict(schema='opentallas.hbm.su_build_profile.v1',profile=name,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                 candidate_sha256=hashlib.sha256(result.encode()).hexdigest(),slices=rows,side_hardware=B.SIDE,
                 compiler_flags=['--mlat',str(target['mlat']),'--alat',str(target['alat']),'--wcopy',str(target['wcopy'])],
                 scope='CANDIDATE_PARAMETERS_ONLY: fresh selected-source bind, per-slice compiler and physical fit/timing required')
    return result,receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('top',type=Path);p.add_argument('--profile',choices=PROFILES,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    result,receipt=apply_profile(a.top.read_text(),a.profile)
    if a.out.exists() or a.receipt.exists():p.error('use fresh candidate output paths')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(result);a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print(a.profile,len(receipt['slices']),'slices; fresh bind/compiler required')
if __name__=='__main__':main()
