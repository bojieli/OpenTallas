#!/usr/bin/env python3
"""Read the immutable r3 mapped graph; emit complete owner/sink ledgers.

Run on the fleet. This consumes the explicit native-bus DIAGNOSTIC, not a
production scalar contract. It never turns its REFUSED verdict into PASS.
"""
import collections, csv, gzip, hashlib, json, pathlib, re, sys

root = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
mp = root/'census/ot_hbm_idx_topk_link_static_p/mapped.json'
x = json.load(gzip.open(root/'transparent_diagnostic.json.gz', 'rt'))
m = json.loads(mp.read_text())['modules'][x['top']]
cells = m['cells']
aliases = collections.defaultdict(set)
for name, record in m['netnames'].items():
    if not name.startswith('$'):
        for bit in record['bits']:
            aliases[bit].add(name)

# Union only actual native BUF/INV cells, retaining inversion-independent
# identity for source naming. Endpoint/load counts remain the original audit's.
parent = {}
def find(a):
    parent.setdefault(a, a)
    if parent[a] != a: parent[a] = find(parent[a])
    return parent[a]
def union(a,b):
    a,b=find(a),find(b)
    if a!=b: parent[b]=a
for z in x['drivers']:
    if not z['transparent'] or not z['driver'].startswith('cell:'): continue
    cn = z['driver'][5:].rsplit('/',1)[0]
    c=cells[cn]
    inputs=[b for p,bs in c['connections'].items() if c['port_directions'][p]=='input' for b in bs]
    if len(inputs)!=1: raise RuntimeError(('non-unary transparent cell', cn))
    union(z['net'], inputs[0])
connected = collections.defaultdict(set)
for bit, names in aliases.items(): connected[find(bit)].update(names)

native_roles = {}
for z in x['drivers']:
    if z['driver'].startswith('cell:'):
        native_roles[z['driver'][5:].rsplit('/',1)[0]]=z['role']

def family(names, driver, endpoint_roles):
    if endpoint_roles.get("reset",0) and sum(endpoint_roles.values())==endpoint_roles["reset"]: return "reset"
    text=' '.join(names)+' '+driver
    for pattern, label in [
      (r'local_selects\.rotate|trep|total_nx|tdrive', 'rotate_total'),
      (r'local_selects\.pair|s1_nac', 'pair_count'),
      (r'local_selects\.quad|s1_nqc', 'quad_count'),
      (r'local_selects\.half|half_select|qcnt', 'half_count'),
      (r'g_partial_carry', 'partial_carry'),
      (r'local_emit', 'emit_output'),
      (r'g_control_ring', 'control_ring'),
      (r'write_control|\.wb\[', 'write_formation'),
      (r'\.grp\[', 'compact'),
      (r'mask_count|s3_n|mask_enable', 'mask_count'),
      (r'rst_sync|rst_core|rst_local', 'reset'),
      (r'\.gm\[', 'sram'),
    ]:
        if re.search(pattern,text): return label
    return 'other_explicit'

role_counts=collections.Counter(); family_counts=collections.Counter()
violations=collections.Counter(); maxima=collections.defaultdict(int)
all_rows=[]; bad=[]; sink_counts=collections.Counter()
for z in x['drivers']:
    if z['transparent']: continue
    names=sorted(connected[find(z['net'])])
    f=family(names,z['driver'],z['endpoint_roles'])
    role_counts[z['role']]+=1; family_counts[(f,z['role'])]+=1
    maxima[z['role']]=max(maxima[z['role']],z['loads'])
    c={}; cn=''; inputs={}
    if z['driver'].startswith('cell:'):
        cn=z['driver'][5:].rsplit('/',1)[0]; c=cells[cn]
        inputs={p:[{'net':b,'names':sorted(connected[find(b)])} for b in bs]
                for p,bs in c['connections'].items() if c['port_directions'][p]=='input'}
    row={'driver':z['driver'],'role':z['role'],'family':f,'net':z['net'],
         'native_master':c.get('type'), 'names':names,
         'loads':z['loads'],'endpoint_roles':z['endpoint_roles'],
         'sink_classes':z['sink_classes'],'native_inputs':inputs,
         'endpoints':z['endpoints']}
    all_rows.append(row)
    for e in z['endpoints']: sink_counts[(z['role'],str(e['owner_role']),str(e['role']))]+=1
    if z['loads']>32:
        violations[(f,z['role'])]+=1
        bad.append(row)
with gzip.open(out/'all_owner_sink_records.jsonl.gz','wt') as h:
    for row in all_rows: h.write(json.dumps(row,separators=(',',':'))+'\n')
with gzip.open(out/'unsafe_owner_equations.jsonl.gz','wt') as h:
    for row in sorted(bad,key=lambda r:-r['loads']): h.write(json.dumps(row,separators=(',',':'))+'\n')
with (out/'unsafe_families.tsv').open('w') as h:
    w=csv.writer(h,delimiter='\t'); w.writerow(['family','role','violating_roots'])
    for (f,r),n in sorted(violations.items()): w.writerow([f,r,n])
summary={'scope':'explicit-bus diagnostic only; native scalar REFUSED remains',
 'source_commit':'5af00a1ab','mapped_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),
 'all_nontransparent_roles':dict(role_counts),'max_by_role':dict(maxima),
 'violation_roles':dict(collections.Counter(r['role'] for r in bad)),
 'family_counts':[{'family':f,'role':r,'count':n} for (f,r),n in sorted(family_counts.items())],
 'sink_roles':[{'driver_role':a,'sink_owner_role':b,'sink_pin_role':c,'pins':n} for (a,b,c),n in sorted(sink_counts.items())],
 'violating_families':[{'family':f,'role':r,'roots':n} for (f,r),n in sorted(violations.items())],
 'unclassified_unsafe':[{'driver':r['driver'],'names':r['names'],'loads':r['loads'],'endpoint_roles':r['endpoint_roles']} for r in bad if r['family']=='other_explicit']}
(out/'inventory_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('all_nontransparent_roles','violation_roles','violating_families')},indent=2))
