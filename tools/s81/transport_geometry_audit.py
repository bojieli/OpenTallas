#!/usr/bin/env python3
"""Audit actual exported partial generator paths; no route/activity closure."""
import argparse,gzip,hashlib,json,html
from pathlib import Path

def key(p):return tuple(round(v,5) for v in p)
def length(p):return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(p,p[1:]))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--capacity',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);a=ap.parse_args();p=json.loads(gzip.decompress(a.plan.read_bytes()));cap=json.loads(a.capacity.read_text());a.out_dir.mkdir(parents=True,exist_ok=True)
 chains={c['chain']:c for c in p['chain_paths']};assert len(chains)==len(p['chain_paths'])
 ranks=[]
 for n,c in chains.items():
  bits=sum(c['lanes']);dist=length(c['path']);ranks.append(dict(chain=n,bits=bits,path_um=dist,bit_um=bits*dist,stations=len(c['stations']),status=c['status']))
 t=p['broadcast_trees']['E'];target=t['root_targets']['2'];parents={key(e['node']):e for e in t['edges']};path=[];node=key(target);seen=set()
 while node!=key(t['entry']):
  assert node not in seen,('cycle',node);seen.add(node);e=parents[node];path.append(e['chain']);node=key(e['parent'])
 path=list(reversed(path));route=t['prefix'][:]
 for n in path:route.extend(chains[n]['path'])
 root2=next(c for c in p['calendar'] if c['root']==2)
 final=chains['cx2']['path'];actual_polyline_sum=length(t['prefix'])+sum(length(chains[n]['path']) for n in path)+length(final)
 route.extend(final)
 # Prefix is exported independently and contributes to actual calendar.
 r=dict(scope=p['scope'],source_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),exported_chains=len(chains),sum_unique_chain_bit_um=sum(v['bit_um'] for v in ranks),top20_widthweighted_chains=sorted(ranks,key=lambda c:c['bit_um'],reverse=True)[:20],root2_calendar=root2,root2_broadcast_chains=path,root2_polyline=route,root2_polyline_length_with_interchain_gaps_um=length(route),root2_actual_chain_polyline_sum_um=actual_polyline_sum,calendar_metric_definition='Ideal-node roadmap tree length plus actual prefix/finalrootchain; not actual LEF pin-wire distance',root2_injector=t['injector'],coverage_gaps=['Generator failed after all root and q/a/ix/co construction; remaining control and endpoints absent','No production transfer activity or serialization weights exported','No clock/PG/halos/full route cuts or fixed-calendar parity qualification','Current legacy single VM reservation is not actual final328core+150edge physical composition'])
 (a.out_dir/'report.json').write_text(json.dumps(r,indent=1)+'\n')
 sc=.02;X=35;Y=90;s=['<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="790" viewBox="0 0 1360 790"><rect width="1360" height="790" fill="#f8fafc"/><g font-family="sans-serif" fill="#17243b"><text x="25" y="31" font-size="22">Actual S81 transport geometry — partial screen 12</text><text x="25" y="55" font-size="14">33 × 26 mm die at true aspect ratio. Exported hardware paths; canonical 2,417 pairs / BF519 / 128 roots.</text>']
 def pt(v):return X+v[0]*sc,Y+(26000-v[1])*sc
 def rect(x,y,w,h,color):
  xx,yy=pt([x,y+h]);s.append(f'<rect x="{xx}" y="{yy}" width="{w*sc}" height="{h*sc}" fill="{color}" stroke="white" stroke-width=".3"/>')
 rect(0,0,33000,26000,'#e2e8f0')
 for f in cap['placements']:rect(*f['origin_um'],*f['outline_um'],'#bfdbfe')
 for name,x,y,w,h in cap['hard_fixed_boxes']:rect(x,y,w,h,'#c4b5fd' if name.startswith('sp_hc') else '#94a3b8')
 for c in chains.values():
  coords=' '.join(f'{x:.3f},{y:.3f}' for x,y in map(pt,c['path']));s.append(f'<polyline points="{coords}" fill="none" stroke="#64748b" stroke-width=".35" opacity=".18"/>')
 coords=' '.join(f'{x:.3f},{y:.3f}' for x,y in map(pt,route));s.append(f'<polyline points="{coords}" fill="none" stroke="#dc2626" stroke-width="2"/>')
 for label,pos in [('E injector',t['prefix'][0]),('Root 2',target)]:
  x,y=pt(pos);s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#dc2626"/><text x="{x-45}" y="{y-9}" font-size="12" fill="#b91c1c">{label}</text>')
 xx=740;yy=115
 lines=['Red: actual root-2 broadcast path',f'{root2["x_path_um"]/1000:.3f} mm calendar metric / {root2["x_stations"]} stations',f'{actual_polyline_sum/1000:.3f} mm actual chain polyline sum (not pins)',f'Return: {root2["return_stations"]} stations; logical W0 / physical E',f'Actual broadcast source: {t["injector"]}',f'{len(chains):,} exported chain paths, with actual placed stations','All 128 broadcasts and returns constructed.','SW q514 / a1026 / ix / co constructed.','Generator next failed at control/service boundary.','','Known structural improvements to compare:','1. New homes for injector + half-tree entry','2. Physical-half / y-coherent return grouping','3. Whole VM/SU/HC service placement and pin faces','','Each comparison must preserve root/output identity,','price fixed stage changes, and include shared trunks.','A gather remap alone does not fix this broadcast.','','Grey parent rectangles contain historical VM geometry.','Actual final VM children are not integrated here.','This drawing is baseline evidence, not candidate B.']
 for line in lines:s.append(f'<text x="{xx}" y="{yy}" font-size="14">{html.escape(line)}</text>');yy+=23
 s.append('<text x="25" y="667" font-size="14">Grey lines: actual exported chain polylines, including shared prefix chains once. Blue: exact typed field regions.</text><text x="25" y="692" font-size="14">Missing activity/serialization, clock/PG, remaining control graph and final VM boundaries prevent final system ranking.</text><text x="25" y="720" font-size="14">No full routed, timing, congestion, round-trip parity or throughput qualification is implied.</text></g></svg>');(a.out_dir/'actual_paths.svg').write_text(''.join(s));print(json.dumps(dict(chains=len(chains),root2_polyline_length=length(route),calendar=root2),indent=1))
if __name__=='__main__':main()
