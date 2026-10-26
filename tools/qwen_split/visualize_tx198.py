#!/usr/bin/env python3
"""Actual scale and directional critical-pin/reset overlay; unknowns stay outside."""
import argparse,gzip,hashlib,html,json
from pathlib import Path
from screen_compressed_tile import xy

def main():
 p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('screen',type=Path);p.add_argument('bundle',type=Path);p.add_argument('out',type=Path);a=p.parse_args();c=json.loads(a.candidate.read_text());s=json.loads(a.screen.read_text());b=json.loads(gzip.decompress(a.bundle.read_bytes()));W,H=c['outline_um'];scale=.55;ox,oy=48,110;height=980;width=1320
 def pt(p):return(ox+p[0]*scale,oy+(H-p[1])*scale)
 def line(p,q,color,stroke=1,opacity=.8,dash=False):
  x,y=pt(p);X,Y=pt(q);return f'<path d="M{x:.3f},{y:.3f} L{X:.3f},{Y:.3f}" stroke="{color}" stroke-width="{stroke}" opacity="{opacity}" fill="none" marker-end="url(#arrow)"'+(' stroke-dasharray="4 3"'if dash else'')+'/>'
 out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>','<rect width="100%" height="100%" fill="white"/>','<text x="25" y="26" font-size="18">Qwen actual TX198 child placement: data direction, critical native pin hops and reset</text>','<text x="25" y="49" font-size="12">Source bitmap 6644fec71; 58 data banks + 14 children + 11 reset bodies = 83 explicit physical roots. Residual root 84 remains unplaced.</text>',f'<text x="25" y="69" font-size="12">481.68 × 1400.22 µm; common physical scale. Native-arc + wire screens exclude parent RNE / gating comb; no parent CTS / route / full-system qualification.</text>',f'<rect x="{ox}" y="{oy}" width="{W*scale}" height="{H*scale}" fill="#f4f6f7" stroke="#222"/>']
 allb=c['children']+c['banks']+c['reset_nodes']
 for q in allb:
  x,y=pt([q['x'],q['y']+q['h']]);color='#aebed0'if q in c['children']else'#91c6a2'if q in c['reset_nodes']else'#efc37e';label='RP'if'rpair'in q['master']else'LSL'if'lsl'in q['master']else'NODE'if'node'in q['master']else''
  out.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{q["w"]*scale:.3f}" height="{q["h"]*scale:.3f}" fill="{color}" stroke="#526170" stroke-width="0.4"><title>{html.escape(q["inst"])} | {q["master"]} | {q.get("orient","R0")} | ({q["x"]},{q["y"]}) µm</title></rect>')
  if label:out.append(f'<text x="{x+2:.1f}" y="{y+10:.1f}" font-size="8">{label}</text>')
 # Keep reset topology separate from payload directions. Each is actual source→sink.
 seen=set()
 for r in b['reset']['source_topology']:
  k=(r['source'],r['sink'])
  if k in seen:continue
  seen.add(k);out.append(line(r['source_xy'],r['sink_xy'],'#248548',.8,.45,True))
 for r in sorted(b['reset']['target_assignment'],key=lambda r:r['margin_ps'])[:5]:out.append(line(r['source_xy'],r['sink_xy'],'#248548',.9,.55,True))
 for q in b['clock_roots']:
  x,y=pt(q['actual_clock_xy_um']);out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="1.1" fill="#235caa"><title>{html.escape(q["instance"])} clock {q["actual_clock_xy_um"]}; R_TT={q["R_TT_ps"]} ps; parent phase unassigned</title></circle>')
 worst=sorted(s['worst_by_group'],key=lambda r:r['margin_ps']);selected=[]
 for r in worst:
  if len(selected)>=12:break
  selected.append(r)
 for r in worst:
  if r['group']in ('n_a_bank_node_data','n_b_bank_node_data','stage_n_y_to_face','stage_t_out_to_face') and r not in selected:selected.append(r)
 for q in c['children']:
  if q['master']=='ot_qwen_tile_node':
   for name in ('a[0]','b[0]','y[0]','t_out[0]'):
    x,y=pt(xy(q,b['actual_views'][q['master']]['actual_LEF_pins'][name]));out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.2" fill="#9d3d92"/><text x="{x+3:.2f}" y="{y-2:.2f}" font-size="6">{name}</text>')
 for i,r in enumerate(selected,1):
  color='#9d3d92'if'node'in r['group']or'stage_'in r['group']else'#ce7626'if any(v in r['group']for v in ('rqr','wrom','s2_w'))else'#287ea9';out.append(line(r['source_xy'],r['sink_xy'],color,1.5,.82));x,y=pt([(r['source_xy'][0]+r['sink_xy'][0])/2,(r['source_xy'][1]+r['sink_xy'][1])/2]);out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="white" stroke="{color}"/><text x="{x:.2f}" y="{y+3:.2f}" text-anchor="middle" font-size="8">{i}</text>')
 out+=['<text x="370" y="122" font-size="14">Actual directed worst native hops (representative bit of each group)</text>','<text x="370" y="143" font-size="11">Purple: node/tree staging. Orange: ROM/weight pipeline. Blue: X/TX data. Green dashed: reset.</text>']
 for i,r in enumerate(selected,1):
  yy=170+(i-1)*27;desc=f"{i}. {r['group']}  |  {r['distance_um']:.3f} µm  |  margin +{r['margin_ps']:.3f} ps";end=f"{r['source'][0]}.{r['source'][1]} → {r['sink'][0]}.{r['sink'][1]}";out.append(f'<text x="370" y="{yy}" font-size="11">{html.escape(desc)}</text><text x="388" y="{yy+13}" font-size="9" fill="#536273">{html.escape(end)}</text>')
 out+=['<text x="370" y="635" font-size="13">Why the right-side NODE can be sensible</text>','<text x="370" y="655" font-size="11">Actual a/b/y/t_out pins are all on its W face, toward the data-stage banks.</text>','<text x="370" y="673" font-size="11">Its clock/reset pins are on E. A MY flip would reverse both data and clock faces;</text>','<text x="370" y="691" font-size="11">it needs legal-orientation, real pin, obstacle and compensated-phase admission.</text>','<rect x="368" y="713" width="900" height="94" fill="#dedede" stroke="#777"/>','<text x="385" y="738" font-size="13">Unknown hardware and routes are explicit — no invented XY or zero-area credit</text>','<text x="385" y="758" font-size="11">Residual root 84: actual 2278 bit-mapped DFFs; control/metadata/RNE/gating comb and physical home unqualified.</text>','<text x="385" y="777" font-size="11">Native outer pin ABI, all parent clock phases, unrepresented endpoints, RC/TT/FF/DRC and full programme remain open.</text>','<text x="385" y="796" font-size="11">This tile drawing does not represent the complete 956-root compute or KV/IO system.</text>',f'<text x="370" y="843" font-size="12">Known payload: {s["screened_payload_pairs"]:,} semantic LEF pairs; minimum +{s["min_margin_ps"]:.5f} ps, 0 failing groups.</text>',f'<text x="370" y="864" font-size="12">Reset: {len(b["reset"]["target_assignment"])} targets, minimum +{min(r["margin_ps"]for r in b["reset"]["target_assignment"]):.5f} ps; no residual placeholder credited.</text>',f'<text x="25" y="930" font-size="10">Candidate SHA256 {hashlib.sha256(a.candidate.read_bytes()).hexdigest()}</text>',f'<text x="25" y="948" font-size="10">Actual LEF/TT bundle SHA256 {hashlib.sha256(a.bundle.read_bytes()).hexdigest()}</text>','<text x="25" y="967" font-size="11">Arrows show actual pin-center direction, not routed tracks. Activity/cuts outside this local source scope remain unknown.</text></svg>']
 a.out.write_text('\n'.join(out)+'\n')
if __name__=='__main__':main()
