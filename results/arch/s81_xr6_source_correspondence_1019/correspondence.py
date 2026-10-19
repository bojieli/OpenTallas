"""Read frozen native endpoint sets; no RTL, mapper, simulator or physical tool."""
import collections, functools, gzip, hashlib, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
census_path = BASE / 's81_xr6_structural_census_1019/native_census.json.gz'
model_path = BASE / 's81_xr6_whole_model_1019/model.json'
census = json.load(gzip.open(census_path, 'rt'))
model = json.loads(model_path.read_text())
records = census['records']
functional = [r for r in records if r['role'] not in ('transparent', 'clock')]
by = {r['driver']: r for r in functional if r['role'] != 'input'}
incoming = collections.defaultdict(dict)
inversions = collections.Counter()
for r in records:
    if r['role'] == 'transparent':
        assert r['master'].startswith(('BUF', 'INV'))
        if r['master'].startswith('INV'):
            inversions.update(tuple(e) for e in r['endpoints'])
for r in functional:
    name = r['net'] if r['role'] == 'input' else r['driver']
    for target, pin in r['endpoints']:
        assert pin not in incoming[target], (target, pin)
        incoming[target][pin] = dict(source=name, role=r['role'],
                                    master=r['master'], inverted=bool(inversions[target, pin] % 2))

@functools.lru_cache(None)
def ancestors(n):
    r = by.get(n)
    if r is None or r['role'] != 'comb':
        return frozenset((n,))
    return frozenset().union(*(ancestors(x['source']) for x in incoming[n].values()))

def family(n):
    return n.split('[')[0].rstrip('\\').replace('u_ot_pr_core.u.', '')

# Source-equation boundaries. Native gates are identified by exact ancestors,
# rather than pretending ABC names are stable RTL source names.
def purpose(n):
    if not n.startswith('_'):
        f = family(n)
        return {
            'u_rr.rst_n': 'same-age local reset relay; rs_c/rs_r/rs_s/rs_o',
            'rst_n__ot_rl1$_DFF_P_': 'second face reset landing, outside XR source',
            'ev_c': 'ENG input valid: eqd write, copy agreement and collector fault',
            'erun$_DFF_PN0_': 'ENG active: x_s/x_si selection and overlap faults',
            'rwr_c': 'CTL row-write override for sw_d destination word',
            'rwe_c': 'RD destination enable for ud packet word capture',
            'un_c': 'OLD packet chunk select for sw_d half-word',
            'tg1_c': 'x_eps/x_scale capture enable',
            'pv': 'partial input valid: pq capture, collection start and faults',
            'cis_c': 'ci_r word selects snd versus cixw',
            'pkw_c': 'pk word write enable from prior lo and pn next state',
            'lov_c': 'lo_sel0 input word qualification',
            'eoh': 'ENG source word in kind-major, then leaf order',
            'poh': 'norm partial source word in leaf order',
        }[f]
    a = ' '.join(ancestors(n))
    if n == '_60297_': return 'send config/reset-qualified next-state control'
    if n == '_77908_': return 'ci selector next-state including V CTL exclusion'
    if n in ('_77877_', '_77881_', '_77884_', '_77885_', '_77888_'):
        return 'RD destination leaf enable from selected E/W packet header'
    if n in ('_87931_', '_87924_', '_50813_'):
        return 'registered E/V valid and kind classification, shared CTL/RD/SC users'
    if 'sid_oh' in a:
        return 'RD source priority and this-slice mask classifier; rdb0/rdat enables'
    return 'unclassified'

copies = {r['driver']: r['copies'] for r in model['model32']['ledger']}
rows = []
assignments = []
for r in model['model32']['ledger']:
    n = r['driver']
    assert purpose(n) != 'unclassified'
    row = dict(r)
    row.update(source_boundary=purpose(n), sequential_ancestors=sorted(ancestors(n)),
               incoming_pin_polarity=incoming[n])
    expanded = [(e, i, p) for e, p in by[n]['endpoints'] for i in range(copies.get(e, 1))]
    slots = [[] for _ in range(r['copies'])]
    for index, (target, target_copy, pin) in enumerate(expanded):
        owner = index // 32
        slots[owner].append((target, target_copy, pin))
        assignments.append(dict(source=n, source_copy=owner, target=target,
                                target_copy=target_copy, pin=pin,
                                inverted=bool(inversions[target, pin] % 2)))
    assert max(map(len, slots)) <= 32
    row['copy_endpoint_counts'] = list(map(len, slots))
    rows.append(row)

cone = set()
def add_cone(n):
    if n in cone or n not in by or by[n]['role'] != 'comb': return
    cone.add(n)
    for x in incoming[n].values(): add_cone(x['source'])
for r in rows:
    if r['role'] == 'comb': add_cone(r['driver'])

out = dict(schema='opentallas.s81.xr6.source_correspondence.v1',
           scope='MODEL/PROPOSAL ONLY; no successor RTL or native retention PASS',
           source_sha256=model['source_sha256'], odb_sha256=census['odb_sha256'],
           census_sha256=hashlib.sha256(census_path.read_bytes()).hexdigest(),
           model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
           copied_original_ff=sum(r['role']=='ff' for r in rows),
           added_ff=sum(r['copies']-1 for r in rows if r['role']=='ff'),
           copied_original_comb=sum(r['role']=='comb' for r in rows),
           added_comb=sum(r['copies']-1 for r in rows if r['role']=='comb'),
           rows=rows, endpoint_assignments=assignments,
           classifier_cone=[dict(driver=n,master=by[n]['master'],incoming=incoming[n]) for n in sorted(cone)],
           polarity_method='For each terminal count all transparent INV output records containing it; unique native input ownership makes the complete ancestor chain unique. BUF is identity. Parity is relative to the nontransparent source output pin, not source RTL variable.',
           hb1_historical_sha256=hashlib.sha256((HERE/'hb1_historical_source.txt').read_bytes()).hexdigest(),
           hb1_native_census=None)
assert out['added_ff']==421 and out['added_comb']==136
assert len(assignments)==sum(r['expanded_pins'] for r in rows)
(HERE/'correspondence.json.gz').write_bytes(gzip.compress((json.dumps(out,indent=2)+'\n').encode(),mtime=0))
print(json.dumps({k:out[k] for k in ('copied_original_ff','added_ff','copied_original_comb','added_comb')}))
print('PASS unique collapsed terminal ownership, complete cloned endpoint partition, native inverter parity; '+str(len(assignments))+' assigned pins, '+str(len(cone))+' classifier cone gates')
print('NOT RUN: RTL miter, mapped retention, HB1 mapped/native graph, physical gate')
