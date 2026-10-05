#!/usr/bin/env python3
"""Minimal actual PC40 simulator source list; no fixture, launch or arithmetic."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=[
 'results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs/ot_gpu_w6_secded_pkg.sv',
 'results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs/ot_hdc_prefix.sv',
 'results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs/ot_gpu_rf_visibility_fence_w6.sv',
 'results/uarch/h4_hbm_pc40_physical_ack_r3_20261003/inputs/ot_gpu_rf_service.sv',
 'rtl/experimental/hbm_c0_connected_20261003/r2/ot_gpu_c0_fmax_leaf_r2.sv',
 'rtl/experimental/hbm_c0_connected_20261003/r2/ot_gpu_pc40_fmin_consumer.sv',
 'rtl/experimental/hbm_c0_connected_20261003/r4/ot_gpu_c0_connected_bridge_r4.sv',
 'rtl/experimental/hbm_c0_connected_20261003/r4/ot_gpu_pc40_physical_ack_source_r4.sv',
 'rtl/experimental/hbm_c0_connected_20261003/r4/ot_gpu_pc40_native_ingress.sv',
 'rtl/experimental/hbm_c0_connected_20261003/r4/ot_gpu_pc40_native_connector.sv',
 'rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv',
 'rtl/model/hbm_pc40_native_sim_20261003/ot_gpu_pc40_native_sim_port.sv',
]


def source_list(root=ROOT):
    root=Path(root)
    return [dict(path=p,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in FILES]


def binding():
    return dict(top='ot_gpu_pc40_native_sim_port',ENABLE_default=0,
        explicit_functional_selection='ENABLE=1',sources=source_list(),
        W2_dependency=False,fixture_dependency=False,compile_or_run=False,
        selected_scope=dict(source_PC=40,template='SILU_GATE/exp',rank=0,SM=0,
                            source_RFslot=38,workspace=[17,18,19],lanes=128),
        ports=dict(
            publish='live512B source -> publish_data[32*i+:32] F32 little-endian lane i; owner46 allocated by actual issuer; private native64 tag/gen retained',
            grants='source_lease_reserved/workspace_reserved/issuer_namespace_reserved/issuer_binding_valid from real compiler/lease/allocation state',
            RF_ACK='internal actual W4 ACK_ID1; exact owner46/slot9 checked, both physical RF copies',
            RF_observe='rf_read_accepted/read_a/read_b, rf_response_accepted/response_a/response_b, rf_write_accepted/write_slot/write_owner, rf_ACK_accepted/ACK_owner/ACK_slot/ACK_fault',
            observe_rule='sample before actual clock edge; retain accepted read slots in simulator transaction context, not current control address at response',
            result='held4096F32 FMIN(FMAX(bitwise_NEG(gate),-87),88) -> actual PC40.exp.step2',
            reverse='matching owner55 child/parent/reverseCDC and held drain request/response + nine real allcopy flags',
            retire='done_valid/ready native64 ID match is fragment completion; sourceRF38 stays live until matching caller source_release55',
            admission='actual admission_stop/allcopy_fenced/reset authority; fault and ACK integration fault block normal progress'),
        fusion=dict(per_primitive_drop_in=False,
                    primitive_dispatch_requires='compiler-selected literal NEG/FMAX/FMIN fragment and matching source recipe/version/lease',
                    FMAX_reply='actual FMAX bytes may be captured on the RF19 response handshake before the FMIN consumer; never reply with the final FMIN bytes as FMAX',
                    FMIN_reply='actual held result bytes with matching fragment owner/context, not host arithmetic',
                    completion_rule='c128 per-primitive reply requires real matching completion/reverse; do not claim these from visibility or infer future RPC acceptance',
                    full_program_scope='other1737-PC primitives/page homes remain full-system dispatcher responsibility; selected module is not whole-program VM'),
        storage=dict(new_engine_FF=0,new_RF_macros=0,
                     existing_RF_macros=4*16*2,existing_RF_bytes=4*16*2*128*32,
                     observer_wires='simulation instrumentation, no extra hardware queues/state',
                     source_model='results/uarch/h4_hbm_pc40_native_ingress_20261003/model.json'),
        limitations=['finiteF32 selected arithmetic scope; nonfinite refusals retained',
                     'runtime-reset fault debt remains retained; no generic reset/rearm recovery proof',
                     'no actualpayload fullconnector runtime/whole token/SSFF/physical credit'])


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--filelist',type=Path);ap.add_argument('--binding',type=Path)
    a=ap.parse_args()
    if not (a.filelist or a.binding):ap.error('select --filelist or --binding')
    if a.filelist:
        with a.filelist.open('x') as f:f.write('\n'.join(str(ROOT/p) for p in FILES)+'\n')
    if a.binding:
        with a.binding.open('x') as f:json.dump(binding(),f,sort_keys=True,indent=2);f.write('\n')
