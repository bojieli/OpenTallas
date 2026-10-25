import json,collections,re
exec(open('/tmp/trx/c2.py').read().split('G=collections')[0])
G=collections.defaultdict(list)
for r in R: G[r['ms']].append(r)
for ms in ['ot_hgi_coll_tkm_tile_e86','su_lane_exp+bank','su_4xlane_plain+banks','3x_hcp_lanes','sfu_lane(ot_su12_sfu+lane_map)','hc_root__rest']:
    L=G[ms]; by=collections.defaultdict(list)
    for r in L: by[tuple(sorted(set(nn(p['name']) for p in r['pins'])))].append(r['mod'].split('__')[-1]+'@'+r['pt'])
    keys=list(by); base=set(keys[0])
    print('==',ms)
    for k in keys:
        s=set(k); print('  n=%d pins=%d'%(len(by[k]),len(k)), sorted(by[k])[:5], 'extra',sorted(s-base)[:3],'missing',sorted(base-s)[:3])
