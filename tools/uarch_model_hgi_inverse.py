"""Protected compact G25 inverse: sized before RTL, opt-in candidate."""
from pathlib import Path
import hashlib
import re


def model(k=2048, group=96):
    if not 1 <= k <= 2048 or group not in (1, 2, 4, 8, 96):
        raise ValueError('unsupported inverse shape')
    path=Path(__file__).resolve().parents[1]/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
    lef=path.read_bytes(); w,h=map(float,re.search(rb'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups())
    return dict(schema='hgi.inverse-selected.rtl-candidate.v1', default_enable=0,
        qualified=False, replicas_per_die=1, read_lanes=4, MACs_per_cycle=0,
        protected_macro_control_complement_bits=8*(12+7+2+1+1+256+7+2+3+4+3+2+3+3),
        protected_record_identity_bits='owner7 inside32b owner record; compactaddr11 inside32b map record',
        owner_macros=4, map_macros=12, macro_bits=128*256, macro_area_um2=16*w*h,
        macro_lef_sha256=hashlib.sha256(lef).hexdigest(), slot_um=[600,240],
        slot_sram_fraction=16*w*h/(600*240), slot_fit='logic/clock channels pending',
        count_storage='owner SRAM payload12b count,12b base,valid; SECDED39; no unprotected count array',
        map_storage='selected i11b plus compactaddr11 and valid; SECDED39,6 records/256b bitmasked write; overwritten K records',
        source='immutable R snapshot across two serialized request/response passes',
        malformed='first pass requires slot==prior owner count; second requires slot<count; K/group/rank bounds',
        build_cycles_conservative=34*k+18*group+16,
        build_delta_vs_initial=28*k+16*group,
        build_basis='real protected count read/modify/write, owner prefix, second owner read + inverse write; pins/capture/encode included',
        lookup_added_cycles=14, lookup_issue_per_cycle=4,
        logic_area='pin/capture and ECC pipeline registers estimated<17000FF; cell mapping/area unqualified',
        control_ff_ceiling_estimate=17000,
        lookup_basis='two registered packed SRAM read pipelines plus bounds/filtered result',
        io_bits=dict(R_request=13,R_response=46,lookup_in=4*(1+7+12+16),lookup_out=4*(1+1+1+11+16)),
        memory_read_bytes_per_cycle=4*2*32, memory_write_bytes_per_cycle=4*32,
        replica_mux_demux='four owner banks and3map banks/lane; registered3:1x256 then6:1x39',
        write_fanout=4, routing_tracks_needed=4*(36+30)+59+92, routing_capacity=6250,
        protected_metadata_complement_bits=4*(6*(12+16+7)+2*6+3*7+7*(16+11))+162,
        build_cycles_base=30*k+18*group+16,
        R_response_delay_basis='base excludes source backpressure/waits; conservative includes0..2 wait edges per entry/pass',
        control_protection='build counters and prefix complemented; invalid/complement mismatch faults sticky',
        retirement='lookup response always consumed; tag captured with request; no consumer stall allowed',
        latency_contribution='build + lookup14; collective delivery/VM arbitration and row FIFO priced by parent',
        no_rate_credit=True)
