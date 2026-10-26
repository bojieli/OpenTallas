"""distinct core/type designs of an HBM plan, keyed as tools/autopilot/ownership.py plan_items()"""
import json, sys, os, collections
sys.path.insert(0, os.path.join(sys.argv[1], 'tools/autopilot'))
import ownership as O
plan_path = sys.argv[2]; pdir = os.path.dirname(plan_path)
plan = json.load(open(plan_path))
pins = {}
for t in plan['partition_types'].values():
    for h in t.get('hard_cores') or []:
        f = h.get('pins_file')
        if f and f not in pins:
            fp = os.path.join(pdir, f)
            pins[f] = open(fp).read() if os.path.exists(fp) else None
ct = json.load(open(os.path.join(pdir, 'cores/harden/canonical_ports_split.json')))
items = O.plan_items('hbm', plan, pins, O.canonical_masters(ct))
c = collections.Counter(i['kind'] for i in items)
print(json.dumps(dict(types=len(plan['partition_types']), partitions=len(plan['partitions']),
      type_designs=c['type'], core_designs=c['core'],
      core_entries=sum(len(t.get('hard_cores') or []) for t in plan['partition_types'].values()),
      modules=len({h['module'] for t in plan['partition_types'].values() for h in t.get('hard_cores') or []}),
      pin_files=len(pins))))
if len(sys.argv) > 3:
    for i in sorted(items, key=lambda i: i['item']):
        if i['kind'] == 'core': print(i['item'], len(i['members']), i['replicas'])
