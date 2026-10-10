"""Record Q14 omissions and reject unclassified ports on RTL-bound masters."""

CLASSES = frozenset(('test', 'debug', 'by_design'))


class PortBindingError(ValueError):
    def __init__(self, message, ledger):
        super().__init__(message)
        self.ledger = ledger


def audit_dropped_ports(masters, used, *, strict=False, bound_masters=None, exemptions=None):
    """Return a deterministic ledger before the caller deletes abstract pins.

    A strict recipe must name its RTL-bound masters. Exemptions are keyed by
    ``master.port`` and contain both a class and an explicit reason. The guard
    validates every exemption, including ones that are not used in this case.
    """
    exemptions = exemptions or {}
    if strict and bound_masters is None:
        raise ValueError('strict_ports requires rtl_bound_masters from the recipe bindings')
    bound = set(bound_masters or ())
    for key, value in exemptions.items():
        if not isinstance(value, dict) or value.get('class') not in CLASSES or not \
                isinstance(value.get('reason'), str) or not value['reason'].strip():
            raise ValueError(f'{key}: port exemption needs test/debug/by_design class and reason')
    rows, failures = [], []
    for name, master in sorted(masters.items()):
        for port in sorted(set(master.order) - set(used.get(name, ()))):
            spec = master.ports[port]
            key = f'{name}.{port}'
            row = dict(master=name, port=port, bits=spec[1], rtl_bound=name in bound,
                       disposition='unclassified', reason='no die bus reaches this abstract port')
            if key in exemptions:
                row.update(disposition=exemptions[key]['class'], reason=exemptions[key]['reason'])
            rows.append(row)
            if strict and name in bound and key not in exemptions:
                failures.append(key)
    if failures:
        raise PortBindingError('strict_ports: functional ports have no die net: ' + ', '.join(failures), rows)
    return rows
