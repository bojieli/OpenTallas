#!/usr/bin/env python3
"""Rank exact functional pin legs, source fanout, and static-age lower bounds.
500um is a geometric screening limit only; related-clock stage ages need actual STA/calendar proof.
"""
import argparse,collections,gzip,json,math,pathlib

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);ap.add_argument('--reach',default='reach_holes.json');a=ap.parse_args();r=a.root;inv=json.load(open(r/'inventory.json'));rep=json.load(open(r/a.reach))['reports'][0];leaf=inv['leaves'];roots=json.load(open(r/'clock_root_join.json'));domains=collections.defaultdict(set)
 for q in roots['roots']:
  for ep in q['hard_leaf_pins']:domains[ep[0]].add('serial'if q['category'].endswith('_s')else'stream')
 groups={};fan=collections.Counter();cuts={name:dict(unique_source_nets=set(),bit_hops=0)for name in ['x1987.2','x3952.8','y2462.4']}
 with gzip.open(r/rep['all_bits_file'],'rt')as f:
  for line in f:
   b=json.loads(line);d,c=b['source'],b['sink'];sd='/'.join(sorted(domains[d[0]]));cd='/'.join(sorted(domains[c[0]]));key=(leaf[d[0]]['master'],d[1],leaf[c[0]]['master'],c[1],sd,cd)
   if key not in groups:groups[key]=dict(bit_hops=0,over500_bit_hops=0,max_L1_um=0,sum_L1_um=0,source_instances=set(),sink_instances=set(),source_bits=set(),worst=None,geometric_extra_stage_histogram=collections.Counter())
   x=groups[key];L=b['L1_um'];extra=max(0,math.ceil((L-1e-6)/500)-1);x['bit_hops']+=1;x['over500_bit_hops']+=L>500;x['sum_L1_um']+=L;x['source_instances'].add(d[0]);x['sink_instances'].add(c[0]);x['source_bits'].add(tuple(d[:3]));x['geometric_extra_stage_histogram'][extra]+=1
   if L>x['max_L1_um']:x['max_L1_um']=L;x['worst']=b
   fan[tuple(d[:3])]+=1
   for name,q in cuts.items():
    axis=0 if name[0]=='x'else 1;at=float(name[1:]);A,B=b['source_xy_um'][axis],b['sink_xy_um'][axis]
    if min(A,B)<at<max(A,B):q['bit_hops']+=1;q['unique_source_nets'].add(tuple(d[:3]))
 rows=[]
 for key,v in groups.items():
  v['unique_source_bit_width']=len(v.pop('source_bits'));v['source_instance_count']=len(v.pop('source_instances'));v['sink_instance_count']=len(v.pop('sink_instances'));v['uniform_geometric_extra_stages_at_500um']=max(v['geometric_extra_stage_histogram']);v['source_master'],v['source_port'],v['sink_master'],v['sink_port'],v['source_domain'],v['sink_domain']=key;v['cross_clock_contract_required']=key[-2]!=key[-1];rows.append(v)
 rows.sort(key=lambda x:(-x['over500_bit_hops'],-x['max_L1_um']));rec=dict(scope='NATIVE_CANDIDATE_READ_PIPE4_CAP_PIPE2_NOT_GENERATOR_ADOPTED',source_commit=inv['source_commit'],placement_option=rep['option'],outline_um=rep['outline_um'],stage_rule='ceil(actual_pin_L1/500um)-1 lower bound only. Requires honest pipeline RTL, uniform age for each compiler interface, related-clock phase STA and measured end-to-end token ledger; no registers/cycles added here.',ranked_boundaries=rows,largest_source_pin_fanouts=[dict(source=list(k),source_path=leaf[k[0]]['path'],source_master=leaf[k[0]]['master'],consumer_pin_count=n)for k,n in fan.most_common(64)],candidate_coordinate_cuts={name:dict(bit_hops=v['bit_hops'],unique_source_bit_nets=len(v['unique_source_nets']))for name,v in cuts.items()},cut_limit='Counts only exactly joined functional hardleaf nets crossing infinite coordinate half-planes. Parentlogic/external/clock/reset/PG omitted; no finite corridor capacity or <=0.60 qualification.')
 (r/'boundary_rank.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps([{k:x[k]for k in ['source_master','source_port','sink_master','sink_port','source_domain','sink_domain','bit_hops','over500_bit_hops','max_L1_um','uniform_geometric_extra_stages_at_500um']}for x in rows[:15]],indent=1))
if __name__=='__main__':main()
