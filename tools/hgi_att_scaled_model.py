"""Exact producer scale provenance, before adding a packed sidecar."""
import json

def model():
    return dict(window_FP8=dict(producer='ot_hdc_actquant fp4=0',existing_outputs='q256,e10,y512 alignedvo',packed_group='{fmt0,UE8M0(e+127),q256}',added_register_bits=0,added_cycles=0,latency_cycles=13,II=1,raw_ROW_D512_bytes=544,adopted=False),default_on=False,producer='ot_hgi_fp4qdq block16, two blocks/edge',
        source_quantizer='hdc_golden_v41.qdq_fp4_e4m3 SATFINITE scale448',
        original_values='BF16-valued FP32; no unscaled E4M3 requirement in golden',
        proposal='preserve existing S5 sign/code/n/qs directly at S6, aligned with unchanged BF16 y and vo',
        exact_arithmetic_change=False,rounding_change=False,
        clock=dict(GHz=1.2,period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        replicas_per_stream=1,macs_per_cycle=0,input_bytes_per_cycle=128,
        legacy_BF16_output_bytes_per_cycle=64,packed_output_bits_per_cycle=265,
        meaningful_packed_bits=145,added_register_bits=144,added_valid_register_bits=0,
        added_latency_cycles=0,quantizer_latency_cycles=8,initiation_interval_cycles=1,
        boundary_bits=dict(input=1027,legacy_output=514,added_packed_output=265,total=1806),
        producer_slot=dict(side_um=1000,density_pins_per_um=0.55,usable_perimeter_um=3913.6,
                           capacity_pins=2152,perimeter_fits=True,area_um2=None,
                           status='area awaiting actual mapped synthesis; no physical closure claim'),
        downstream=dict(existing_engine_group_bits=265,group_dims=32,groups_D512=16,
                        row_bits=4240,aligned_row_bytes=544,FP32_row_bytes=2048,
                        metadata='fmt1, two original E4M3 scale bytes, original32 E2M1 nibbles; padding zero',
                        memory='selected packed row mutable ECC required; raw STORE/GATHER must preserve all bits and tags',
                        actual_existing_engine=True,new_arithmetic_macros=0),
        latency_composition='producer +0cycles; packed read17sectors vs64FP32sectors atD512; actual selected arb/drain measurement pending',
        mechanism_gate='actual quantizer->packed sidecar->existing dequant and chunk8 tile on5.25/2.625 and golden random blocks',
        packed_consumer=dict(default_on=False,parameter='PACKED_ROWS',source_format=3,record_formats='B/C fmt3 rawpacked; per265bitgroup fmt chooses originalwindow orcompressedrow',row_bits_D512=4240,storage_bits_added_vs_codebuffer_D512=144,sectors_per_row_D512=17,register_capture_cycles_added=0,memory='17 staticallyselected registerstations; actual finite valid-qualified payload, no ideal SRAM claim',tail='last14zero bytes checked',engine_wire_bits_added=0,physical='distributedstation/engine views unqualified; no giantflattened PNR'),full_unit='packed row producer STORE/GATHER binding pending; restricted old transport stays off',
        model_rate_credit=0,adoption=False)

if __name__=='__main__':print(json.dumps(model(),indent=2))
