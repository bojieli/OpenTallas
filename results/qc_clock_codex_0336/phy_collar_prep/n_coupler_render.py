import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
m=json.load(open('/tmp/qcclock0336/n_coupler_macro_repack.json'));p=json.load(open('/tmp/qcclock0336/n_seam_repeaters_prep.json'));t=json.load(open('/tmp/qcclock0336/n_s_terminal_models.json'));fig,ax=plt.subplots(1,3,figsize=(14,7))
for a,typ in zip(ax[:2],['coll_s','coll_n']):
 v=m['types'][typ];w,h=v['outline_candidate_um'];a.add_patch(Rectangle((0,0),w,h,fill=False,ec='black'));r=v['coupler_macrofree_rect_um'];a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='lightgreen',alpha=.5))
 for z in v['native_memories']:
  x,y=z['candidate_origin_um'];ww,hh=z['outline_um'];a.add_patch(Rectangle((x,y),ww,hh,fc='#ccc',ec='black',lw=.6));a.text(x+4,y+hh/2,z['logical_face'],fontsize=9)
 for z in v['existing_CA_bands_rebased']:
  x,y,x1,y1=z['rect_um'];a.add_patch(Rectangle((x,y),x1-x,y1-y,fc='cyan',alpha=.8))
 if typ=='coll_s':
  rr=p['cells'];a.scatter([c['origin_um'][0]-777.6 for c in rr],[c['origin_um'][1] for c in rr],s=.7,c='purple');a.add_patch(Rectangle((4.32,0),254.592,17.28,fc='blue',alpha=.3))
 else:
  rr=t['S_cells'].values();a.scatter([c['origin_um'][0]-777.6 for c in rr],[h+c['origin_um'][1] for c in rr],s=.7,c='purple');a.add_patch(Rectangle((4.32,h-17.28),254.592,17.28,fc='blue',alpha=.3))
 a.set_aspect('equal');a.set_xlim(-40,810);a.set_ylim(-20,h+20);a.set_title(f'{typ}: {w} x {h}um\n12/6 nativeSRAM only + existingCA bands');a.set_xlabel('local x(um)')
a=ax[2];a.add_patch(Rectangle((0,0),286,86.4,fc='lightgreen',alpha=.4));a.add_patch(Rectangle((4.32,0),254.592,17.28,fc='blue',alpha=.3));a.add_patch(Rectangle((-40,0),40,86.4,fc='orange',alpha=.3));a.scatter([c['origin_um'][0]-777.6 for c in p['cells']],[c['origin_um'][1] for c in p['cells']],c='purple',s=3);a.plot([753.48-777.6,810.792-777.6],[-.096]*2,'r-',lw=4);a.set_xlim(-40,300);a.set_ylim(-4,90);a.set_aspect('equal');a.set_title('4,562 real dataBUF24 per normal PHY\nblue: existingFF candidate reserve; orange:no logic');a.set_xlabel('relative coll_s x(um)')
fig.suptitle('Normal N/S no-added-FF coupler PREP; macro/CA witness only — codec/clock/PG/FT/root HOLD');fig.tight_layout();fig.savefig('/tmp/qcclock0336/n_s_coupler_prep.png',dpi=160)
