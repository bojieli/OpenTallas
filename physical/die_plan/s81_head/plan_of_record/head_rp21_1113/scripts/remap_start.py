"""remap_start.py REPO OLD_PLAN IN_PLAN OUT_PLAN : re-derive clock.landing_reader_start / landing_writer_start stage
raw_reset names after a reset re-solve renumbered or moved a type's relays (rawfix.py covers reset_start_raw_exports and
landing_local_resets).  Rule (fixed): the stage keeps the SAME physical relay (same xy, same depth offset from the type
release) when it still exists (renumbered); otherwise the new relay with the same depth offset nearest the old relay's
xy.  r3 (11-13): clock.landing_local_resets[].raw follow the same rule.  Only types whose solved relay list differs from OLD are touched."""
import copy, json, sys
sys.path.insert(0, sys.argv[1] + '/tools/die_plan')
import schema as S, reset_tree as RT
man = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
Po = S.Plan(json.load(open(sys.argv[2])), sys.argv[2])
raw = json.load(open(sys.argv[3])); Pn = S.Plan(raw, sys.argv[3]); out = copy.deepcopy(raw)
stat = dict(types_changed=[], same=0, renumbered=0, moved=0)
for tn, t in sorted(Pn.types.items()):
    import os
    if os.environ.get('ONLY') and tn not in os.environ['ONLY'].split(','): continue
    if tn in os.environ.get('SKIP', '').split(','): continue
    c = t.get('clock') or {}
    keys = [k for k in ('landing_reader_start', 'landing_writer_start') if c.get(k)]
    if c.get('landing_local_resets'): keys.append('landing_local_resets')   # r3: same rule for local raw resets
    if not keys or tn not in Po.types:
        continue
    To, Tn = RT.for_type(Po, tn), RT.for_type(Pn, tn)
    sig = lambda T: sorted((r['q'], round(r['xy'][0], 3), round(r['xy'][1], 3), r['depth']) for r in T['relays'])
    if sig(To) == sig(Tn) and To['depth'] == Tn['depth']:
        continue
    stat['types_changed'].append(tn)
    oq = {r['q']: r for r in To['relays']}
    def items(k):
        cfg = out['partition_types'][tn]['clock'][k]
        if k == 'landing_local_resets':
            for i, st in enumerate(cfg): yield st.get('name', i), i, st, 'raw'
            return
        for bus, br in sorted(cfg.get('branches', {}).items()):
            for i, st in enumerate(br.get('stages', []) if isinstance(br, dict) else []): yield bus, i, st, 'raw_reset'
    for k in keys:
        if True:
            for bus, i, st, fld in items(k):
                q = st.get(fld); o = oq.get(q)
                if o is None and isinstance(q, str) and q.startswith('rr_t'):
                    # HEAD-97 rp21: raw copy rr_t<k> of the gated leaf rst_n_t<k>: follow the leaf (same depth offset,
                    # nearest to the old leaf, gated role), as reach_fix.fix_raw_tap_refs does
                    import re as _re, street_rule as SR
                    lo = oq.get('rst_n_t' + q[4:])
                    if lo is not None:
                        off = To['depth'] - lo['depth']
                        try: rol = {k_: r_.get('role') for k_, r_ in SR._q_roles(Tn).items()}
                        except Exception: rol = {}
                        cand = [r for r in Tn['relays'] if _re.match(r'rst_n_t\d+$', r['q']) and Tn['depth'] - r['depth'] == off
                                and (not Tn.get('start') or rol.get(r['q']) == 'gated')]
                        if cand:
                            best = min(cand, key=lambda r: (man(r['xy'], lo['xy']), r['q']))
                            nq = 'rr_t' + best['q'][len('rst_n_t'):]
                            if nq != q:
                                stat['moved'] += 1
                                print(f'{tn}.{k}.{bus}[{i}]: {q} -> {nq} (raw copy follows leaf, {man(best["xy"], lo["xy"]):.1f} um, depth offset {off})')
                                st[fld] = nq
                            else: stat['same'] += 1
                            continue
                if o is None:
                    print(f'{tn}.{k}.{bus}[{i}]: {q} not in OLD tree (kept)'); continue
                off = To['depth'] - o['depth']
                cand = [r for r in Tn['relays'] if Tn['depth'] - r['depth'] == off]
                same = [r for r in cand if man(r['xy'], o['xy']) < 1e-3]
                if same:
                    nq = sorted(same, key=lambda r: r['q'])[0]['q']
                    if nq == q: stat['same'] += 1; continue
                    stat['renumbered'] += 1; print(f'{tn}.{k}.{bus}[{i}]: {q} -> {nq} (same relay, renumbered)')
                else:
                    best = min(cand, key=lambda r: (man(r['xy'], o['xy']), r['q']))
                    nq = best['q']; stat['moved'] += 1
                    print(f'{tn}.{k}.{bus}[{i}]: {q} -> {nq} (moved {man(best["xy"], o["xy"]):.1f} um, depth offset {off})')
                st[fld] = nq
json.dump(out, open(sys.argv[4], 'w'), indent=1)
print(json.dumps(stat))
