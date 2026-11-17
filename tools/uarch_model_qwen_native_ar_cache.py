#!/usr/bin/env python3
"""Before-RTL sizing for the optional native Qwen AR GO-phase cache."""
from __future__ import annotations
import json


def model(hr=None, ar=None, local=None):
    hr=list(range(12)) if hr is None else list(hr)
    if len(hr)!=12 or any(type(x)is not int or x<0 for x in hr):
        raise ValueError('twelve nonnegative integer HR receiver ages required')
    ar=[2*s for s in range(12)] if ar is None else list(ar)
    local=[0]*12 if local is None else list(local)
    if any(len(v)!=12 or any(type(x)is not int or x<0 for x in v) for v in (ar,local)):
        raise ValueError('twelve nonnegative integer AR/local receiver ages required')
    rel=[v-hr[0] for v in hr]
    rel_ar=[v-ar[0] for v in ar];rel_local=[v-local[0] for v in local]
    tau=max(rel[s]+rel_ar[s]+rel_local[s]-8*s for s in range(12))+2
    delays=[tau+8*s-rel[s]-rel_ar[s]-rel_local[s] for s in range(12)]
    if min(delays)<2 or max(delays)>65535:
        raise ValueError('phase cache needs2..65535 edges; this source profile is not representable')
    ff=379*2+12+12+16+1+1+1+4+4
    return dict(schema='opentallas.uarch.qwen-native-ar-go-cache.v1',status='BEFORE_RTL_CANDIDATE',
        function='Delay ONE O/down GO per slice, retain its entire IB, keep XPF field routing; no runtime queue.',
        source_scope='Current native input HR453: GO452, IB451:73, XPF72:1, valid0. Existing SID selects a common per-die phase vector.',
        selected_hr_receiver_ages=hr,selected_ar_receiver_ages=ar,selected_local_receiver_ages=local,tau=tau,go_delay_edges=delays,
        ar_role_predicate=dict(nout=4096,tiles=3,K=[2,6],wsrc=0,split=8,mmode=0,oen=1,amax=0),
        compute=dict(new_MACs_per_cycle=0,arithmetic_change=False,replicas=12),
        memory=dict(new_macros=0,new_bytes_per_cycle=0,mutable_ECC_change=False),
        boundaries=dict(HR_input_bits_per_cycle=453,HR_output_bits_per_cycle=453,
            input_or_output_required_tracks=453,proposed_M2_pitch_um=0.036,
            track_span_um=453*0.036,reservation_cross_section_um=30.24,
            retained_bits_per_transaction=379,sustained_XPF_passthrough_words_per_cycle=1,
            XPF_valid_law='out.outer_valid=raw.outer_valid|emit; out.XPFvalid=raw.outer_valid&raw.XPFvalid, preventing stale descriptor replay on emitted GO',
            GO_pending_transactions=1,second_GO_policy='fault and suppress, no queued retry'),
        registers=dict(IB_pipe=379,IB_hold=379,hold_enable_copies=12,emit_select_copies=12,counter=16,pending=1,
            emitted_GO=1,sticky_fault=1,transaction_SID=4,reset_relay_FF=4,per_slice=ff,die_total=12*ff,
            max_hold_enable_fanout=32,max_emit_select_fanout=32,max_control_reset_fanout=24,reset_only_control=True),
        combinational=dict(phase_map='12x16 constant source parameter:12onehot SIDcomparators each fanout<=16; SIDbit comparators<=12plusidentity/range, no wide binarymux selector',
            full_shape_decode='nout/tiles/K/wsrc/split/mmode/oen/amax',
            no_new_external_pins=True),
        area=dict(FF_proxy_um2_each=0.335,FF_proxy_um2_per_slice=ff*0.335,
            logic_proxy_um2_per_slice=120,cell_proxy_um2_per_slice=ff*0.335+120,
            die_cell_proxy_mm2=12*(ff*0.335+120)/1e6,
            proposed_standalone_unit_slot_um=[86.4,30.24],slot_area_um2=86.4*30.24,
            proxy_utilization=(ff*0.335+120)/(86.4*30.24),
            slot_scope='Self-contained candidate element reservation; no current die placement/fit or timing closure asserted.'),
        latency=dict(native_example_AR_spacing='HR hop1 + HGD step5 + AR hop2 =8 edges/slice',
            common_tau_edges=tau,other_matvec_added_edges=0,reset_release_edges=3,
            general_phase_rule='phi[s]=tau+8*s-relativeHR[s]-relativeAR[s]-relativeLocal[s]; tau=max(relativeHR+relativeAR+relativeLocal-8*s)+2',
            exact_compiler_rule='Apply this explicit HGD vector ONCE to AR head GO/read-end and tile/AR result dates. Do not multiply by flits or add native HR transport again.',
            token_aggregate=None),
        admission=dict(component_simulation_only=True,physical_build_ready=False,
            required_before_physical='Actual per-slice slot assignment/clock/reset/channel review and selected source/compiler profile.'),
        required_mechanism_proof=['Complete captured IB retained across intervening HR writes',
            'XPF/epoch/bank identity with two distinct finite vectors and current native head',
            'Minimum and maximum selected delay; no AR GO passes raw and no duplicate emitted GO',
            'Pending second GO, invalid SID/delay, reset, stale-IB and one-edge-short negative controls',
            'Default-off wire/cycle identity; QKV/GU/HEAD bypass the full AR predicate'])


if __name__=='__main__':
    print(json.dumps(model(),indent=2))
