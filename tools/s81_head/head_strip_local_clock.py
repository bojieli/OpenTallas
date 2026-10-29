#!/usr/bin/env python3
"""Fresh neighbour-fed clock with balanced local trees on exact HEAD HK4 data geometry.

No clock trim/pad, no global H-tree: a maximum-traffic tree on physical region
adjacencies feeds local bisection trees; all CA origins must be recomputed.
"""
import argparse,gzip,json,shutil,subprocess,sys
from pathlib import Path
W=Path(__file__).resolve().parents[2];sys.path.insert(0,str(W/'tools/die_plan'))
from head_spine_strip_delta import spine_channels,X0
import locality as L
from head_strip_landing_types import split

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',required=True);a=a.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
 d=W/'results/die_head_21_1028/hk4';inp=out/'input';inp.mkdir();p=json.load(gzip.open(d/'plan_spine_raw.json.gz','rt'))
 for q in p['partitions']:
  if q['type'] in ('hd_spn','hd_spn_end'):
   p['die'].setdefault('channels',[]).extend(spine_channels(q['name'],q['origin_um'][0]-X0,q['origin_um'][1]))
 p,aliases=split(p);(inp/'type_aliases.json').write_text(json.dumps(aliases,indent=1))
 (inp/'plan.json').write_text(json.dumps(p,indent=1));shutil.copytree(d/'core_pins',inp/'core_pins')
 mapping=json.load(open(d/'spine_regions.json'))['part_region'];D=L.load_plan(p);G=L.region_geom(D,mapping);adj=L.part_adjacency(D);cross=L.crossings(D,mapping,G,adj);E=L.region_graph(D,mapping,adj,cross)
 # Only existing physical neighbour graph edges or declared data crossings;
 # disconnected regions are explicitly recorded by the generic proposer.
 f=L.feed_tree(G,E,cross,1.0,'fish')
 # Fork at each column: clock must not traverse the full data U-turn before
 # feeding its physically adjacent return tile. These are real neighbor edges,
 # without changing data paths or introducing a balanced die clock.
 assert f['root']=='sp3',f['root']
 for row in range(6):
  for side in ('W','E'):
   for j in range(11):
    f['parent'][f't{side}{row}o{j}']=f'sp{row}' if j==0 else f't{side}{row}o{j-1}'
    f['parent'][f't{side}{row}b{j}']=f't{side}{row}o{j}'
   f['parent'][f'turn{side}{row}a']=f't{side}{row}o10'
   f['parent'][f'turn{side}{row}b']=f'turn{side}{row}a'
 for child in f['parent']:
  seen=set();n=child
  while f['parent'][n] is not None:
   assert n not in seen,('feed cycle',child,n)
   seen.add(n);n=f['parent'][n]
  assert n==f['root'],('wrong root',child,n)
 f['tap']={(parent,child):L.xing_point(G[parent]['bbox'],G[child]['bbox']) for child,parent in f['parent'].items() if parent is not None}
 assert all(tuple(sorted((x,y))) in E for x,y in f['tap']), 'non-neighbor feed edge'
 feed={'root':f['root'],'parent':f['parent'],'tap':{f'{x}->{y}':v for (x,y),v in f['tap'].items()},'joined':f['joined'],'source':'neighbor graph; spine/column forks prevent serial clock trip around data turns'}
 (out/'feed.json').write_text(json.dumps(feed,indent=1));shutil.copy(d/'spine_regions.json',out/'spine_regions.json')
 (out/'estimate.md').write_text(f'''HEAD HK4 local clock estimate — geometric first trial

327 logical regions, 351 physical parts. Feed root {f['root']}; 326 neighbour-forwarded edges. Explicit disconnected-component joins: {len(f['joined'])}, {f['joined']}.

The previous traveling local rib produced a measured 949.7 ps within-region spread. Local H-tree bisection to 100 um makes the final unmatched leg at most 100 um Manhattan; at the assumed illustrative 430 ps/mm clock-wire slope this is approximately 43 ps before cell/load/site variation. All retained bisection paths have equal geometric depth; no timing trim or pads are introduced. Actual legal sites and GRT determine the final spread. Singleton regions retain their one local path. Shims stay in their six original spine regions; independent N3 transit/turn have separate fresh feeds. All CA origins/K and START endpoints require fresh measured proof.

First trial uses inv2, NDR, 200 um repeaters, actual edge reach at most 405 um; two-corner TT/FF GRT after personal image review. No SS gate or release claim.
''')
 cmd=[sys.executable,str(W/'tools/die_plan/die_trial.py'),'kit',str(inp/'plan.json'),'--out',str(out/'kit'),'--tree-form','link_htree','--region-trees',str(out/'spine_regions.json'),'--feed',str(out/'feed.json'),'--leaf-um','100','--rep-um','200','--tree-site-slide','--clock-cell','inv2','--clock-rc','ndr','--tree-opt','region_stub=1','--cell-paths','--rep-actual-max','405']
 print(' '.join(cmd),flush=True);return subprocess.call(cmd,cwd=W)
if __name__=='__main__':raise SystemExit(main())
