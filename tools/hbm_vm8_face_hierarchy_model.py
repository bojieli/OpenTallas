"""Size real SE-n face relay hierarchy before RTL or physical builds."""

def model():
    widths_in = [2264, 2256, 2264, 2256, 1078]
    widths_out = [2264, 2256, 2264, 2256, 3855]
    bank = 128
    ni = sum((w + bank - 1)//bank for w in widths_in)
    no = sum((w + bank - 1)//bank for w in widths_out)
    # Fixed full128-bit hardened views: padding is priced as real storage.
    ff = ni*bank + no*bank*3
    return dict(schema='opentallas.hbm.vm8.face_hierarchy.v1',
        source='physical/hbm_accel_die_views/vm/split8/hfd_vm_se_n.sv',
        failure_source='f6bc7c10baa9191e33c65b22f242b5848bfa6c68',
        default_enabled=False, adopted=False, MACs_per_cycle=0,
        compute_intensity=0, memory_bytes_per_cycle=96,
        input_capture=dict(widths=widths_in, bank_bits=bank, banks=ni, cycles=1),
        output_relay=dict(widths=widths_out, bank_bits=bank, banks=no, cycles=3),
        replicas=ni+no, register_bits=ff,
        storage_macro_count=3,
        storage_macro='ot_sram_1r1w_128x256_m1_r2c2',
        leaf_boundary_bits_per_cycle=256,
        parent_boundary_bits_per_cycle=sum(widths_in)+sum(widths_out),
        routing_tracks_required_per_leaf=256,
        channel_capacity_tracks=None,
        mux_demux_cost='static128-bit slices; final bank padded, no run-time mux',
        fanout_cost='one source clock distribution into184 real leaf clocks; '
            'each leaf local CTS covers128 or384FF, not one giant flat tree',
        leaf_area_floor_um2=dict(input_ff=128*.2916, output_ff=384*.2916),
        provisional_leaf_geometry_um=[64,64],
        leaf_pin_budget='128 input and128 output pins on opposite faces; '
            '64um side at0.48um pitch, actual layer/pin legality must be measured',
        leaf_slot_area_um2=(ni+no)*64*64,
        parent_floorplan_candidate_um=[1600,1000],
        parent_target_utilization=.55, actual_slot_fit=False,
        latency_cycles=dict(input=1, output=3, added_vs_f3_face_chain=0),
        token_latency='Preserve every original per-bit f3 pipeline path; '
            'macro read paths and duplicated seam data require actual fullshape '
            'alignment gate, no uniform token +0 claim until that passes',
        clocks=dict(period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        physical_method='Harden full128-bit D1 andD3 relay elements, '
            'then assemble real abstract instances and three SRAM macros hierarchically',
        dependencies=['Claude review before physical route',
            'current actual die slot and fullpin clock budgets',
            'real relay leaf SS/FF/DRC qualification and CTS arrival',
            'finite VM command/read protocols remain original, no protection bypass',
            'actual complete per-bit same-face/seam/macro-read exactness'],
        functional_qualified=False,physical_qualified=False,headline_credit=False)
