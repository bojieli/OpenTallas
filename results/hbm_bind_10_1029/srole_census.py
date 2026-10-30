"""HBM-BIND-10: is the S-role vmdel producer (plan u_vmdel_Q0..7__q0) determined by the as-built source or the plan?
Read-only census. usage: srole_census.py <top_native.sv> <die_plan.json> <map.json> <fold_producer_closure.json> <out.json>"""
import json, re, sys, hashlib, collections
top, plan, mapf, closf, out = sys.argv[1:6]
src = open(top).read()
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
inst = dict((m.group(2), m.group(1)) for m in re.finditer(r'^\s+(\w+)\s+(?:#\([^;]*?\)\s+)?(\w+)\s*\(\s*$', src, re.M))
r = {'inputs': {'top_native': [top, sha(top)], 'plan': [plan, sha(plan)], 'map': [mapf, sha(mapf)], 'closure': [closf, sha(closf)]}}
# 1. S-role producers / their upstreams present in the source?
want = [f'vmdel_{s}{i}' for s in ('SE', 'SW') for i in range(8)] + ['vmfc_SE', 'vmfc_SW'] + [f'vmks_SW{i}' for i in range(8)] + \
       ['calendar_SE', 'calendar_SW', 'vmfc_NE', 'vmfc_NW'] + [f'vmks_NW{i}' for i in range(8)]
r['source_instances'] = {w: inst.get(w) for w in want}
r['vmb_S_dq_is_top_input'] = all(re.search(rf'input wire \[280:0\] vmdel_{s}{i}__dq;', src) for s in ('SE', 'SW') for i in range(8))
# 2. vmks fill lanes: who consumes each lane
lanes = collections.defaultdict(list)
for m in re.finditer(r'ot_hbm_svc_vmdel_lane_n\s+#\(\.NPC\(\d+\)\)\s+(\w+)\s*\((.*?)\);', src, re.S):
    fv = re.search(r'\.fill_v_i\(\{([^}]*)\}\)', m.group(2)).group(1)
    for ks, b in re.findall(r'(vmks_\w+?)__fill_v\[(\d+):\d+\]', fv):
        lanes[f'{ks}[{b}]'].append(m.group(1))
r['vmks_fill_lanes_total'] = 4 * sum(1 for k in inst if re.fullmatch(r'vmks_NW\d', k))
r['vmks_fill_lanes_consumed'] = len(lanes)
r['vmks_fill_lane_consumers'] = dict(sorted(lanes.items()))
r['vmks_fill_lanes_multiply_consumed'] = [k for k, v in lanes.items() if len(v) > 1]
# 3. vmfc role calendar payload port vs non-role calendar_S*
r['calendar_SE_has_payload_port'] = bool(re.search(r'calendar_SE\s*\((?:(?!\);).)*\.payload\(', src, re.S))
# 4. plan: what does the plan wire to the S-role copies and S banks?
P = json.load(open(plan)); ps = json.dumps(P)
r['plan_srole_refs'] = dict(collections.Counter(re.findall(r'u_vmdel_Q[0-7]__q0(?:\.\w+)?', ps)))
r['plan_srole_station_conns'] = sum(1 for t in P['partition_types'].values() for s in t.get('internal_stations', [])
                                    if '__q0' in json.dumps(s) and 'u_vmdel_Q' in json.dumps(s))
r['plan_S_bank_dq_stations'] = sum(1 for t in P['partition_types'].values() for s in t.get('internal_stations', [])
                                   if re.search(r'u_vmb_Q\d_mu1\.dq\b', json.dumps(s)))
r['plan_vmfc_cells'] = sorted(set(re.findall(r'"u_vmfc_\w+"', ps)))
r['plan_vmdel_q0_notes'] = sorted({c.get('note', '')[:80] for t in P['partition_types'].values() for c in t.get('contents', []) if re.fullmatch(r'u_vmdel_Q\d__q0', c.get('inst', ''))})
M = json.load(open(mapf)); ms = json.dumps(M)
r['map_S_banks'] = dict(re.findall(r'"(vmb_S[EW]\d)": \[("[A-Z]+_hub", "[\w]+")\]', ms))
C = json.load(open(closf))
r['closure_undefined_after_all28'] = len(C['undefined_after_all28'])
r['closure_vmdel_S_open_upstream'] = sorted({n for row in C['rows'] if row['instance'].startswith('vmdel_S') for n in row['undefined_after_all28']})
json.dump(r, open(out, 'w'), indent=1); print(json.dumps({k: v for k, v in r.items() if k not in ('vmks_fill_lane_consumers', 'map_S_banks')}, indent=1))
