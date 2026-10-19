"""Pre-RTL exact ownership model for packed136 assembler, no latency change."""
import json

def model():
    cases=[]
    for count in range(1,65):
        total=((count*136+127)//128)*4
        live=set(); received=head=emitted=phase=elapsed=0; peak=overlaps=0
        while not(emitted==count and received==total):
            row=elapsed>=2 and phase!=1 and emitted<count
            pop=set(range(head,head+(5 if emitted%4==3 else 4))) if row else set()
            if row: assert set(range(head,head+5))<=live
            n=min(1 if phase==4 else 4,total-received)
            push=set(range(received,received+n))
            # Old gather completes before NBA writes; consumed slots may recycle.
            survivors=live-pop
            assert not ({x%8 for x in survivors}&{x%8 for x in push})
            overlaps+=len({x%8 for x in pop}&{x%8 for x in push})
            live=survivors|push; peak=max(peak,len(live)); assert len(live)<=8
            if row: head+=len(pop);emitted+=1
            received+=n;phase=(phase+1)%5;elapsed+=1
        cases.append(dict(count=count,cycles=elapsed,peak=peak,recycled=overlaps,padding_live=len(live)))
    return dict(runtime_storage_bits=8*256,old_storage_bits=16*256,added_cycles=0,
      ingress_sectors_per_five_edges=17,rows_per_five_edges=4,
      gather_bits=1280,boundary_bits_per_edge=1024,row_bits=1088,
      macro_change=0,replicas_per_sm=1,replicas_per_die=16,
      physical_status="OPEN: mux depth, kept control fanout, pin regs, floorplan not measured",
      latency="same row SRAM write/read edges as original; 0 added cycles",
      invariant="survivor and incoming modulo-8 slots disjoint; push wins on recycled slots",
      max_live=max(x['peak'] for x in cases),cases=cases)
if __name__=='__main__':print(json.dumps(model(),indent=2))
