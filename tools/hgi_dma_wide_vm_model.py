"""Actual wide DMA/protected shared VM sizing, before successor RTL."""
import hashlib,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1]

def model(*,data_hops=96,credit_hops=96):
    p=R/'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.json'
    m=json.loads(p.read_text());area=m['area'];stacks=4;nl=32;logical=512;physical=logical*2;macros=physical*2;depth=256
    return dict(scope='opt-in wider front and actual protected shared VM, no route/adoption claim',default_enable=0,
        design_applicability={'Qwen3-8B ROM':False,'DeepSeek-V4.1 ROM':False,'Qwen3-8B HBM':True,'DeepSeek-V4.1 HBM':True},
        MACs_per_cycle=0,clock_hz=1.2e9,
        HBM=dict(sustained_Bpc=3.8e12/1.2e9,nominal_Bpc=4e12/1.2e9,required_raw_Bpc=3000,implemented_lane_roof_Bpc=stacks*nl*32),
        front=dict(stacks=stacks,lanes_per_stack=nl,service_tag_bits=6,tags_per_stack=64,request_packet_bits=53,response_packet_bits=272,
            source_run_sectors=256,source_run_cycles=8,read_latency=104,
            native_descriptor_lifetime_cycles=96+104+3+5+data_hops+8+2,minimum_tags_per_stack=math.ceil((96+104+3+5+data_hops+8+2)/8),
            credit_depth=depth,credit_round_trip=data_hops+credit_hops+7,
            lane_fifo_bits=stacks*nl*depth*(256+18),format_expansion={'FP32':1,'BF16':2,'FP8':4},
            placement='128 near-VM converter tiles; each owns four logical banks with two physical phases; transport raw272bits, expand beside memory'),
        VM=dict(payload_bytes=8*1024*1024,word_address_bits=21,sector_address_bits=18,
            logical_banks=logical,physical_banks=physical,physical_phase='sector bit9',row='sector bits17:10',logical_bank='sector bits8:0',
            physical_read_II=2,physical_write_II=2,macro_count=macros,macro_name=m['spec']['name'],macro_rows=256,
            ECC='eight independent39,32 SECDED words per sector; two256bit macros store312protectedbits',
            maximum_sector_writes_per_cycle=physical/2,maximum_write_Bpc=physical*32/2,
            actual_bank_write_edges=5,actual_bank_read_edges=6,
            actual_body_write_publication_elapsed=5,actual_body_read_publication_elapsed=6,
            allocation_visibility_bits=physical*256*8*2,
            visibility_policy='protected per-word initialized bitmap; read waits all eight words durable, never fabricates zero SRAM contents',
            allocation_write_pipeline_bits=physical*(5+5*16)*2,
            allocation_logic_area_um2=None,allocation_physical_fit_qualified=False,
            decoded_capacity_raw_equivalent_Bpc={'FP32':16384,'BF16':8192,'FP8':4096},
            producer_ports=dict(DMA=512,native_COLL=8,packet='existing337/273 ABI byteaddress32 holds8MiB; bounds become23bytebits'),
            arbitration='bank-local ready/reserve before admission; COLL and packet write compete with DMA; tagged ACK only after macro publication',
            COLL_completion='DEL credit returns on filtered slot or actual tagged write ACK, never merely arrival',
            ATT_binding='reader uses same18bitsector region descriptor; selected rows0..4MiB, query/scratch4..8MiB pending compiler live interval inventory',
            region_descriptor=dict(selected_row_base_sector=0,selected_rows_max=2048,row_bytes=2048,selected_rows_bytes=4*1024*1024,
                query_and_scratch_base_sector=131072,query_and_scratch_reserved_bytes=4*1024*1024,live_interval_qualified=False)),
        boundaries=dict(raw_data_bits=stacks*nl*272,service_request_bits=stacks*53,credit_bits=stacks*nl,
            DMA_local_bank_bits=512*(1+18+256+8),expanded_global_die_bus_allowed=False),
        physical=dict(macro_area_um2=macros*area['macro_area_um2'],macro_dimensions_um=[area['macro_width_um'],area['macro_height_um']],
            SS_macro_clk_to_q_ps=m['timing']['ss']['clk_to_q_ps'],SS_macro_min_period_ps=m['timing']['ss']['min_period_ps'],
            macro_count_per_converter_tile=16,tile_count=128,proposal_tile_width_um=900,proposal_tile_height_um=500,
            proposal_grid=[8,16],proposal_grid_area_mm2=128*900*500/1e6,
            tile_macro_area_um2=16*area['macro_area_um2'],tile_logic_capacity_at60pct_um2=900*500*.6-16*area['macro_area_um2'],
            tracks_per_long_data_lane=272,tracks_per_short_local_bank_port=283,
            channel_capacity='die owner supplies actual layer/occupancy budget; no route admitted',
            floorplan_fit='macro geometry legal in proposed tile; slot placement and mapped logic/pins remain unqualified'),
        macro_source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        latency_composition=dict(read104=104,data_transport=data_hops,front_convert='measured successor RTL',write_publication_min=5,
            credit_transport=credit_hops,token_latency='include every cold-start and format expansion; service and VM occupancy measured independently'),
        physical_admitted=False,adoption=False,HBM90pct_proven=False)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'model_before_rtl.json').write_text(json.dumps(model(),indent=2)+'\n')
    print('SIZED opt-in128 rawlanes;1024 physicalII2banks;2048 actual SRAM macros')
