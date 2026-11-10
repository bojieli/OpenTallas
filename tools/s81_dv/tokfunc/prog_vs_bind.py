"""TOK-VERIFY-1 stale-programme gate: does a compiled S81 layer programme (dv_layer_compile --bound-data output) carry
exactly the transport ages of BIND?  Re-reads BIND with the compiler's own reader (load_bind + Die(b178 netlist) +
rebind_links + bound_ctl_lanes.load) and compares, link by link and lane by lane, with the programme's
bound_data_links.json and the bound_ctl terms recorded in lowering.json.  Exit 0 = every age equal, 1 = any differs.
usage: prog_vs_bind.py REPO PROG_DIR BIND MANIFEST OUT.json"""
import json, sys
from pathlib import Path
repo, prog, bind, man, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
for rel in ('tools', 'tools/s81_dv', 'tools/s81_dv/layer_prog'):
    sys.path.insert(0, str(repo / rel))
import dv_layer_compile as C
from layer_prog import bound_data as BD, bound_ctl_lanes as BCL
B = BD.load_bind(bind, man, repo)
die = C.Die(repo, netlist=B['netlist_path'], netlist_sha=B['netlist_sha256'], bound_rtl=Path(B['bound']) / 'rtl')
rep = BD.rebind_links(die, B)
ctl = BCL.load(B['bound'])
P = json.loads((prog / 'bound_data_links.json').read_text())
diff = []
for k in sorted(set(rep['rows']) | set(P['rows'])):
    a, b = P['rows'].get(k, {}), rep['rows'].get(k, {})
    if (a.get('status'), a.get('bound_age')) != (b.get('status'), b.get('bound_age')):
        diff.append(dict(link=k, prog=(a.get('status'), a.get('bound_age')), bind=(b.get('status'), b.get('bound_age')),
                         lanes=b.get('lanes') or a.get('lanes')))
low = json.loads((prog / 'lowering.json').read_text())
terms = BCL.idxnet(ctl); tp4 = BCL.tp4_on_die(terms); ctl_diff = []
for o in low['ops']:
    bc = (o.get('bench') or {}).get('bound_ctl') if isinstance(o.get('bench'), dict) else None
    bc = bc or o.get('bound_ctl')
    if bc:
        want = dict(tree_legs={str(k): v for k, v in terms['tree_legs'].items()}, query_lane=terms['query_lane'],
                    tp4_on_die=tp4, idx_chain=terms['idx_chain'])
        got = json.loads(json.dumps(dict((k, bc.get(k)) for k in want)))
        if got != json.loads(json.dumps(want)):
            ctl_diff.append(dict(op=o['op'], prog=got, bind=want))
lane_diff, ctl_rec = [], prog / 'bound_ctl_lanes.json'
if ctl_rec.exists():
    got = json.loads(ctl_rec.read_text())['lanes']
    for k in sorted(set(got) | set(ctl)):
        if got.get(k) != ctl.get(k):
            lane_diff.append(dict(lane=k, prog=got.get(k), bind=ctl.get(k)))
res = dict(schema='tok-verify-1.prog_vs_bind.v1', prog=str(prog), bind=str(bind), bind_sha256=B['sha256'],
           prog_bind_sha256=P.get('bind_sha256'), links=len(rep['rows']), link_diffs=diff, ctl_terms_diffs=ctl_diff, ctl_lane_record=ctl_rec.exists(),
           ctl_lane_diffs=lane_diff,
           verdict='PASS' if not diff and not ctl_diff and not lane_diff else 'FAIL')
outp.write_text(json.dumps(res, indent=1, default=str) + '\n')
print(res['verdict'], 'link diffs', len(diff), diff[:4], 'ctl term diffs', len(ctl_diff), 'ctl lane record', ctl_rec.exists(), 'ctl lane diffs', lane_diff[:4])
sys.exit(0 if res['verdict'] == 'PASS' else 1)
