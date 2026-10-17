#!/usr/bin/env python3
"""Source-derived coherent CDC/capture groups and physical-slice read ownership.
All interfaces are measured at their real pins; no parent age/clock adoption.
"""
import argparse,collections,gzip,json,pathlib,re

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();r=a.root;iv=json.load(open(r/'inventory.json'));ls=iv['leaves'];pins=json.load(gzip.open(r/'master_pins.json.gz','rt'));groups=[];read_dependencies=collections.defaultdict(collections.Counter);fsr_dependencies=collections.defaultdict(collections.Counter)
 for lane in range(16):
  ids=[i for i,x in enumerate(ls)if x['path'].startswith(f'dut.u_cap.lane[{lane}].')];by={ls[i]['master']:i for i in ids};cap,s,t=[by[m]for m in ['dsfd_vm_static_cap_leaf','ot_s81_vm_x34_s','ot_s81_vm_x34_t']];groups.append(dict(name='cap_lane'+str(lane),kind='capture_plus_related_CDC_halves',positions={str(cap):[0,86.4],str(s):[194.4,0],str(t):[259.2,0]},outline_um=[345.6,345.6],internal_bits=0,over500_bits=0,max_L1_um=0,interfaces={}))
 parents=collections.defaultdict(list)
 for i,x in enumerate(ls):
  if x['master'].startswith(('ot_s81_vm_x34_','ot_s81_vm_x43_'))and'u_cap.lane['not in x['path']:parents[x['path'].rsplit('.',1)[0]].append(i)
 for path,ids in parents.items():
  assert len(ids)==2;writer=next(i for i in ids if ls[i]['master']in ['ot_s81_vm_x34_s','ot_s81_vm_x43_t']);reader=next(i for i in ids if i!=writer);W=ls[writer]['outline_um'][0];groups.append(dict(name=path,kind='related_CDC_halves',positions={str(writer):[0,0],str(reader):[W+21.6,0]},outline_um=[W+21.6+ls[reader]['outline_um'][0],max(ls[i]['outline_um'][1]for i in ids)],internal_bits=0,over500_bits=0,max_L1_um=0,interfaces={}))
 member={int(k):g for g in groups for k in g['positions']}
 def xy(ep,g):
  i,p,b,d=ep;name=p if ls[i]['ports'][p]['bits']==1 else f'{p}[{b}]';x=pins[ls[i]['kit']]['pins'][name];pos=g['positions'][str(i)];return [x[k]+pos[k]for k in [0,1]]
 for line in gzip.open(r/'pin_producer_join.jsonl.gz','rt'):
  net=json.loads(line)
  if net['status']!='ONE_DRIVER':continue
  d=net['drivers'][0]
  if d[0]<0:continue
  for c in net['consumers']:
   if c[0]<0:continue
   if ls[c[0]]['master'].startswith('dsfd_vm_static_read_q')and c[1]=='i_data':read_dependencies[c[0]][d[0]]+=1
   if ls[d[0]]['master'].startswith('dsfd_vm_static_fsr_b')and ls[c[0]]['master']=='dsfd_vm_static_relay128_b8':fsr_dependencies[d[0]][c[0]]+=1
   if d[0]in member and member[d[0]]is member.get(c[0]):
    g=member[d[0]];A,B=xy(d,g),xy(c,g);L=sum(abs(A[k]-B[k])for k in [0,1]);g['internal_bits']+=1;g['over500_bits']+=L>500;g['max_L1_um']=max(g['max_L1_um'],L);key=ls[d[0]]['master']+'.'+d[1]+' -> '+ls[c[0]]['master']+'.'+c[1];q=g['interfaces'].setdefault(key,dict(bits=0,max_L1_um=0));q['bits']+=1;q['max_L1_um']=max(q['max_L1_um'],L)
 reads=[]
 for i,dd in read_dependencies.items():
  source_slices=sorted(set(int(re.search(r'u_mem.slice\[(\d+)\]',ls[j]['path'])[1])for j in dd));assert len(source_slices)==1
  reads.append(dict(leaf=i,path=ls[i]['path'],physical_slice=source_slices[0],i_data_bits=sum(dd.values()),actual_producers=[dict(leaf=j,path=ls[j]['path'],bits=n)for j,n in sorted(dd.items())]))
 fsr=[dict(leaf=i,path=ls[i]['path'],actual_consumers=[dict(leaf=j,path=ls[j]['path'],bits=n)for j,n in sorted(dd.items())])for i,dd in fsr_dependencies.items()]
 rec=dict(scope='NATIVE_CANDIDATE_READ_PIPE4_CAP_PIPE2_NOT_GENERATOR_ADOPTED',source_commit=iv['source_commit'],groups=groups,read_data_ownership=reads,fsr_request_groups=fsr,physical_rules=['No orientations/RTL/pin orders/edges changed; all coordinates are R0 actual-pin geometry','Each64-bit data stripe reads exactly one physical memory slice: group16data leaves withthat slice fourreturn lanes; valid8leaves still aggregate acrossallfour slices','Capture3leaf345.6square atoms keep full measuredcap->writer andwriter->reader paths local; globalcapctl andexternal832-bit inputs are outsideatoms','All incidentexternal/group-to-group nets still needfullplacement/route/cuts/clock/staticageproof; zero localover500is notclosure'])
 (r/'coherent_groups.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps(dict(groups=len(groups),internal_bits=sum(g['internal_bits']for g in groups),over500=sum(g['over500_bits']for g in groups),worst_L1_um=max(g['max_L1_um']for g in groups),cap_worst=max(g['max_L1_um']for g in groups if g['kind'].startswith('capture')),read_leaves=len(reads)),indent=1))
if __name__=='__main__':main()
