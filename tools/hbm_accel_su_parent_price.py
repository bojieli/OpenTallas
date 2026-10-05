#!/usr/bin/env python3
"""Selected DS20 whole-native staging inventory for Maxwell's unified model.

This consumes the current unified-model authority, but does not register the
new parent implementation in it. Unknown mux/clock/corridor costs stay unknown;
this record cannot admit a build, qualify a clock, or supply a composed gain.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def unified_price():
    # The actual model entry is self-contained. Loading that exact function
    # avoids uarch_model's import-time reads of unrelated ROM physical records
    # in a sparse worktree; it does not copy or substitute a pricing formula.
    path = ROOT/'tools/uarch_model.py'
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == 'hbm_su_finite_provider_tradeoff_model')
    scope = {'__file__':str(path)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), scope)
    return scope[node.name]()


def proposal():
    n, ncl, maxo = 1024, 4, 32
    inventory = dict(
        read_metadata_and_reply_SECDED_bits=5*n*2*72,
        VM_KV_reduction_write_SECDED_bits=(2*n+n//8)*72,
        comb_post_scalar_bits=20*32,
        native_program_transport_bits=8*704,
        native_program_chunk_valid_bits=8*11,
        held_request_bits=337, held_response_bits=273,
        previous_request_tag_kind_valid_bits=ncl*maxo*18,
        previous_request_counts_bits=ncl*6,
        last_sector_read_cache_bits=5*(32+256+1),
        held_context_bits=32+4+17+20+32,
        controller_bits_ESTIMATE=256)
    bits = sum(inventory.values())
    paths = ['rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv',
             'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
             'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_simt_sm20.sv',
             'rtl/gpu_sys/ot_gpu_mreq_cdc.sv',
             'rtl/hdc/ot_hdc_cg.sv', 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
             'rtl/hdc/v41x/ot_hdc_v41x_vec.sv',
             'rtl/hbm_accel/su/ot_hbm_accel_su_fused_vm.sv']
    return dict(schema='opentallas.ds20-su-parent.pre-rtl.v1',
        unified_model_authority=unified_price(),
        composition_owner='Maxwell', parent_writer='Einstein',
        selected_source='ot_ds_hbm_cluster20 SM0 LSU client0',
        model_registration_pending=True, RTL_build_admitted=False,
        minimum_case='L0.hc_post.attn original four scheduled words',
        original_word_sha256='0cfed448f54896266ce57d3a94826e4044cf47f8b09a22419fe16eb5e5a180d7',
        native=dict(N=n,M=256,MLAT=6,ALAT=5,BCAST=7,RET=8),
        fused=dict(KIND=4,N=n,D=5120,MLAT=5,ALAT=4,PUBLISH_QUANT=0),
        inventory_FF_bits=inventory, inventory_total_bits_ESTIMATE=bits,
        DFF_body_floor_mm2_ESTIMATE=bits*.2916/1e6,
        protection_scope='stage data uses existing SECDED64/72; controls/cache/loader protection and mapped codec area still need final inventory',
        MACs_per_cycle_added=0, replicas=1, added_memory_ports=0,
        memory_payload_bytes_per_accepted_sector=32,
        borrowed_boundary_request_bits=337, borrowed_boundary_response_bits=273,
        gate='existing ot_hdc_cg; whole engine and original issuer step together',
        read_before_write='snapshot pre-edge reads; complete reads before VM/KV/res writes; preserve original lane/collision order',
        write_publication='matched tag+kind ACK and same-sector readback; no completion from engine done alone',
        owner_transfer='actual all-client debt consumed and SM busy/launch quiet before borrow; hold through checked publication',
        muxes=dict(request_2to1_bits=337,response_1to2_bits=273,
                   read_record_serial_selection_entries=5*n,
                   write_record_serial_selection_entries=2*n+n//8,
                   native_or_fused_read_payload_bits=4*n*32,
                   native_or_fused_read_control_bits=4*n*(24+2+1),
                   native_or_fused_VM_write_bits=n*(24+32+1)),
        mux_codec_area_mm2=None, gate_clock_tree_area_mm2=None,
        floorplan_slot_fit=None, corridor_capacity_tracks=None,
        boundary_payload_tracks_lower_bound=256,
        serial_controller_edges='one staged engine edge + scan/capture/service/drain/publication edges; measure on actual accepted calendar',
        single_outstanding=True,
        latency_equation='sum accepted request-to-matched-response intervals + nonoverlapped scan/virtual-edge/control/publication; actual CDC/backend included once',
        original_native_measured_us=None, fused_measured_us=None,
        composed_token_delta_us=None, composed_gain_percent=None,
        measured_wire_CDC_credits_refresh_us=None,
        SS60_FF25_qualified=False, default_enabled=False, adopted=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})


if __name__ == '__main__':
    print(json.dumps(proposal(),indent=2))
