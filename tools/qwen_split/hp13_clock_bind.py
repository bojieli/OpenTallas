"""Connect the selected two-clock TT source to explicit existing clock endpoints.

This constructs logical topology only. Regional phase, insertion and data landing
qualification remain the responsibility of the actual generated die chain.
"""
import os


def apply(model, buses, instances, tt_ports):
    if os.environ.get('OT_QWEN_HP13_CLOCKS', '0') != '1':
        return None
    for port in ('ck_core', 'ck_hr'):
        if tt_ports.get(port) != (1, 'input'):
            raise ValueError('HP13 clock binding: actual TT input differs: ' + port)
    groups = [g.split(',') for g in os.environ.get('OT_SPLIT_CK_COROOT', '').split(';')]
    if any('tt_ctlm' in g for g in groups):
        raise ValueError('HP13 clock binding: legacy first-clock TT co-root is forbidden')
    by = {i.name: i for i in instances}
    targets = {'ck_core': ('native59', 'ck'), 'ck_hr': ('dvs_W5', 'ck')}
    endpoints = list(targets.values()) + [('embed_prov', 'ck')]
    found = {}
    for endpoint in endpoints:
        rows = [(j, b) for j, b in enumerate(buses)
                if b[1] == 'clock_trunk' and endpoint in b[3]]
        if len(rows) != 1 or rows[0][1][2] != 1:
            raise ValueError('HP13 clock binding: actual receiving root is not unique: ' + str(endpoint))
        j, b = rows[0]
        if len(b[3]) < 2 or tuple(b[3][0]) == endpoint:
            raise ValueError('HP13 clock binding: missing actual clock driver: ' + str(endpoint))
        found[endpoint] = (j, b)
    domains = {n: by[n].domain for n, _ in endpoints}
    if any(not isinstance(d, str) or not d for d in domains.values()):
        raise ValueError('HP13 clock binding: actual functional clock family is missing: ' + str(domains))
    if len(set(domains.values())) != 1:
        raise ValueError('HP13 clock binding: selected 1:1 functional clock families disagree: ' + str(domains))
    core = found[targets['ck_core']][1]
    hr = found[targets['ck_hr']][1]
    embed = found[('embed_prov', 'ck')][1]
    if core[0] != embed[0]:
        raise ValueError('HP13 clock binding: native and embedding core roots differ')
    if core[3][0][0] != hr[3][0][0]:
        raise ValueError('HP13 clock binding: selected roots have different actual clock producers')
    if any(i == 'tt_ctlm' for b in buses if b[1] == 'clock_trunk' for i, _ in b[3]):
        raise ValueError('HP13 clock binding: TT clock endpoint already exists')
    record = dict(kind='same_pll_fixed_phase', ratio=[1, 1], phase_ps=0,
                  physical_phase_status='UNMEASURED', domains=domains, pins={})
    for port, endpoint in targets.items():
        j, b = found[endpoint]
        current = buses[j]
        buses[j] = (current[0], current[1], current[2], list(current[3]) + [('tt_ctlm', port)])
        record['pins'][port] = dict(receiver=list(endpoint), bus=b[0], driver=list(b[3][0]))
    model['hp13_clock_bind'] = record
    print('HP13_CLOCK_BIND', record, flush=True)
    return record
