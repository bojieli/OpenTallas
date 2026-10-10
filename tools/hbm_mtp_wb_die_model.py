"""Model-first low-spine native MTP/WB integration reservation for R25I."""
from hbm_mtp_native_contract import model as mtp_model


def model(root=None):
    mtp = mtp_model(root)
    return dict(schema='opentallas.hbm-mtp-wb-die.v1', adopted=False,
        default_enabled=False, base_variant='r25i',
        replicas=dict(MTP=1, WB=1, physical_stacks=4),
        slots=dict(mtp_um=[466.56,200.88], kvwb_um=[300.24,241.92]),
        clock_domains=dict(mtp='stream_1p2', kvwb='stream_1p2', service='HBM native clock'),
        MTP=mtp,
        WB=dict(source='eb4c566ed ot_hbm_kvwb_hub_sram full-shape successor',
            MACs_per_cycle=0, bytes_per_cycle_row_input=32,
            producer_bits=258, credit_return_bits=1,
            service_bits_per_stack=292, service_return_bits_per_stack=16,
            control_output_bits=34, die_identity_bits=7,
            SRAM_master='ot_sram_1r1w_128x256_m1_r2c2', SRAM_macros=2,
            raw_macro_area_um2=2*94.824*41.04,
            mutable_control_FF_upper=24000,
            FF_cell_floor_um2=24000*0.2916,
            slot_capacity_um2_at_55pct=300.24*241.92*.55,
            route_fit_qualified=False,
            producer_identity='actual quantized row serializer required; no unpriced four-quarter fan-in',
            service_identity='four independent native stack sector endpoints and Gray completion counts',
            shadow_handshake='hold sh_v/slot/data until sh_r; no single-cycle preload pulse'),
        native_loader=dict(ND=1, ADDR_W=37, request_bits=344, response_bits=275,
            formatter_location='service landing', endpoint_ownership='single per-die transaction owner',
            not_yet_installed=True),
        routing=dict(MTP_signal_tracks=sum(g['bits'] for g in mtp['groups'].values()),
            WB_signal_tracks=258+1+4*292+4*16+34+7,
            channel_capacity_qualified=False),
        latency=dict(MTP_facade_extra_cycles=0, WB_preload_sectors=17,
            WB_shadow_extra_cycles='actual ready/sector credit and fence measurement required',
            native_loader='boot/readback only, no claimed per-token gain'),
        qualification='native slot and pin reservations only; producer joins, real views and die routing required')
