import json,gzip
from pathlib import Path
out={'scope':'Actual directed R0 A/Y plus FF INV/D wire geometry; not RC or routed extraction. Distinguishes endpoint Manhattan reach from summed materialized wire.','candidates':{}}
for mode,path,n,bitsfile in [('Nreturn9','e_collar_placement_prep.json',9,'collar_geometry_prep.json'),('MXreturn3','mx3_collar_placement_prep.json',3,'serdes_mx_return_option.json')]:
 p=json.load(open('/tmp/qcclock0336/'+path));cells={c['id']:c for c in p['cells']};raw=json.load(open('/tmp/qcclock0336/'+bitsfile))['bits'];bits=[b for b in raw if b.get('type','phy_serdes_b')=='phy_serdes_b']
 def route(a,b):
  same=(a[1]>=2322.216 and b[1]>=2322.216) if mode=='Nreturn9' else(a[1]<=66.96 and b[1]<=66.96)
  if same:return[a,[b[0],a[1]],b]
  if a[0]>=1566 and b[0]>=1566:return[a,[a[0],b[1]],b]
  native=(a[1]<2322.216 and a[0]<1566) if mode=='Nreturn9' else(a[1]>66.96 and a[0]<1566)
  return[a,[a[0],b[1]],b] if native else[a,[b[0],a[1]],b]
 rows=[]
 for b in bits:
  rev=b['bus'] in ['tx_flit','tx_v'];key=b['bus']+'['+str(b['bit'])+']';native=b['polyline_um'][0]
  for j in range(1,n+1):
   ff=cells[f'b{j}.{key}'];prev=cells.get(f'b{j-1}.{key}');src=ff['positive_data_output_pin_um'] if rev else(prev['positive_data_output_pin_um'] if prev else native);dest=(prev['positive_data_input_pin_um'] if prev else native) if rev else ff['positive_data_input_pin_um'];chain=[cells[f'{key}.h{j}.r{q}'] for q in [.01,.2,.4,.6,.8]];chain=chain[::-1] if rev else chain;cur=src;total=0;maximum=0
   for c in chain:
    pp=route(cur,c['A_xy_um']);ll=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(pp,pp[1:]));total+=ll;maximum=max(maximum,ll);cur=c['Y_xy_um']
   pp=route(cur,dest);ll=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(pp,pp[1:]));total+=ll;maximum=max(maximum,ll);internal=0 if rev and j==1 else 1.036;rows.append({'bus':b['bus'],'bit':b['bit'],'hop':j,'flow':'TXexistingFF_to_native' if rev else 'RXnative_to_outer','wire_total_um':total+internal,'longest_wire_section_um':maximum,'origin_L1_um':abs(src[0]-dest[0])+abs(src[1]-dest[1])})
 v={'hops':len(rows),'maximum_endpoint_L1_um':max(r['origin_L1_um'] for r in rows),'maximum_total_wire_um':max(r['wire_total_um'] for r in rows),'wire_totals_over405':sum(r['wire_total_um']>405 for r in rows),'max_wire_section_um':max(r['longest_wire_section_um'] for r in rows),'sections_over120':sum(r['longest_wire_section_um']>120 for r in rows),'top_wire_witnesses':sorted(rows,key=lambda z:-z['wire_total_um'])[:12],'verdict':'MATERIALIZED_WIRE_DETOUR_FAIL' if any(r['wire_total_um']>405 for r in rows) else'GEOMETRY_BOUND_ONLY'};out['candidates'][mode]=v
Path('/tmp/qcclock0336/registered_collar_wire_profile.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2)[:7000])
