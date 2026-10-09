"""Analytical four-adjacent-tile shared pool; no RTL/physical adoption claim."""
import argparse,gzip,hashlib,heapq,json
from collections import defaultdict
from pathlib import Path
from qwen_kv_landing_fabric import placement_m

def model(trace,depth,grouping="four"):
    positions=placement_m();groups=defaultdict(list)
    with gzip.open(trace,'rt') as f:
        for line in f:
            cy,fo,p,n,t0,t1=map(int,line.split())
            for tile in [t0,t1][:max(n,0)]:
                col,row=positions[tile]
                groups[(col,0) if grouping=="column" else (col//4,row)].append((fo,p,tile))
    origin=min(t for es in groups.values() for t,p,tile in es)
    final=0;wait=0;peak=0
    for (gc,row),es in groups.items():
        # Existing worst-case row chain ending at the farthest member.
        col=gc if grouping=="column" else gc*4+3
        # Column candidate adds half-column distance to a central queue.
        # 24 rows of1291.656um: maximum 15mm, 35 hops at430.56um.
        vhops=35 if grouping=="column" else 0
        fw=col%32+11+vhops;rev=col%32+3+vhops
        free=[0]*depth;heapq.heapify(free);sendlast=servicelast=-1
        es.sort();block=es[0][0]-origin+fw
        for when,p,tile in es:
            offer=when-origin
            send=max(offer,sendlast+1,heapq.heappop(free));sendlast=send
            service=max(send+fw,servicelast+1)
            if block<=service<block+8: service=block+8
            servicelast=service;heapq.heappush(free,service+2+rev)
            wait+=send-offer
        final=max(final,servicelast+2);peak=max(peak,len(es))
    dest=5 if grouping=="column" else 2
    bits=1031+dest;ff=depth*bits+2*(bits+1)+32
    frame=[160, max(160, ((ff*.2916+3655)/.55/160+2.159)//2.16*2.16)]
    return dict(schema='opentallas.qwen-shared-skid-traffic.v1',trace_sha256=hashlib.sha256(Path(trace).read_bytes()).hexdigest(),
      grouping=grouping,tiles_per_pool=24 if grouping=="column" else 4,shared_entries=depth,replicas=len(groups),offered_words=sum(len(e) for e in groups.values()),
      max_group_words=peak,fill_edges=final,sum_wait_edges=wait,
      service_words_per_cycle=1,token_preemption_edges=8,
      state_bits_per_pool=ff,estimated_cell_um2_per_pool=ff*.2916+3655,
      shared_frame_um=frame,provisional_frame_area_mm2=len(groups)*frame[0]*frame[1]/1e6,
      routing=dict(ingress_bits=bits+1,broadcast_bits=1031+dest,local_dest_select_bits=dest,
        fanout=24 if grouping=="column" else 4,added_vertical_hops_per_direction=35 if grouping=="column" else 0,pin_capacity_2layer_160um=2*int(160/.096)),
      latency=dict(fill_edges=final,gross_layer_cycles=36*(final+2)),
      adopted=False,physical_fit=False,rtl_built=False,
      limitations=['timing-only offers; no golden full-width shared implementation yet',
        'frame includes55percent cell bound; actual pin/channel and placement qualification required',
        'one output bus must meet all actual group tile write ports without duplicated buses',
        'token conflict policy eight grouped edges is provisional; actual independent producers may extend it',
        'group arbitration/credit ownership and far relay costs must be implemented before adoption'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--depth',type=int,default=8)
    p.add_argument("--grouping",choices=("four","column"),default="four")
    a=p.parse_args();print(json.dumps(model(a.trace,a.depth,a.grouping),indent=2))
