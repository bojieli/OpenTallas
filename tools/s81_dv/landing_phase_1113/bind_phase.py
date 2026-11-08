"""Conditional final landing law; callers must book actual source/clock epochs."""
PERIOD_FS=833000
LANDING_SHA='2f223b19bc4d65333738a9bf6f7df2829618b60c110003b763eb01f7b99b5d2c'
RING_SHA='72750a546e10260ec6fa1e8ec69f34ae29302c5362eb3baa4df72bf28bd29396'


def consumer_observation(book,source_sampling_edge):
    required=('source_rise_epoch_fs','core_rise_epoch_fs','phase_guard_fs',
              'receiver_ready_core_edge','source_register_identity','consumer_register_identity',
              'bound_top_sha256','source_reference','W','WNEG','FREG',
              'period_fs','landing_sha256','ring_sha256')
    if any(k not in book for k in required):
        raise ValueError('actual phase/epoch/source booking missing')
    if book['period_fs']!=PERIOD_FS or book['WNEG']!=1 or book['FREG']!=0 or book['W'] not in (46,177):
        raise ValueError('selected source landing profile differs')
    if book['landing_sha256']!=LANDING_SHA or book['ring_sha256']!=RING_SHA:
        raise ValueError('actual captured landing/ring source differs')
    if book['source_reference']!='cland_input_source_register_sampling':
        raise ValueError('HWIN/declared lane count is not the final landing input epoch')
    for k in ('source_register_identity','consumer_register_identity','bound_top_sha256'):
        if not book[k]:raise ValueError('actual source/consumer identity missing')
    for k in ('source_rise_epoch_fs','core_rise_epoch_fs','phase_guard_fs','receiver_ready_core_edge'):
        if not isinstance(book[k],int):raise ValueError('booked clock/ready dates must be integer fs/edges')
    phi=(book['core_rise_epoch_fs']-book['source_rise_epoch_fs'])%PERIOD_FS
    guard=book['phase_guard_fs']
    if guard<=0 or not guard<phi<PERIOD_FS-guard:
        raise ValueError('phase lies in unqualified coincidence/uncertainty envelope')
    t=book['source_rise_epoch_fs']+source_sampling_edge*PERIOD_FS+3*PERIOD_FS+phi
    edge=(t-book['core_rise_epoch_fs'])//PERIOD_FS
    if edge<=book['receiver_ready_core_edge']:
        raise ValueError('consumer event is not after actually observed readiness')
    return dict(consumer_output_visible_after_core_edge=edge,observation_time_fs=t,
        source_to_consumer_age_fs=3*PERIOD_FS+phi,phase_fs=phi,
        scope='FINAL_LANDING_SOURCE_REGISTER_TO_CONSUMER_REGISTER_ONLY',
        physical_phase_timing_qualified=False,
        reset_boundary_note='seqhost raw36 and published tap44 remain distinct source-relative declarations; neither is an absolute epoch here')
