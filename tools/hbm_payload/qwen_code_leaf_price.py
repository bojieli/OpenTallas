"""Bound the existing post-CDC paired-column SRAM writer; no architecture selection."""
import json
from pathlib import Path

def price():
    banks=(4496+1023)//1024
    return dict(schema='qwen_code_payload_leaf_price.v1', default_enabled=False,
        mode='CODE_ONLY_POST_CDC_CORE_833_333PS', rows=4496, columns_per_leaf=2,
        payload_bits_per_sector=256, W6_check_bits_per_sector=32,
        data_macro='ot_sram_1r1w_1024x256_m2_r2c2', check_macro='ot_sram_1r1w_128x256_m1_r2c2',
        banks_per_column=banks, data_macros_per_leaf=2*banks, check_macros_per_leaf=2*banks,
        payload_bytes_per_leaf=2*4496*32, coded_bytes_per_leaf=2*4496*36,
        installed_macro_bytes_per_leaf=2*banks*(32768+4096),
        macro_outline_area_um2_per_leaf=2*banks*(12314.20968+3891.57696),
        leaf_replica_count_if_parent_selects_all_columns=1536,
        payload_bytes_full_array=441974784, coded_bytes_full_array=497221632,
        padded_macro_bytes_full_array=1536*2*banks*(32768+4096),
        ports=dict(writes_per_core_edge=1, write_payload_bits=256, write_check_bits=32,
                   reads_per_core_edge=2, read_payload_bits=512, read_check_bits=64,
                   read_row_bits=26, destination_row_bits=13, destination_column_bits=12,
                   owned_return_bits=465, same_clock_1R1W=True),
        state=dict(protected_read_code_bits=576, protected_visible_metadata_bits=288,
                   protected_control_bits=72, total_stored_bits=936,
                   FF_cell_area_floor_um2=936*0.2916),
        codecs=dict(payload_encode64_instances=4, payload_decode64_instances=8,
                    visible_metadata_encode64_instances=4, visible_metadata_decode64_instances=4,
                    control_encode64_instances=1, control_decode64_instances=1, source='rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
                    correction_after_read_register=True, combinational_delay_ps=None,
                    decode_mux_fanout_area_um2=None),
        latency=dict(macro_read_edges=1, protected_read_capture_edges=1,
                     read_response_edges=2, added_read_edges_against_existing_tile_macro=1,
                     write_admission_extra_edges=0, visible_after_joint_write_capture=True,
                     visible_receipt_backpressure_must_not_repeat_write=True,
                     composed_token_delta_edges=None,
                     Hubble_15287_edges_one_extra_exposed_edge_fraction=1/15287,
                     no_zero_cycle_correction_or_fulltoken_claim=True),
        requirements=['Sagan supplies immutable installed-span row/column mapping and real publication authorization',
                      'Sagan retains striping/CDC/global complete prefix/reuse and transport credit',
                      'Both data and packed check SRAM use identical write edge and independent masked write pins',
                      'Caller must align tile bank selection/capture to explicit two-edge read latency',
                      'Kant binds actual placement/clock/read decode/CTS/PG in context; no assumed timing closure'],
        accepted_visible_global_occupancy='Parent-owned: this leaf reports one joint stored sector, not SPW24/NPC128 full-word completion',
        allocator_spanmap='UNBOUND: supplied physical row13/column12; no sector-to-row/PC striping guessed',
        adopted=False, SS_FF_qualified=False)

if __name__=='__main__':
    print(json.dumps(price(),indent=2))
