#!/usr/bin/env python3
"""Fixed bounded transport sizing proposal for Maxwell/Kepler; no RTL change."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def generate(provider_root):
    ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=provider_root,text=True).strip()
    paths=['rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
           'results/uarch/qwen_hbm_endpoint_r14_20261002/review_r14.json']
    provider={p:subprocess.check_output(['git','show',ref+':'+p],cwd=provider_root) for p in paths}
    command=provider[paths[1]].decode();owner=provider[paths[2]].decode()
    if 'if(return_arb==6)' not in command or 'if(delay==11)' not in owner:
        raise ValueError('Re-price changed arbitration/owner lookup')
    local_paths=['tools/qwen_rom_kv_transport_candidate.py','tools/qwen_rom_kv_finite_window_gate.py',
                 'rtl/test/tb_qwen_rom_kv_finite_window.sv','rtl/hdc/kv/ot_hdc_qwen_kv_system.sv',
                 'rtl/hdc/kv/ot_hdc_qwen_hbm_sector_bridge.sv','rtl/hdc/ot_qwen_rom_tile_w12.sv',
                 'tools/uarch_model.py']
    local={p:(ROOT/p).read_bytes() for p in local_paths}
    records=16;beats=32;stack_count=4
    return dict(schema='opentallas.qwen-rom-kv-transport-candidate.v1',status='BLOCKED_MODEL_PROVIDER_JOIN',
        provider_ref=ref,provider_sha256={p:hashlib.sha256(b).hexdigest() for p,b in provider.items()},
        source_sha256={p:hashlib.sha256(b).hexdigest() for p,b in local.items()},
        fixed_candidate=dict(stacks_per_die=stack_count,burst_sectors=beats,burst_bytes=1024,
                             outstanding_bursts_per_stack=records,outstanding_sectors_per_stack=records*beats,
                             response_data_capacity_bytes_per_stack=records*beats*32,
                             burst_record_payload_bits_per_stack=records*(192+12+32),
                             burst_record_boundary='Identity192 + physical tag12 + received mask32; excludes allocation, retirement, quarantine and CDC state. These are proposed adapter credits, not existing allocated hardware.'),
        capacity_checks=dict(provider_request_slots_per_stack=32*64,provider_return_slots_per_stack=32*32,
                             candidate_inflight_sectors=512,candidate_fits_aggregate_queue_counts=True,
                             per_PC_distribution_and_backpressure_qualified=False,
                             provider_tag_capacity=4096,candidate_burst_tags=16),
        assembly=dict(source_logical_word_bytes=16,provider_sector_bytes=32,tile_fill_bytes=64,
                      sectors_per_full_tile_fill=2,logical_quarters_per_tile_fill=4,
                      proposed_assembly_slots_per_stack=16,
                      payload_bits_per_slot=512+64+11+7+192+1,
                      payload_boundary='Data512 + mask64 + tile11 + local row7 + owner192 + valid1; excludes generation, fragments, leases, retirement, CDC, mux/route/logic area.',
                      admission_rule='Reserve burst tag, all beat credits, destination assembly slots and SRAM write credits before request. Split at allocated extent/stack boundaries; never alias masked partial quarters.',
                      codec_rule='Retain original E4M3 byte codes for the tile SRAM; existing streamer BF16 window cannot be wired into FP8 fill. A raw-code branch or proven exact repack needs separately priced integration.'),
        credit_lifecycle=['reserve legal owner/extent and tag+beat+assembly+write credits',
                          'accept burst; enqueue at most32 sector commands, each with beat owner',
                          'accept held owned return; retain tag and match allocation generation',
                          'assemble two sectors or explicit masked quarters at one tile/local-row owner',
                          'publish only after registered fill and macro write visibility; block read/fill collision',
                          'return reverse credit after destination acceptance; quarantine tag until provider retirement',
                          'reuse window only after last reader drain and no stale return/fill lease'],
        source_bottlenecks=dict(current_bridge_outstanding_reads=1,current_physical_request_len=1,
                               provider_commands_per_stack_per_edge_at_most=1,
                               owner_lookup_edges_at_least=12,owner_lookup_parallelism=1,
                               return_arbitration_edges=7,
                               owner_only_upper_bound_bytes_s_per_die_at_1p2GHz=stack_count*32*1.2e9/12,
                               owner_only_lower_bound_cycles_per_4MiB_layer=131072*12//stack_count,
                               boundary='Analytical optimistic owner-only bounds. Additional arbitration, command, DRAM, CDC and fill waits make service slower. Burst length32 amortizes request allocation but does not bypass per-sector command/lookup.'),
        required_owner_actions=[
            'Maxwell: compose actual finite service into layer calendar once against existing144MiB/die read charge; determine whether fixed16-burst credits are useful given serial owner/return service. No rate adoption from capacities.',
            'Kepler: fix retained-owner reverse credit validation/quarantine and TP4 physical/logical identity binding; explicitly decide and price owner lookup service before copying r14.',
            'Euclid: join raw FP8 transport to actual tile masked fill and registered macro visibility only after these dimensions are in unified model.',
            'Archimedes: source-match tile/spine plus actual fill-port mux/replicas, macro slots, routing and SS/FF; no historical closure transfer.'],
        model_changed=False,hardware_implemented=False,second_position_queued=False,full_token_repeat_queued=False,
        physical_build_ready=False,actual_provider_join=False,adoption=False,
        claim_boundary='One fixed sizing candidate, not a concurrency sweep, allocated transport or product proof. Existing read-window diagnostic is separate and uses behavioral endpoint/memories.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--provider-root',type=Path,required=True)
    ap.add_argument('--result',type=Path,required=True)
    a=ap.parse_args()
    if a.result.exists():ap.error('Refusing to overwrite evidence')
    r=generate(a.provider_root);a.result.parent.mkdir(parents=True,exist_ok=True)
    with a.result.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(r['source_bottlenecks'],indent=2))
    return 1


if __name__=='__main__':raise SystemExit(main())
