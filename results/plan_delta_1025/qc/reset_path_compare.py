import sys,json
sys.path.insert(0,'tools/die_plan')
import schema as S, reset_tree as RT
base_p, new_p = sys.argv[1], sys.argv[2]
def wp(p):
    raw=S.load(p); return raw, RT.wf_plan(S.Plan(raw, path=p))
rb,B=wp(base_p); rn,N=wp(new_p)
PATHP=[p['name'] for p in rb['partitions'] if p['name'].startswith('sl_W5_') or p['type'] in ('coll_ftc','native59','glue','phy_ucie_kv')]
PATHT=sorted({p['type'] for p in rb['partitions'] if p['name'] in PATHP})
out=dict(path_types=PATHT, path_parts=PATHP,
  path_type_json_changed=[t for t in PATHT if json.dumps(rb['partition_types'][t],sort_keys=True)!=json.dumps(rn['partition_types'][t],sort_keys=True)],
  path_type_reset_changed=[t for t in PATHT if t in B['types'] and B['types'][t]!=N['types'].get(t)],
  path_part_reset_changed=[n for n in PATHP if B['parts'][n]!=N['parts'][n]],
  path_part_orient_type_changed=[n for n in PATHP if {p['name']:p for p in rb['partitions']}[n]!={p['name']:p for p in rn['partitions']}[n]],
  max_release=[B['max_release'],N['max_release']], unreachable=[len(B['unreachable']),len(N['unreachable'])],
  types_reset_changed=[t for t in N['types'] if t in B['types'] and B['types'][t]!=N['types'][t]],
  parts_release_changed=[(n,B['parts'][n]['release'],N['parts'][n]['release']) for n in N['parts'] if B['parts'][n]['release']!=N['parts'][n]['release']])
print(json.dumps(out,indent=0,default=str))
