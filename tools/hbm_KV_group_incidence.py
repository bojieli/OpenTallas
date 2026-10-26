#!/usr/bin/env python3
"""Exact canonical NL2 mapping incidence. No route/timing qualification."""
import argparse,json
from pathlib import Path

def model():
 records=[];demands={(l,j):{(16*l+j)%4} for l in range(2) for j in range(16)}
 matrix=[[0]*4 for _ in range(4)]
 for tile in range(32):
  for lane in range(2):
   j=tile//2;source=16*lane+j;src=source%4;dst=tile%4
   records.append(dict(tile=tile,lane=lane,code_bank=source,code_group=j,XOFF=16*(tile%2),useful_code_bits=128,metadata_bits=9,whole_source_codeword_bits=256,source_QK_local_physical_group=src,destination_PV_physical_group=dst,crosses_group=src!=dst))
   matrix[src][dst]+=1;demands[lane,j].add(dst)
 by_group=[]
 for g in range(4):
  banks=[16*l+j for (l,j),groups in demands.items() if g in groups]
  by_group.append(dict(group=g,code_bank_ids=banks,code_macro_copies=len(banks),unique_metadata_bits=9*len(banks),merged_metadata_macros_256b=(9*len(banks)+255)//256))
 return dict(schema='opentallas.hbm.KV_group_incidence.v1',source_mapping='QKtile=16*lane+SL; PVtile consumes both lanes of group=floor(tile/2),XOFF=16*(tile%2)',physical_tile_groups='tile%4; canonical PVoutput bankpair{2g,2g+1}',source_to_consumer_group_leg_matrix=matrix,PV_legs=records,local_PV_legs=sum(not r['crosses_group'] for r in records),cross_group_PV_legs=sum(r['crosses_group'] for r in records),whole_codeword_replication={'unit':'one entire1024x256 macro per source bank per physical consumer group','minimal_code_macros':sum(len(v) for v in demands.values()),'baseline_code_macros':32,'additional_code_macros':sum(len(v) for v in demands.values())-32,'per_group':by_group,'metadata_merge_lower_bound_macros':sum(g['merged_metadata_macros_256b'] for g in by_group),'total_code_plus_local_metadata_macros':sum(len(v) for v in demands.values())+sum(g['merged_metadata_macros_256b'] for g in by_group),'requirements':['Same writes update all admitted physical copies; real write fanout and lane masks must be proved.','Metadata merged across lanes needs real per-bit masks; no phantom second port.','Minimum is conditional on whole256b codeword replication and fixed tile%4 grouping; alternate packing changes problem.']},mode_specific_candidate={'total_macros':34,'code_macros':32,'metadata_macros':2,'K_bank_t':'256codes from lane=t//16,group=t%16','V_bank_t':'low128codes from lane0, high128codes from lane1; group=t//2,half=t%2','locality':'same physical bankt next to logicaltile t for both QK andPV; metadata remains narrow nonlocal','physical_clock_pins':34,'payload_sram_bits':34*1024*256,'status':'NEW ABI/calendar-controlled packing candidate, not implemented/qualified','requirements':['Mode known and frozen before first write of record.','K/PV load/reuse/residency semantics prove no stale or differently packed reads.','Independent lane masks become low/high128b masks in V packing.','Exact1edge old-data read and external8480b ABI preserved.','Both decoder directions and metadata bit/format packing need actual DUT proof.']},whole_native_qualified=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();r=model();Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['source_to_consumer_group_leg_matrix','local_PV_legs','cross_group_PV_legs','whole_codeword_replication']}))
if __name__=='__main__':main()
