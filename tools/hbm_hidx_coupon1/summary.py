from pathlib import Path
import json,collections
p=json.loads(Path('out/native.json').read_text());j=json.loads(Path('out/netlist.json').read_text())['modules']['hidx_coupon1'];s=p['summary']
s['max_by_role']={k:max((r['loads'] for r in p['all_roots'] if r['kind']==k),default=0) for k in ['ff','comb','input']}
s['max_cap_by_role']={k:max((r['cap'] for r in p['all_roots'] if r['kind']==k),default=0) for k in ['ff','comb','input']}
s['longest_comb']=p['paths'][0]
s['output_sources']=dict(collections.Counter(r['kind'] for r in p['all_roots'] for e in r['endpoints'] if e['kind']=='output'))
s['all_input_endpoints_native_ff']=all(e['kind']=='ff' for r in p['all_roots'] if r['kind']=='input' for e in r['endpoints'])
s['depth_by_endpoint_kind']={k:max((r['depth'] for r in p['paths'] if any(e['kind']==k for e in r['endpoints'])),default=0) for k in ['ff','output']}
s['boundary_note']='compacted is the internal gc combinational boundary; source S1 capture FF is outside coupon. Count outputs are the actual S1 selector FF. No hardened top or registered-output claim.'
Path('out/summary.json').write_text(json.dumps(s,indent=2)+'\n')
