"""Source-relative fragment overlap estimate; never adopts new k straps."""
import collections
import itertools
import json
import sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
rb={x['vn_b']:x for x in r['rstd_broadcast']if x['port']=='rb_v'}
rows=collections.defaultdict(list)
for x in r['xf_forward']:
    n=x['vq'].rsplit('.',1)[0]+'.u_vn.u_b';b=rb[n]
    if x['status']!=b['status']or x['status']!='PASS_RAW_WORD':raise ValueError('current transport not qualified')
    rows[x['sid']].append(dict(leaf_input=x['leaf_input'],k=x['k_strap'],wire_base=x['age_edges']+b['age_edges'],vq=x['vq']))
def collisions(perm=None):
    bad={}
    for sid,ls in rows.items():
        occ=collections.defaultdict(list)
        for l in ls:
            k=l['k']if perm is None else perm[l['leaf_input']]
            for e in range(l['wire_base']+4*k,l['wire_base']+4*k+4):occ[e].append(l['leaf_input'])
        fail={str(k):v for k,v in occ.items()if len(v)>1}
        if fail:bad[str(sid)]=fail
    return bad
base=collisions();candidates=[list(p)for p in itertools.permutations(range(5))if not collisions(p)]
rec={'scope':'SOURCE_RELATIVE_ANALYTIC_FRAGMENT_SLOT_ESTIMATE_NOT_ADOPTED',
 'source_asbuilt_sha256':r['source_asbuilt_sha256'],'die_sha256':r['die_sha256'],
 'premise':'one common XR release per slice, uniform local VN/VQ latency; each leaf emits4 consecutive fragments; wire ages and k are current exact bindings',
 'current_collision_slices':len(base),'current_collisions':base,
 'common_k_permutations_without_internal_overlap':candidates,'source_rows':dict(rows),
 'uniform_sid_release_hold_cannot_change_internal_overlap':True,'adoption':False,'full_token':False}
Path(sys.argv[2]).write_text(json.dumps(rec,indent=2)+'\n')
print('CURRENT_COLLISION_SLICES',len(base),'COMMON_LEGAL_K',candidates)
