#!/usr/bin/env python3
"""Pre-RTL rate/ownership/storage model for a full-bandwidth reverse boundary.

An actual-PHY baseline is a separate measured artifact. This analytical model
never substitutes the PHY's peak bandwidth for its measured block latency.
"""
from fractions import Fraction
import argparse
import json


def pc_of(s):return ((s>>2)^(s>>7)^(s>>12))&31


def per_pc_bursts(base,total):
    end=base+total; result=[]
    for pc in range(32):
        group=base>>7
        candidate=lambda g:((g<<5)|(pc^(g&31)^((g>>5)&31)))<<2
        if candidate(group)+4<=base:group+=1
        bursts=[]
        while candidate(group)<end:
            address=max(candidate(group),base)
            count=min(candidate(group)+4,end)-address
            assert 1<=count<=4 and all(pc_of(address+i)==pc for i in range(count))
            bursts.append(dict(address=address,ordinal=address-base,count=count))
            group+=1
        result.append(bursts)
    covered=sorted(x['ordinal']+i for bursts in result for x in bursts for i in range(x['count']))
    assert covered==list(range(total))
    return result


def report():
    hbm_ps=1024; stream_ps=Fraction(2500,3)
    stream_rate=Fraction(8*hbm_ps,1)/stream_ps
    full_rate=Fraction(900_000_000_000*hbm_ps,32*10**12)
    scenarios=[]
    for banks,fifo_count,issue_bursts in [(8,8,4),(8,16,4),(32,32,8),(32,32,32)]:
        response_rate=fifo_count
        issue_rate=issue_bursts*4
        scenarios.append(dict(logical_banks=banks,response_FIFO_count=fifo_count,
            four_sector_bursts_per_HBM_cycle=issue_bursts,
            max_request_sectors_per_HBM_cycle=issue_rate,
            max_CDC_response_sectors_per_HBM_cycle=response_rate,
            supports_eight_lane_stream_rate=min(issue_rate,response_rate)>=stream_rate,
            supports_900GBs_stack_peak=min(issue_rate,response_rate)>=full_rate))
    cases=[]
    for base,total in [(4099,640),(12295,2048),(3001,5),(127,2048)]:
        bursts=per_pc_bursts(base,total)
        cases.append(dict(base=base,total=total,burst_count=sum(map(len,bursts)),
                          max_bursts_per_PC=max(map(len,bursts)),
                          burst_count_per_PC=list(map(len,bursts)),
                          perfect_32PCparallel_issue_lower_bound_HBM_cycles=max(map(len,bursts)),
                          stream_delivery_cycles=(total+7)//8))
    return dict(schema='opentallas.prefetch_burst_pipeline_model.v1',
        status='pre_RTL_analytical_only_actual_PHY_baseline_measurement_required',
        clocks=dict(stream_period_ps=float(stream_ps),hbm_period_ps=hbm_ps),
        required_rates=dict(eight_lane_stream_sectors_per_HBM_cycle=float(stream_rate),
                            aggregate_service_bytes_s=3_600_000_000_000,stacks=4,
                            per_stack_bytes_s=900_000_000_000,
                            full_service_sectors_per_HBM_cycle=float(full_rate)),
        scenarios=scenarios,cases=cases,
        selected_architecture=dict(logical_ordinal_banks=32,macro_count=32,macro_rows=128,
            macro_data_bits=256,bank_count=2,rows_per_block_per_logical_bank=64,
            SRAM_total_bytes=32*128*32,response_FIFO_count=32,response_FIFO_width=284,
            response_FIFO_depth=8,response_FIFO_data_FF_total=32*284*8,
            FIFO_HBM_clock_roots=8,FIFO_data_FF_per_root=4*284*8,
            FIFO_stream_clock_roots=4,PC_metadata_clock_roots=32,
            entries_per_PC=32,max_owner_beats_per_PC=128,actual_PHY_queue_beats_per_PC=64,
            owner_entry_bits=dict(valid=1,generation=12,epoch=16,bank=1,ordinal_start=11,length=3,seen_beats=4),
            owner_entry_bits_total=48,metadata_entry_FF_per_PC=32*48,metadata_FF_total=32*32*48,
            additional_per_PC_register_FF=41,metadata_clock_sink_FF_per_PC=1577,
            tag_format='generation12:index5',
            address_formula='chunk=((group<<5)|(PC^(group&31)^((group>>5)&31))); sector=chunk<<2',
            request_issue='independent one burst per PC per HBM edge; 32 PC-parallel paths',
            landing='logical_bank=ordinal%32,row={block_bank,ordinal[10:5]}',
            delivery='8 lanes from one group of eight logical banks; four groups per 32-sector row',
            physical_clock_routing_and_tracks='unpriced; no physical adoption',
            candidate_FIFO_depth8='performance ablation pending; depth4 measured failed immutable latency gate'),
        latency_gate=dict(reference='immutable measured actual-PHY baseline on identical addresses and reset/refresh state',
                          max_multiplier=1.10,baseline_cycles=None,
                          descriptor_CDC_and_landing_price='must be separately measured and explicitly included',
                          bandwidth_qualified=False))


def main():
    p=argparse.ArgumentParser();p.add_argument('--out');a=p.parse_args();text=json.dumps(report(),indent=2)+'\n'
    if a.out:open(a.out,'w').write(text)
    print(text,end='')


if __name__=='__main__':main()
