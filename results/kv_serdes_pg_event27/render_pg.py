import json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent;W=O.parents[1];sys.path.insert(0,str(W/'tools/die_plan'));import schema as S,gen_phys as GP
P=S.Plan(json.load(open(W/'physical/die_plan/qwen_kvsys/die_plan.json')),W/'physical/die_plan/qwen_kvsys/die_plan.json');rr=json.load(open(O/'phy_footprints.json'));fig,axs=plt.subplots(1,2,figsize=(15,6));doms=[]
for ax,r in zip(axs,rr):
 tn=r['partition_type'];x,y=r['origin_type_um'];w,h=r['outline_um'];ax.add_patch(plt.Rectangle((0,0),1900.8,1036.8,fill=False,ec='black'));ax.add_patch(plt.Rectangle((x,y),w,h,fc='#dde5ea',ec='navy'));ax.add_patch(plt.Rectangle((1883.52,54),17.28,982.8,fc='#f6edd2',alpha=.9))
 for port,cx,cy in GP.clock_pins(P,tn):ax.plot(cx,cy,'bo',ms=4)
 for name,(px,py) in r['signal_pins'].items():ax.plot(x+px,y+py,'.',color='#23964b',ms=1)
 for b,i,d,bx,by,f in GP.type_pins(P,tn):ax.plot(bx,by,'.',color='#c44',ms=1)
 # Show the planned local clock/reset corridor; no new die clock ports.
 for py in (172.8,432,648,864):ax.add_patch(plt.Rectangle((1887.84,py-4.32),8.64,8.64,fill=False,ec='purple'))
 ax.set_aspect('equal');ax.set_xlim(-30,1930);ax.set_ylim(-30,1060);ax.set_title(f'{r["part"]}: {r["parameter_W"]}-bit modeled x6 PHY\n1.813985mm², E data pins; bottom clock entries retained',fontsize=9);ax.text(500,550,'PHY VDD/VSS M6 contacts\nVDD maps to dedicated VDDPHY supply',fontsize=9);ax.text(400,5,'54um digital clock/PG strip',fontsize=8)
 p=r['part'];a=P.to_die(p,(x,y));b=P.to_die(p,(x+w,y+h));rect=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])];io='io_'+p+'_serdes';grid=[]
 for row in P.die['pg']['grid']:q=dict(row);q['nets']=['VDDPHY_'+p[4:],'VSS'];grid.append(q)
 doms.append(dict(name='phy_'+p+'_serdes',nets=['VDDPHY_'+p[4:],'VSS'],io=[io],rect_um=rect,grid=grid,bumps=dict(lattice_io_ref=io,site_pitch_um=45.0,pg_share=.45,effective_pg_pitch_um=67.082,source='existing infra_pg.pg_bumps; keep original IO-window lattice points, assign only inside leaf to VDDPHY'),power_w=4.37,leaf=dict(instance='serdes',logical_module=r['logical_module'],physical_master=r['physical_master'],parameter_W=r['parameter_W'],origin_type_um=r['origin_type_um'],outline_um=r['outline_um'],pg_access_layer='M6'),status='PENDING physical-synth master alias + macro placement/PG import; no full-IO domain relabel'))
fig.savefig(O/'phy_floorplan.png',dpi=140,bbox_inches='tight');(O/'pg_domains_candidate.json').write_text(json.dumps(dict(source='KV R26 + pending event; additions to existing UCIe domain only',domains=doms,scope='candidate input, no source plan PG mutation before truthful leaf integration'),indent=1)+'\n');print(json.dumps([dict(part=r['io'],rect=r['rect_um']) for r in doms]))
