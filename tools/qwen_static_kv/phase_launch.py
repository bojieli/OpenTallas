"""Exact digital edge law of qkd_static_kv_phase_launch; physical data mandatory."""

def launch(core_capture,*,core_origin_u,hbm_origin_u,ph0,safe_low_u,safe_high_u,meta_hold_core,first_active_hbm):
    vals=(core_capture,core_origin_u,hbm_origin_u,ph0,safe_low_u,safe_high_u,meta_hold_core,first_active_hbm)
    if any(type(v)is not int for v in vals):raise ValueError('explicit integer actual phase profile required')
    if core_capture<0 or not 0<=ph0<768 or not 0<safe_low_u<=safe_high_u<768 or not 6<=meta_hold_core<=255:
        raise ValueError('unsafe or missing actual phase/hold profile')
    # Toggle is1 edge after the input was sampled. First HBM sample is strictly
    # later than that launch; coincident launch/capture is never presumed safe.
    toggle_core=core_capture+1;toggle_u=core_origin_u+625*toggle_core
    first_hbm=(toggle_u-hbm_origin_u)//768+1
    if first_hbm<first_active_hbm:raise ValueError('launch precedes actual destination reset release')
    first_u=hbm_origin_u+768*first_hbm;gap=first_u-toggle_u
    phase_gap=(ph0-625*toggle_core)%768
    phase_gap=phase_gap or 768
    if phase_gap!=gap:raise ValueError('actual core/HBM reset/PLL phase origin disagrees with PH0')
    if not safe_low_u<=gap<=safe_high_u:raise ValueError('compiled launch violates measured setup/hold phase window')
    return dict(toggle_core=toggle_core,first_hbm=first_hbm,output_hbm=first_hbm+2,
                output_u=first_u+2*768,metadata_consumer_hbm=first_hbm+3,gap_u=gap,
                native_qualified=False,physical_qualified=False)
