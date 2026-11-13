"""resetsum.py REPO PLAN OUT.json : reset solve summary (RT.check errors/warnings, wavefront plan, per-type trees)."""
import json, sys
sys.path.insert(0, sys.argv[1] + '/tools/die_plan')
import schema as S, reset_tree as RT
P = S.Plan(json.load(open(sys.argv[2])), sys.argv[2])
errs, warns, info = RT.check(P)
W = RT.wf_plan(P)
types = {}
for tn, v in W['types'].items():
    types[tn] = dict(depth_K=v['depth_K'], relays=v['relays'], max_hop_um=v['max_hop_um'], in_um=v['in_um'],
                     entry=v['entry'], release_after_pin=v['release_after_pin'], column=RT.column_spec(P, tn) and True,
                     relay_um=RT.relay_um(P, tn),
                     core_resets=[dict(inst=c['inst'], pin_um=c['pin_um'], xy=c['xy'],
                                       dist_um=round(abs(c['pin_um'][0]-c['xy'][0])+abs(c['pin_um'][1]-c['xy'][1]), 2))
                                  for c in v.get('core_resets', [])])
parts = {p: dict(type=r['type'], parent=r['parent'], hop_um=r.get('hop_um'), release=r['release'], source=r.get('source'))
         for p, r in W['parts'].items()}
json.dump(dict(plan=sys.argv[2], errors=errs, warnings=warns, unreachable=W['unreachable'], max_release=W['max_release'],
               max_die_hop_um=W['max_die_hop_um'], long_hops=W['long_hops'], hop_um=W['hop_um'], relay_um=W['relay_um'],
               types=types, parts=parts), open(sys.argv[3], 'w'), indent=1, default=str)
print(json.dumps(dict(errors=len(errs), warnings=len(warns), unreachable=len(W['unreachable']), max_release=W['max_release'],
                      max_die_hop_um=W['max_die_hop_um'], long_hops=len(W['long_hops']))))
