"""Actual R8 BC4 epoch law: explicit sampling-edge origin, no package epoch guess."""
def bind_image_profile(image_profile, selected_profile):
    if image_profile != selected_profile:
        differing=sorted(k for k in image_profile if image_profile[k]!=selected_profile.get(k))
        raise ValueError('selected image/profile mismatch: '+','.join(differing))
    return dict(selected_profile)

def epoch_calendar(forward_epoch_sampling_edge, profile, *, rf=False):
    if type(forward_epoch_sampling_edge) is not int or forward_epoch_sampling_edge<0:
        raise ValueError('actual original D2D public fwd_epoch sampling edge required')
    # R8 wires u_dcal.epoch_go <- D2D.fwd_epoch, halt <- epoch_abort.
    # RF adds one output capture before BC4 and one control-input capture after it.
    # This says nothing about when the native D2D creates fwd_epoch from a package event.
    n=forward_epoch_sampling_edge
    before=int(rf);after=int(rf)
    dcal=n+before
    source=dict(admission=dcal+profile['ADM_OFS']+4,
                token_base_tx=dcal+profile['ADM_OFS']+profile['ADM_LEN']+4,
                token_base_rx=dcal+profile['ADM_OFS']+profile['ADM_LEN']+5,
                first_token=dcal+profile['FIRST_OFS']+3)
    receiver={k:v+after for k,v in source.items()}
    if receiver['first_token']-receiver['token_base_rx']<2:
        raise ValueError('native runtime CFG settle violated')
    return dict(original_forward_epoch_sampling_edge=n,dcal_epoch_sampling_edge=dcal,
                source_control_events=source,d2d_control_sampling_events=receiver,
                feedback_output_capture=before,control_input_capture=after,
                cfg_settle_edges=receiver['first_token']-receiver['token_base_rx'],
                global_package_epoch_bound=False,production_qualified=False)
