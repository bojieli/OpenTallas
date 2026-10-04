"""Compile preGO row debt from canonical plans and exact retained root map.

Called on each actual emitted matrix/phase association by the source emitter;
this is immutable configuration, not a host grant or acceptance decision.
"""
from bisect import bisect_right

def compile_profile(matrix,connectivity,positions):
    if not 0<matrix['rows']<65536:raise ValueError('actual 16-bit phase row aperture; emitter must select phase, not flatten larger operator')
    if not 1<=positions<=8:raise ValueError('source position count')
    if not connectivity['inventory_bound'] or connectivity['pairs']!=2417 or len(connectivity['BF_site_IDs'])!=519:
        raise ValueError('selected canonical S81 binding required')
    if not connectivity['no_READY'] or connectivity['RD']!=64:raise ValueError('source return contract')
    bounds=connectivity['region_bounds'];owners={};subtrees={}
    for segment,pair,first,n,stride,start,words in matrix['plans']:
        root=bisect_right(bounds,pair)-1
        if not 0<=root<128 or not bounds[root]<=pair<bounds[root+1]:raise ValueError('physical pair owner')
        if matrix['format']=='bf16' and pair not in connectivity['BF_site_IDs']:raise ValueError('BF physical site')
        for j in range(n):
            sr=first+j*stride
            for row in (2*sr,2*sr+1):
                if row>=matrix['rows']:continue
                if row in owners and owners[row]!=root:raise ValueError('cross-root K tree')
                if (row,segment) in subtrees:raise ValueError('duplicate ordered subtree')
                owners[row]=root;subtrees[row,segment]=pair
    if set(owners)!=set(range(matrix['rows'])):raise ValueError('omitted output row')
    if len(subtrees)!=matrix['rows']*len(matrix['segments']):raise ValueError('missing K subtree')
    rows=[[r for r in sorted(owners) if owners[r]==root] for root in range(128)]
    return dict(stage=matrix['stage'],layer=matrix['layer'],alias=matrix['alias'],
      positions=positions,rows=rows,root_return_counts=[len(x)*positions for x in rows],
      total_returns=matrix['rows']*positions,
      row_owner_lookup=[owners[r] for r in range(matrix['rows'])],
      source='canonical plans + retained root region_bounds; preserve subtree order',
      VM_acceptance_supplied=False,hardware_admission_granted=False)
