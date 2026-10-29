import json, sys
sys.path.insert(0, '/srv/opentallas-scratch2/claude/wt/hbm-bind-6-1029/tools/hbm_b2')
import fused_lower_tree as F
R = '/srv/opentallas-scratch2/claude/hbm-bind-6-1029'; P = '/srv/opentallas-scratch2/claude/hbm-bind-5-1029'
S = '/srv/opentallas-scratch2/claude/wt/codex-hbm-sourcefull-0310'
m = json.load(open(P + '/c2/map.json'))
for side in F.SIDES:
    for k, v in F.plan_map(side).items():
        assert k not in m['parts']
        m['parts'][k] = v
m['note'] = 'HBM-BIND-6 c3: c2 map + 60 lower FUSED tree cores (fused_lower_tree.plan_map) | ' + m.get('note', '')
json.dump(m, open(R + '/c3/map.json', 'w'), indent=1)
d = json.load(open(P + '/c2/asbuilt.json'))
d['map_file'] = R + '/c3/map.json'
d['compose'] = P + '/c2/compose.json'
d['straps'] = d['straps'] + [r'u_mu_fused_\d+_n[ew]\.lid']
d['strap_note'] += ' | HBM-BIND-6 10-29: FUSED lane lid = 16 side + L lane ID strap (hbm_n4_lanemap required_lid)'
d['note'] = 'HBM-BIND-6 c3: c2 + lower FUSED tree spliced (fused_lower_tree_splice.py; = current_native_top --fused-lower-tree) | ' + d['note']
json.dump(d, open(R + '/c3/asbuilt.json', 'w'), indent=1)
s = json.load(open(P + '/c2/out/asbuilt_sources.json'))
f = S + '/rtl/hbm_next/fused/ot_hnx_fused_eng.sv'
if f not in s['lib']:
    s['lib'].append(f)
json.dump(s, open(R + '/c3/out/asbuilt_sources.json', 'w'), indent=1)
print('ok', len(m['parts']))
