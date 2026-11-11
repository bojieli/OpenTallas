"""DIE-LAYOUT-HBM F1 (11-11): NW_io u_host_ep back beside u_ep_N0. The bound NW_io netlist has a direct 1230-b
u_ep_N0.h_* <-> u_host_ep.vc_* link (no pipeline regs; h_* on the ep_N0 N face, vc_* on the host_ep S face, x-aligned).
Form h (12:00 cut) moved host_ep to y 4069.44 (2998 um away). host_ep goes to y 1468.80 (29333b2b 1503.36 - 34.56: pin gap
133.9 um, centre distance 397.4 <= 405), its clock entry moves with it, and its two chains (L8008_i 6 regs, L8007_o 7 regs,
counts unchanged) are re-spread evenly N face -> host_ep in the 29333b2b columns x 380.16 / 557.184. All other form-h
changes are kept. Positions only."""
import json, sys
cur, out = sys.argv[1], sys.argv[2]
P = json.load(open(cur)); t = P['partition_types']['NW_io']
Y = 1468.80; H = 246.24
for k in ('hard_cores', 'contents'):
    for h in t[k]:
        if h.get('inst') == 'u_host_ep': h['origin_um'] = [129.6, Y]
for x in t['clock']['taps']:
    if x['name'] == 'u_host_ep.clk': x['xy'] = [349.92, round(Y + 25.92, 3)]
st = t['internal_stations']
tag = ' | DIE-LAYOUT-HBM 11-11 F1: host_ep back beside ep_N0 (bound 1230-b h_*<->vc_* direct link was 2998 um after form h); regs re-spread, count kept'
s = st[57]; assert s['conn'] == 'bus:L8008_i' and len(s['regs_um']) == 6
s['from_um'] = [379.123, 4320.0]; s['to_um'] = [379.123, round(Y + H, 3)]
L = 4320.0 - (Y + H)
s['regs_um'] = [[380.16, round(4320.0 - L * (i + 1) / 7, 3)] for i in range(6)]
s['note'] += tag
s = st[58]; assert s['conn'] == 'bus:L8007_o' and len(s['regs_um']) == 7
# out bus launched by cores (ep_N0.fault_cause / host_ep.fault): regs written from the leaf (station_lint, as form h)
s['from_um'] = [557.184, round(Y + 92.568, 3)]; s['to_um'] = [323.998, 4320.0]
dx = 557.184 - 323.998; L = dx + 4320.0 - s['from_um'][1]; step = L / 8
s['regs_um'] = [[557.184, round(4320.0 - (step * (i + 1) - dx), 3)] for i in range(7)][::-1]
s['note'] += tag
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
print(st[57]['regs_um'], st[58]['regs_um'], round(step, 1))
