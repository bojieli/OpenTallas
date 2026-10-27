import json, collections, statistics as st
M = json.load(open('me1/mesh.json'))
rs = M['off_core_resites']; print('resite rec sample', rs[0])
rcells = set()
for r in rs:
    for k in ('cell', 'name', 'node'):
        if isinstance(r.get(k), str): rcells.add(r[k])
legs = json.load(open('/tmp/pd10_legs_TT.json'))
nm = collections.defaultdict(list)
for h in M['htree']: nm[h['level']].append(h['len_um'])
ideal = {L: st.median(v) for L, v in nm.items()}
moved_nodes = {h['node'] for h in M['htree'] if h.get('node') and h.get('node_move_um', 0) > 1}
print('level ideal_len  legs  |dev|>25%  of_which_end_or_parent_node_moved  dly_sd_regular dly_sd_irregular')
node_of = {h['tag']: h.get('node') for h in M['htree']}
for L in range(1, 13):
    R = [r for r in legs if r['level'] == L and r['dly'] is not None]
    irr = [r for r in R if abs(r['len_um'] - ideal[L]) > 0.25 * ideal[L]]
    mv = [r for r in irr if (r.get('end') in moved_nodes) or (node_of.get(r['tag'][:-1]) in moved_nodes)]
    reg = [r['dly'] for r in R if r not in irr]; ir = [r['dly'] for r in irr]
    print(f"L{L:2d} {ideal[L]:8.1f} {len(R):5d} {len(irr):5d} {len(mv):5d}  {st.pstdev(reg) if len(reg)>1 else 0:6.1f} {st.pstdev(ir) if len(ir)>1 else 0:6.1f}")
print('nodes moved >1um', len(moved_nodes), 'drivers moved', sum(1 for d in M['drivers'].values() if d['move_um'] > 1))
