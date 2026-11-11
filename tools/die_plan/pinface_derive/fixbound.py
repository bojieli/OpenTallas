"""DIE-QC-97 11-11: re-solve the su START / local reset relay names on the tree the strict bind EMITTED (bind rtl/<type>.sv,
reset_anchor.bound_tree), not the plan-level reset_tree.for_type tree (they differ on 8 of 9 su_l types).
Per su type: (1) take the bind's own anchor re-picks (bind_reset_anchor.json), (2) any stage / local reset > 405 um from its
bound relay is re-picked to the nearest same-depth non-ported bound rst_rl relay measured from the stage (RELAY-REMAP-1
rule, fail closed), (3) clock.reset_tree_anchor re-recorded on the bound tree (reset_anchor.record, tol 405).  Every other
type byte-as-PLAN.  usage: fixbound.py SRC PLAN BIND_DIR OUT REP"""
import hashlib, json, re, sys
SRC, PL, BD, OUT, REP = sys.argv[1:6]
sys.path.insert(0, SRC + '/tools/die_plan')
import reset_anchor as A
rb = open(PL, 'rb').read(); raw = json.loads(rb)
for f in (lambda p: json.dumps(p, separators=(',', ':')) + '\n', lambda p: json.dumps(p) + '\n',
          lambda p: json.dumps(p, indent=1) + '\n', lambda p: json.dumps(p, indent=2) + '\n',
          lambda p: json.dumps(p, separators=(',', ':')), lambda p: json.dumps(p)):
    if f(raw).encode() == rb: dump = f; break
else: raise SystemExit('style')
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
rec = {r['type']: {m['name']: m['to'] for m in r['remaps']} for r in json.load(open(BD + '/bind_reset_anchor.json'))['receipts'] if r}
rep = {}
for tn, t in raw['partition_types'].items():
    if not any('su_lane' in c['module'] for c in t.get('hard_cores', [])):
        continue
    sv = open(f'{BD}/rtl/{tn}.sv').read(); bt = A.bound_tree(sv); R = {r['q']: r for r in bt['relays']}
    port = set(re.findall(r'\bassign\s+rst_o_\w+\s*=\s*(\w+)\s*;', sv))
    mp = rec.get(tn, {}); ck = t['clock']
    pts = [(s, 'raw_reset') for k in ('landing_reader_start', 'landing_writer_start')
           for br in ((ck.get(k) or {}).get('branches') or {}).values() for s in br.get('stages', []) if s.get('raw_reset')]
    pts += [(s, 'raw') for s in ck.get('landing_local_resets') or [] if s.get('raw')]
    rows = []; nmap = 0
    for c, k in A.refs(t):                       # (1) the bind's own re-picks, every reference the anchor covers
        if c[k] in mp: c[k] = mp[c[k]]; nmap += 1
    for s, k in pts:                             # (2) reach on the bound tree
        r = R[s[k]]; d = L1(r['xy'], s['xy_um'])
        if d <= 405 + 1e-6: continue
        cand = [x for q, x in R.items() if re.fullmatch(r'rst_rl_\d+', q) and q not in port and x['depth'] == r['depth']]
        b = min(cand, key=lambda x: (L1(x['xy'], s['xy_um']), x['q'])); nd = L1(b['xy'], s['xy_um'])
        if nd > 405 + 1e-6:
            raise SystemExit(f'{tn}: {s[k]} stage {s["xy_um"]}: nearest same-depth bound relay {b["q"]} {nd:.1f} um > 405')
        rows.append(dict(was=s[k], to=b['q'], depth=r['depth'], hop_was=round(d, 1), hop=round(nd, 1))); s[k] = b['q']
    ck.pop(A.KEY, None); ck[A.KEY] = A.record(t, bt, SRC, 405.0)   # (3)
    rep[tn] = dict(bind_remaps=nmap, reach_repicks=rows, anchored=len(ck[A.KEY]['relays']))
    print(tn, 'bind remaps applied', nmap, 'reach re-picks', [(x['was'], x['to'], x['hop_was'], x['hop']) for x in rows], 'anchored', len(ck[A.KEY]['relays']))
open(OUT, 'w').write(dump(raw))
rep['sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
json.dump(rep, open(REP, 'w'), indent=1); print('sha', rep['sha256'])
