"""C25c planned host packet stages: coherent320bit source-hop leaves and real FF bays.
Usage SRC OUT HOST_ESTIMATE. This is a physical trial plan; regional CA/reset/timing are explicitly pending.
25 source-hop FF banks INCLUDE the two partition-boundary banks. Do not add them again as source latency.
"""
import json,sys,shutil,hashlib,math
from pathlib import Path
s,o,e=map(Path,sys.argv[1:]);est=json.load(open(e));p=json.load(open(s/'die_plan.json'));o.mkdir(parents=True,exist_ok=True)
N=est['station_count'];NW=len(est['legs'][0]['stations_um']);assert N==sum(len(q['stations_um']) for q in est['legs']);assert N>=2 and NW>=1
for f in s.iterdir():
 if f.is_file() and f.suffix=='.json':shutil.copy2(f,o/f.name)
shutil.copytree(s/'cores',o/'cores',dirs_exist_ok=True)
rows=[];ix=0
for leg in est['legs']:
 t=p['partition_types'][leg['type']]
 for xy in leg['stations_um']:
  name=f'u_host_boot_hop{ix:02d}';assert not any(c['inst']==name for c in t['contents'])
  origin=[round(z-8.64,4) for z in xy]
  t['contents'].append(dict(inst=name,module='ot_hnx_host_boot_hop',status='proposed',cells=320,origin_um=origin,outline_um=[17.28,17.28],note=f'C25c native boot-packet source hop{ix}/{N-1};320FF,only3validreset;clock/CA/reset timing pending'))
  t.setdefault('channels',[]).append(dict(rect_um=[*origin,round(origin[0]+17.28,4),round(origin[1]+17.28,4)],reason=f'C25c reserved320FF boot packet bank {name}; FFfill40.6%, clock/reset access retained'))
  t['clock']['taps'].append(dict(name=name+'.clk',kind='glue',xy=xy,insertion_ps=250.,insertion_ff_ps=202.5,budget_owner='C25c boot packet320FF cluster',note='PLANNED local cluster; no signed latency view, forwarded regional clock/reset pending trial'))
  # Exact lower-left320FFs,12columns; actualplan placement hook uses this bank, never nominal point only.
  sites=[[round(origin[0]+(b%12)*1.404,6),round(origin[1]+4.86+(b//12)*.27,6)] for b in range(320)]
  rows.append(dict(instance=name,type=leg['type'],centre_um=xy,outline_um=[17.28,17.28],origin_um=origin,cell_um=[1.404,.27],bit_sites_um=sites,reset_bits=[319,42,0],payload_bits_reset=False,boundary=ix in (NW-1,NW)))
  ix+=1
nw=p['partition_types']['q_hub_nw'];rt=p['partition_types']['root']
nw['buses'].append(dict(name='host_boot_o',dir='out',width=320,kind='data',leaf=f'u_host_boot_hop{NW-1:02d}.q'))
rt['buses'].append(dict(name='host_boot_i',dir='in',width=320,kind='data',leaf=f'u_host_boot_hop{NW:02d}.d'))
p['ports'].append(dict(id='HOST_BOOT_0',src=dict(part='NW_hub',bus='host_boot_o'),dst=dict(part='root',bus='host_boot_i'),width=320,kind='data',face='E',layers=['M6','M4'],window_um=est['port_window_die_um']))
p['lanes'].append(dict(id='HOST_BOOT',ports=['HOST_BOOT_0'],fixed_cycles=N-2,note=f'C25c boot-only coherent320-bit registered packet:{N}source-hop banks including boundary{NW-1}/{NW} ={N-2}interior+2boundary; source emit{N}/consumer{N+1}; regionalCA K and exact bind reconciliation still pending'))
p['latency']['lanes']['HOST_BOOT']=dict(cycles=N,stations=0,boundary=2,faces=1,fixed=N-2,natural=N,pad=0,param='LAT_HOST_BOOT')
p['note']=p.get('note','')+f' | C25c HOST_BOOT{N} nativeFFbanks={NW}NW+{N-NW}root, reserved320FFsites, no payload multicycle; regionalCA/reset/build/bind reconciliation pending'
(o/'die_plan.json').write_text(json.dumps(p,indent=1));sha=hashlib.sha256((o/'die_plan.json').read_bytes()).hexdigest()
report=dict(schema='opentallas.hbm.c25c_host_packet.v1',plan_sha256=sha,transport_cycles=N,consumer_edge_from_producer=N+1,production_token_cycles_added=0,source_hops=N,boundary_hops_included=[NW-1,NW],regional_ca_status='PENDING current local-clock tree bound; K is extra and must be priced from actual bind',reset_status='only3validFFreset perhop; current regional delivered-reset hookup pending generated binder',bit_sites=rows,max_intra_partition_hop_um=max(a['max_hop_um'] for a in est['legs']),bay_ff_fill=320*1.404*.27/17.28**2)
(o/'host_boot_sites.json').write_text(json.dumps(report,indent=1))
side=json.load(open(s/'c25b_side.json'));side.update(schema='opentallas.hbm.c25c_side.v1',plan='die_plan.json',plan_sha256=sha,plan_sha8=sha[:8])
side['provider_legs']['host_to_provider'].update(cycles=N+1,transport_port_cycles=N,load_capture_cycles=N+1,form=f'coherent320bit packet,{N}source FFhops incl2boundary banks; provider LOADcapture{N+1}; CAK pending',status='SOURCE PIPE PROVED; actual FF bays reserved; CA/reset/boundary bind timing pending',source='rtl/hbm_next/bind/ot_hnx_host_boot_hop.sv + host30_map.json; real RTL30pipe308comparisonsPASS')
side['host_write_interval']=dict(value=5,status='CHECKED source ingress AXI bvalid spacing; no payload-stability multicycle required with coherentpacket pipeline',payload_interval_info=40)
side['provider_legs']['provider_to_root']['length_um']=34.56;side['provider_legs']['root_to_provider']['length_um']=34.56
side['pending']= ['source_plan_commit (set to immutable archived plan commit)','regionalCAK and delivered-reset contract on new crossing','actual source/binder boundary hop identity','28foldedservice producer source closure; placement is conditional','current NQ2 HC service +4 vs inherited wrong4quarter price']
(o/'c25c_side.json').write_text(json.dumps(side,indent=1));print(json.dumps({k:v for k,v in report.items() if k!='bit_sites'},indent=1))
