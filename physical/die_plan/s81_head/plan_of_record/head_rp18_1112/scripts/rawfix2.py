"""rawfix2.py REPO OLD_PLAN IN_PLAN OUT_PLAN : second pass after rawfix.py / remap_start.py, for references that name
START-broadcast relay copies (RT.start_relays: raw / run / gated, e.g. rr_t<k>):
 (a) reset_start_raw_exports rows with existing_port rst_o_<k>: the export IS that out port, so the row's
     instance/net/xy become the raw-role start relay that drives rst_o_<k> in the re-solved tree (at the out site, deepest).
 (b) landing_reader_start / landing_writer_start stages whose raw_reset names a start relay: same physical relay
     (same xy, same depth offset from release) if it still exists, else the same-role same-offset relay nearest the old xy.
Fixed rule, no hand edits; reach_fix class 5 is the check."""
import copy, json, sys
sys.path.insert(0, sys.argv[1] + '/tools/die_plan')
import schema as S, reset_tree as RT
man = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
Po = S.Plan(json.load(open(sys.argv[2])), sys.argv[2])
raw = json.load(open(sys.argv[3])); Pn = S.Plan(raw, sys.argv[3]); out = copy.deepcopy(raw)
def pool(T): return (RT.start_relays(T) if T.get('start') else []) + list(T['relays'])
n = 0
for tn, t in sorted(Pn.types.items()):
    Tn = RT.for_type(Pn, tn); pn = pool(Tn); byq = {r['q']: r for r in pn}
    T = out['partition_types'][tn]
    outs = {o[0]: (o[1], o[2]) for o in RT.out_pins(Pn, tn)}
    rawrel = [r for r in pn if r.get('role') in ('raw', 'boot', 'bootstrap_transport')]
    for row in T.get('reset_start_raw_exports', []):
        ep = row.get('existing_port')
        if not ep or not ep.startswith('rst_o_'): continue
        pin = row['xy_um']
        at = [nm for nm, xy in outs.items() if man(xy, pin) < 2.0]
        if at:      # an out port still sits on the export pin: the export is that port, driven by its raw relay
            nep = ep if ep in at else sorted(at)[0]
            cand = [r for r in pn if r.get('role') == 'raw' and man(r['xy'], outs[nep]) < 1e-3]
            best = max(cand, key=lambda r: (r['depth'], r['name']))
            if (nep, best['name'], best['q']) != (ep, row['instance'], row['net']):
                print(f'[offset {Tn["depth"]-best["depth"]}] {tn}.{row["port"]}: existing {ep} -> {nep} (out still on the pin {pin}); {row["instance"]}/{row["net"]} -> {best["name"]}/{best["q"]} d{best["depth"]}')
                row.update(existing_port=nep, instance=best['name'], net=best['q'], xy_um=list(best['xy'])); n += 1
        else:       # no out on the pin any more (column moved the exit): a private raw export from the nearest raw relay
            To_ = RT.for_type(Po, tn); o = next(r for r in pool(To_) if r['name'] == row['instance'] and r['q'] == row['net'])
            off = To_['depth'] - o['depth']
            cand = [r for r in pn if r.get('role') == o.get('role') and Tn['depth'] - r['depth'] == off]
            best = min(cand, key=lambda r: (man(r['xy'], pin), r['name']))
            print(f'[old {o.get("role")} offset {off}] {tn}.{row["port"]}: existing {ep} no longer on the pin {pin} (now {outs.get(ep)}) -> private raw export {best["name"]}/{best["q"]} {[round(v,1) for v in best["xy"]]} {man(best["xy"], pin):.1f} um')
            row.pop('existing_port'); row.update(instance=best['name'], net=best['q'], xy_um=list(best['xy'])); n += 1
    ck = T.get('clock') or {}
    stale = [(k, bus, i, st) for k in ('landing_reader_start', 'landing_writer_start')
             for bus, br in sorted((ck.get(k) or {}).get('branches', {}).items())
             for i, st in enumerate(br.get('stages', []) if isinstance(br, dict) else [])
             if st.get('raw_reset') and (st['raw_reset'] not in byq or man(byq[st['raw_reset']]['xy'], st['xy_um']) > RT.relay_um(Pn, tn))]
    if not stale: continue
    To = RT.for_type(Po, tn); oq = {r['q']: r for r in pool(To)}
    for k, bus, i, st in stale:
        o = oq.get(st['raw_reset'])
        if o is None: print(f'{tn}.{k}.{bus}[{i}]: {st["raw_reset"]} unknown in OLD (kept)'); continue
        off = To['depth'] - o['depth']
        cand = [r for r in pn if Tn['depth'] - r['depth'] == off and r.get('role') == o.get('role')]
        best = min(cand, key=lambda r: (man(r['xy'], o['xy']), r['q']))
        print(f'{tn}.{k}.{bus}[{i}]: {st["raw_reset"]} -> {best["q"]} (role {o.get("role")}, offset {off}, {man(best["xy"], o["xy"]):.1f} um from old, {man(best["xy"], st["xy_um"]):.1f} um from stage)')
        st['raw_reset'] = best['q']; n += 1
json.dump(out, open(sys.argv[4], 'w'), indent=1)
print('changed', n)
