#!/usr/bin/env python3
"""Convert a proved full-bind WP profile to exact BG request receiver targets."""
import argparse,json
p=argparse.ArgumentParser(description=__doc__);p.add_argument('groups');p.add_argument('previous');p.add_argument('depth_map');p.add_argument('ages');p.add_argument('--out',required=True);a=p.parse_args()
g=json.load(open(a.groups));d=json.load(open(a.previous));paths={x['key']:x for x in json.load(open(a.depth_map))['schedule_paths']};ages=json.load(open(a.ages));actual={}
for group in g['landing']:
 for m in group['members']:actual[(group['sink'],m['sink_port'],m['source'],m['asbuilt_stages'])]=m
added=0;total=0;targets={}
for m in d['members']:
 v=m['sink'];path=paths['pvrq_'+v.removeprefix('vport_')];live=actual[(v,m['sink_port'],m['source'],m['asbuilt'])]
 target=int(live['asbuilt_stages'])+int(ages['vport'][v]['WP'])-int(path['asbuilt']);bound=int(live['bound_stages']);width=sum(hi-lo+1 for lo,hi in m['sink_bits'])
 if target<live['landed_stages'] or target<bound:raise ValueError(f'negative final request padding: {v}')
 added+=width*(target-live['landed_stages']);total+=width*(target-bound);m.update(bound=bound,pad=target-bound,landed=target,WP_target=ages['vport'][v]['WP'],WP_source_asbuilt=path['asbuilt']);targets[v]=target
assert added==1695,added
d['kind']='pv_landed_request_final_profile';d['note']=__doc__+' Actual compiled image, receiver footprints and full path programme remain gates.';d['summary']=dict(members=len(d['members']),additional_ff_vs_coherent_b41=added,logical_member_pad_ff_conservative=total,BG_target_by_port=targets,RL=ages['pv']['RL'],FIRST_INPUT_AGE=ages['pv']['FIRST_INPUT_AGE'])
with open(a.out,'w') as f:json.dump(d,f,indent=1);f.write('\n')
print(d['summary'])
