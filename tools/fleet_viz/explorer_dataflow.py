"""Source-bound bus overlays. A port width is not a scheduled bandwidth.

Endpoints are undirected unless explicitly declared by a source exporter. Geometry
centres are inspection aids, never routed wire shapes or pin timing evidence.
"""
import math

SCHEMA = 'opentallas.explorer.dataflow.v1'
CONTROL_CLASSES = {'clock_trunk', 'reset', 'clock', 'rst'}


def width(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def model_connections(model):
    """Keep raw recipe IDs and ports before geometry compression loses them."""
    out = []
    for ordinal, bus in enumerate(model.get('buses', [])):
        if not isinstance(bus, (list, tuple)) or len(bus) < 4:
            continue
        bid, cls, bits, endpoints = bus[:4]
        out.append(dict(id=str(bid), kind='ported_bus', bus_class=str(cls),
                        width_bits=width(bits), endpoints=[
                            dict(instance=str(e[0]), port=str(e[1]) if len(e) > 1 else None)
                            if isinstance(e, (list, tuple)) else dict(instance=str(e), port=None)
                            for e in endpoints], ordinal=ordinal))
    return out


def dataflow(geometry, safe=False):
    """Export exact-name geometry bindings; unknown endpoints remain visible.

    Cached v1 geometries omit IDs/ports and truncate broadcasts. Such records are
    explicitly marked legacy and omitted endpoints counted, not reconstructed.
    """
    inst = geometry.get('inst', {})
    names = inst.get('name', [])
    by_name = {name: i for i, name in enumerate(names)}
    source = dict(commit=geometry.get('commit'), recipe_key=geometry.get('key'),
                  kind='recipe_model_bus' if 'dataflow_connections' in geometry else 'legacy_compressed_bus')
    classes = geometry.get('bus_classes', [])
    records = geometry.get('dataflow_connections')
    omitted = 0
    if records is None:
        records = []
        for i, bus in enumerate(geometry.get('buses', [])):
            if not isinstance(bus, list) or len(bus) < 3:
                continue
            cls, bits, ids = bus[:3]
            eps = []
            for index in ids:
                if isinstance(index, int) and 0 <= index < len(names):
                    eps.append(dict(instance=names[index], index=index, port=None))
                elif isinstance(index, int) and index < 0:
                    omitted += max(0, -index - len(eps))
            records.append(dict(id='legacy-bus-%d' % i, bus_class=classes[cls] if isinstance(cls, int) and 0 <= cls < len(classes) else 'unknown',
                                kind='ported_bus', width_bits=width(bits), endpoints=eps))
    edges = []
    unresolved = known_width = controls = 0
    for record in records:
        if record.get('kind') == 'dependency':
            continue
        cls = record.get('bus_class', 'unknown')
        if cls in CONTROL_CLASSES:
            controls += 1
            continue
        eps = []
        for endpoint in record.get('endpoints', []):
            name = endpoint.get('instance')
            index = by_name.get(name)
            # Cached indices are accepted only if they still name this instance.
            point = None
            if index is not None:
                try:
                    point = [inst['x'][index] + inst['w'][index] / 2,
                             inst['y'][index] + inst['h'][index] / 2]
                    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point):
                        point = None
                except (KeyError, IndexError, TypeError):
                    pass
            if point is None:
                unresolved += 1
            eps.append(dict(instance=('instance-%d' % index if index is not None else None) if safe else name,
                            index=index, port=None if safe else endpoint.get('port'), point=point,
                            point_kind='instance_center_not_route' if point else 'unmapped', role='unknown'))
        bits = width(record.get('width_bits'))
        known_width += bits is not None
        first = eps[0] if eps else {}
        second = eps[1] if len(eps) > 1 else {}
        edges.append(dict(id='bus-%d' % len(edges) if safe else record.get('id'), kind='ported_bus',
                          label=cls, bus_class=cls, src=first.get('instance'), dst=second.get('instance'),
                          src_index=first.get('index'), dst_index=second.get('index'),
                          **{'from': first.get('point'), 'to': second.get('point')}, endpoints=eps,
                          width_bits=bits, direction='unknown', directed=False,
                          required_bps=None, capacity_bps=None, bytes=None, cycles=None, clock_hz=None,
                          critical=None, start=None, end=None,
                          geometry_kind='instance_center_not_route', source=None if safe else source['kind']))
    return dict(schema=SCHEMA, die=geometry.get('die'), edges=edges,
                provenance={} if safe else source,
                coverage=dict(connections=len(edges), known_width=known_width,
                              unknown_width=len(edges)-known_width, unresolved_endpoints=unresolved,
                              omitted_broadcast_endpoints=omitted, filtered_control_buses=controls,
                              directed_connections=0, known_bandwidth=0,
                              token_mapping='unavailable', geometry='instance_centers_not_routes',
                              source_scope='cached_recipe_geometry',
                              note='Bus widths are physical interface widths, not bytes per token or scheduled bandwidth. Endpoint order does not prove direction.'))
