"""Opt-in record transport ports, using the actual ot_hgi_seq ABI.

This declares the die graph, never fabricates an engine adapter or a closure.
The generic functional-binding preflight must pass before implementation/adoption.
"""
from math import ceil

# Exact bit order in a per-unit record bus, low bit first.
RECORD_FIELDS = [('valid', 1), ('header', 128), ('sut', 256), ('descriptors', 1024)]
RETURN_FIELDS = [('ready', 1), ('done', 1), ('fault', 1)]
UNIT_CODES = {'quant': 4, 'coll': 6}


def layout(fields):
    offset, rows = 0, []
    for name, bits in fields:
        rows.append({'name': name, 'lo': offset, 'hi': offset + bits})
        offset += bits
    return rows, offset


def transport_model(hub, units, reach_um=504.0):
    commands, cbits = layout(RECORD_FIELDS)
    returns, rbits = layout(RETURN_FIELDS)
    source = hub['cmdproc']
    rows = []
    for unit in units:
        if unit not in UNIT_CODES or unit not in hub:
            raise ValueError(f'no installed HGI record consumer: {unit}')
        sink = hub[unit]
        distance = abs(source.x + source.w / 2 - sink.x - sink.w / 2) + abs(source.y + source.h / 2 - sink.y - sink.h / 2)
        minimum_relays = max(0, ceil(distance / reach_um) - 1)
        rows.append(dict(unit=unit, code=UNIT_CODES[unit], replicas=1, command_bits=cbits,
                         return_bits=rbits, bits_per_dispatch=cbits + rbits,
                         fp32_macs_per_cycle=0, memory_bytes_per_cycle=0,
                         requested_records_per_cycle=1, two_tracks_per_bit=2 * (cbits + rbits),
                         centre_distance_um=distance, minimum_relay_edges=minimum_relays,
                         minimum_return_round_trip_edges=2 * minimum_relays,
                         command_fields=commands, return_fields=returns,
                         readiness='DECLARED_GRAPH_ONLY_ADAPTER_AND_FINITE_FLOW_REQUIRED'))
    return dict(schema='opentallas.hgi_die_record_transport_model.v1',
                source_abi='ot_hgi_seq: u_v, d_hdr, d_sut, d_desc / u_rdy,u_done,u_fault',
                scope='lower bounds: actual pin routes, finite flow and full field adapters unqualified',
                units=rows, total_added_signal_bits=sum(r['bits_per_dispatch'] for r in rows),
                added_area_mm2=None, reticle_fit=None,
                physical_ready=False)


def install(model, buses, paths, units):
    """Declare actual source ABI fields; no static ties, local cfg shifts or folds."""
    hub = model['hub']
    from uarch_model import hgi_die_record_transport_model
    record = hgi_die_record_transport_model(hub, units)
    names = {b[0] for b in buses}
    for row in record['units']:
        unit = row['unit']
        cp, peer = hub['cmdproc'].name, hub[unit].name
        for direction, bits, endpoints in (
            ('cmd', row['command_bits'], [(cp, f't_hgi_{unit}'), (peer, 'f_hgi_cmdproc')]),
            ('ret', row['return_bits'], [(peer, 't_hgi_cmdproc'), (cp, f'f_hgi_{unit}')])):
            name = f'hgi_{unit}_{direction}'
            if name in names:
                raise ValueError(f'duplicate generic record bus {name}')
            buses.append((name, 'hub', bits, endpoints))
            paths[name] = [name]
            names.add(name)
    model['hgi_record_transport'] = record
    model['notes'].append('HGI record ports are opt-in graph declarations; finite-flow adapters, actual record consumers, field decode and physical qualifications remain required. No generic-die completion is claimed.')
