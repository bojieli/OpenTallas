"""Existing saved-route library-corner tables; no STA/CAD or current die claim."""
from pathlib import Path
import json, statistics, math
R=Path(__file__).parent


def read(p):
    out={}
    for line in p.read_text().splitlines():
        f=line.split()
        if not f or f[0].startswith('#'):continue
        assert len(f)==5 and f[0] in ('T','F')
        k=tuple(f[:2]);assert k not in out
        out[k]=tuple(map(float,f[2:]));assert all(math.isfinite(x) for x in out[k])
    return out


out={}
for view in ('nw_v1','nw_v2'):
    d=R.parent/f'hbm_{view}_drt_readout_1102'
    stem='edges_drt_' if view=='nw_v1' else 'edges_'
    tt,ff=read(d/(stem+'TT.txt')),read(d/(stem+'FF.txt'));assert tt.keys()==ff.keys()
    groups={}
    for edge in ('T','F'):
        keys=[k for k in tt if k[0]==edge and k[1].startswith('L_')]
        assert len(keys)==266
        fields={}
        for j,name in ((0,'arrival_max'),(1,'arrival_min')):
            ratios=[ff[k][j]/tt[k][j] for k in keys if tt[k][j]>0]
            delta={k:ff[k][j]-.8666*tt[k][j] for k in keys}
            lo=min(delta,key=delta.get);hi=max(delta,key=delta.get)
            nonzero={k:v for k,v in delta.items() if tt[k][j]>0}
            fields[name]=dict(actual_FF_over_TT=dict(min=min(ratios),median=statistics.median(ratios),max=max(ratios)),
                actual_FF_minus_TT_times_0p8666_ps=dict(min=delta[lo],max=delta[hi]),
                largest_possible_same_edge_pair_skew_error_ps=delta[hi]-delta[lo],
                nonzero_arrival_load_pair_skew_error_range_ps=max(nonzero.values())-min(nonzero.values()),
                zero_TT_arrival_loads=[k[1] for k in keys if tt[k][j]==0],
                extremal_leaf_pair=[lo[1],hi[1]])
        groups[edge]=fields
    out[view]=dict(native_DRC=2 if view=='nw_v1' else 0,paired_actual_A_pin_edges=len(tt),actual_leaves=266,groups=groups)
result=dict(status='LEGACY_ACTUAL_CORNER_MEASUREMENT_NOT_CURRENT_DIE_PROOF',
    source='Previously recovered same saved DEF/SPEF; actual TT/FF libraries, no new route or STA',
    transition_labels='T=rise and F=fall; files TT/FF are library corners',
    old_assumption=.8666,views=out,
    implication='Use measured tree_drt_FF.txt when available; a uniform FF/TT scale does not reproduce these saved-route FF arrivals or leaf skew. Current mesh_form.rec already reads the FF file when present.',
    scope='All-leaf differential error is diagnostic, not an actual related-pair/CPPR timing failure. Native current-source/START66/parent/PG/dieG4 remain held; NWv1 DRC2 remains FAIL. No Monte Carlo or obsolete post7 replay.')
(R/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
