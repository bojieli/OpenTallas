import json,sys,types
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'tools/die_plan');import gen_phys,schema
b=Path('results/codex_head_collect_1030/serdes_reshape');p=json.load(open('/tmp/head_collect_review/source25r.json'));P=types.SimpleNamespace(layer_budget=p['die']['layer_budget'],layers={x['name']:x for x in p.get('layers',schema.ASAP7_LAYERS)})
rows=[]
for name,old in [('pma_rck',[1106.04,149.904]),('pma_tck',[1442.88,149.904])]:
 snap=gen_phys._snap_tap(P,old[0],149.728);new=[round(snap[0]+2*P.layers['M7']['pitch_um'],6),snap[1]]
 assert all(not schema.pg_blocked(ln,c-o) for ln,c in [('M7',new[0]),('M6',new[1])] for o in (0,gen_phys.CORE_MARGIN_UM))
 assert new[1]+.096 <150-.128
 rows.append(dict(name=name,dir='in' if name=='pma_rck' else 'out',layer='M7',old_pg_blocked_xy_um=old,minimum_snap_tap_xy_um=list(snap),proposed_xy_um=new,pin_box_um=[new[0]-.096,new[1]-.096,new[0]+.096,new[1]+.096],two_phase_center_pg_guard_clear=True,M7_source_nominal_pair_edge_gap_um=.176,M6_source_nominal_pair_edge_gap_um=.256,PHY_region_edge_gap_um=.176,extra_M7_tracks_over_minimum=2,period_ps=None,source=None,adopted=False))
x=dict(status='PG_SOURCE_GEOMETRY_PREP_ONLY_PERIOD_AND_PHYSICAL_READBACK_HELD',PDN_source='gen_phys.py partition_pdngen M7 width.288 spacing.096 pitch8.64 offset4.128; M6 width.288 spacing.096 pitch4.32 offset1.968; phase includes CORE_MARGIN4.32. Conservative schema PART_PG_BANDS checked at origins0 and4.32.',pin_size_um=[.192,.192],M7_track_pitch_um=.064,M7_track_offset_um=.032,M6_track_pitch_um=.064,M6_track_offset_um=.032,pins=rows,unchanged='All945 exact child pins, childclock[138.36,69.12], macrooutline/neighbours unchanged. No PHY clock period or qualification supplied.')
(b/'pad_pg_prep.json').write_text(json.dumps(x,indent=1)+'\n')
fig,axes=plt.subplots(1,2,figsize=(11,5))
for ax,row in zip(axes,rows):
 xn=row['proposed_xy_um'][0];xc=round(xn/8.64)*8.64;yc=149.04
 ax.axvspan(xc-.48,xc+.48,color='#ffb3b3',alpha=.3,label='M7 PG access guard')
 for c in [xc-.192,xc+.192]:ax.axvspan(c-.144,c+.144,color='#b73434',alpha=.65)
 ax.axhspan(yc-.48,yc+.48,color='#e7b3ff',alpha=.25)
 for c in [yc-.192,yc+.192]:ax.axhspan(c-.144,c+.144,color='#713b8e',alpha=.45)
 ax.axhspan(150,151,color='.8');ax.axhline(150,color='.4',ls='--');ax.text(xc+.9,150.05,'PHY reserved starts y150',ha='center',fontsize=8)
 a,c,d,e=row['pin_box_um'];ax.add_patch(Rectangle((a,c),d-a,e-c,fill=False,lw=2,edgecolor='#006a4e'));ax.plot(*row['old_pg_blocked_xy_um'],'rx',ms=10,label='old proposal FAIL');ax.text(xn+.15,row['proposed_xy_um'][1],f'NEW {xn:.3f}, {row["proposed_xy_um"][1]:.3f}',fontsize=8)
 ax.set_xlim(xc-.7,xc+1.6);ax.set_ylim(148.2,150.3);ax.set_aspect('equal');ax.set_title(row['name']+' M7 full.192-square pad PREP');ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8)
fig.suptitle('Revised PG-clear track sites — source PDN geometry only; period and actual PG readback HELD');fig.tight_layout();fig.savefig(b/'pad_pg_preview.png',dpi=140)
for row in rows:print(row['name'],row['proposed_xy_um'])
