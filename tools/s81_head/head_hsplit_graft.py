#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT graft: l48uo plan of record + the composed host_w/host_e (new files only).
Everything not owned by the host comes from l48uo byte-for-byte; the host records come from the compose of the
split plan (comp_split), which leaves all 24 other types identical. Post-compose HEAD fields of the two new types
are added by later steps (raw START exports, count strap sites, landing stage keys)."""
import json, sys, copy
base_p, base_s, comp_p, comp_s, out_dir = sys.argv[1:6]
B = json.load(open(base_p)); BS = json.load(open(base_s)); C = json.load(open(comp_p)); CS = json.load(open(comp_s))
G = copy.deepcopy(B)
NEW = ('hd_host_w', 'hd_host_e')
del G['partition_types']['hd_host']
for tn in NEW:
    t = copy.deepcopy(C['partition_types'][tn])
    t['clock']['landing_contract']['forwarded_clock_only_inputs'] = True      # as every l48uo HEAD landed type
    G['partition_types'][tn] = t
for k in ('partitions', 'ports', 'lanes', 'latency', 'reset'):
    G[k] = copy.deepcopy(C[k])
G['clock']['tap_window'] = copy.deepcopy(C['clock']['tap_window'])
ln = G['clock']['landing_network']; cln = C['clock']['landing_network']
ce = {e['id']: e for e in cln['edges']}
assert set(e['id'] for e in ln['edges']) <= set(ce), 'edge set changed'
ln['edges'] = [copy.deepcopy(ce[e['id']]) for e in ln['edges']] + [copy.deepcopy(e) for e in cln['edges'] if e['id'] not in {x['id'] for x in ln['edges']}]
uses = [u for u in ln['start_tree']['uses'] if not (u['part'] == 'host' and u['pin'] == 'cland_tstart_in')]
uses += [copy.deepcopy(u) for u in cln['start_tree']['uses'] if u['part'] in ('host_w', 'host_e')]
ln['start_tree']['uses'] = uses       # host rst_start_raw_* uses are re-derived by the raw-export step
# sidecar: l48uo + CA roles (ca_split) + composed collector records of the host parts
S = copy.deepcopy(BS)
S['ports'] = copy.deepcopy(CS['ports']); S['regions'] = copy.deepcopy(CS['regions'])
S['count_aligned'] = copy.deepcopy(CS['count_aligned'])
S['count_aligned']['start_pins']['reset_inputs'] = copy.deepcopy(BS['count_aligned']['start_pins']['reset_inputs'])
col, ccol = S['collector'], CS['collector']
for k in ('parts', 'base_type_by_part'):
    col[k].pop('host', None)
    for pn in ('host_w', 'host_e', 'lk_HOST1'):
        if pn in ccol[k]: col[k][pn] = copy.deepcopy(ccol[k][pn])
for k in ('types', 'tree_bus'):
    col[k].pop('hd_host', None)
    for tn in NEW: col[k][tn] = copy.deepcopy(ccol[k][tn])
be = {(e['src'], e['dst'], e.get('port')): e for e in col['edges']}
ne = []
for e in ccol['edges']:
    key = (e['src'], e['dst'], e.get('port'))
    if 'host_w' in key or 'host_e' in key:
        ne.append(copy.deepcopy(e))
    else:
        ne.append(be.get(key, e))
col['edges'] = ne
import os
os.makedirs(out_dir, exist_ok=True)
json.dump(G, open(out_dir + '/source_plan.json', 'w'), indent=1); json.dump(S, open(out_dir + '/source_sidecar.json', 'w'), indent=1)
print('GRAFT', len(G['partition_types']), len(G['partitions']), len(G['ports']), len(ln['edges']), len(uses), len(col['edges']))
