#!/usr/bin/env python3
"""mk_n4x.py BASE_DIE_PLAN_JSON_GZ BASE_CLOCK_ENTRIES_GZ OLD_PINS NEW_PINS OUT_DIR

COUNT-ARCHIVE-2 2026-11-10 (COORD: count n4ext as NEEDS_PARENT once plan event n4ext1110 lands; it landed on main
4b05fb41165f): counter plan d44v_gqi_cp1109_q3vm_smk_n4x = d44v_gqi_cp1109_q3vm_smk (BASE) + the n4ext1110 delta, the
same items mk_plan_n4rf.py (DIE-HBM-89, physical/die_plan/hbm/n4ext_1110) changes, applied to the counter plan:
  type root: hard_cores / contents u_mu_fused_root outline 216 x 207.36 -> 293.76 x 250.56 (origin kept), hard_cores
  pins_file -> cores/ot_hnx_fused_hub_n4ext__293.76x250.56__n4rf.json (byte copy of the merged event table c756b869),
  internal_stations bus:n4x_up_ne_i / bus:n4x_dn_ne_o landing x 950.4 -> 1028.16, clock tap u_mu_fused_root.clk;
  clock_entries u_mu_fused_root xy / island; top-level note.
Fails closed if the base does not hold the 216 x 207.36 form with the old table, or if any other leaf changes.
"""
import gzip, hashlib, json, pathlib, sys

bp, bce, oldp, newp, out = (pathlib.Path(a) for a in sys.argv[1:6])
W, H, OW, OH = 293.76, 250.56, 216.0, 207.36
ORIGIN = [734.4, 5503.68]
CLK = (146.904, 120.96)
ISLAND = [142.56, 116.64, 151.2, 125.28]
OLD_PINS = 'cores/ot_hnx_fused_hub_n4ext__216x207.36__c25b__centry.json'
NEW_PINS = 'cores/ot_hnx_fused_hub_n4ext__293.76x250.56__n4rf.json'
sha = lambda b: hashlib.sha256(b).hexdigest()

raw = gzip.decompress(bp.read_bytes()).decode()
B = json.loads(raw)
assert json.dumps(B) == raw, 'base plan is not compact json.dumps output'
N = json.loads(raw)
nb = newp.read_bytes()
assert sha(nb).startswith('c756b86982b8'), 'new pins table is not the merged event table'
# the new table = old table with the event's moves only (444 E, rst_n, clk), as mk_plan_n4rf.py asserts
old, new = json.loads(oldp.read_text()), json.loads(nb)
assert [p['name'] for p in old] == [p['name'] for p in new]
moved = sum(1 for a, b in zip(old, new) if (a['x'], a['y']) != (b['x'], b['y']))
assert moved == 446, moved
assert all(a.get('layer') == b.get('layer') for a, b in zip(old, new))

root = N['partition_types']['root']
hc = [c for c in root['hard_cores'] if c.get('inst') == 'u_mu_fused_root']
ct = [c for c in root['contents'] if c.get('inst') == 'u_mu_fused_root']
assert len(hc) == 1 and len(ct) == 1
assert hc[0]['module'] == 'ot_hnx_fused_hub_n4ext' and hc[0]['pins_file'] == OLD_PINS, hc[0].get('pins_file')
for c in hc + ct:
    assert c['origin_um'] == ORIGIN and c['outline_um'] == [OW, OH], (c['origin_um'], c['outline_um'])
    c['outline_um'] = [W, H]
hc[0]['pins_file'] = NEW_PINS
hc[0]['note'] = (hc[0].get('note') or '') + ' | n4ext1110 (COORD 11-10 A, main 4b05fb41165f): RE-FORM 293.76 x 250.56 adopted, E pins + rst_n moved, clk entry at the re-centred island'
nst = 0
for s in root['internal_stations']:
    if s.get('conn') in ('bus:n4x_up_ne_i', 'bus:n4x_dn_ne_o'):
        assert abs(s['to_um'][0] - (ORIGIN[0] + OW)) < 1e-6, s['to_um']
        s['to_um'][0] = round(ORIGIN[0] + W, 4); nst += 1
assert nst == 2, nst
ntap = 0
for t in root['clock']['taps']:
    if t.get('name') == 'u_mu_fused_root.clk':
        t['xy'] = [round(ORIGIN[0] + CLK[0] - 0.024, 4), round(ORIGIN[1] + CLK[1], 4)]; ntap += 1
assert ntap == 1, ntap
N['note'] = ('COUNT-ARCHIVE-2 n4x_1110 (counter overlay: plan event n4ext1110, main 4b05fb41165f, on the counter plan; '
             'root u_mu_fused_root only) <- ' + (B.get('note') or ''))


def leaves(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from leaves(v, p + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from leaves(v, '%s[%d]' % (p, i))
    else: yield p, o


lb, ln = dict(leaves(B)), dict(leaves(N))
changed = sorted(k for k in set(lb) | set(ln) if lb.get(k, '<absent>') != ln.get(k, '<absent>'))
okp = ('/partition_types/root/hard_cores', '/partition_types/root/contents', '/partition_types/root/internal_stations',
       '/partition_types/root/clock/taps')
outside = [k for k in changed if k != '/note' and not k.startswith(okp)]
assert not outside, outside[:10]
assert len(changed) <= 12, changed

# clock entries sidecar
ceraw = gzip.decompress(bce.read_bytes())
ce = json.loads(ceraw)
n = 0
for blk in ce.values():
    if isinstance(blk, dict) and isinstance(blk.get('u_mu_fused_root'), dict):
        e = blk['u_mu_fused_root']
        e['xy_um'] = [round(CLK[0] - 0.024, 4), CLK[1]]; e['island_um'] = ISLAND
        e['source'] = (e.get('source') or '') + ' | n4ext1110: re-centred island of the 293.76 x 250.56 RE-FORM'
        n += 1
assert n >= 1, n

out.mkdir(parents=True, exist_ok=True)
(out / 'cores').mkdir(exist_ok=True)
data = json.dumps(N).encode()
(out / 'die_plan.json.gz').write_bytes(gzip.compress(data, mtime=0))
(out / 'clock_entries.json.gz').write_bytes(gzip.compress(json.dumps(ce).encode(), mtime=0))
(out / (NEW_PINS + '.gz')).write_bytes(gzip.compress(nb, mtime=0))
ev = dict(schema='opentallas.hbm_plan_event.v1', event='n4x_1110', plan='d44v_gqi_cp1109_q3vm_smk_n4x',
          base='d44v_gqi_cp1109_q3vm_smk die_plan.json (sha256 %s)' % sha(raw.encode()),
          source='plan event n4ext1110 (physical/die_plan/hbm/n4ext_1110, main 4b05fb41165f; COORD 11-10 ruling A)',
          lane='COUNT-ARCHIVE-2', date='2026-11-10', module='ot_hnx_fused_hub_n4ext', inst='root.u_mu_fused_root',
          origin_um=ORIGIN, outline_um=dict(to=[W, H], **{'from': [OW, OH]}), pins_file=NEW_PINS,
          pins_file_sha256=sha(nb), pins_moved=moved, stations=nst, taps=ntap, clock_entries=n,
          leaves_changed=changed, plan_sha256=sha(data),
          not_changed='partitions, ports, lanes, every other type and hard core, core_conns/core_macros sidecars')
(out / 'n4x_1110_event.json').write_text(json.dumps(ev, indent=1) + '\n')
print(json.dumps({k: ev[k] for k in ('pins_moved', 'stations', 'taps', 'clock_entries', 'leaves_changed', 'plan_sha256')}, indent=1))
