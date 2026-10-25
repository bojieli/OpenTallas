import json,re,collections,sys
B='/tmp/tr/tree/physical/die_plan/hbm_arch/B2n/'
d=json.load(open(B+'die_plan.json'));T=d['partition_types']
ninst=collections.Counter(p['type'] for p in d['partitions'])
def master(m):
    if '__' not in m: return m
    a,l=m.split('__',1)
    if a=='ot_hbm_idx_score_quarter_static':
        if l.startswith('tail'): return 'ot_hbm_idx_tail_native'
        return 'ot_hidx_score_hcol#HALF'+l[-1]
    if a=='ot_hgi_coll_tkm_m_tp192': return 'ot_hgi_coll_tkm_tile_e86' if l.startswith('tile') else a+'__root'
    if a=='ot_hgi_sfu_core_split3': return 'sfu_lane(ot_su12_sfu+lane_map)' if re.match(r'lane\d',l) else m
    if a=='ot_hbm_su_static_pgslice_lg':
        if re.match(r'lane_exp\d',l): return 'su_lane_exp+bank'
        if re.match(r'lanes(_plain)?\d',l): return 'su_4xlane_plain+banks'
        return m
    if a.startswith('ot_hbm_hc_bankq'):
        if l in('lanes0_2','lanes3_5'): return '3x_hcp_lanes'
        return m
    if a=='ot_hbm_hc_root_static':
        return 'hc_root__'+re.sub(r'tail\d_','',l)
    return m
rows=[]
for k,t in T.items():
    for h in t.get('hard_cores',[]):
        p=json.load(open(B+h['pins_file']))
        if isinstance(p,dict):p=p['pins']
        rows.append(dict(pt=k,ni=ninst[k],mod=h['module'],ms=master(h['module']),w=h['outline_um'][0],h=h['outline_um'][1],pins=p,inst=h['inst']))
json.dump([{k:v for k,v in r.items()} for r in rows],open('/tmp/trx/rows.json','w'))
