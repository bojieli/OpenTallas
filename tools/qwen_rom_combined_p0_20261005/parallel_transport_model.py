#!/usr/bin/env python3
"""Price parallel protected P0 boundary using the existing transport model.

No inherited narrow-corridor slot fit or physical rate qualification.
The protected endpoint owner must replace conservative leaf charges with its
literal source counts before physical adoption.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from qwen_stream4_transport_model import ring


def model():
    old = json.loads((ROOT / 'results/rtl/qwen_stream4_protected_20261005/transport_r2/prebuild_model.json').read_text())
    util, pair = old['utilization'], old['codec_pair_cell_um2']
    landing = ring(281, 64, 128, pair, util)
    write = ring(289, 16, 128, pair, util)
    ack = ring(9, 64, 128, pair, util)
    callback = ring(4, 4, 4, pair, util)
    endpoint_core = sum(x['core_mm2_all'] for x in (landing, write, ack, callback))
    from qwen_stream4_parallel_pc_model import model as leaf_model
    owner_leaf = leaf_model(ROOT)
    return dict(schema='qwen.p0.parallel-protected.prebuild.v1', default_OFF=True,
        owner_directive='e1701384d', MACs_per_edge=0, arithmetic_change=False,
        stacks_per_rank=4, PCs_per_stack=32, TP_ranks=4,
        topology='128 independent protected sector landing/ACK/write endpoints per rank; no stack row funnel',
        required_leaf='actual ot_qwen_stream4_cdc_pc RSEL1 with owner sector/control protection',
        owner_leaf=owner_leaf,
        owner_leaf_cell_area_delta_mm2_per_rank=128*owner_leaf['estimated_cell_area_delta_per_PC_mm2'],
        owner_leaf_FF_delta_per_rank=128*owner_leaf['estimated_FF_delta_per_PC'],
        leaf_charges_conservative_existing_model=dict(landing=landing, write=write, ack=ack, callback=callback),
        conservative_endpoint_core_mm2_per_rank=endpoint_core,
        root_checked_callback_and_sync_FF=4*(2*6+8),
        root_checked_callback_and_sync_core_mm2=4*(2*6+8)*.2916/1e6/util,
        conservative_endpoint_core_mm2_four_ranks=4*endpoint_core,
        charge_is_not_new_area_delta='existing per-PC endpoints are reused; literal owner rawCDC+sector-code inventory must reconcile before physical adoption',
        root_payload_bits_per_edge_per_rank=128*256,
        root_landing_metadata_bits_per_edge_per_rank=128*25,
        sealed_return_bits_per_edge_per_stack=32*landing['coded_bits'],
        sealed_return_bits_per_edge_per_rank=128*landing['coded_bits'],
        independent_ACK_coded_bits_per_edge_per_stack=32*ack['coded_bits'],
        independent_write_coded_bits_per_edge_per_stack=32*write['coded_bits'],
        boundary_tracks='charge all coded data, identity, held-valid/accept, credit rails, clock/reset and physical lane spans at actual mapped homes',
        old_1056_duplex_tracks_valid=False, physical_slot_fit=None,
        route_capacity_margin=None, routing_tracks_required_min_return_only=32*landing['coded_bits'],
        old_capacity_tracks_per_stack=1056,
        mux_demux='no32:1 return mux or root redistribution; independent corrected kept per-PC read selector; broadcast descriptor/GO fanout4 checked controls',
        bytes_per_rank_core_edge_max=128*32, bytes_per_rank_HCLK_edge_max=128*32,
        core_period_fs=833333, HCLK_period_fs=1024000,
        nominal_system_backend_payload_Bps=4*128*32/1.024e-9,
        actual_controller_timing_credit_stalls_additional=True,
        P8191_bytes_system=603979776,
        nominal_backend_payload_floor_us=603979776/(4*128*32/1.024e-9)*1e6,
        latency='actual endpoint encode/decode/crossing/route cycles and per-layer overlap must be measured; callback descriptor/GO consumption fence retained; no token rate credit',
        local_routes='owner must supply parallel source-to-tile landing homes and coded lane spans; old stack trunk/local span calendar is not reused',
        tile_KV_MiB_per_rank=12, tile_residency='one current layer window, mandatory36layer traffic',
        protected_leaf_inventory_pending=False, physical_qualified=False,
        setup_uncertainty_ps=60, hold_uncertainty_ps=25,
        new_controller=False, new_arithmetic=False, rate_credit=False)


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
