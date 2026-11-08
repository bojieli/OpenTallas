"""Actual eight-row native HWIN output ledger, in input-sampling edge units.

Consumes the selected source's decoded boot rows and real KS descriptors. It
never chooses resource allocations, clocks, resets, KS dates or consumer dates.
"""

SOURCE = 'rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv'
MEASURED_SOURCE_SHA256 = 'fe83722aed98be5c319ebc7c2b63514b75016add0dfa7522e878c907f6bfee49'
ENDPOINTS = ('s_7N', 's_7S', 's_0N', 's_0S')


def event_ledger(mu, descriptor, ks_sampling_edge):
    """Predict actual output pins after the native HWIN output register.

    For KS sampled at N, table records at N+1. Configured event delay D is
    relative to that record; mu_c/mu_rc are visible after edge N+D+1. This is
    distinct from a driving-NBA pin-event convention, which adds another edge.
    """
    if mu.get('selected_params') != dict(HOSTB_ENABLE=0, STATIC_KS6=0, STATIC_KS_SPAN=0, STATIC_KS_GRAPH_TAG=0, FMUT=0):
        raise ValueError('selected direct source variant required; no HBE/static/RF input delay inferred')
    if mu.get('hwin_source_sha256') != MEASURED_SOURCE_SHA256:
        raise ValueError('actual HWIN timing source differs from measured full47/eight-row vehicle')
    if type(ks_sampling_edge) is not int or ks_sampling_edge < 0:
        raise ValueError('actual KS input sampling edge required')
    for name, width in (('user', 10), ('position', 21)):
        if type(descriptor.get(name)) is not int or not 0 <= descriptor[name] < 1 << width:
            raise ValueError('actual KS '+name+' descriptor required')
    relative = ks_sampling_edge - mu['first_KS_seq_capture']
    if relative < 0 or relative % mu['period'] not in mu['slot_offsets']:
        raise ValueError('KS lies outside actual armed MU slot calendar')
    slot = mu['slot_offsets'].index(relative % mu['period'])
    rows = mu.get('hwin_events')
    if not isinstance(rows, list) or len(rows) != 8:
        raise ValueError('all eight decoded actual HWIN rows required')
    events = []
    for index, row in enumerate(rows):
        kind, endpoint, delay = row['kind'], row['endpoint'], row['delay']
        if kind not in (0, 1) or type(endpoint) is not int or endpoint not in range(4):
            raise ValueError('actual HWIN event kind/endpoint malformed')
        if type(delay) is not int or not len(mu['slot_offsets'])+2 <= delay <= mu['return_latency']-2:
            raise ValueError('actual HWIN event delay outside selected table lifetime')
        if len(row['attributes']) != len(mu['slot_offsets']):
            raise ValueError('actual HWIN event does not cover every used slot')
        attr = row['attributes'][slot]
        if any(type(attr.get(k)) is not int or attr[k] not in (0, 1) for k in ('ab', 'land')):
            raise ValueError('actual HWIN copy/replay bits malformed')
        if kind == 1 and not attr['land']:
            continue
        payload = ((descriptor['position'] << 13) | (descriptor['user'] << 3) |
                   (attr['land'] << 2) | (attr['ab'] << 1) | 1) if kind == 0 else (descriptor['user'] << 1) | 1
        events.append(dict(event=index, kind=kind, endpoint=endpoint, endpoint_name=ENDPOINTS[endpoint],
                           output='mu_c' if kind == 0 else 'mu_rc', slot=slot,
                           pin_visible_after_edge=ks_sampling_edge+delay+1,
                           user=descriptor['user'], position=descriptor['position'],
                           ab=attr['ab'], land=attr['land'], payload=payload))
    return dict(schema='opentallas.s81.native_hwin_event_ledger.v1', events=events,
                KS_input_sampling_edge=ks_sampling_edge, slot=slot,
                clock_reset_identity=mu['clock_reset_identity'],
                source_sha256=mu['hwin_source_sha256'],
                RX_sampling_first=ks_sampling_edge+1,
                RX_sampling_last=ks_sampling_edge+mu['return_latency']-1,
                production_consumer_booked=False)


def check_consumer_book(ledger, book, resource):
    """Match actual source events to explicit parent resource/consumer dates."""
    if book is None:
        return [dict(cause='native_HWIN_consumer_event_book_missing', resource=list(resource),
                     required_events=len(ledger['events']))]
    if book.get('schema') != 'opentallas.s81.native_hwin_consumer_booking.v1':
        return [dict(cause='native_HWIN_consumer_event_book_schema')]
    if book.get('clock_reset_identity') != ledger['clock_reset_identity'] or book.get('resource') != list(resource):
        return [dict(cause='native_HWIN_consumer_clock_or_resource_mismatch')]
    actual = book.get('events')
    if not isinstance(actual, list) or len(actual) != len(ledger['events']):
        return [dict(cause='native_HWIN_consumer_event_count_mismatch')]
    if len({e.get('event') for e in actual}) != len(actual):
        return [dict(cause='native_HWIN_consumer_event_repeated')]
    expected = {e['event']: e for e in ledger['events']}
    problems = []
    for row in actual:
        source = expected.get(row.get('event'))
        if source is None or any(row.get(k) != v for k, v in source.items()):
            problems.append(dict(cause='native_HWIN_source_pin_identity_or_date_mismatch', event=row.get('event')))
            continue
        edge, transit = row.get('consumer_sampling_edge'), row.get('transport_edges')
        if (type(transit) is not int or transit < 1 or type(edge) is not int or
                edge != source['pin_visible_after_edge']+transit or not row.get('consumer_source')):
            problems.append(dict(cause='native_HWIN_consumer_transport_booking_missing_or_mismatched', event=row['event']))
    return problems


def check_rx_return(ledger, returned, descriptor):
    """Check actual sampled mu_rt identity while its start entry is live."""
    edge = returned.get('input_sampling_edge')
    return (type(edge) is int and ledger['RX_sampling_first'] <= edge <= ledger['RX_sampling_last'] and
            returned.get('user') == descriptor['user'] and returned.get('position') == descriptor['position'])
