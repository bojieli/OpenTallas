#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: die START stages after the host split (stage tree, clocks and geometry unchanged).
5 stages re-sourced from host_e raw exports (raw_exports.json); pst_host -> pst_host_w; new pst_host_e = the same
origin stage b1745 output (same cycle as host_w: both halves are CA origins on one START parent)."""
import json, sys, gzip, re, copy
st = json.load(gzip.open(sys.argv[1])); sv = gzip.open(sys.argv[2], 'rt').read(); rx = json.load(open(sys.argv[3])); out = sys.argv[4]
new = copy.deepcopy(st); byid = {r['stage']: r for r in rx['stages']}
for s in new['stages']:
    if s['id'] not in byid: continue
    r = byid[s['id']]; c = dict(r['new']); old = s['reset_port']
    port = f"wrst_{c['part']}__{c['port']}"
    pat = r'(u_st_' + re.escape(s['id']) + r' \(\.clk\(' + re.escape(s['clock_port']) + r'\), \.rst_raw_n\()' + re.escape(old) + r'(\))'
    sv, n = re.subn(pat, lambda m: m[1] + port + m[2], sv); assert n == 1, s['id']
    s['reset_port'] = port; s['reset_source'] = c; s['reset_hop_um'] = r['hop']
rp = {k: v for k, v in new['reset_ports'].items() if not k.startswith('wrst_host__')}
for r in rx['stages']:
    c = r['new']; rp[f"wrst_{c['part']}__{c['port']}"] = dict(c)
new['reset_ports'] = rp
old_in = [l for l in sv.splitlines() if re.match(r'\s*input\s+wire wrst_host__rst_start_raw_\d+,', l)]
assert len(old_in) == 4, old_in
ins = ''.join(f'    input  wire wrst_host_e__rst_start_raw_{k},\n' for k in range(len({(r['new']['part'], r['new']['port']) for r in rx['stages']})))
sv = sv.replace('\n'.join(old_in) + '\n', ins, 1)
assert sv.count('    output wire pst_host,\n') == 1 and sv.count('    assign pst_host = st_b1745_start;\n') == 1
sv = sv.replace('    output wire pst_host,\n', '    output wire pst_host_e,\n    output wire pst_host_w,\n')
sv = sv.replace('    assign pst_host = st_b1745_start;\n', '    assign pst_host_e = st_b1745_start;\n    assign pst_host_w = st_b1745_start;\n')
assert 'wrst_host__' not in sv and not re.search(r'\bpst_host\b', sv)
outs = []
for d in new['die_outputs']:
    if d.get('dst_part') == 'host':
        for pn in ('host_w', 'host_e'):
            outs.append(dict(d, port=d['port'][:-len('host')] + pn, dst_part=pn, net='pst_' + pn))
    else: outs.append(d)
new['die_outputs'] = outs
r0 = next(s for s in new['stages'] if s['root'])['reset_source']['raw_release']
span = max(s['reset_source']['raw_release'] - r0 for s in new['stages'])
assert span + new['root_settle_guard']['guard_cycles'] <= new['root_settle'], span
new['reset_refresh'] = dict(by='DIE-HEAD-84 HSPLIT 11-07', scope='host split: 5 stages re-sourced from hd_host_e raw exports, pst_host -> pst_host_w + pst_host_e (b1745); stage tree, clock ports, geometry unchanged',
                            prev=st.get('reset_refresh'))
json.dump(new, open(out + '/start_stages.json', 'w'), indent=1); open(out + '/start_stages.sv', 'w').write(sv)
print(json.dumps(dict(stages=len(byid), span=span, settle=new['root_settle'], max_hop=max(s['reset_hop_um'] for s in new['stages']), ports=len(rp))))
