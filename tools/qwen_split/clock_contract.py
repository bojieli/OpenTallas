"""Source-graph clock identities; physical intent is never clock-generation proof."""
from collections import defaultdict
import hashlib
from pathlib import Path


def build(model, root):
    by = {i.name: i for i in model['insts']}
    joins = model.get('port_join', {})
    ports = defaultdict(set)
    nets = []
    for bid, cl, bits, endpoints in model['buses']:
        if cl != 'clock_trunk':
            continue
        if bits != 1 or len(endpoints) < 2:
            raise ValueError(f'{bid}: clock trunk must be one bit with a source and sinks')
        for inst, port in endpoints[1:]:
            master = by[inst].master
            ports[master].add(joins.get(master, {}).get(port, (port, []))[0])
        nets.append(bid)
    production = model.get('native_static_io_bind', {})
    related = []
    periods = dict(stream=2500.0/3, serial=10000.0/9, ucie=1000.0, serdes=1000.0)
    if production:
        # Actual r10 source documents B(m)=F(5m)=C(6m). No async or
        # multicycle exception may replace these ordinary timing relations.
        periods['coll_blk'] = 5000.0
        related = [['stream', 'ucie', 'coll_blk']]
        if 'clk_coll_blk' not in nets:
            raise ValueError('r10 collective is missing its real 200 MHz clock trunk')
    path = Path(root) / 'rtl/physical/ot_qfd_ucie_six_five.sv'
    return dict(schema='opentallas.qwen-source-clock-contract.v1',
                clock_ports={m: sorted(ps) for m, ps in sorted(ports.items())},
                clock_trunks=sorted(nets), periods_ps=periods, related_domains=related,
                source=str(path.relative_to(root)), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                phase_ps={d: 0.0 for group in related for d in group},
                clock_generation='OPEN: real common-PLL/divider implementation and physical delivery required',
                qualification=False)
