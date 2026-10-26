#!/usr/bin/env python3
"""Inventory actual SML incident seams and candidate pin-register latency/state deltas."""
import argparse,collections,csv,hashlib,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--census',type=Path,required=True);p.add_argument('--pin-table',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 cells=json.loads(a.census.read_bytes())['modules']['dsfd_sp_su_static']['cells'];sml={n:c for n,c in cells.items() if c['type']=='ot_s81_su_sml'}
 pin=list(csv.DictReader(a.pin_table.open(),delimiter='\t'));pinby={r['port']:r for r in pin};wanted={b for c in sml.values() for p,bs in c['connections'].items() if p not in ('clk','rst_in') for b in bs if isinstance(b,int)}
 drivers=collections.defaultdict(list);sinks=collections.defaultdict(list)
 for n,c in cells.items():
  for port,bs in c['connections'].items():
   if port in ('clk','ck','rst_in','rst_n','CLK','ARST'):continue
   d=drivers if c['port_directions'][port]=='output' else sinks
   count=collections.Counter(b for b in bs if b in wanted)
   for b,k in count.items():d[b].append((n,c['type'],port,k))
 seams=[]
 for n,c in sml.items():
  for port,bs in c['connections'].items():
   if port in ('clk','rst_in'):continue
   r=pinby[port];neigh=collections.Counter()
   for b in bs:
    if not isinstance(b,int):continue
    for name,typ,np,k in (drivers if r['dir']=='input' else sinks)[b]:
     if name!=n:neigh[(name,typ,np)]+=k
   seams.append(dict(sml=n,port=port,direction=r['dir'],bits=len(bs),old_boundary_extra_edges=0,current_boundary_extra_edges=int(r['cycles']),incident_neighbors=[dict(owner=k[0],module=k[1],port=k[2],shared_bits=v) for k,v in sorted(neigh.items())],calendar='OPEN: all control/data ages and dependencies must be recompiled; no inherited original parent qualification'))
 delay=sum(int(c['parameters']['W'],2)*int(c['parameters']['D'],2) for c in cells.values() if c['type']=='ot_hdc_delay');state=sum(len(c['connections']['Q']) for c in cells.values() if c['type'] in ('$dff','$adff'))
 added={d:sum(int(r['width'])*int(r['cycles']) for r in pin if r['dir']==d) for d in ['input','output']}
 report=dict(scope='Actual source graph seam inventory, not re-aged calendar/physical qualification',sml_count=len(sml),pin_table=pin,pin_state_bits_per_leaf=added,pin_state_bits_total=len(sml)*sum(added.values()),old_transport_state_bits=dict(explicit_delay=delay,parent_glue=state,total=delay+state),new_transport_state_bits_if_all256_replaced=delay+state+len(sml)*sum(added.values()),existing_glue_transform_delta=0,added_candidate_edges_per_dependency='one on source SML output and one on target SML input when both endpoints are SML; propagate actual graph instead of assuming universal +2',seams=seams,input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.census,a.pin_table]})
 a.out.write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('seams','pin_table','input_sha256')}))
if __name__=='__main__':main()
