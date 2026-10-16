#!/usr/bin/env python3
"""Pre-build mapping/owner budget for checkpoint-backed packed136 service."""
import json

def model():
 return dict(schema='opentallas.hbm-packed136-mapped4.v1',enabled_default=False,
   descriptor_extra_bits=35,allocated_physical_PCs=4,owner_entries_per_pc=32,
   record_bytes=136,full64row_block_sectors=272,full40row_block_sectors=172,
   perPC_sector_count64rows=68,perPC_sector_count40rows=43,
   address='actual inverse ot_hbm_kport_map; bank={t9:7,t1:0},col=t6:2,row=allocation_row_base+(t>>10)',
   full_group_request='4 consecutive native sectors on one actual PC; t_low2=beat XOR row_low2',
   tail_request='single exact sector per missing tail word, no synthetic payload or padding except final128Bline',
   response_identity='owner tag index5+generation12; full16epoch,bank,groupordinal and permutation metadata',
   landing='32real128x256SRAM and32actualresponseFIFOs, existing4stream/8HBMFIFO/32PC actualclock roots',
   clock_period_ps=dict(stream=2500/3,hbm=1024),immutable_SM_cycles_per136Brecord=1.3743157894736842,
   PHYraw_bytes_per_second=125e9,PHY95percent_bytes_per_second=118.75e9,
   maximum_steady_raw_bytes_per_stream_edge=118.75e9/1.2e9,
   cold_prefetch_and_production_overlap_measured=False,compiler_calendar_bound=False,
   physical_qualified=False,adopted=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
