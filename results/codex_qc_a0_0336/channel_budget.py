from pathlib import Path
import json,re
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336');fig,axs=plt.subplots(1,2,figsize=(9,12));rows={}
for tag,ax in zip(('nl','nk'),axs):
 fr=json.load(open(p/f'widen/{tag}_freeze_candidate.json'));kit=p/f'physical/{tag}_widen2';geo=p/'actual_nk/auto_geom.json' if tag=='nk' else kit/'geom/auto_geom.json';g=json.load(open(geo));m=g['metrics']
 boxes=[]
 for h in fr['hard_children']:
  txt=(kit/'macros'/f"{h['master']}.lef").read_text();w,hh=map(float,re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',txt).groups());x,y=h['at'];boxes.append((x,y,w,hh));ax.add_patch(Rectangle((x,y),w,hh,facecolor='#c8c8c8',edgecolor='black',linewidth=.5))
 vertical=[232.,4.32,264.,669.60];horizontal=[64.,976.86,449.,992.86]
 ax.add_patch(Rectangle((vertical[0],vertical[1]),32,vertical[3]-vertical[1],facecolor='#3b87c8',alpha=.5));ax.add_patch(Rectangle((horizontal[0],horizontal[1]),horizontal[2]-horizontal[0],16,facecolor='#3b87c8',alpha=.5))
 for c in fr['candidate_clock_corridors']:
  a,b,z,d=c['clock_reserved_rect_um'];ax.add_patch(Rectangle((a,b),z-a,d-b,facecolor='#b94b43',alpha=.85))
 tv=m['tracks_v_per_um'];th=m['tracks_h_per_um'];vd=m['channel_v_max']*9*tv;cd=m['col_v_max']*7.5*tv;hd=m['channel_h_max']*9*th
 realgap=(20.112 if tag=='nk'else 20.112);vclear=79.32 if tag=='nk'else 73.032
 # Explicitly retain equivalent demand reported in the small sliding windows;
 # budget the same demand against a continuous real corridor, no gate relaxed.
 rows[tag]=dict(scope='pre-route corridor feasibility estimate, not a routing PASS',auto_geom_verdict=g['verdict'],original_warning_windows_um=dict(channel_v=9.,col_v=7.5,channel_h=9.),actual_clear_vertical_corridor_um=vclear,actual_clear_horizontal_corridor_um=realgap,proposed_data_vertical_rect_um=vertical,proposed_data_horizontal_rect_um=horizontal,equivalent_demand_tracks=dict(channel_v=vd,col_v=cd,channel_h=hd),track_supply_per_um=dict(vertical=tv,horizontal=th),clock_reserved_equivalent_tracks=8.,ratios=dict(channel_v=vd/(32*tv-8),col_v=cd/(32*tv-8),channel_h=hd/(16*th-8)),r2r_endpoint_max_um=m['r2r_max'],r2r_captures_gt405=m['r2r_captures_gt405'],pending=['Current die-over-core FT/obs budget owner check','Clock subtree model and physical clock placement','Actual >=50iter GRT and routed-geometry reach/STA; estimates never freeze core/die'])
 ax.set_xlim(0,fr['outline_um'][0]);ax.set_ylim(0,fr['outline_um'][1]);ax.set_aspect('equal');ax.set_title(tag.upper()+': explicit data/clock corridors\nblue=data routing; red=clock micro-islands');ax.set_xlabel('um');ax.set_ylabel('um')
fig.tight_layout();fig.savefig(p/'widen/corridor_budget.png',dpi=170);(p/'widen/corridor_budget.json').write_text(json.dumps(dict(basis='Actual hardmacro boxes + unchanged AUTO-GEOM equivalent demand; native layer pitches and existing routing derate; no measured timing',clock_layers=dict(vertical_spine='M7',horizontal_branches='M6',entry='M5',existing_parent_max_clock='M7'),dies=rows),indent=1)+'\n');print(json.dumps({k:v['ratios'] for k,v in rows.items()}))
