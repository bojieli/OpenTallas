"""Measure Q4 finite-credit stall cost on the existing immutable KVTRACE."""
import argparse,gzip,heapq,json,hashlib
from collections import defaultdict
from pathlib import Path
from qwen_kv_landing_fabric import placement_m
from uarch_model_qwen_kv_skid import model

def run(trace,depth):
    pos=placement_m();arrivals=defaultdict(list)
    with gzip.open(trace,'rt') as f:
        for ln in f:
            cy,fo,p,n,t0,t1=map(int,ln.split())
            for tile in [t0,t1][:max(n,0)]:arrivals[tile].append((fo,p))
    origin=min(cy for a in arrivals.values() for cy,p in a)
    final=base_final=0;stalls=0;max_tile=0
    for tile,events in arrivals.items():
        col=pos[tile][0]%32;fw=col+11;rev=col+3
        free=[0]*depth;heapq.heapify(free);prev_send=-1;prev_service=-1;base_service=-1
        ordered=sorted(events)
        # Eight current-token writes pre-empt every tile after its first arrival.
        burst_begin=ordered[0][0]-origin+fw
        for when,p in ordered:
            offer=when-origin
            send=max(offer,prev_send+1,heapq.heappop(free));prev_send=send
            service=max(send+fw,prev_service+1)
            if burst_begin<=service<burst_begin+8:service=burst_begin+8
            prev_service=service
            base_service=max(offer+fw,base_service+1)
            if burst_begin<=base_service<burst_begin+8:base_service=burst_begin+8
            heapq.heappush(free,service+2+rev)
            stalls+=send-offer
        final=max(final,prev_service+2);base_final=max(base_final,base_service+2)
        max_tile=max(max_tile,len(events))
    rec=model(depth)
    rec['trace_measurement']=dict(trace=str(trace),sha256=hashlib.sha256(Path(trace).read_bytes()).hexdigest(),
        payload_scope='timing only; full-width numerical mechanism has separate RTL bench',
        credit_return_is_actual_dequeue=True,token_block_edges_per_tile=8,
        offered_words=sum(map(len,arrivals.values())),tile_count=len(arrivals),busiest_tile_words=max_tile,
        unconstrained_credit_fill_edges=base_final,finite_credit_fill_edges=final,
        added_credit_stall_edges_per_fill=final-base_final,
        composed_gross_token_added_cycles=36*(final-base_final+2),
        sum_offer_to_send_wait_edges=stalls,
        scope='per-tile finite credits; row arbitration+PC atomic halves remain separate obligations')
    tile=max(arrivals,key=lambda t:len(arrivals[t]));selected=sorted(arrivals[tile])
    return rec,[(cy-origin,p) for cy,p in selected]

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--trace',type=Path,required=True);a.add_argument('--depth',type=int,default=8)
    a.add_argument('--out',type=Path,required=True);a.add_argument('--vectors',type=Path);args=a.parse_args()
    record,vectors=run(args.trace,args.depth);args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(record,indent=2)+'\n')
    if args.vectors:args.vectors.write_text(''.join(f'{cy} {pc}\n' for cy,pc in vectors))
    print(json.dumps(record['trace_measurement']))
