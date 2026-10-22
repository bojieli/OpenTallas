#!/usr/bin/env python3
"""Render and bind the exact diagnostic candidate; no timing inference."""
import json,hashlib,collections
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Patch

load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
D=load('input.json');O=load('columns_root_corrected.json');G=load('source_graph.json')
C=load('column_geometry.json');R=load('root_sites.json');S=load('source_geometry.json')
assert G['geometry_sha256']==sha('column_geometry.json')
assert O['root_keepout_sha256']==sha('root_sites.json')
assert O['placed_columns']==128 and len(O['individual_source_rectangles'])==6144
assert len(R['sites'])==45 and not O['remaining_root_intersections'] and not O['repair_failures']
kinds=collections.Counter(r['kind'] for r in O['individual_source_rectangles'].values())
assert kinds['pair']==512 and kinds['SRAM']==1536
assert len(G['columns'])==128 and G['clock_bits_active_per_quarter']==143
assert all(len(v)==143 for v in G['active_clock_names'].values())
P={n:dict(a) for n,a in D['placement'].items() if n not in O['automatic_relays_requiring_regeneration'] and n!='hc_eng'}
P.update(O['existing_bodies_moved'])
W,H=D['die_um'];fig,ax=plt.subplots(figsize=(13,17))
for n,a in P.items():
 color='#d4d9df'
 if n.startswith('hb_idx__s_'):color='#f4c77a'
 if n in O['existing_bodies_moved']:color='#70bad1'
 ax.add_patch(Rectangle((a['x'],a['y']),a['w'],a['h'],facecolor=color,edgecolor='#84909b',linewidth=.18))
for b in S['last_step_postcut_bands']:
 x,y,w,h=(b['start_um'],0,b['width_um'],H) if b['axis']=='x' else (0,b['start_um'],W,b['width_um'])
 ax.add_patch(Rectangle((x,y),w,h,facecolor='#bfa27c',alpha=.27,linewidth=0))
colors={'pair':'#326dba','SRAM':'#3e9e74','FF_band':'#8a63b5','control_reserve':'#b591be'}
for n,a in O['placed_service_envelopes'].items():
 if n=='hc_eng':
  ax.add_patch(Rectangle((a['x'],a['y']),a['w'],a['h'],facecolor='#e36564',edgecolor='#8b3634',linewidth=.7))
 else:ax.add_patch(Rectangle((a['x'],a['y']),a['w'],a['h'],fill=False,edgecolor='#aeb5bf',linewidth=.22,linestyle=':'))
for r in O['individual_source_rectangles'].values():
 ax.add_patch(Rectangle((r['x_um'],r['y_um']),r['width_um'],r['height_um'],facecolor=colors[r['kind']],edgecolor='none'))
for s in R['sites']:
 x0,y0,x1,y1=s['keepout'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='#d62728',linewidth=.8))
for n,a in O['existing_bodies_moved'].items():
 old=D['placement'][n]
 ax.annotate('',xy=(a['x']+a['w']/2,a['y']+a['h']/2),xytext=(old['x']+old['w']/2,old['y']+old['h']/2),arrowprops=dict(arrowstyle='->',lw=.25,color='#305769',alpha=.5))
ax.set(xlim=(0,W),ylim=(0,H),xlabel='Die x (µm)',ylabel='Die y (µm)',aspect='equal')
ax.set_title('Diagnostic full-count reticle composition\n128 Col8 columns + enlarged HC root; routed timing and rate remain open',fontsize=13)
legend=[Patch(facecolor='#d4d9df',label='Existing bodies retained'),Patch(facecolor='#70bad1',label=f"{len(O['existing_bodies_moved'])} smaller bodies relocated"),Patch(facecolor='#f4c77a',label='4 conservative residual-control reserves'),Patch(facecolor='#326dba',label='512 exact pair bodies (R3 stand-ins)'),Patch(facecolor='#3e9e74',label='1,536 raw wide-seam SRAMs'),Patch(facecolor='#8a63b5',label='FF/control bands'),Patch(facecolor='#e36564',label='Enlarged HC root diagnostic body'),Patch(facecolor='none',edgecolor='#d62728',label='45 source clock-root keepouts')]
ax.legend(handles=legend,loc='upper center',bbox_to_anchor=(.5,-.045),ncol=2,fontsize=9)
fig.text(.5,.018,'143 active clock inputs per quarter • source-bound geometry • no outline shrink • no routed-age or rate credit',ha='center',fontsize=9)
fig.subplots_adjust(bottom=.13,top=.95)
fig.savefig('columns_root_corrected.png',dpi=160)
plt.close(fig)
transforms={n:dict(before=D['placement'][n],after=a,delta_um=[a['x']-D['placement'][n]['x'],a['y']-D['placement'][n]['y']]) for n,a in O['existing_bodies_moved'].items()}
check=dict(status='DIAGNOSTIC_BODY_MODEL_REVIEW_PACKET_NOT_PHYSICAL_SIGNOFF',
 inputs={p:sha(p) for p in ['input.json','source_geometry.json','column_geometry.json','source_graph.json','root_sites.json','columns_root_corrected.json','residual_census.json','residual_census_current.json']},
 die_um=D['die_um'],source_manifest_sha256=D['manifest_sha256'],
 columns=128,pairs=512,wide_seam_srams=1536,individual_rectangles=6144,
 active_clock_inputs_per_quarter=143,active_clock_inputs_all_quarters=572,
 root_keepouts=45,new_or_moved_body_root_intersections=[],
 residual_control_reserves=O['original_quarter_reserves'],
 transformed_insertion_bands=S['last_step_postcut_bands'],
 original_smaller_body_moves=32,root_correction_additional_body_moves=len(transforms)-32,
 existing_body_move_transforms=transforms,column_root_repair_transforms=O['named_root_repair_transforms'],
 local_seam_reach_bound_um=C['reach_audit']['max_band_corner_um'],
 source_graph_commit='5d3de3d67',current_col8_source=G['source_commit'],
 baseline_root_within_old_body_cases=R.get('inside_blocks'),
 required_next_actions=[
 'Independent ROOT review of this exact image and source-bound checklist.',
 'Build actual hierarchical Col8 source split, all real clock/reset terminals and relay routes from these placements.',
 'Resolve inherited root-within-body cases using actual source clock-entry ports and legal carved-channel/root construction; 45 root sites are not a capacity proof.',
 'Regenerate all automatic relays displaced or invalidated by new bodies and 36 old-body transforms.',
 'Build actual delivery/return hops and calendar padding for long column/chunk routes; +23 is only the proved local seam cost.',
 'Replace R3 and HC diagnostic stand-ins with exact CLOSED views and qualify composed clock/reset/timing.',
 'Replace conservative residual controls with actual source-bound native footprints; current source metadata SRAMs stay within those explicit reserves.',
 'Re-compose future DMA converter/gather grants when corrected physical source geometry is available; current base manifest lacks those new paths.'],
 no_claims=['Global routing capacity','Composed clock or reset closure','Whole-token functional qualification','Routed ages','Throughput credit'])
Path('review_checklist.json').write_text(json.dumps(check,indent=1)+'\n')
Path('REVIEW_CHECKLIST.md').write_text('Diagnostic body model for independent ROOT review\n\nAll 128 columns, 512 pair bodies, 1,536 wide-seam SRAMs and 6,144 individual rectangles are explicit. All four residual-control reserves remain. The corrected candidate preserves all 45 source root keepouts; no new or moved body intersects them. It retains 143 active clock inputs per quarter.\n\nThe first body-only fit moved 32 smaller bodies. The three named clock-root corrections required four additional old-body moves, for 36 total. Exact before/after transforms and input hashes are in review_checklist.json.\n\nRequired next actions:\n\n'+''.join('- '+s+'\n' for s in check['required_next_actions'])+'\nThe rendered image and packing alone supply no routed timing, global routing capacity, full functional or rate qualification.\n')
print(json.dumps({k:check[k] for k in ['status','columns','pairs','wide_seam_srams','root_keepouts']}))
