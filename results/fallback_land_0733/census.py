#!/usr/bin/env python3
"""Static all-plan-partition cut census. Never substitutes counts for DAG cost."""
import argparse,gzip,json
from collections import Counter,defaultdict
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('--status',required=True);p.add_argument('--out',required=True);a=p.parse_args()
file=Path(a.plan);d=json.load(gzip.open(file,'rt') if file.suffix=='.gz' else open(file));parts=d['partitions'];parts={q['name']:q for q in parts} if isinstance(parts,list) and parts and 'name' in parts[0] else parts
if isinstance(parts,list):parts={q['id']:q for q in parts}
ports=d['ports'];ports=list(ports.values()) if isinstance(ports,dict) else ports
lanes=d['lanes'];lanes=list(lanes.values()) if isinstance(lanes,dict) else lanes
bykind=defaultdict(lambda:Counter());bycut=defaultdict(lambda:Counter());skipped=[];external=[];used=[]
for q in ports:
 src=q['src']['part'];dst=q['dst']['part'];bits=int(q['width']);kind=q.get('kind','data')
 if src==dst:skipped.append(q['id']);continue
 if src not in parts or dst not in parts:external.append(q['id']);continue
 bykind[kind]['ports']+=1;bykind[kind]['bit_crossings']+=bits;bycut[src+' -> '+dst]['ports']+=1;bycut[src+' -> '+dst]['bit_crossings']+=bits;used.append(q['id'])
landing=sum(v['bit_crossings'] for k,v in bykind.items() if k in ('data','ctl','control'))
# Gross new stages, no source-fanout sharing or existing bank reuse deducted.
envelope=1.404*.27
out=dict(schema='opentallas.fallback_land_analysis.v1',die=d['die'].get('name','unknown') if isinstance(d['die'],dict) else d['die'],source_plan=a.plan,status=a.status,parts=len(parts),types=len(d['partition_types']),lanes=len(lanes),all_plan_ports=len(ports),internal_same_partition_ports=skipped,unresolved_or_external_ports=external,kind_census={k:dict(v) for k,v in bykind.items()},eligible_data_control_bit_crossings=landing,crossing_port_ids=used,partition_pair_census={k:dict(v) for k,v in bycut.items()},scenarios={str(n):dict(extra_cycles_per_crossed_partition_seam=n,gross_new_ff_bit_sites=n*landing,gross_legal_ff_envelope_um2=n*landing*envelope,token_throughput='UNPRICED',critical_path_added_cycles='UNPRICED: current programme-operation to traversed seam map required') for n in (2,3)},area_basis='Gross stage-bit sites times canonical1.404x0.27um legal FF envelope; not synthesizedcellarea, notnetincrementalarea. Existingbanks/sourcefanoutsharing/notlandableprotocolsnotdeducted.',limitations=['Only explicit plan partition seams, not unenumerated hard-core/datapath cuts within partition types.','Clock/reset/PG not landed; their networks are separate plan contracts.','Adding latency changes handshakes/reset/epoch/calendar; no scalar totalstationcount pricing.','No rule, plan, programme, RTL or physical build changed.'])
Path(a.out).write_text(json.dumps(out,indent=1));print(json.dumps({k:out[k] for k in ('die','parts','types','all_plan_ports','kind_census','eligible_data_control_bit_crossings')}))
