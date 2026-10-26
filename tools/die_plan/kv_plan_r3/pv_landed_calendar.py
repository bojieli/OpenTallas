#!/usr/bin/env python3
"""B39 native-proven PV result calendar; preserve source age and target separately.

Only the proved T21->T24 and pair1 result-header transports may exceed their
actual source ages. Every other unexpected faster source fails closed.
"""
import argparse,json,re,collections
p=argparse.ArgumentParser(description=__doc__);p.add_argument('groups');p.add_argument('membership');p.add_argument('--out',required=True);a=p.parse_args()
g=json.load(open(a.groups));old=json.load(open(a.membership));actual={}
def key(m):return (m['sink'],m['sink_port'],tuple(map(tuple,m['sink_bits'])),m['source'])
for group in g['landing']:
 for member in group['members']:
  m={**member,**{k:group[k] for k in ['sink','sink_part','src_part']}}
  k=key(m);assert k not in actual,k;actual[k]=m
rows=[];exceptions=collections.Counter();flops=0
for o in old['members']:
 m=actual[key(o)];src=int(m['asbuilt_stages']);bound=int(m['bound_stages']);target=src;kind='source_calendar'
 if re.fullmatch(r'pvw_[01]__u_T[01]Q[01]_24_r0',m['sink']) and (m['sink_port']=='a' or (m['sink_port']=='y' and m['sink_bits']==[[257,257]])):
  assert src==2 and bound==5,m;target=5;kind='T21_to_T24_data_3'
 elif m['sink']=='pvw_1__u_RH_r0' and m['sink_port'] in ['a0','a1','a0v','a1v','a0t','a1t']:
  assert src==2 and bound==5,m;target=5;kind='pair1_header_T0_3'
 elif m['sink']=='pvw_1__u_RH_r0' and m['sink_port'] in ['b0','b1']:
  assert src==4 and bound==5,m;target=5;kind='pair1_header_T1_1'
 if bound>target:raise ValueError(f'unproved PV transport exceeds calendar: {m}')
 bits=m['sink_bits'];width=sum(hi-lo+1 for lo,hi in bits);pad=target-bound;flops+=width*pad;exceptions[kind]+=1
 rows.append(dict(id=f"{m['sink']}.{m['sink_port']}"+''.join(f'[{lo}:{hi}]' for lo,hi in bits)+f"<-{m['source']}@{src}",sink=m['sink'],sink_part=m['sink_part'],src_part=m['src_part'],sink_port=m['sink_port'],sink_bits=bits,source=m['source'],asbuilt=src,bound=bound,pad=pad,landed=target,lane=m['lane'],calendar_rule=kind))
assert len(rows)==944,len(rows)
d=dict(schema=old['schema'],die='qwen_kvsys',kind='pv_landed_result_calendar',note='Opt-in candidate: native actual two-pair/two-half/32-column proof + data/select mutants; output +6 cycles, no later PV_START. Physical emitted bank allocation and new link image remain gates.',merge_rule=old['merge_rule'],summary=dict(members=len(rows),logical_member_pad_ff_conservative=flops,rules=dict(exceptions),output_cycles_added=6),members=rows)
with open(a.out,'w') as f:json.dump(d,f,indent=1);f.write('\n')
print(d['summary'])
