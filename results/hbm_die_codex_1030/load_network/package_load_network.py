import json,collections,shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
src=Path('/srv/opentallas-scratch/claude/codex-hbm-1030');out=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-1030/results/hbm_die_codex_1030/load_network');out.mkdir(parents=True,exist_ok=True)
for name in ['network_centres_fine.json','lots_wide.json','central_conflicts.json','mapped_area_budget.json','mapped_stat.txt','map.ys']:
 shutil.copy(src/'load_lot'/name,out/name)
for name in ['load_network_centres_fine.py','map_load_area.py','allocate_load_lots.py']:
 shutil.copy(src/name,out/name)
d=json.load(open(out/'network_centres_fine.json'));lots=json.load(open(out/'lots_wide.json'));b=json.load(open(out/'central_conflicts.json'))
summary={}
for f in sorted(set(r['family'] for r in d['links'])):
 rr=[r for r in d['links'] if r['family']==f];ns=[r['result']['relay_groups']for r in rr if 'relay_groups'in r['result']]
 summary[f]=dict(links=len(rr),verdicts=dict(collections.Counter(r['result']['verdict']for r in rr)),min_relay_groups=min(ns),max_relay_groups=max(ns),independent_relay_FFs=sum(r['width_bits']*r['result'].get('relay_groups',0)for r in rr))
model=dict(scope='Unadopted S2-only network alternatives. Does not close STACK0, native face-shell bridges, physical HBM timing, ACK return or whole-programme calendar.',widths=dict(PC_fill=280,per_leaf_two_PC_fill=560,leaf_command=63,BACK_export=341,normalized_packet=281,per_hub_ACK_status=48),link_summary=summary,independent_total_FFs=sum(x['independent_relay_FFs']for x in summary.values()),model_A=dict(lots=16,lot_um=[302.4,151.2],local_command_padding=31,fill_padding=13,packet_to_quartet_padding=13,regional_merge=1,quartet_to_local_bank_padding=24,local_bank_source_mux=1,local_data_network_M=39,conditional_step_to_local_ACK_without_return=82,formula='12+C+M+A =82+A for C31,M39. Existing body+nativebank ACK basis; physical outer wrappers and actual return A remain additional.',not_solved=['Simultaneous per-bit FIRM and corridor/clock/PG capacity','New crosshub 281-bit forward /48-bit return transports; existing HCOL/VMS lanes fully occupied','Bank-owner pipeline and real DMA slot6 reservations at dated arrival','RAW loading/mux timing and fault/UE propagation','Sharing delivery trunks or separate transport hard cuts to keep parent soft cells <=400k']),model_B=dict(lots=16,root_cluster_bounds_um=[216,6480,1522.8,7182],inter_lot_channels_um=32.4,fill_bits_each_hub_to_root=4480,command_export_bits_each_hub=341,existing_explicit_FF_collisions=b['blocked_explicit_FF_sites'],not_solved=['Nine affected old/new FT slots require same-count resiting or explicit R8 cycle reprice','Actual per-bit fill transport to root and dated delivery back to native banks','Full clock/reset/START/PG and parent capacity','Current HBM source only S2; no S0 provider capacity credit']),clock='Logical PLLstream0=833ps; existing offdie Gray CDC3+stream1 preserved. Physical F4 implementation and physical-ns profile remain separately qualified.',ACK_ownership='Per physical bank retain RAW/LOAD_NW/LOAD_NE source identity through external DQ capture→ACK4; gate done/FAULT/UE by owner and reconstruct all32 real banks. ACK alone cannot prove write because invalid writes also pulse done.',admission='Neither model approved for route. Fine-grid paths are individual point/centre solutions and conditional on future <=40um-L1 group allocation. No coexistence or <=405 per-bit claim.')
(out/'network_models.json').write_text(json.dumps(model,indent=2)+'\n')
fig,axes=plt.subplots(1,3,figsize=(18,7),layout='constrained')
colors={'fill_tap_extension':'#c06b00','LOADcmd':'#3581b8','packet_to_quartet':'#27854a','local_bank_delivery':'#9264a0'}
base=json.load(open(src/'load_lot'/'base_plan.json'))
for ax,part in zip(axes[:2],['NW_hub','NE_hub']):
 pp=next(p for p in base['partitions'] if p['name']==part); typ=base['partition_types'][pp['type']]
 for h in typ['hard_cores']:
  x,y=h['origin_um'];w,hh=h['outline_um'];ax.add_patch(Rectangle((x,y),w,hh,fc='#dfdfdf',ec='#999999',lw=.4,zorder=-1))
 for r in d['links']:
  if r['part']!=part:continue
  p=[r['a_um']]+r['result'].get('points_um',[])+[r['b_um']]
  ax.plot([x[0]for x in p],[x[1]for x in p],color=colors[r['family']],alpha=.17,lw=.7)
 for p in lots['proposals']:
  if p['part']!=part:continue
  x,y=p['origin_um'];ax.add_patch(Rectangle((x,y),302.4,151.2,fc='#e0f3e7',ec='black'));ax.text(x+150,y+75,p['raw'].split('_')[-1],fontsize=7,ha='center')
 ax.set(xlim=(0,8216.64),ylim=(0,4320),aspect='equal',title=f'A: {part}, distributed LOAD lots',xlabel='local x (um)',ylabel='local y (um)')
 ax.text(.02,.98,'Individual centre paths; not simultaneous FIRM\nOrange fill560 / blue cmd63 / green packet281\nPurple delivery281; crosshub+ACK paths OPEN',transform=ax.transAxes,va='top',fontsize=8,bbox={'fc':'white','alpha':.9})
ax=axes[2]
for i,(a,bx,c,e)in enumerate(b['root_lot_rectangles']):ax.add_patch(Rectangle((a,bx),c-a,e-bx,fc='#f6c9c9',ec='black'));ax.text((a+c)/2,(bx+e)/2,str(i),ha='center',fontsize=8)
ax.set(xlim=(100,1650),ylim=(6380,7280),aspect='equal',title='B: root cluster (NOT admitted)',xlabel='root x (um)',ylabel='root y (um)');ax.text(.02,.98,'22,931 existing FF-site collisions\nNine FT slots need resiting/reprice\n4,480 fill bits per hub reach root',transform=ax.transAxes,va='top',fontsize=9,bbox={'fc':'white','alpha':.9})
fig.suptitle('New S2 LOAD physical network alternatives — plan diagnostic, no route approval')
fig.savefig(out/'network_models.png',dpi=140)
